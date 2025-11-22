"""
Backblaze B2 Storage Service for user file uploads.
Creates dedicated folders for each user and handles file uploads.
"""
import logging
import uuid
from typing import Optional, BinaryIO
from pathlib import Path
from datetime import datetime

from b2sdk.v2 import InMemoryAccountInfo, B2Api
from b2sdk.v2.exception import B2Error
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_storage_service_instance = None


class StorageService:
    """Service for managing Backblaze B2 storage operations."""
    
    def __init__(self):
        """Initialize Backblaze B2 API client."""
        self.info = InMemoryAccountInfo()
        self.b2_api = None
        self.bucket = None
        self._initialized = False
        
        # Check if B2 credentials are configured
        if not settings.B2_APPLICATION_KEY_ID or not settings.B2_APPLICATION_KEY:
            logger.warning("Backblaze B2 credentials not configured. Storage operations will be disabled.")
            return
        
        if settings.B2_APPLICATION_KEY_ID == "your-key-id" or settings.B2_APPLICATION_KEY == "your-application-key":
            logger.warning("Backblaze B2 credentials are still set to placeholder values. Please update your .env file.")
            return
        
        try:
            self.b2_api = B2Api(self.info)
            self.b2_api.authorize_account(
                "production",
                settings.B2_APPLICATION_KEY_ID,
                settings.B2_APPLICATION_KEY
            )
            logger.info("Successfully authorized Backblaze B2 account")
            
            # Get or find bucket
            if settings.B2_BUCKET_ID:
                try:
                    self.bucket = self.b2_api.get_bucket_by_id(settings.B2_BUCKET_ID)
                    logger.info(f"Found bucket by ID: {self.bucket.name} (ID: {self.bucket.id_})")
                except B2Error as e:
                    logger.error(f"Bucket with ID {settings.B2_BUCKET_ID} not found: {e}")
                    raise
            elif settings.B2_BUCKET_NAME:
                try:
                    self.bucket = self.b2_api.get_bucket_by_name(settings.B2_BUCKET_NAME)
                    logger.info(f"Found bucket by name: {self.bucket.name} (ID: {self.bucket.id_})")
                except B2Error as e:
                    logger.error(f"Bucket '{settings.B2_BUCKET_NAME}' not found: {e}")
                    logger.error("Please check that the bucket name exists in your Backblaze account")
                    raise
            else:
                logger.error("B2_BUCKET_NAME or B2_BUCKET_ID must be set")
                raise ValueError("B2_BUCKET_NAME or B2_BUCKET_ID must be set")
            
            self._initialized = True
                
        except B2Error as e:
            logger.error(f"Failed to initialize Backblaze B2: {e}")
            logger.error("Storage operations will be disabled. Please check:")
            logger.error("  1. B2_APPLICATION_KEY_ID is correct (should be 25 characters)")
            logger.error("  2. B2_APPLICATION_KEY is correct (should start with 'K' and be ~31 characters)")
            logger.error("  3. B2_BUCKET_NAME matches an existing bucket in your Backblaze account")
            logger.error("  4. The application key has 'readFiles' and 'writeFiles' capabilities")
            # Don't raise - allow service to exist but mark as not initialized
            self.b2_api = None
            self.bucket = None
    
    def user_folders_exist(self, user_id: uuid.UUID) -> bool:
        """
        Check if user folders exist in B2.
        Returns True if all three folders exist, False otherwise.
        """
        if not self._initialized:
            return False
        
        try:
            folders = [
                "wan-animate",
                "image-to-video",
                "image-to-image",
            ]
            
            for folder in folders:
                placeholder_path = f"{user_id}/{folder}/.keep"
                folder_prefix = f"{user_id}/{folder}/"
                # Try to check if file exists by listing files with prefix
                try:
                    # List files in the folder - if the placeholder exists, we'll find it
                    file_list = list(self.bucket.list_file_versions(folder_prefix))
                    found = False
                    for file_info, _ in file_list:
                        if file_info.file_name == placeholder_path:
                            found = True
                            break
                    
                    if not found:
                        logger.info(f"Folder {user_id}/{folder}/ does not exist (placeholder not found)")
                        return False
                    # File exists, continue to next folder
                    continue
                except B2Error:
                    # File doesn't exist, folder doesn't exist
                    logger.info(f"Folder {user_id}/{folder}/ does not exist (placeholder not found)")
                    return False
            
            logger.info(f"All folders exist for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking user folders for {user_id}: {e}", exc_info=True)
            return False
    
    def create_user_folders(self, user_id: uuid.UUID) -> bool:
        """
        Create folder structure for a new user.
        Creates: {user_id}/wan-animate/, {user_id}/image-to-video/, {user_id}/image-to-image/
        
        In B2, folders are created implicitly when files are uploaded.
        We create placeholder files to ensure the folder structure exists.
        
        Returns True if successful, False otherwise.
        """
        if not self._initialized:
            logger.warning(f"Cannot create folders for user {user_id}: B2 not initialized")
            return False
        
        try:
            # Check if folders already exist
            if self.user_folders_exist(user_id):
                logger.info(f"Folders already exist for user {user_id}, skipping creation")
                return True
            
            folders = [
                "wan-animate",
                "image-to-video",
                "image-to-image",
            ]
            
            for folder in folders:
                # Create a placeholder file to ensure the folder exists
                placeholder_path = f"{user_id}/{folder}/.keep"
                try:
                    # Upload a small placeholder file
                    self.bucket.upload_bytes(
                        b"",  # Empty file
                        file_name=placeholder_path,
                        content_type="text/plain"
                    )
                    logger.info(f"Created folder structure: {user_id}/{folder}/")
                except B2Error as e:
                    # If folder already exists or other error, log and continue
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Could not create placeholder for {placeholder_path}: {e}")
            
            logger.info(f"Successfully created folder structure for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user folders for {user_id}: {e}", exc_info=True)
            return False
    
    def verify_and_create_user_folders(self, user_id: uuid.UUID) -> bool:
        """
        Verify if user folders exist, and create them if they don't.
        This is a convenience method that combines checking and creating.
        
        Returns True if folders exist or were successfully created, False otherwise.
        """
        if not self._initialized:
            logger.warning(f"Cannot verify/create folders for user {user_id}: B2 not initialized")
            return False
        
        if self.user_folders_exist(user_id):
            return True
        
        return self.create_user_folders(user_id)
    
    def upload_file(
        self,
        user_id: uuid.UUID,
        file_data: bytes,
        file_name: str,
        content_type: str,
        folder: str  # "wan-animate", "image-to-video", or "image-to-image"
    ) -> Optional[str]:
        """
        Upload a file to Backblaze B2 for a specific user.
        
        Args:
            user_id: UUID of the user
            file_data: File content as bytes
            file_name: Original file name
            content_type: MIME type of the file
            folder: Folder name (wan-animate, image-to-video, image-to-image)
        
        Returns:
            Backblaze B2 public download URL if successful, None otherwise
        """
        if not self._initialized:
            logger.error("Cannot upload file: B2 not initialized")
            return None
        
        try:
            # Generate unique file name to avoid collisions
            file_ext = Path(file_name).suffix
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Construct B2 file path
            b2_file_path = f"{user_id}/{folder}/{unique_filename}"
            
            # Upload to B2
            uploaded_file = self.bucket.upload_bytes(
                file_data,
                file_name=b2_file_path,
                content_type=content_type
            )
            
            logger.info(f"Uploaded file {b2_file_path} to B2 (file_id: {uploaded_file.id_})")
            
            # Get public download URL from B2
            download_url = self.b2_api.get_download_url_for_fileid(uploaded_file.id_)
            
            return download_url
            
        except B2Error as e:
            logger.error(f"Error uploading file to B2: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}", exc_info=True)
            return None
    
    def delete_file(self, user_id: uuid.UUID, file_path: str) -> bool:
        """
        Delete a file from Backblaze B2.
        
        Args:
            user_id: UUID of the user
            file_path: Path to the file (relative to user folder)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Construct full B2 file path
            b2_file_path = f"{user_id}/{file_path}"
            
            # List files with prefix to find the file
            try:
                file_list = list(self.bucket.list_file_versions(b2_file_path))
                found_file = None
                for file_info, _ in file_list:
                    if file_info.file_name == b2_file_path:
                        found_file = file_info
                        break
                
                if not found_file:
                    logger.warning(f"File not found: {b2_file_path}")
                    return False
                
                # Delete the file
                self.bucket.delete_file_version(
                    file_id=found_file.id_,
                    file_name=b2_file_path
                )
                
                logger.info(f"Deleted file {b2_file_path} from B2")
                return True
            except B2Error as e:
                logger.error(f"Error deleting file {b2_file_path}: {e}", exc_info=True)
                return False
            
        except B2Error as e:
            logger.error(f"Error deleting file from B2: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}", exc_info=True)
            return False
    
    def list_user_files(self, user_id: uuid.UUID, folder: Optional[str] = None) -> list:
        """
        List files for a user, optionally filtered by folder.
        
        Args:
            user_id: UUID of the user
            folder: Optional folder name to filter by
        
        Returns:
            List of file information dictionaries
        """
        try:
            prefix = f"{user_id}/"
            if folder:
                prefix += f"{folder}/"
            
            files = []
            # Limit to first 1000 files by using itertools.islice or manual counting
            count = 0
            for file_version, _ in self.bucket.list_file_versions(prefix):
                if count >= 1000:
                    break
                count += 1
                
                # Skip placeholder files
                if file_version.file_name.endswith(".keep"):
                    continue
                
                # Get public download URL from B2
                download_url = self.b2_api.get_download_url_for_fileid(file_version.id_)
                
                files.append({
                    "name": file_version.file_name,
                    "size": file_version.size,
                    "upload_timestamp": file_version.upload_timestamp,
                    "url": download_url
                })
            
            return files
            
        except B2Error as e:
            logger.error(f"Error listing files from B2: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}", exc_info=True)
            return []


def get_storage_service() -> StorageService:
    """
    Get or create the singleton StorageService instance.
    This ensures the service is only initialized once, preventing blocking on every request.
    """
    global _storage_service_instance
    if _storage_service_instance is None:
        logger.info("Initializing StorageService singleton...")
        _storage_service_instance = StorageService()
    return _storage_service_instance

