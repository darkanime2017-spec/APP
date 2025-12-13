import io
import random
from typing import List, Dict, Any
from app.core.config import settings
from app.services.drive_service import GoogleDriveService
# import pandas as pd  # Commented out as requested

class DataService:
    def __init__(self, drive_service: GoogleDriveService):
        self.drive_service = drive_service
        # self.metadata_df: pd.DataFrame = pd.DataFrame()  # Commented out
        self.metadata_list: List[Dict[str, Any]] = []  # replace pandas DataFrame
        self.authors: List[str] = []
        self.author_ids: List[int] = []

    async def load_metadata(self):
        """
        Loads metadata.csv from Google Drive into a list of dicts (no pandas).
        """
        metadata_file_id = await self.drive_service.find_item_id_by_name(
            settings.DRIVE_ROOT_FOLDER_ID, "metadata.csv", is_folder=False
        )

        if not metadata_file_id:
            raise FileNotFoundError(f"metadata.csv not found in Drive root folder {settings.DRIVE_ROOT_FOLDER_ID}")

        metadata_bytes = await self.drive_service.download_file_by_id(metadata_file_id)
        content = metadata_bytes.decode("utf-8").splitlines()
        headers = content[0].split(",")
        self.metadata_list = [
            dict(zip(headers, line.split(",")))
            for line in content[1:]
        ]

        self.authors = list({row['Author'] for row in self.metadata_list})
        self.author_ids = list({int(row['AuthorID']) for row in self.metadata_list})
        print(f"Loaded {len(self.metadata_list)} entries from metadata.csv.")
        print(f"Unique authors: {len(self.authors)}")

    def get_unique_authors(self) -> List[str]:
        """Returns a list of all unique authors."""
        return self.authors

    def sample_authors(self, num_authors: int = 3) -> List[str]:
        """Samples a specified number of unique authors randomly."""
        return random.sample(self.authors, num_authors)

    def get_files_for_authors(self, authors: List[str]) -> List[Dict[str, Any]]:
        """
        Returns a list of metadata dicts for the given list of authors.
        """
        return [row for row in self.metadata_list if row['Author'] in authors]

    def select_hidden_test_ids(self, student_files_list: List[Dict[str, Any]], min_hidden: int = 1) -> List[Dict[str, Any]]:
        """Select 10% of rows as hidden test items using the list index as text_id."""
        num_files = len(student_files_list)
        num_hidden = max(min_hidden, int(num_files * 0.10))

        if num_files == 0:
            return []

        hidden_indices = random.sample(range(num_files), min(num_hidden, num_files))
        hidden_items = [student_files_list[i] for i in hidden_indices]

        return [
            {
                "text_id": int(idx),
                "ground_truth": int(row['AuthorID'])
            }
            for idx, row in zip(hidden_indices, hidden_items)
        ]

# This instance will be initialized at application startup
# data_service = DataService(drive_service) # We need to pass drive_service here. This will be done in main.py
