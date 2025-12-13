import pandas as pd
import io
import random
from typing import List, Dict, Any
from app.core.config import settings
from app.services.drive_service import GoogleDriveService

class DataService:
    def __init__(self, drive_service: GoogleDriveService):
        self.drive_service = drive_service
        self.metadata_df: pd.DataFrame = pd.DataFrame()
        self.authors: List[str] = []
        self.author_ids: List[int] = []

    async def load_metadata(self):
        """
        Loads metadata.csv from Google Drive into a pandas DataFrame.
        """
        metadata_file_id = await self.drive_service.find_item_id_by_name(
            settings.DRIVE_ROOT_FOLDER_ID, "metadata.csv", is_folder=False
        )

        if not metadata_file_id:
            raise FileNotFoundError(f"metadata.csv not found in Drive root folder {settings.DRIVE_ROOT_FOLDER_ID}")

        metadata_bytes = await self.drive_service.download_file_by_id(metadata_file_id)
        self.metadata_df = pd.read_csv(io.BytesIO(metadata_bytes))
        self.authors = self.metadata_df['Author'].unique().tolist()
        self.author_ids = self.metadata_df['AuthorID'].unique().tolist()
        print(f"Loaded {len(self.metadata_df)} entries from metadata.csv.")
        print(f"Unique authors: {len(self.authors)}")

    def get_unique_authors(self) -> List[str]:
        """Returns a list of all unique authors."""
        return self.authors

    def sample_authors(self, num_authors: int = 3) -> List[str]:
        """Samples a specified number of unique authors randomly."""
        return random.sample(self.authors, num_authors)

    def get_files_for_authors(self, authors: List[str]) -> pd.DataFrame:
        """
        Returns a DataFrame of files for the given list of authors.
        """
        return self.metadata_df[self.metadata_df['Author'].isin(authors)].copy()

    def select_hidden_test_ids(self, student_files_df: pd.DataFrame, min_hidden: int = 1) -> List[Dict[str, Any]]:
        """Select 10% of rows as hidden test items using the row index as text_id.

        The global metadata.csv does not have a dedicated FileId column, so we
        use the per-student dataframe index as the text identifier.
        """
        num_files = len(student_files_df)
        num_hidden = max(min_hidden, int(num_files * 0.10))

        if num_files == 0:
            return []

        hidden_indices = random.sample(range(num_files), min(num_hidden, num_files))
        hidden_items = student_files_df.iloc[hidden_indices]

        return [
            {
                "text_id": int(idx),
                "ground_truth": row['AuthorID']
            }
            for idx, row in hidden_items.iterrows()
        ]

# This instance will be initialized at application startup
# data_service = DataService(drive_service) # We need to pass drive_service here. This will be done in main.py
