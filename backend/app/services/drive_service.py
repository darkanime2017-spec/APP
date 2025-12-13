import os
import io
import asyncio
import json
import base64
import logging
from typing import Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from app.core.config import settings

class GoogleDriveService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.credentials = self._get_credentials()
        self.service = self._build_drive_service()

    def _get_credentials(self):
        """Loads service account credentials from base64 encoded environment variable."""
        credentials_b64 = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_B64')
        if not credentials_b64:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_B64 environment variable not set")
        
        try:
            # Decode the base64 string to get the JSON
            credentials_json = base64.b64decode(credentials_b64).decode('utf-8')
            credentials_info = json.loads(credentials_json)
            
            return service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive']
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"Error parsing credentials: {str(e)}")
            raise ValueError("Invalid credentials format in GOOGLE_APPLICATION_CREDENTIALS_B64") from e
        except Exception as e:
            self.logger.error(f"Unexpected error loading credentials: {str(e)}")
            raise

    def _build_drive_service(self):
        """Builds and returns an authorized Google Drive service client."""
        return build('drive', 'v3', credentials=self.credentials, cache_discovery=False)

    async def _run_blocking_io(self, func, *args, **kwargs):
        """Runs a blocking I/O operation in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def find_item_id_by_name(self, parent_id: Optional[str], name: str, is_folder: bool = True) -> Optional[str]:
        """Finds an item (file or folder) by name in a parent folder."""
        if parent_id is None:
            raise ValueError("parent_id cannot be None when searching for a Drive item.")

        mime_type = "application/vnd.google-apps.folder" if is_folder else ""
        safe_name = name.replace("'", "\\'")
        query = f"name='{safe_name}' and trashed=false"
        
        if parent_id:
            query = f"'{parent_id}' in parents and {query}"
        if is_folder:
            query += f" and mimeType='{mime_type}'"

        results = await self._run_blocking_io(
            self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute
        )
        files = results.get('files', [])
        return files[0]['id'] if files else None

    async def ensure_folder(self, parent_id: str, folder_name: str) -> str:
        """
        Ensures a folder exists within a parent folder.
        Returns the ID of the existing or newly created folder.
        """
        folder_id = await self.find_item_id_by_name(parent_id, folder_name, is_folder=True)
        if folder_id:
            return folder_id

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = await self._run_blocking_io(
            self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute
        )
        return folder.get('id')

    async def download_file_by_id(self, file_id: str) -> bytes:
        """Downloads a file's content by its ID. Returns the file content as bytes."""
        request = self.service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while done is False:
            status, done = await self._run_blocking_io(downloader.next_chunk)
        return file_content.getvalue()

    async def upload_file_to_folder(self, folder_id: str, file_path: str, filename: Optional[str] = None) -> str:
        """
        Uploads a file from a local path to a specified Drive folder.
        Returns the Drive file ID.
        """
        if filename is None:
            filename = os.path.basename(file_path)
            
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaFileUpload(file_path, resumable=True)
        
        file = await self._run_blocking_io(
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute
        )
        return file.get('id')

    async def upload_bytes_as_file(self, folder_id: str, bytes_data: bytes, filename: str, 
                                 mime_type: str = 'application/octet-stream') -> str:
        """
        Uploads bytes data as a file to a specified Drive folder.
        Returns the Drive file ID.
        """
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaIoBaseUpload(
            io.BytesIO(bytes_data),
            mimetype=mime_type,
            resumable=True
        )
        
        file = await self._run_blocking_io(
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute
        )
        return file.get('id')

    async def list_files_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """Lists all files in a folder."""
        results = await self._run_blocking_io(
            self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, size, modifiedTime)",
                pageSize=1000
            ).execute
        )
        return results.get('files', [])

# Create a singleton instance
drive_service = GoogleDriveService()
