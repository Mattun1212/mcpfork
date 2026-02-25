
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
            logger.debug("Full exception details for comments", exc_info=True)
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
            logger.debug("Full exception details for adding comment", exc_info=True)
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

            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            # Use the Confluence REST API to get inline comments
            # Note: This uses a direct HTTP request since atlassian-python-api may not support inline comments yet
            from urllib.parse import urljoin

            # Construct the inline comments endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

            if is_cloud:
                # Confluence Cloud uses API v2
                inline_comments_url = urljoin(base_url, "wiki/api/v2/inline-comments")
                params = {"pageId": page_id}
            else:
                # Confluence Server/Data Center uses API v1
                inline_comments_url = urljoin(base_url, f"rest/api/content/{page_id}/child/comment")
                params = {"expand": "body.view.value,version,extensions.inlineProperties"}

            # Make the request with retry logic for rate limiting
            import time
            max_retries = 3
            retry_delay = 1.0  # seconds

            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        inline_comments_url,
                        auth=auth,
                        headers=headers,
                        params=params,
                        verify=self.config.verify_ssl
                    )
                    response.raise_for_status()
                    response_data = response.json()

                    # For Server/Data Center, check if we got results
                    # If empty and not the last attempt, retry after delay
                    if not is_cloud:
                        result_count = len(response_data.get("results", []))
                        if result_count == 0 and attempt < max_retries - 1:
                            logger.warning(f"[DEBUG] Got 0 results on attempt {attempt + 1}, retrying after {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue

                    # Success, break out of retry loop
                    break

                except requests.exceptions.HTTPError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"[DEBUG] HTTP error on attempt {attempt + 1}: {e}, retrying after {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise

            # Filter inline comments for Server/Data Center
            if is_cloud:
                inline_comments_response = response_data
            else:
                # For Server/Data Center, filter comments with location="inline"
                all_comments = response_data.get("results", [])
                inline_comments = [
                    comment for comment in all_comments
                    if comment.get("extensions", {}).get("location") == "inline"
                ]

                inline_comments_response = {
                    "results": inline_comments
                }

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

                # For Server/Data Center, map extensions.inlineProperties to API v2 format
                if not is_cloud and "extensions" in modified_comment_data:
                    inline_props = modified_comment_data["extensions"].get("inlineProperties", {})
                    if inline_props:
                        # Map Server/Data Center format to API v2 format
                        modified_comment_data["inlineCommentProperties"] = {
                            "textSelection": inline_props.get("originalSelection", ""),
                            "textSelectionMatchCount": inline_props.get("numMatches", 1),
                            "textSelectionMatchIndex": inline_props.get("matchIndex", 0)
                        }
                        # Also add pageId from container
                        if "container" in modified_comment_data:
                            modified_comment_data["pageId"] = modified_comment_data["container"].get("id")

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
            logger.debug("Full exception details for inline comments", exc_info=True)
            return []

    def _count_text_matches(self, page_content: str, text_selection: str) -> int:
        """
        Count the number of occurrences of text_selection in page content.

        Args:
            page_content: The page content (HTML or text)
            text_selection: The text to count

        Returns:
            Number of matches found
        """
        if not page_content or not text_selection:
            return 0

        # Convert HTML to plain text for more accurate matching
        from html import unescape
        import re

        # Remove HTML tags and decode HTML entities
        text_only = re.sub(r'<[^>]+>', '', page_content)
        text_only = unescape(text_only)

        # Count occurrences
        return text_only.count(text_selection)

    def add_inline_comment(
        self,
        page_id: str,
        content: str,
        text_selection: str,
        text_selection_match_count: int | None = None,
        text_selection_match_index: int = 0,
        auto_detect_matches: bool = True
    ) -> tuple[ConfluenceInlineComment | None, str | None]:
        """
        Add an inline comment to a Confluence page.

        Args:
            page_id: The ID of the page to add the inline comment to
            content: The content of the comment (in markdown format)
            text_selection: The text that was selected for the inline comment
            text_selection_match_count: How many matches of the text exist (if None and auto_detect_matches=True, will be auto-detected)
            text_selection_match_index: Which match to target (0-based, default: 0)
            auto_detect_matches: Whether to automatically detect the number of matches (default: True)

        Returns:
            Tuple of (ConfluenceInlineComment or None, error_message or None)
            - On success: (comment_object, None)
            - On failure: (None, error_message)
        """
        try:
            # Get page info to extract space details and content for auto-detection
            page = self.confluence.get_page_by_id(
                page_id=page_id,
                expand="space,body.storage" if auto_detect_matches and text_selection_match_count is None else "space"
            )
            space_key = page.get("space", {}).get("key", "")

            # Auto-detect match count if requested and not provided
            if auto_detect_matches and text_selection_match_count is None:
                page_content = page.get("body", {}).get("storage", {}).get("value", "")
                text_selection_match_count = self._count_text_matches(page_content, text_selection)
                logger.info(f"Auto-detected {text_selection_match_count} matches for text selection: {text_selection[:50]}...")

                if text_selection_match_count == 0:
                    error_msg = f"No matches found for text selection: '{text_selection[:100]}...'"
                    logger.warning(error_msg)
                    return None, error_msg
                elif text_selection_match_index >= text_selection_match_count:
                    error_msg = f"text_selection_match_index ({text_selection_match_index}) is out of range. Found {text_selection_match_count} matches."
                    logger.error(error_msg)
                    return None, error_msg
            elif text_selection_match_count is None:
                # Fallback to default if auto_detect is disabled
                text_selection_match_count = 1

            # Convert markdown to Confluence storage format if needed
            if not content.strip().startswith("<"):
                # If content doesn't appear to be HTML/XML, treat it as markdown
                content = self.preprocessor.markdown_to_confluence_storage(content)

            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            from urllib.parse import urljoin
            import time

            # Get authentication
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

            # Construct the URL and request body based on Confluence version
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            if is_cloud:
                # Confluence Cloud uses API v2
                inline_comments_url = urljoin(base_url, "wiki/api/v2/inline-comments")
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
            else:
                # Confluence Server/Data Center uses API v1
                inline_comments_url = urljoin(base_url, "rest/api/content")
                request_body = {
                    "type": "comment",
                    "container": {
                        "id": page_id,
                        "type": "page"
                    },
                    "body": {
                        "storage": {
                            "value": content,
                            "representation": "storage"
                        }
                    },
                    "extensions": {
                        "location": "inline",
                        "inlineProperties": {
                            "numMatches": text_selection_match_count,
                            "originalSelection": text_selection,
                            "matchIndex": text_selection_match_index,
                            "serializedHighlights": f'[["{text_selection}"]]',
                            "lastFetchTime": str(int(time.time()))
                        }
                    }
                }

            # Debug logging
            logger.debug(f"Making POST request to: {inline_comments_url}")
            logger.debug(f"Request body: {request_body}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Using {'Cloud' if is_cloud else 'Server/Data Center'} API")

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
                error_msg = "Failed to add inline comment: empty response from API"
                logger.error(error_msg)
                return None, error_msg

            # Log successful response for debugging
            logger.info(f"Successfully created inline comment with ID: {response_data.get('id', 'unknown')}")

            # Process the comment to return a consistent model
            body_content = ""
            if "body" in response_data:
                # Try different body formats
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
            inline_comment = ConfluenceInlineComment.from_api_response(
                modified_response,
                base_url=self.config.url,
            )
            return inline_comment, None

        except requests.RequestException as e:
            error_msg = f"Network error when adding inline comment to page {page_id}: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" | Status: {e.response.status_code} | Response: {e.response.text}"
                logger.error(error_msg)
            else:
                logger.error(error_msg)
            return None, error_msg
        except (ValueError, TypeError, KeyError
        ) as e:
            error_msg = f"Error processing inline comment data for page {page_id}: {str(e)}"
            logger.error(error_msg)
            logger.debug("Full exception details for data processing", exc_info=True)
            return None, error_msg
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            error_msg = f"Unexpected error adding inline comment to page {page_id}: {str(e)}"
            logger.error(error_msg)
            logger.debug("Full exception details for adding inline comment", exc_info=True)
            return None, error_msg

    def get_inline_comment_by_id(self, comment_id: str) -> ConfluenceInlineComment | None:
        """
        Get a specific inline comment by its ID.

        Args:
            comment_id: The ID of the inline comment to retrieve

        Returns:
            ConfluenceInlineComment object if found, None otherwise
        """
        try:
            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            # Use the Confluence REST API to get specific inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            if is_cloud:
                # Confluence Cloud uses API v2
                inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")
                params = {}
            else:
                # Confluence Server/Data Center uses API v1
                inline_comment_url = urljoin(base_url, f"rest/api/content/{comment_id}")
                params = {"expand": "body.view.value,version,extensions.inlineProperties,container"}

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

            # Debug logging
            logger.debug(f"Making GET request to: {inline_comment_url}")

            # Make the request
            response = requests.get(
                inline_comment_url,
                auth=auth,
                headers=headers,
                params=params,
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

            # For Server/Data Center, map extensions.inlineProperties to API v2 format
            if not is_cloud and "extensions" in modified_comment_data:
                inline_props = modified_comment_data["extensions"].get("inlineProperties", {})
                if inline_props:
                    # Map Server/Data Center format to API v2 format
                    modified_comment_data["inlineCommentProperties"] = {
                        "textSelection": inline_props.get("originalSelection", ""),
                        "textSelectionMatchCount": inline_props.get("numMatches", 1),
                        "textSelectionMatchIndex": inline_props.get("matchIndex", 0)
                    }
                    # Also add pageId from container
                    if "container" in modified_comment_data:
                        modified_comment_data["pageId"] = modified_comment_data["container"].get("id")

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
            logger.debug("Full exception details for fetching inline comment", exc_info=True)
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

            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            # Use the Confluence REST API to update inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            if is_cloud:
                # Confluence Cloud uses API v2
                inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")
                # Prepare the request body according to Confluence API v2 specification
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
            else:
                # Confluence Server/Data Center uses API v1
                inline_comment_url = urljoin(base_url, f"rest/api/content/{comment_id}")
                # Prepare the request body according to Confluence API v1 specification
                request_body = {
                    "version": {
                        "number": version_number,
                        "message": version_message
                    },
                    "body": {
                        "storage": {
                            "value": content,
                            "representation": "storage"
                        }
                    }
                }
                # Note: resolved status is not directly supported in API v1 update

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

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

            # For Server/Data Center, map extensions.inlineProperties to API v2 format
            if not is_cloud and "extensions" in modified_response:
                inline_props = modified_response["extensions"].get("inlineProperties", {})
                if inline_props:
                    # Map Server/Data Center format to API v2 format
                    modified_response["inlineCommentProperties"] = {
                        "textSelection": inline_props.get("originalSelection", ""),
                        "textSelectionMatchCount": inline_props.get("numMatches", 1),
                        "textSelectionMatchIndex": inline_props.get("matchIndex", 0)
                    }
                    # Also add pageId from container
                    if "container" in modified_response:
                        modified_response["pageId"] = modified_response["container"].get("id")

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
            logger.debug("Full exception details for data processing", exc_info=True)
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error updating inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for updating inline comment", exc_info=True)
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
            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            # Use the Confluence REST API to delete inline comment
            from urllib.parse import urljoin

            # Construct the inline comment endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            if is_cloud:
                # Confluence Cloud uses API v2
                inline_comment_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}")
            else:
                # Confluence Server/Data Center uses API v1
                inline_comment_url = urljoin(base_url, f"rest/api/content/{comment_id}")

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

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
            logger.debug("Full exception details for deleting inline comment", exc_info=True)
            return False

    def get_inline_comment_children(
        self,
        comment_id: str,
        return_markdown: bool = True,
        limit: int = 25,
        cursor: str | None = None
    ) -> list[ConfluenceInlineComment]:
        """
        Get child comments of a specific inline comment.

        Args:
            comment_id: The ID of the parent inline comment
            return_markdown: When True, returns content in markdown format,
                           otherwise returns raw HTML (default: True)
            limit: Maximum number of child comments to return (default: 25)
            cursor: Cursor for pagination (optional)

        Returns:
            List of ConfluenceInlineComment models containing child comment content and metadata
        """
        try:
            # Check if this is Confluence Cloud or Server/Data Center
            is_cloud = self.config.is_cloud

            # Use the Confluence REST API to get child comments
            from urllib.parse import urljoin

            # Construct the inline comment children endpoint URL
            base_url = self.config.url
            if not base_url.endswith('/'):
                base_url += '/'

            if is_cloud:
                # Confluence Cloud uses API v2
                children_url = urljoin(base_url, f"wiki/api/v2/inline-comments/{comment_id}/children")
                # Prepare query parameters
                params = {"limit": limit}
                if cursor:
                    params["cursor"] = cursor
            else:
                # Confluence Server/Data Center uses API v1
                # Child comments are retrieved using the same endpoint as regular child comments
                children_url = urljoin(base_url, f"rest/api/content/{comment_id}/child/comment")
                params = {"expand": "body.view.value,version,extensions.inlineProperties,container"}

            # Get authentication headers
            auth = self.confluence._session.auth if hasattr(self.confluence, '_session') else None
            headers = {"Accept": "application/json"}

            # Copy Authorization header from session if it exists (for Personal Access Token auth)
            if hasattr(self.confluence, '_session') and 'Authorization' in self.confluence._session.headers:
                headers['Authorization'] = self.confluence._session.headers['Authorization']

            # Debug logging
            logger.debug(f"Making GET request to: {children_url}")
            logger.debug(f"Query params: {params}")

            # Make the request
            response = requests.get(
                children_url,
                auth=auth,
                headers=headers,
                params=params,
                verify=self.config.verify_ssl
            )

            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text}")

            response.raise_for_status()

            response_data = response.json()

            if not response_data or "results" not in response_data:
                logger.info(f"No child comments found for inline comment {comment_id}")
                return []

            # Process each child comment
            comment_models = []
            for comment_data in response_data.get("results", []):
                # Get the content based on format
                body_content = ""
                if "body" in comment_data:
                    body = comment_data["body"]
                    if "view" in body and body["view"].get("value"):
                        body_content = body["view"]["value"]
                    elif "storage" in body and body["storage"].get("value"):
                        body_content = body["storage"]["value"]
                    elif "atlas_doc_format" in body and body["atlas_doc_format"].get("value"):
                        body_content = body["atlas_doc_format"]["value"]

                # Process HTML content if we have it
                if body_content:
                    processed_html, processed_markdown = (
                        self.preprocessor.process_html_content(
                            body_content, space_key="", confluence_client=self.confluence
                        )
                    )

                    # Create a copy of the comment data to modify
                    modified_comment_data = comment_data.copy()

                    # For Server/Data Center, map extensions.inlineProperties to API v2 format
                    if not is_cloud and "extensions" in modified_comment_data:
                        inline_props = modified_comment_data["extensions"].get("inlineProperties", {})
                        if inline_props:
                            # Map Server/Data Center format to API v2 format
                            modified_comment_data["inlineCommentProperties"] = {
                                "textSelection": inline_props.get("originalSelection", ""),
                                "textSelectionMatchCount": inline_props.get("numMatches", 1),
                                "textSelectionMatchIndex": inline_props.get("matchIndex", 0)
                            }
                            # Also add pageId from container
                            if "container" in modified_comment_data:
                                modified_comment_data["pageId"] = modified_comment_data["container"].get("id")
                        # Set parent comment ID for Server/Data Center
                        modified_comment_data["parentCommentId"] = comment_id

                    # Modify the body value based on the return format
                    if "body" not in modified_comment_data:
                        modified_comment_data["body"] = {}
                    if "view" not in modified_comment_data["body"]:
                        modified_comment_data["body"]["view"] = {}

                    # Set the appropriate content based on return format
                    modified_comment_data["body"]["view"]["value"] = (
                        processed_markdown if return_markdown else processed_html
                    )
                else:
                    modified_comment_data = comment_data

                # Create the model with the processed content
                comment_model = ConfluenceInlineComment.from_api_response(
                    modified_comment_data,
                    base_url=self.config.url,
                )

                comment_models.append(comment_model)

            logger.info(f"Retrieved {len(comment_models)} child comments for inline comment {comment_id}")
            return comment_models

        except requests.RequestException as e:
            logger.error(f"Network error when fetching child comments for inline comment {comment_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return []
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error processing child comments data for inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for child comments", exc_info=True)
            return []
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error fetching child comments for inline comment {comment_id}: {str(e)}")
            logger.debug("Full exception details for child comments", exc_info=True)
            return []
