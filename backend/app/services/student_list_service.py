import csv
from pathlib import Path
from typing import Set


class StudentListService:
    """Loads students_list.csv and exposes simple validation helpers.

    Expected CSV header: N°,Nom,Prénoms,Full_Name
    We only care about the Full_Name column for now.
    """

    def __init__(self) -> None:
        self._full_names: Set[str] = set()
        self._all_names: list[str] = []
        self._load_students()

    def _normalize(self, name: str) -> str:
        """Normalize names for comparison: lowercase and collapse whitespace."""
        return " ".join(name.split()).strip().lower()

    def _load_students(self) -> None:
        # students_list.csv is in the backend project root
        backend_root = Path(__file__).resolve().parents[2]
        csv_path = backend_root / "students_list.csv"
        if not csv_path.exists():
            return

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = (row.get("Full_Name") or "").strip()
                if full_name:
                    self._full_names.add(self._normalize(full_name))
                    self._all_names.append(full_name)

    def is_valid_full_name(self, full_name: str) -> bool:
        return self._normalize(full_name) in self._full_names

    def get_all_full_names(self) -> list[str]:
        return self._all_names


student_list_service = StudentListService()
