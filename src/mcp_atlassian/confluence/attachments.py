"""Attachment operations for Confluence API."""

import logging
import os
import re
from pathlib import Path
from typing import Any

from .client import ConfluenceClient

# Configure logging
logger = logging.getLogger("mcp-atlassian")


class AttachmentsMixin(ConfluenceClient):
    """Mixin for Confluence attachment operations."""

    def download_attachment(self, url: str, target_path: str) -> bool:
        """
        Download a Confluence attachment to the specified path.

        Args:
            url: The URL of the attachment to download
            target_path: The path where the attachment should be saved

        Returns:
            True if successful, False otherwise
        """
        if not url:
            logger.error("No URL provided for attachment download")
            return False

        try:
            # Convert to absolute path if relative
            if not os.path.isabs(target_path):
                target_path = os.path.abspath(target_path)

            logger.info(f"Downloading attachment from {url} to {target_path}")

            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Use the Confluence session to download the file
            response = self.confluence._session.get(url, stream=True)
            response.raise_for_status()

            # Write the file to disk
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify the file was created
            if os.path.exists(target_path):
                file_size = os.path.getsize(target_path)
                logger.info(
                    f"Successfully downloaded attachment to {target_path} (size: {file_size} bytes)"
                )
                return True
            else:
                logger.error(f"File was not created at {target_path}")
                return False

        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            return False

    def download_page_attachments(
        self,
        page_id: str,
        target_dir: str,
        media_type_filter: str | None = None,
        only_used_in_content: bool = True,
    ) -> dict[str, Any]:
        """
        Download attachments for a Confluence page.

        Args:
            page_id: The Confluence page ID
            target_dir: The directory where attachments should be saved
            media_type_filter: Optional media type filter (e.g., 'image/' for all images)
            only_used_in_content: If True, only download attachments that are actually
                referenced in the latest page content (default: True)

        Returns:
            A dictionary with download results
        """
        # Convert to absolute path if relative
        if not os.path.isabs(target_dir):
            target_dir = os.path.abspath(target_dir)

        logger.info(
            f"Downloading attachments for page {page_id} to directory: {target_dir}"
        )

        # Create the target directory if it doesn't exist
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Get the page content if we need to filter by usage
        referenced_filenames = set()
        if only_used_in_content:
            try:
                logger.info(f"Fetching page content to identify referenced attachments")
                page = self.confluence.get_page_by_id(
                    page_id=page_id, expand="body.storage"
                )
                content = page["body"]["storage"]["value"]

                # Extract filenames from <ac:image> tags with ri:filename attribute
                image_matches = re.findall(
                    r'<ac:image[^>]*>.*?ri:filename="([^"]+)".*?</ac:image>',
                    content,
                    re.DOTALL,
                )
                referenced_filenames.update(image_matches)

                # Also check for direct attachment references
                # Pattern: /download/attachments/{page_id}/{filename}
                attachment_url_pattern = rf'/download/attachments/{page_id}/([^"\'?\s]+)'
                url_matches = re.findall(attachment_url_pattern, content)
                # URL decode filenames
                import urllib.parse

                referenced_filenames.update(
                    [urllib.parse.unquote(f) for f in url_matches]
                )

                logger.info(
                    f"Found {len(referenced_filenames)} referenced attachments in page content"
                )
            except Exception as e:
                logger.warning(
                    f"Error fetching page content, will download all attachments: {str(e)}"
                )
                only_used_in_content = False

        # Get the page attachments
        logger.info(f"Fetching attachments for page {page_id}")
        try:
            attachments_response = self.confluence.get_attachments_from_content(
                page_id=page_id, limit=100
            )
        except Exception as e:
            logger.error(f"Error fetching attachments: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "downloaded": [],
                "failed": [],
            }

        if not attachments_response or "results" not in attachments_response:
            logger.info(f"No attachments found for page {page_id}")
            return {
                "success": True,
                "message": "No attachments found",
                "downloaded": [],
                "failed": [],
            }

        attachments = attachments_response["results"]
        logger.info(f"Found {len(attachments)} total attachments")

        # Filter by content usage if requested
        if only_used_in_content and referenced_filenames:
            attachments = [
                att
                for att in attachments
                if att.get("title", "") in referenced_filenames
            ]
            logger.info(
                f"After filtering by content usage: {len(attachments)} attachments"
            )

        # Filter by media type if specified
        if media_type_filter:
            filtered_attachments = []
            for att in attachments:
                # Try to get mediaType from metadata or extensions
                media_type = None
                if "metadata" in att and "mediaType" in att["metadata"]:
                    media_type = att["metadata"]["mediaType"]
                elif "extensions" in att and "mediaType" in att["extensions"]:
                    media_type = att["extensions"]["mediaType"]

                if media_type and media_type.startswith(media_type_filter):
                    filtered_attachments.append(att)

            attachments = filtered_attachments
            logger.info(
                f"After filtering by '{media_type_filter}': {len(attachments)} attachments"
            )

        downloaded = []
        failed = []

        for attachment in attachments:
            attachment_id = attachment.get("id", "unknown")
            title = attachment.get("title", "unknown")

            # Get media type from metadata or extensions
            media_type = "unknown"
            if "metadata" in attachment and "mediaType" in attachment["metadata"]:
                media_type = attachment["metadata"]["mediaType"]
            elif "extensions" in attachment and "mediaType" in attachment["extensions"]:
                media_type = attachment["extensions"]["mediaType"]

            logger.info(
                f"Processing attachment: {title} (ID: {attachment_id}, Type: {media_type})"
            )

            # Get download URL from _links
            if "_links" not in attachment or "download" not in attachment["_links"]:
                logger.warning(f"No download link found for attachment: {title}")
                failed.append(
                    {
                        "id": attachment_id,
                        "title": title,
                        "error": "No download link available",
                    }
                )
                continue

            download_path = attachment["_links"]["download"]

            # Construct full URL if path is relative
            if download_path.startswith("/"):
                # Get base URL from config
                base_url = self.config.url.rstrip("/")
                download_url = base_url + download_path
            else:
                download_url = download_path

            # Create target file path
            file_path = target_path / title

            # Download the file
            success = self.download_attachment(str(download_url), str(file_path))

            if success:
                downloaded.append(
                    {
                        "id": attachment_id,
                        "title": title,
                        "path": str(file_path),
                        "size": os.path.getsize(str(file_path)),
                        "media_type": media_type,
                    }
                )
            else:
                failed.append(
                    {
                        "id": attachment_id,
                        "title": title,
                        "error": "Download failed",
                    }
                )

        result = {
            "success": len(failed) == 0,
            "total_attachments": len(attachments),
            "downloaded": downloaded,
            "failed": failed,
            "target_directory": target_dir,
        }

        logger.info(
            f"Download complete: {len(downloaded)} succeeded, {len(failed)} failed"
        )

        return result
