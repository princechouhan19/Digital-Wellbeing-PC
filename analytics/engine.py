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

