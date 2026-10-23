from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Optional

from core.logger import logger
from database.repository import Repository


class CSVExporter:
    def __init__(self) -> None:
        self._repo = Repository()

    def export_sessions(
        self,
        start_date: date,
        end_date: date,
        output_path: Optional[Path] = None,
    ) -> Path:
        if output_path is None:
            output_path = (
                Path.home()
                / "Documents"
                / f"digital_wellbeing_{start_date}_{end_date}.csv"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = self._repo.export_sessions_csv_data(start_date, end_date)

        headers = [
            "Process Name",
            "Executable Path",
            "Window Title",
            "Start Time",
            "End Time",
            "Duration (s)",
            "Category",
            "Is Idle",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(list(row))

        logger.info("Exported %d sessions to %s", len(rows), output_path)
        return output_path
