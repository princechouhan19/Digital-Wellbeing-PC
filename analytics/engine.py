from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from database.models import DailyStat
from database.repository import Repository
import math


@dataclass
class PeriodSummary:
    total_screen_time_s: float
    active_time_s: float
    idle_time_s: float
    average_daily_s: float
    longest_session_s: float
    longest_session_app: Optional[str]
    top_apps: List[dict]
    category_breakdown: List[dict]
    days_tracked: int


@dataclass
class DailyPoint:
    day: str
    active_s: float
    idle_s: float


@dataclass
class FlowBlock:
    start: datetime
    end: datetime
    duration_s: float
    primary_app: str
    apps: List[str]

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "duration_s": self.duration_s,
            "primary_app": self.primary_app,
            "apps": self.apps,
        }


FLOW_CATEGORIES = ("Programming", "Productivity", "Education")
FLOW_MIN_DURATION_S = 45 * 60
FLOW_MAX_GAP_S = 120.0


class AnalyticsEngine:
    def __init__(self) -> None:
        self._repo = Repository()

    def get_today_summary(self) -> PeriodSummary:
        today = date.today()
        return self._build_summary(today, today)

    def get_week_summary(self) -> PeriodSummary:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        return self._build_summary(start, today)

    def get_month_summary(self) -> PeriodSummary:
        today = date.today()
        start = today.replace(day=1)
        return self._build_summary(start, today)

    def get_custom_summary(self, start: date, end: date) -> PeriodSummary:
        return self._build_summary(start, end)

    def _build_summary(self, start: date, end: date) -> PeriodSummary:
        top_apps = self._repo.get_top_apps_for_range(start, end, limit=100)
        category_breakdown = self._repo.get_category_breakdown_for_range(start, end)
        daily_totals = self._repo.get_daily_totals_for_range(start, end)
        longest = self._repo.get_longest_session_for_range(start, end)

        total_active = sum(d["active_s"] for d in daily_totals)
        total_idle = sum(d["idle_s"] for d in daily_totals)
        days = (end - start).days + 1
        avg_daily = total_active / max(len(daily_totals), 1)

        return PeriodSummary(
            total_screen_time_s=total_active + total_idle,
            active_time_s=total_active,
            idle_time_s=total_idle,
            average_daily_s=avg_daily,
            longest_session_s=longest.duration_s if longest else 0.0,
            longest_session_app=longest.process_name if longest else None,
            top_apps=top_apps,
            category_breakdown=category_breakdown,
            days_tracked=len(daily_totals),
        )

    def get_daily_chart_data(self, start: date, end: date) -> List[DailyPoint]:
        rows = self._repo.get_daily_totals_for_range(start, end)
        points: List[DailyPoint] = []

        current = start
        row_map = {r["day"]: r for r in rows}
        while current <= end:
            key = current.strftime("%Y-%m-%d")
            row = row_map.get(key)
            points.append(DailyPoint(
                day=key,
                active_s=row["active_s"] if row else 0.0,
                idle_s=row["idle_s"] if row else 0.0,
            ))
            current += timedelta(days=1)
        return points

    def get_hourly_chart_data(self, target_date: date) -> List[dict]:
        rows = self._repo.get_hourly_breakdown_for_date(target_date)
        hour_map = {r["hour"]: r["total_s"] for r in rows}
        return [
            {"hour": f"{h:02d}:00", "total_s": hour_map.get(f"{h:02d}", 0.0)}
            for h in range(24)
        ]

    # ─── Attention quality: fragmentation + flow ────────────────────────────

    def get_focus_fragmentation(self, target_date: Optional[date] = None) -> dict:
        """Task-switch frequency per hour for a day.

        A "switch" is a new non-idle app session starting in that hour. The
        fragmentation index is switches per active hour; the hourly series is
        what the Insights chart renders.
        """
        target_date = target_date or date.today()
        sessions = [
            s
            for s in self._repo.get_sessions_for_date(target_date)
            if not s.is_idle and s.duration_s > 0
        ]
        sessions.sort(key=lambda s: s.start_time)

        buckets = [
            {"hour": f"{hour:02d}:00", "switches": 0, "active_s": 0.0}
            for hour in range(24)
        ]

        for session in sessions:
            if not (0 <= session.start_time.hour < 24):
                continue
            buckets[session.start_time.hour]["switches"] += 1

            # Split the session across hour boundaries so long sessions do not
            # inflate a single hour's active time.
            cursor = session.start_time
            remaining = float(session.duration_s)
            guard = 0
            while remaining > 0.5 and guard < 48:
                guard += 1
                hour_end = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                chunk = min(remaining, max(0.0, (hour_end - cursor).total_seconds()))
                if chunk <= 0:
                    break
                if 0 <= cursor.hour < 24:
                    buckets[cursor.hour]["active_s"] += chunk
                remaining -= chunk
                cursor = hour_end

        total_active = sum(b["active_s"] for b in buckets)
        total_switches = sum(b["switches"] for b in buckets)
        active_hours = max(total_active / 3600.0, 0.25)
        peak = max(buckets, key=lambda b: b["switches"])

        return {
            "date": target_date,
            "hourly": buckets,
            "total_switches": total_switches,
            "active_hours": round(active_hours, 2),
            "fragmentation_index": round(total_switches / active_hours, 2),
            "peak_hour": peak["hour"],
            "peak_switches": peak["switches"],
        }

    def get_flow_analytics(self, days: int = 7, end_date: Optional[date] = None) -> dict:
        """Sustained >=45-minute productive runs (gaps <=2 minutes merged)."""
        today = end_date or date.today()
        start = today - timedelta(days=max(1, days) - 1)
        sessions = [
            s
            for s in self._repo.get_sessions_for_range(start, today)
            if s.duration_s > 0
        ]
        sessions.sort(key=lambda s: s.start_time)

        blocks: List[FlowBlock] = []
        current = None
        current_apps: dict[str, float] = {}

        def flush():
            nonlocal current, current_apps
            if current is None:
                return
            duration = (current["end"] - current["start"]).total_seconds()
            if duration >= FLOW_MIN_DURATION_S:
                apps = sorted(current_apps, key=lambda name: current_apps[name], reverse=True)
                blocks.append(
                    FlowBlock(
                        start=current["start"],
                        end=current["end"],
                        duration_s=duration,
                        primary_app=apps[0] if apps else "",
                        apps=apps[:4],
                    )
                )
            current = None
            current_apps = {}

        for session in sessions:
            category = session.category.value if hasattr(session.category, "value") else str(session.category)
            end = session.end_time or (session.start_time + timedelta(seconds=session.duration_s))
            if category not in FLOW_CATEGORIES:
                flush()
                continue

            if current is None:
                current = {"start": session.start_time, "end": end}
            else:
                gap = (session.start_time - current["end"]).total_seconds()
                if gap > FLOW_MAX_GAP_S:
                    flush()
                    current = {"start": session.start_time, "end": end}
                else:
                    current["end"] = max(current["end"], end)

            if current is not None:
                name = session.process_name.lower()
                current_apps[name] = current_apps.get(name, 0.0) + session.duration_s

        flush()

        blocks.sort(key=lambda b: b.start, reverse=True)
        longest = max(blocks, key=lambda b: b.duration_s) if blocks else None
        total_flow_s = sum(b.duration_s for b in blocks)
        today_blocks = [b for b in blocks if b.start.date() == today]

        return {
            "days": days,
            "blocks": [b.to_dict() for b in blocks],
            "total_flow_s": total_flow_s,
            "longest": longest.to_dict() if longest else None,
            "today_flow_s": sum(b.duration_s for b in today_blocks),
            "today_blocks": [b.to_dict() for b in today_blocks],
            "count": len(blocks),
        }

    # ─── Focus recap & weekly attention report ─────────────────────────────

    def get_switch_count_since(self, minutes: int = 30, now: Optional[datetime] = None) -> int:
        now = now or datetime.now()
        start = now - timedelta(minutes=max(1, minutes))
        return len(self._repo.get_sessions_between(start, now))

    def get_focus_recap_metrics(
        self,
        start: datetime,
        end: datetime,
        blocked_apps: int = 0,
        blocked_sites: int = 0,
        interruptions: int = 0,
    ) -> dict:
        sessions = self._repo.get_sessions_between(start, end)
        switches = len(sessions)
        active_s = sum(max(0.0, s.duration_s) for s in sessions)
        active_hours = max(active_s / 3600.0, 0.25)
        index = switches / active_hours

        baseline_values = []
        for offset in range(1, 8):
            day = end.date() - timedelta(days=offset)
            value = self.get_focus_fragmentation(day)["fragmentation_index"]
            if value > 0:
                baseline_values.append(value)
        baseline = sum(baseline_values) / len(baseline_values) if baseline_values else 0.0
        delta_pct = ((index - baseline) / baseline * 100.0) if baseline > 0 else None

        return {
            "start": start,
            "end": end,
            "switches": switches,
            "active_s": active_s,
            "fragmentation_index": round(index, 2),
            "baseline_index": round(baseline, 2),
            "fragmentation_delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
            "blocked_apps": int(blocked_apps),
            "blocked_sites": int(blocked_sites),
            "interruptions": int(interruptions),
            "best_next_window": self.get_best_next_focus_window(end),
        }

    def get_best_next_focus_window(
        self,
        now: Optional[datetime] = None,
        horizon_hours: int = 8,
        lookback_days: int = 14,
    ) -> dict:
        now = now or datetime.now()
        hour_switches = [0] * 24
        hour_active = [0.0] * 24
        for offset in range(lookback_days):
            day = now.date() - timedelta(days=offset)
            data = self.get_focus_fragmentation(day)
            for row in data["hourly"]:
                hour = int(row["hour"].split(":")[0])
                hour_switches[hour] += int(row["switches"])
                hour_active[hour] += float(row["active_s"])

        start_hour = now.hour + 1
        candidates = []
        for offset in range(max(1, horizon_hours - 1)):
            hour = (start_hour + offset) % 24
            next_hour = (hour + 1) % 24
            switches = hour_switches[hour] + hour_switches[next_hour]
            active_h = (hour_active[hour] + hour_active[next_hour]) / 3600.0
            candidates.append((switches / max(active_h, 0.25), hour, switches))

        if not candidates:
            return {
                "start_hour": start_hour % 24,
                "end_hour": (start_hour + 2) % 24,
                "label": "Next 2 hours",
                "score": None,
            }

        score, hour, switches = min(candidates, key=lambda item: item[0])
        day_label = "Today" if hour >= now.hour else "Tomorrow"
        return {
            "start_hour": hour,
            "end_hour": (hour + 2) % 24,
            "label": f"{day_label} {hour:02d}:00–{(hour + 2) % 24:02d}:00",
            "score": round(score, 2),
            "switches": switches,
        }

    def get_weekly_attention_report(self, end_date: Optional[date] = None) -> dict:
        end_day = end_date or date.today()
        start_day = end_day - timedelta(days=6)
        days = []
        aggregate_switches = [0] * 24
        aggregate_active = [0.0] * 24
        total_switches = 0
        total_active = 0.0

        for offset in range(7):
            day = start_day + timedelta(days=offset)
            data = self.get_focus_fragmentation(day)
            hours = []
            for row in data["hourly"]:
                hour = int(row["hour"].split(":")[0])
                switches = int(row["switches"])
                active_s = float(row["active_s"])
                hours.append({"switches": switches, "active_s": active_s})
                aggregate_switches[hour] += switches
                aggregate_active[hour] += active_s
            total_switches += data["total_switches"]
            total_active += sum(float(row["active_s"]) for row in data["hourly"])
            days.append(
                {
                    "date": day,
                    "label": day.strftime("%a"),
                    "hours": hours,
                    "index": data["fragmentation_index"],
                    "switches": data["total_switches"],
                }
            )

        hourly_index = []
        for hour in range(24):
            active_hours = aggregate_active[hour] / 3600.0
            if aggregate_active[hour] >= 900:
                hourly_index.append(
                    {
                        "hour": hour,
                        "index": round(aggregate_switches[hour] / max(active_hours, 0.25), 2),
                        "switches": aggregate_switches[hour],
                    }
                )
        best_hour = min(hourly_index, key=lambda r: r["index"]) if hourly_index else None
        worst_hour = max(hourly_index, key=lambda r: r["index"]) if hourly_index else None

        flow = self.get_flow_analytics(days=30, end_date=end_day)
        flow_days = {b["start"].date() for b in flow["blocks"]}
        current_streak = 0
        cursor = end_day
        while cursor in flow_days:
            current_streak += 1
            cursor -= timedelta(days=1)
        best_streak = 0
        run = 0
        previous = None
        for day in sorted(flow_days):
            run = run + 1 if previous and (day - previous).days == 1 else 1
            best_streak = max(best_streak, run)
            previous = day

        active_hours_total = max(total_active / 3600.0, 0.25)
        return {
            "start": start_day,
            "end": end_day,
            "days": days,
            "total_switches": total_switches,
            "total_active_s": total_active,
            "average_index": round(total_switches / active_hours_total, 2),
            "best_hour": best_hour,
            "worst_hour": worst_hour,
            "flow": {
                "total_flow_s": flow["total_flow_s"],
                "count": flow["count"],
                "longest": flow["longest"],
                "current_streak": current_streak,
                "best_streak": best_streak,
            },
        }


    def get_yesterday_comparison(self) -> dict:
        today = date.today()
        yesterday = today - timedelta(days=1)

        t_summary = self._build_summary(today, today)
        y_summary = self._build_summary(yesterday, yesterday)

        t_val = t_summary.total_screen_time_s
        y_val = y_summary.total_screen_time_s

        # Require at least 30 mins (1800s) of activity yesterday for a meaningful comparison
        eff_y_val = y_val if y_val >= 1800.0 else 0.0
        yesterday_was_zero = (eff_y_val == 0.0)

        if not yesterday_was_zero:
            pct_change = ((t_val - eff_y_val) / eff_y_val) * 100.0
        else:
            pct_change = None

        t_cats = {c["category"].lower(): c["total_s"] for c in t_summary.category_breakdown}
        y_cats = {c["category"].lower(): c["total_s"] for c in y_summary.category_breakdown}
        
        return {
            "today_total_s": t_val,
            "yesterday_total_s": y_val,
            "today_active_s": t_summary.active_time_s,
            "yesterday_active_s": y_summary.active_time_s,
            "pct_change": pct_change,
            "is_increase": pct_change > 0 if pct_change is not None else False,
            "today_cats": t_cats,
            "yesterday_cats": y_cats,
            "yesterday_was_zero": yesterday_was_zero
        }

    def get_trend_insights(self) -> dict:
        today = date.today()
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)

        curr_week = self._build_summary(this_week_start, today)
        prev_week = self._build_summary(last_week_start, last_week_end)

        curr_active = curr_week.active_time_s
        prev_active = prev_week.active_time_s

        # Require at least 2 hours (7200s) of activity last week for a meaningful comparison
        eff_prev_active = prev_active if prev_active >= 7200.0 else 0.0
        prev_week_was_zero = (eff_prev_active == 0.0)

        if not prev_week_was_zero:
            week_pct_change = ((curr_active - eff_prev_active) / eff_prev_active) * 100.0
        else:
            week_pct_change = None

        # Category shifts
        curr_cats = {c["category"].lower(): c["total_s"] for c in curr_week.category_breakdown}
        prev_cats = {c["category"].lower(): c["total_s"] for c in prev_week.category_breakdown}

        prod_curr = sum(curr_cats.get(k, 0.0) for k in ("programming", "productivity", "education", "utilities"))
        prod_prev = sum(prev_cats.get(k, 0.0) for k in ("programming", "productivity", "education", "utilities"))

        ent_curr = sum(curr_cats.get(k, 0.0) for k in ("entertainment", "social", "gaming"))
        ent_prev = sum(prev_cats.get(k, 0.0) for k in ("entertainment", "social", "gaming"))

        prod_change = ((prod_curr - prod_prev) / prod_prev * 100.0) if prod_prev >= 300.0 else (100.0 if prod_curr >= 300.0 else 0.0)
        ent_change = ((ent_curr - ent_prev) / ent_prev * 100.0) if ent_prev >= 300.0 else (100.0 if ent_curr >= 300.0 else 0.0)

        if prod_change > 999.0: prod_change = 999.0
        if ent_change > 999.0: ent_change = 999.0

        return {
            "week_pct_change": week_pct_change,
            "prod_change_pct": prod_change,
            "ent_change_pct": ent_change,
            "curr_week_active_s": curr_active,
            "prev_week_active_s": prev_active,
            "prev_week_was_zero": prev_week_was_zero,
        }

    def get_long_term_analytics(self) -> dict:
        today = date.today()
        # Summaries for all time up to today
        all_stats = self._repo.get_all_daily_stats()
        
        # Calculate streaks based on a 8hr default goal, or settings-based goal
        from settings.manager import SettingsManager
        sm = SettingsManager()
        goal_s = sm.get_int("daily_limit_minutes", 480) * 60
        
        current_streak = 0
        best_streak = 0
        temp_streak = 0
        
        days_tracked = len(all_stats)
        total_time = sum(s.active_time_s for s in all_stats)
        avg_daily = (total_time / days_tracked) if days_tracked > 0 else 0
        
        # We need to sort by date to calculate streaks
        sorted_stats = sorted(all_stats, key=lambda x: x.date)
        
        most_productive_day = None
        highest_prod_time = 0.0
        
        longest_continuous = 0.0
        longest_focus = 0.0
        
        for stat in sorted_stats:
            # Streak - Only count days where the PC was used for at least 5 minutes
            if stat.active_time_s >= 300:
                if stat.total_screen_time_s <= goal_s:
                    temp_streak += 1
                    best_streak = max(best_streak, temp_streak)
                else:
                    temp_streak = 0
                
            # Productivity
            import json
            try:
                cats = json.loads(stat.category_usage_json)
                prod = sum(c["total_s"] for c in cats if c["category"].lower() in ("programming", "productivity", "education", "utilities"))
                if prod > highest_prod_time:
                    highest_prod_time = prod
                    most_productive_day = stat.date
            except:
                pass
                
        # To get current streak, we count backwards from today/yesterday
        current_streak = 0
        for stat in reversed(sorted_stats):
            if stat.active_time_s >= 300:
                if stat.total_screen_time_s <= goal_s:
                    current_streak += 1
                else:
                    break
                
        # Estimate longest sessions across all time
        for stat in all_stats:
            longest_continuous = max(longest_continuous, stat.idle_time_s) # Proxy, wait we have top_app longest?
            
        return {
            "avg_daily_s": avg_daily,
            "avg_weekly_s": avg_daily * 7 if days_tracked > 0 else 0,
            "avg_monthly_s": avg_daily * 30 if days_tracked > 0 else 0,
            "current_streak": current_streak,
            "best_streak": best_streak,
            "most_productive_day": most_productive_day,
            "most_productive_s": highest_prod_time,
            "days_tracked": days_tracked
        }

    @staticmethod
    def format_duration(seconds: float) -> str:
        total = int(seconds)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    @staticmethod
    def format_duration_short(seconds: float) -> str:
        total = int(seconds)
        h, m = divmod(total // 60, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m"

    def generate_daily_snapshot(self, target_date: date) -> None:
        """Computes and saves a historical snapshot for the given date."""
        summary = self._build_summary(target_date, target_date)
        sessions = self._repo.get_sessions_for_date(target_date)
        unlocks = self._repo.get_unlock_count_for_date(target_date)
        
        # Serialize Timeline
        timeline_data = []
        for s in sessions:
            timeline_data.append({
                "process_name": s.process_name,
                "window_title": s.window_title,
                "start_time": s.start_time.isoformat(),
                "duration_s": s.duration_s,
                "category": s.category.value if hasattr(s.category, "value") else str(s.category)
            })
            
        stat = DailyStat(
            date=target_date,
            total_screen_time_s=summary.total_screen_time_s,
            active_time_s=summary.active_time_s,
            idle_time_s=summary.idle_time_s,
            top_app=summary.longest_session_app,
            session_count=len(sessions),
            unlock_count=unlocks,
            category_usage_json=json.dumps(summary.category_breakdown),
            app_usage_json=json.dumps(summary.top_apps),
            timeline_json=json.dumps(timeline_data)
        )
        self._repo.upsert_daily_stat(stat)

    def ensure_historical_snapshots(self) -> None:
        """Backfills missing snapshots for all days that have tracking data, up to yesterday."""
        today = date.today()
        # Find all distinct days with sessions
        rows = self._repo.get_daily_totals_for_range(date(2000, 1, 1), today - timedelta(days=1))
        
        # Determine which days are already snapshotted
        existing_stats = self._repo.get_all_daily_stats()
        existing_dates = {s.date for s in existing_stats}
        
        for row in rows:
            d = date.fromisoformat(row["day"])
            if d not in existing_dates and d < today:
                self.generate_daily_snapshot(d)
                
    def run_cleanup(self, retention_days: int) -> int:
        """Runs the database cleanup to delete raw events older than retention_days."""
        return self._repo.cleanup_old_sessions(retention_days)

    # ─── Website Analytics ───────────────────────────────────────────────────

    def get_top_websites_for_browser(
        self,
        browser_process: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Return top websites visited in a specific browser during a date range."""
        start_d = start or date.today()
        end_d = end or date.today()
        return self._repo.get_top_websites_for_browser(browser_process, start_d, end_d, limit=limit)

    def get_top_websites_for_range(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
        browser_process: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Return top websites across all web browsers (or filtered) during a date range."""
        start_d = start or date.today()
        end_d = end or date.today()
        return self._repo.get_top_websites_for_range(
            start_d, end_d, browser_process=browser_process, limit=limit
        )

    def get_distinct_browsers_for_range(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> List[str]:
        """Return list of distinct browsers that have recorded website activity."""
        start_d = start or date.today()
        end_d = end or date.today()
        return self._repo.get_distinct_browsers_for_range(start_d, end_d)

    def get_top_websites_today(self, limit: int = 20) -> List[dict]:
        """Return top websites visited today across all browsers."""
        today = date.today()
        return self.get_top_websites_for_range(today, today, limit=limit)

    def get_total_website_time(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
        browser_process: Optional[str] = None,
    ) -> float:
        """Return total duration in seconds spent on websites."""
        start_d = start or date.today()
        end_d = end or date.today()
        return self._repo.get_total_website_time_for_range(start_d, end_d, browser_process=browser_process)

