import os
import io
import asyncio
from typing import Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from app.core.config import settings

class GoogleDriveService:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = self._build_drive_service()

    def _get_credentials(self):
        """Loads service account credentials from the specified JSON file."""
        if not os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
            raise FileNotFoundError(
                f"Google application credentials file not found at: {settings.GOOGLE_APPLICATION_CREDENTIALS}"
            )
        return service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/drive']
        )

    def _build_drive_service(self):
        """Builds and returns an authorized Google Drive service client."""
        return build('drive', 'v3', credentials=self.credentials)

    async def _run_blocking_io(self, func, *args, **kwargs):
        """Runs a blocking I/O operation in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def find_item_id_by_name(self, parent_id: str | None, name: str, is_folder: bool = True) -> Optional[str]:
        if parent_id is None:
            raise ValueError("parent_id cannot be None when searching for a Drive item.")
        """Find a file or folder ID by its name within a parent folder.

        Escapes single quotes in the name so it can be safely used in the Drive
        search query (q parameter).
        """
        mime_type = "application/vnd.google-apps.folder" if is_folder else ""
        # Escape single quotes for the Drive query syntax
        safe_name = name.replace("'", "\\'")
        query = f"'{parent_id}' in parents and name='{safe_name}' and trashed=false"
        if is_folder:
            query += f" and mimeType='{mime_type}'"

        results = await self._run_blocking_io(
            self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute
        )
        files = results.get('files', [])
        return files[0]['id'] if files else None

    async def ensure_folder(self, parent_id: str, folder_name: str) -> str:
        """
        Ensures a folder exists within a parent folder. If it doesn't exist, it creates it.
        Returns the ID of the folder.
        """
        folder_id = await self.find_item_id_by_name(parent_id, folder_name, is_folder=True)
        if folder_id:
            return folder_id

        file_metadata = {
            'name': folder_name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, fields='id').execute
        )
        return folder.get('id')

    async def download_file_by_id(self, file_id: str) -> bytes:
        """
        Downloads a file's content by its ID.
        Returns the file content as bytes.
        """
        request = self.service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while done is False:
            status, done = await self._run_blocking_io(downloader.next_chunk)
            # print(f"Download progress: {int(status.progress() * 100)}%") # Optional: for debugging
        return file_content.getvalue()

    async def upload_file_to_folder(self, folder_id: str, file_path: str, filename: str) -> str:
        """
        Uploads a file from a local path to a specified Drive folder.
        Returns the Drive file ID.
        """
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute
        )
        return file.get('id')

    async def upload_bytes_as_file(self, folder_id: str, bytes_data: bytes, filename: str, mime_type: str = 'application/zip') -> str:
        """
        Uploads bytes data as a file to a specified Drive folder.
        Returns the Drive file ID.
        """
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(bytes_data), mime_type, resumable=True)
        file = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute
        )
        return file.get('id')

drive_service = GoogleDriveService()