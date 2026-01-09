"""
Google Cloud Storage helper module for handling image uploads.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError


class GCSStorage:
    """Google Cloud Storage handler for image uploads."""

    def __init__(self):
        """
        Initialize GCS client.
        Requires GOOGLE_APPLICATION_CREDENTIALS environment variable or GKE workload identity.
        """
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "swappo-images")
        self.project_id = os.getenv("GCP_PROJECT_ID")

        try:
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
        except Exception as e:
            print(f"Warning: GCS client initialization failed: {e}")
            self.client = None
            self.bucket = None

    def upload_image(
        self, file_content: bytes, filename: str, content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload an image to Google Cloud Storage.

        Args:
            file_content: Binary content of the image
            filename: Original filename (will be made unique)
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded image

        Raises:
            GoogleCloudError: If upload fails
        """
        if not self.bucket:
            raise GoogleCloudError("GCS bucket not initialized")

        # Generate unique filename
        file_ext = Path(filename).suffix.lower() or ".jpg"
        unique_filename = f"catalog/{uuid.uuid4()}{file_ext}"

        # Create blob and upload
        blob = self.bucket.blob(unique_filename)
        blob.upload_from_string(file_content, content_type=content_type)

        # Make blob publicly accessible
        blob.make_public()

        # Return public URL
        return blob.public_url

    def delete_image(self, image_url: str) -> bool:
        """
        Delete an image from Google Cloud Storage.

        Args:
            image_url: Full public URL of the image

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.bucket:
            return False

        try:
            # Extract blob name from URL
            # Format: https://storage.googleapis.com/bucket-name/path/to/file.jpg
            blob_name = image_url.split(f"{self.bucket_name}/")[-1]
            blob = self.bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            return False

    def get_signed_url(
        self, blob_name: str, expiration_minutes: int = 60
    ) -> Optional[str]:
        """
        Generate a signed URL for temporary access to a private blob.

        Args:
            blob_name: Name of the blob in the bucket
            expiration_minutes: URL expiration time in minutes

        Returns:
            Signed URL or None if failed
        """
        if not self.bucket:
            return None

        try:
            from datetime import timedelta

            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes), method="GET"
            )
            return url
        except Exception as e:
            print(f"Error generating signed URL: {e}")
            return None


# Singleton instance
_gcs_storage = None


def get_gcs_storage() -> GCSStorage:
    """Get or create GCS storage singleton instance."""
    global _gcs_storage
    if _gcs_storage is None:
        _gcs_storage = GCSStorage()
    return _gcs_storage
