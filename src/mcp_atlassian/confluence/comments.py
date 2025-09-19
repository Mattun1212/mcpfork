
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
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
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

            # Make the request
            response = requests.post(
                inline_comments_url,
                auth=auth,
                headers=headers,
                json=request_body,
                verify=self.config.verify_ssl
            )
            response.raise_for_status()

            response_data = response.json()

            if not response_data:
                logger.error("Failed to add inline comment: empty response")
                return None

            # Process the comment to return a consistent model
            body_content = ""
            if "body" in response_data:
                if "view" in response_data["body"]:
                    body_content = response_data["body"]["view"].get("value", "")
                elif "storage" in response_data["body"]:
                    body_content = response_data["body"]["storage"].get("value", "")

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
            logger.error(f"Network error when adding inline comment: {str(e)}")
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error processing inline comment data: {str(e)}")
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error adding inline comment: {str(e)}")
            logger.debug("Full exception details for adding inline comment:", exc_info=True)
            return None
