import os
import io
import asyncio
import json
import base64
import tempfile
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from app.core.config import settings

class GoogleDriveService:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = self._build_drive_service()

    def _get_credentials(self):
        """Load credentials from base64 environment variable."""
        credentials_b64 = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_B64') or settings.GOOGLE_APPLICATION_CREDENTIALS_B64
        if not credentials_b64:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_B64 environment variable not set")

        # Decode the Base64 string
        credentials_json = base64.b64decode(credentials_b64).decode("utf-8")

        # Write to a temporary JSON file
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp_file.write(credentials_json.encode("utf-8"))
        tmp_file.flush()
        tmp_file.close()

        # Use the temp file path to load credentials
        return service_account.Credentials.from_service_account_file(
            tmp_file.name,
            scopes=['https://www.googleapis.com/auth/drive']
        )

    def _build_drive_service(self):
        """Builds and returns an authorized Google Drive service client."""
        return build('drive', 'v3', credentials=self.credentials, cache_discovery=False)

    async def _run_blocking_io(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def find_item_id_by_name(self, parent_id: str | None, name: str, is_folder: bool = True) -> Optional[str]:
        if parent_id is None:
            raise ValueError("parent_id cannot be None when searching for a Drive item.")
        mime_type = "application/vnd.google-apps.folder" if is_folder else ""
        safe_name = name.replace("'", "\\'")
        query = f"'{parent_id}' in parents and name='{safe_name}' and trashed=false"
        if is_folder:
            query += f" and mimeType='{mime_type}'"

        results = await self._run_blocking_io(
            self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute
        )
        files = results.get('files', [])
        return files[0]['id'] if files else None

    async def ensure_folder(self, parent_id: str, folder_name: str) -> str:
        folder_id = await self.find_item_id_by_name(parent_id, folder_name, is_folder=True)
        if folder_id:
            return folder_id
        file_metadata = {'name': folder_name, 'parents': [parent_id], 'mimeType': 'application/vnd.google-apps.folder'}
        folder = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, fields='id').execute
        )
        return folder.get('id')

    async def download_file_by_id(self, file_id: str) -> bytes:
        request = self.service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = await self._run_blocking_io(downloader.next_chunk)
        return file_content.getvalue()

    async def upload_file_to_folder(self, folder_id: str, file_path: str, filename: str) -> str:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute
        )
        return file.get('id')

    async def upload_bytes_as_file(self, folder_id: str, bytes_data: bytes, filename: str, mime_type: str = 'application/zip') -> str:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(bytes_data), mime_type, resumable=True)
        file = await self._run_blocking_io(
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute
        )
        return file.get('id')


# Singleton instance
drive_service = GoogleDriveService()
