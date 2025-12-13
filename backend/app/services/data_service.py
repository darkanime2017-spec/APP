import csv
import io
import random
from typing import List, Dict, Any
from app.core.config import settings
from app.services.drive_service import GoogleDriveService

class DataService:
    def __init__(self, drive_service: GoogleDriveService):
        self.drive_service = drive_service
        self.metadata_list: List[Dict[str, Any]] = []
        self.authors: List[str] = []
        self.author_ids: List[int] = []

    async def load_metadata(self):
        """
        Loads metadata.csv from Google Drive into a list of dicts.
        Ensures AuthorID is an integer and skips invalid rows.
        """
        metadata_file_id = await self.drive_service.find_item_id_by_name(
            settings.DRIVE_ROOT_FOLDER_ID, "metadata.csv", is_folder=False
        )

        if not metadata_file_id:
            raise FileNotFoundError(f"metadata.csv not found in Drive root folder {settings.DRIVE_ROOT_FOLDER_ID}")

        metadata_bytes = await self.drive_service.download_file_by_id(metadata_file_id)
        metadata_str = metadata_bytes.decode("utf-8")

        reader = csv.DictReader(io.StringIO(metadata_str))
        self.metadata_list = []

        for row in reader:
            try:
                row['AuthorID'] = int(row['AuthorID'])
            except (ValueError, KeyError):
                # Skip rows with invalid or missing AuthorID
                print(f"Skipping invalid row: {row}")
                continue
            self.metadata_list.append(row)

        self.authors = list({row['Author'] for row in self.metadata_list})
        self.author_ids = list({row['AuthorID'] for row in self.metadata_list})

        print(f"Loaded {len(self.metadata_list)} valid entries from metadata.csv.")
        print(f"Unique authors: {len(self.authors)}")

    def get_unique_authors(self) -> List[str]:
        """Returns a list of all unique authors."""
        return self.authors

    def sample_authors(self, num_authors: int = 3) -> List[str]:
        """Samples a specified number of unique authors randomly."""
        return random.sample(self.authors, min(num_authors, len(self.authors)))

    def get_files_for_authors(self, authors: List[str]) -> List[Dict[str, Any]]:
        """Returns a list of files for the given list of authors."""
        return [row for row in self.metadata_list if row['Author'] in authors]

    def select_hidden_test_ids(self, student_files_list: List[Dict[str, Any]], min_hidden: int = 1) -> List[Dict[str, Any]]:
        """Select 10% of rows as hidden test items using the row index as text_id."""
        num_files = len(student_files_list)
        num_hidden = max(min_hidden, int(num_files * 0.10))

        if num_files == 0:
            return []

        hidden_indices = random.sample(range(num_files), min(num_hidden, num_files))
        hidden_items = [student_files_list[i] for i in hidden_indices]

        return [
            {
                "text_id": int(idx),
                "ground_truth": row['AuthorID']
            }
            for idx, row in zip(hidden_indices, hidden_items)
        ]
