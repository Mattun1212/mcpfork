
"""Module for Confluence comment operations."""

import logging

import requests

from ..models.confluence import ConfluenceComment, ConfluenceInlineComment
from .client import ConfluenceClient

logger = logging.getLogger("mcp-atlassian")


class CommentsMixin(ConfluenceClient):
    """Mixin for Confluence comment operations."""

    def get_page_comments(
        self, page_id: str, *, return_markdown: bool = True
    ) -> list[ConfluenceComment]:
        """
        Get all comments for a specific page.

        Args:
            page_id: The ID of the page to get comments from
            return_markdown: When True, returns content in markdown format,
                           otherwise returns raw HTML (keyword-only)

        Returns:
            List of ConfluenceComment models containing comment content and metadata
        """
        try:
            # Get page info to extract space details
            page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
            space_key = page.get("space", {}).get("key", "")

            # Get comments with expanded content
            comments_response = self.confluence.get_page_comments(
                content_id=page_id, expand="body.view.value,version", depth="all"
            )

            # Process each comment
            comment_models = []
            for comment_data in comments_response.get("results", []):
                # Get the content based on format
                body = comment_data["body"]["view"]["value"]
                processed_html, processed_markdown = (
                    self.preprocessor.process_html_content(
                        body, space_key=space_key, confluence_client=self.confluence
                    )
                )

                # Create a copy of the comment data to modify
                modified_comment_data = comment_data.copy()

                # Modify the body value based on the return format
                if "body" not in modified_comment_data:
                    modified_comment_data["body"] = {}
                if "view" not in modified_comment_data["body"]:
                    modified_comment_data["body"]["view"] = {}

                # Set the appropriate content based on return format
                modified_comment_data["body"]["view"]["value"] = (
                    processed_markdown if return_markdown else processed_html
                )

                # Create the model with the processed content
                comment_model = ConfluenceComment.from_api_response(
                    modified_comment_data,
                    base_url=self.config.url,
                )

                comment_models.append(comment_model)

            return comment_models

        except KeyError as e:
            logger.error(f"Missing key in comment data: {str(e)}")
            return []
        except requests.RequestException as e:
            logger.error(f"Network error when fetching comments: {str(e)}")
            return []
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing comment data: {str(e)}")
            return []
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error fetching comments: {str(e)}")
            logger.debug("Full exception details for comments:", exc_info=True)
            return []

    def add_comment(self, page_id: str, content: str) -> ConfluenceComment | None:
        """
        Add a comment to a Confluence page.

        Args:
            page_id: The ID of the page to add the comment to
            content: The content of the comment (in Confluence storage format)

        Returns:
            ConfluenceComment object if comment was added successfully, None otherwise
        """
        try:
            # Get page info to extract space details
            page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
            space_key = page.get("space", {}).get("key", "")

            # Convert markdown to Confluence storage format if needed
            # The atlassian-python-api expects content in Confluence storage format
            if not content.strip().startswith("<"):
                # If content doesn't appear to be HTML/XML, treat it as markdown
                content = self.preprocessor.markdown_to_confluence_storage(content)

            # Add the comment via the Confluence API
            response = self.confluence.add_comment(page_id, content)

            if not response:
                logger.error("Failed to add comment: empty response")
                return None

            # Process the comment to return a consistent model
            processed_html, processed_markdown = self.preprocessor.process_html_content(
                response.get("body", {}).get("view", {}).get("value", ""),
                space_key=space_key,
                confluence_client=self.confluence,
            )

            # Modify the response to include processed content
            modified_response = response.copy()
            if "body" not in modified_response:
                modified_response["body"] = {}
            if "view" not in modified_response["body"]:
                modified_response["body"]["view"] = {}

            modified_response["body"]["view"]["value"] = processed_markdown

            # Create and return the comment model
            return ConfluenceComment.from_api_response(
                modified_response,
                base_url=self.config.url,
            )

        except requests.RequestException as e:
            logger.error(f"Network error when adding comment: {str(e)}")
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error processing comment data: {str(e)}")
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error adding comment: {str(e)}")
            logger.debug("Full exception details for adding comment:", exc_info=True)
            return None

    def get_inline_comments(
        self, page_id: str, *, return_markdown: bool = True
    ) -> list[ConfluenceInlineComment]:
        """
        Get all inline comments for a specific page.

        Args:
            page_id: The ID of the page to get inline comments from
            return_markdown: When True, returns content in markdown format,
                           otherwise returns raw HTML (keyword-only)

        Returns:
            List of ConfluenceInlineComment models containing inline comment content and metadata
        """
        try:
            # Get page info to extract space details
            page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
            space_key = page.get("space", {}).get("key", "")

            # Use the Confluence REST API v2 to get inline comments
            # Note: This uses a direct HTTP request since atlassian-python-api may not support inline comments yet
            from urllib.parse import urljoin

            # Construct the inline comments endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'
            inline_comments_url = urljoin(base_url, f"wiki/api/v2/pages/{page_id}/inline-comments")

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Make the request
            response = requests.get(
                inline_comments_url,
                auth=auth,
                headers=headers,
                verify=self.config.verify_ssl
            )
            response.raise_for_status()

            inline_comments_response = response.json()

            # Process each inline comment
            comment_models = []
            for comment_data in inline_comments_response.get("results", []):
                # Get the content based on format
                body = ""
                if "body" in comment_data:
                    if "view" in comment_data["body"]:
                        body = comment_data["body"]["view"].get("value", "")
                    elif "storage" in comment_data["body"]:
                        body = comment_data["body"]["storage"].get("value", "")
                    elif "atlas_doc_format" in comment_data["body"]:
                        body = comment_data["body"]["atlas_doc_format"].get("value", "")

                processed_html, processed_markdown = (
                    self.preprocessor.process_html_content(
                        body, space_key=space_key, confluence_client=self.confluence
                    )
                )

                # Create a copy of the comment data to modify
                modified_comment_data = comment_data.copy()

                # Modify the body value based on the return format
                if "body" not in modified_comment_data:
                    modified_comment_data["body"] = {}
                if "view" not in modified_comment_data["body"]:
                    modified_comment_data["body"]["view"] = {}

                # Set the appropriate content based on return format
                modified_comment_data["body"]["view"]["value"] = (
                    processed_markdown if return_markdown else processed_html
                )

                # Create the model with the processed content
                comment_model = ConfluenceInlineComment.from_api_response(
                    modified_comment_data,
                    base_url=self.config.url,
                )

                comment_models.append(comment_model)

            return comment_models

        except requests.RequestException as e:
            logger.error(f"Network error when fetching inline comments: {str(e)}")
            return []
        except KeyError as e:
            logger.error(f"Missing key in inline comment data: {str(e)}")
            return []
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing inline comment data: {str(e)}")
            return []
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error fetching inline comments: {str(e)}")
            logger.debug("Full exception details for inline comments:", exc_info=True)
            return []

    def add_inline_comment(
        self,
        page_id: str,
        content: str,
        text_selection: str,
        text_selection_match_count: int = 1,
        text_selection_match_index: int = 0
    ) -> ConfluenceInlineComment | None:
        """
        Add an inline comment to a Confluence page.

        Args:
            page_id: The ID of the page to add the inline comment to
            content: The content of the comment (in markdown format)
            text_selection: The text that was selected for the inline comment
            text_selection_match_count: How many matches of the text exist (default: 1)
            text_selection_match_index: Which match to target (0-based, default: 0)

        Returns:
            ConfluenceInlineComment object if comment was added successfully, None otherwise
        """
        try:
            # Get page info to extract space details
            page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
            space_key = page.get("space", {}).get("key", "")

            # Convert markdown to Confluence storage format if needed
            if not content.strip().startswith("<"):
                # If content doesn't appear to be HTML/XML, treat it as markdown
                content = self.preprocessor.markdown_to_confluence_storage(content)

            # Use the Confluence REST API v2 to create inline comment
            from urllib.parse import urljoin

            # Construct the inline comments endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'
            inline_comments_url = urljoin(base_url, "wiki/api/v2/inline-comments")

            # Prepare the request body according to Confluence API specification
            request_body = {
                "pageId": page_id,
                "body": {
                    "representation": "storage",
                    "value": content
                },
                "inlineCommentProperties": {
                    "textSelection": text_selection,
                    "textSelectionMatchCount": text_selection_match_count,
                    "textSelectionMatchIndex": text_selection_match_index
                }
            }

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Debug logging
            logger.debug(f"Making POST request to: {inline_comments_url}")
            logger.debug(f"Request body: {request_body}")
            logger.debug(f"Headers: {headers}")

            # Make the request
            response = requests.post(
                inline_comments_url,
                auth=auth,
                headers=headers,
                json=request_body,
                verify=self.config.verify_ssl
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content: {response.text}")

            response.raise_for_status()

            response_data = response.json()

            if not response_data:
                logger.error("Failed to add inline comment: empty response")
                return None

            # Log successful response for debugging
            logger.info(f"Successfully created inline comment with ID: {response_data.get('id', 'unknown')}")

            # Process the comment to return a consistent model based on API v2 response structure
            body_content = ""
            if "body" in response_data:
                # API v2 returns body with storage, atlas_doc_format, and view
                if "view" in response_data["body"]:
                    body_content = response_data["body"]["view"].get("value", "")
                elif "storage" in response_data["body"]:
                    body_content = response_data["body"]["storage"].get("value", "")
                elif "atlas_doc_format" in response_data["body"]:
                    body_content = response_data["body"]["atlas_doc_format"].get("value", "")

            _, processed_markdown = self.preprocessor.process_html_content(
                body_content,
                space_key=space_key,
                confluence_client=self.confluence,
            )

            # Modify the response to include processed content
            modified_response = response_data.copy()
            if "body" not in modified_response:
                modified_response["body"] = {}
            if "view" not in modified_response["body"]:
                modified_response["body"]["view"] = {}

            modified_response["body"]["view"]["value"] = processed_markdown

            # Create and return the inline comment model
            return ConfluenceInlineComment.from_api_response(
                modified_response,
                base_url=self.config.url,
            )

        except requests.RequestException as e:
            logger.error(f"Network error when adding inline comment to page {page_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except (ValueError, TypeError, KeyError
        ) as e:
            logger.error(f"Error processing inline comment data for page {page_id}: {str(e)}")
            logger.debug("Full exception details for data processing:", exc_info=True)
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error adding inline comment to page {page_id}: {str(e)}")
            logger.debug("Full exception details for adding inline comment:", exc_info=True)
            return None

    def get_inline_comment_by_id(self, comment_id: str) -> ConfluenceInlineComment | None:
        """
        Get a specific inline comment by its ID.

        Args:
            comment_id: The ID of the inline comment to retrieve

        Returns:
            ConfluenceInlineComment object if found, None otherwise
        """
        try:
            # Use the Confluence REST API v2 to get specific inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'
            inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json"}

            # Debug logging
            logger.debug(f"Making GET request to: {inline_comment_url}")

            # Make the request
            response = requests.get(
                inline_comment_url,
                auth=auth,
                headers=headers,
                verify=self.config.verify_ssl
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text}")

            response.raise_for_status()

            comment_data = response.json()

            if not comment_data:
                logger.error(f"Failed to get inline comment {comment_id}: empty response")
                return None

            # Get page info to extract space details for content processing
            page_id = comment_data.get("pageId")
            space_key = ""
            if page_id:
                try:
                    page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
                    space_key = page.get("space", {}).get("key", "")
                except Exception:
                    # If we can't get page info, continue without space context
                    pass

            # Get the content based on format
            body_content = ""
            if "body" in comment_data:
                if "view" in comment_data["body"]:
                    body_content = comment_data["body"]["view"].get("value", "")
                elif "storage" in comment_data["body"]:
                    body_content = comment_data["body"]["storage"].get("value", "")
                elif "atlas_doc_format" in comment_data["body"]:
                    body_content = comment_data["body"]["atlas_doc_format"].get("value", "")

            _, processed_markdown = self.preprocessor.process_html_content(
                body_content, space_key=space_key, confluence_client=self.confluence
            )

            # Create a copy of the comment data to modify
            modified_comment_data = comment_data.copy()

            # Modify the body value to include processed markdown
            if "body" not in modified_comment_data:
                modified_comment_data["body"] = {}
            if "view" not in modified_comment_data["body"]:
                modified_comment_data["body"]["view"] = {}

            modified_comment_data["body"]["view"]["value"] = processed_markdown

            # Create the model with the processed content
            return ConfluenceInlineComment.from_api_response(
                modified_comment_data,
                base_url=self.config.url,
            )

        except requests.RequestException as e:
            logger.error(f"Network error when fetching inline comment {comment_id}: {str(e)}")
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error processing inline comment data for {comment_id}: {str(e)}")
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error fetching inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for fetching inline comment:", exc_info=True)
            return None

    def update_inline_comment(
        self,
        comment_id: str,
        content: str,
        version_number: int,
        version_message: str = "",
        resolved: bool = False
    ) -> ConfluenceInlineComment | None:
        """
        Update an existing inline comment on a Confluence page.

        Args:
            comment_id: The ID of the inline comment to update
            content: The new content of the comment (in markdown format)
            version_number: Current version number (required for optimistic locking)
            version_message: Optional message for this version
            resolved: Whether to mark the comment as resolved

        Returns:
            ConfluenceInlineComment object if comment was updated successfully, None otherwise
        """
        try:
            # Convert markdown to Confluence storage format if needed
            if not content.strip().startswith("<"):
                # If content doesn't appear to be HTML/XML, treat it as markdown
                content = self.preprocessor.markdown_to_confluence_storage(content)

            # Use the Confluence REST API v2 to update inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'
            inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")

            # Prepare the request body according to Confluence API specification
            request_body = {
                "version": {
                    "number": version_number,
                    "message": version_message
                },
                "body": {
                    "representation": "storage",
                    "value": content
                },
                "resolved": resolved
            }

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Debug logging
            logger.debug(f"Making PUT request to: {inline_comment_url}")
            logger.debug(f"Request body: {request_body}")

            # Make the request
            response = requests.put(
                inline_comment_url,
                auth=auth,
                headers=headers,
                json=request_body,
                verify=self.config.verify_ssl
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content: {response.text}")

            response.raise_for_status()

            response_data = response.json()

            if not response_data:
                logger.error("Failed to update inline comment: empty response")
                return None

            # Log successful response for debugging
            logger.info(f"Successfully updated inline comment with ID: {response_data.get('id', 'unknown')}")

            # Get page info to extract space details for content processing
            page_id = response_data.get("pageId")
            space_key = ""
            if page_id:
                try:
                    page = self.confluence.get_page_by_id(page_id=page_id, expand="space")
                    space_key = page.get("space", {}).get("key", "")
                except Exception:
                    # If we can't get page info, continue without space context
                    pass

            # Process the comment to return a consistent model based on API v2 response structure
            body_content = ""
            if "body" in response_data:
                # API v2 returns body with storage, atlas_doc_format, and view
                if "view" in response_data["body"]:
                    body_content = response_data["body"]["view"].get("value", "")
                elif "storage" in response_data["body"]:
                    body_content = response_data["body"]["storage"].get("value", "")
                elif "atlas_doc_format" in response_data["body"]:
                    body_content = response_data["body"]["atlas_doc_format"].get("value", "")

            _, processed_markdown = self.preprocessor.process_html_content(
                body_content,
                space_key=space_key,
                confluence_client=self.confluence,
            )

            # Modify the response to include processed content
            modified_response = response_data.copy()
            if "body" not in modified_response:
                modified_response["body"] = {}
            if "view" not in modified_response["body"]:
                modified_response["body"]["view"] = {}

            modified_response["body"]["view"]["value"] = processed_markdown

            # Create and return the inline comment model
            return ConfluenceInlineComment.from_api_response(
                modified_response,
                base_url=self.config.url,
            )

        except requests.RequestException as e:
            logger.error(f"Network error when updating inline comment {comment_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error processing inline comment update for {comment_id}: {str(e)}")
            logger.debug("Full exception details for data processing:", exc_info=True)
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error updating inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for updating inline comment:", exc_info=True)
            return None

    def delete_inline_comment(self, comment_id: str) -> bool:
        """
        Delete an inline comment from a Confluence page.

        Args:
            comment_id: The ID of the inline comment to delete

        Returns:
            True if comment was deleted successfully, False otherwise
        """
        try:
            # Use the Confluence REST API v2 to delete inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'
            inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json"}

            # Debug logging
            logger.debug(f"Making DELETE request to: {inline_comment_url}")

            # Make the request
            response = requests.delete(
                inline_comment_url,
                auth=auth,
                headers=headers,
                verify=self.config.verify_ssl
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content: {response.text}")

            # API returns 204 No Content on successful deletion
            if response.status_code == 204:
                logger.info(f"Successfully deleted inline comment with ID: {comment_id}")
                return True
            else:
                response.raise_for_status()
                return False

        except requests.RequestException as e:
            logger.error(f"Network error when deleting inline comment {comment_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return False
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error deleting inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for deleting inline comment:", exc_info=True)
            return False
