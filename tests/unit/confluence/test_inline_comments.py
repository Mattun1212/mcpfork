"""Tests for Confluence inline comments functionality."""

from unittest.mock import Mock, patch

import pytest
import requests

from mcp_atlassian.confluence.comments import CommentsMixin
from mcp_atlassian.models.confluence import ConfluenceInlineComment


class TestInlineCommentsMixin:
    """Test class for CommentsMixin inline comments functionality."""

    @pytest.fixture
    def comments_mixin(self, confluence_client):
        """Create a CommentsMixin instance for testing."""
        # CommentsMixin inherits from ConfluenceClient, so we need to create it properly
        with patch(
            "mcp_atlassian.confluence.comments.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = CommentsMixin()
            # Copy the necessary attributes from our mocked client
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    @pytest.fixture
    def mock_inline_comment_response(self):
        """Mock inline comment API response."""
        return {
            "results": [
                {
                    "id": "12345",
                    "title": "Inline comment title",
                    "body": {
                        "view": {
                            "value": "<p>This is an inline comment</p>"
                        }
                    },
                    "created": "2023-01-01T00:00:00.000Z",
                    "updated": "2023-01-01T00:00:00.000Z",
                    "version": {
                        "by": {
                            "displayName": "Test User",
                            "accountId": "user123"
                        }
                    },
                    "pageId": "67890",
                    "resolutionStatus": "open",
                    "properties": {
                        "inlineMarkerRef": "marker123",
                        "inlineOriginalSelection": "selected text"
                    }
                }
            ]
        }

    def test_get_inline_comments_success(self, comments_mixin, mock_inline_comment_response):
        """Test successful retrieval of inline comments."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock the preprocessor
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>This is an inline comment</p>",
            "This is an inline comment"
        )

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_inline_comment_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute the method
            result = comments_mixin.get_inline_comments("67890")

            # Verify results
            assert len(result) == 1
            assert isinstance(result[0], ConfluenceInlineComment)
            assert result[0].id == "12345"
            assert result[0].body == "This is an inline comment"
            assert result[0].page_id == "67890"
            assert result[0].resolution_status == "open"
            assert result[0].inline_marker_ref == "marker123"
            assert result[0].inline_original_selection == "selected text"

    def test_get_inline_comments_with_html_return(self, comments_mixin, mock_inline_comment_response):
        """Test retrieval of inline comments with HTML format."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock the preprocessor
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>This is an inline comment</p>",
            "This is an inline comment"
        )

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_inline_comment_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute with HTML return format
            result = comments_mixin.get_inline_comments("67890", return_markdown=False)

            # Verify HTML content is returned
            assert len(result) == 1
            assert result[0].body == "<p>This is an inline comment</p>"

    def test_get_inline_comments_network_error(self, comments_mixin):
        """Test handling of network errors when fetching inline comments."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            # Execute the method
            result = comments_mixin.get_inline_comments("67890")

            # Should return empty list on error
            assert result == []

    def test_get_inline_comments_empty_response(self, comments_mixin):
        """Test handling of empty inline comments response."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute the method
            result = comments_mixin.get_inline_comments("67890")

            # Should return empty list
            assert result == []

    def test_add_inline_comment_success(self, comments_mixin):
        """Test successful creation of inline comment."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock markdown to storage conversion
        comments_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            "<p>This is a new inline comment</p>"
        )

        # Mock the preprocessor for processing response
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>This is a new inline comment</p>",
            "This is a new inline comment"
        )

        mock_response_data = {
            "id": "54321",
            "body": {
                "view": {
                    "value": "<p>This is a new inline comment</p>"
                }
            },
            "pageId": "67890",
            "resolutionStatus": "open",
            "properties": {
                "inlineMarkerRef": "new_marker",
                "inlineOriginalSelection": "new selection"
            }
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Execute the method
            result = comments_mixin.add_inline_comment(
                page_id="67890",
                content="This is a new inline comment",
                inline_marker_ref="new_marker",
                inline_original_selection="new selection"
            )

            # Verify results
            assert result is not None
            assert isinstance(result, ConfluenceInlineComment)
            assert result.id == "54321"
            assert result.body == "This is a new inline comment"
            assert result.page_id == "67890"
            assert result.inline_marker_ref == "new_marker"
            assert result.inline_original_selection == "new selection"

    def test_add_inline_comment_network_error(self, comments_mixin):
        """Test handling of network errors when adding inline comment."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock markdown to storage conversion
        comments_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            "<p>This is a new inline comment</p>"
        )

        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.RequestException("Network error")

            # Execute the method
            result = comments_mixin.add_inline_comment(
                page_id="67890",
                content="This is a new inline comment",
                inline_marker_ref="new_marker",
                inline_original_selection="new selection"
            )

            # Should return None on error
            assert result is None

    def test_add_inline_comment_empty_response(self, comments_mixin):
        """Test handling of empty response when adding inline comment."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock markdown to storage conversion
        comments_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            "<p>This is a new inline comment</p>"
        )

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = None
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Execute the method
            result = comments_mixin.add_inline_comment(
                page_id="67890",
                content="This is a new inline comment",
                inline_marker_ref="new_marker",
                inline_original_selection="new selection"
            )

            # Should return None on empty response
            assert result is None

    def test_add_inline_comment_with_html_content(self, comments_mixin):
        """Test adding inline comment with HTML content (should not convert)."""
        # Mock the page response
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"}
        }

        # Mock the preprocessor for processing response
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>HTML content</p>",
            "HTML content"
        )

        mock_response_data = {
            "id": "54321",
            "body": {
                "view": {
                    "value": "<p>HTML content</p>"
                }
            },
            "pageId": "67890"
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Execute with HTML content
            result = comments_mixin.add_inline_comment(
                page_id="67890",
                content="<p>HTML content</p>",
                inline_marker_ref="marker",
                inline_original_selection="selection"
            )

            # Should not call markdown conversion
            comments_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

            # Verify the request was made with the original HTML
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['body']['storage']['value'] == "<p>HTML content</p>"