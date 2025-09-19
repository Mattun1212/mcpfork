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
                    "inlineCommentProperties": {
                        "textSelection": "selected text",
                        "textSelectionMatchCount": 1,
                        "textSelectionMatchIndex": 0
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
            assert result[0].text_selection == "selected text"
            assert result[0].text_selection_match_count == 1
            assert result[0].text_selection_match_index == 0

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
        # Mock the page response with content for auto-detection
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"},
            "body": {
                "storage": {
                    "value": "<p>This is new selection content</p><p>Other content</p><p>This is new selection content</p>"
                }
            }
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
            "inlineCommentProperties": {
                "textSelection": "new selection",
                "textSelectionMatchCount": 1,
                "textSelectionMatchIndex": 0
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
                text_selection="new selection"
            )

            # Verify results
            assert result is not None
            assert isinstance(result, ConfluenceInlineComment)
            assert result.id == "54321"
            assert result.body == "This is a new inline comment"
            assert result.page_id == "67890"
            assert result.text_selection == "new selection"
            assert result.text_selection_match_count == 1
            assert result.text_selection_match_index == 0

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
                text_selection="new selection"
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
                text_selection="new selection"
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
                text_selection="selection"
            )

            # Should not call markdown conversion
            comments_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

            # Verify the request was made with the original HTML
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['body']['storage']['value'] == "<p>HTML content</p>"
            assert request_body['inlineCommentProperties']['textSelection'] == "selection"

    def test_add_inline_comment_auto_detect_success(self, comments_mixin):
        """Test successful creation of inline comment with auto-detection."""
        # Mock the page response with content containing multiple matches
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"},
            "body": {
                "storage": {
                    "value": "<p>セットJANの価格関連情報について</p><p>他の内容</p><p>セットJANの価格関連情報も重要</p><p>セットJANの価格関連情報を確認</p>"
                }
            }
        }

        # Mock markdown to storage conversion
        comments_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            "<p>確認しました</p>"
        )

        # Mock the preprocessor for processing response
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>確認しました</p>",
            "確認しました"
        )

        mock_response_data = {
            "id": "54321",
            "body": {
                "view": {
                    "value": "<p>確認しました</p>"
                }
            },
            "pageId": "67890",
            "resolutionStatus": "open",
            "inlineCommentProperties": {
                "textSelection": "セットJANの価格関連情報",
                "textSelectionMatchCount": 3,
                "textSelectionMatchIndex": 1
            }
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Execute the method with auto-detection enabled
            result = comments_mixin.add_inline_comment(
                page_id="67890",
                content="確認しました",
                text_selection="セットJANの価格関連情報",
                text_selection_match_index=1,
                auto_detect_matches=True
            )

            # Verify results
            assert result is not None
            assert isinstance(result, ConfluenceInlineComment)
            assert result.id == "54321"
            assert result.body == "確認しました"
            assert result.page_id == "67890"
            assert result.text_selection == "セットJANの価格関連情報"
            assert result.text_selection_match_count == 3
            assert result.text_selection_match_index == 1

            # Verify the API call was made with correct match count
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['inlineCommentProperties']['textSelectionMatchCount'] == 3
            assert request_body['inlineCommentProperties']['textSelectionMatchIndex'] == 1

    def test_add_inline_comment_auto_detect_no_matches(self, comments_mixin):
        """Test handling when no matches are found during auto-detection."""
        # Mock the page response with content that doesn't contain the text
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"},
            "body": {
                "storage": {
                    "value": "<p>Different content here</p>"
                }
            }
        }

        # Execute the method with auto-detection enabled
        result = comments_mixin.add_inline_comment(
            page_id="67890",
            content="確認しました",
            text_selection="存在しないテキスト",
            auto_detect_matches=True
        )

        # Should return None when no matches found
        assert result is None

    def test_add_inline_comment_auto_detect_index_out_of_range(self, comments_mixin):
        """Test handling when match index is out of range."""
        # Mock the page response with content containing only 2 matches
        comments_mixin.confluence.get_page_by_id.return_value = {
            "space": {"key": "TEST"},
            "body": {
                "storage": {
                    "value": "<p>テスト文字列がここにあります</p><p>テスト文字列が再度登場</p>"
                }
            }
        }

        # Execute the method with auto-detection enabled and index out of range
        result = comments_mixin.add_inline_comment(
            page_id="67890",
            content="確認しました",
            text_selection="テスト文字列",
            text_selection_match_index=5,  # Out of range (only 2 matches available)
            auto_detect_matches=True
        )

        # Should return None when index is out of range
        assert result is None

    def test_count_text_matches(self, comments_mixin):
        """Test the _count_text_matches helper method."""
        # HTML content with multiple matches
        html_content = "<p>セットJANの価格関連情報について</p><p>他の内容</p><p>セットJANの価格関連情報も重要</p><p>セットJANの価格関連情報を確認</p>"

        # Should find 3 matches
        count = comments_mixin._count_text_matches(html_content, "セットJANの価格関連情報")
        assert count == 3

        # Should find 0 matches for non-existent text
        count = comments_mixin._count_text_matches(html_content, "存在しないテキスト")
        assert count == 0

        # Should handle empty inputs
        assert comments_mixin._count_text_matches("", "test") == 0
        assert comments_mixin._count_text_matches("test content", "") == 0
        assert comments_mixin._count_text_matches("", "") == 0

        # Should handle HTML entities
        html_with_entities = "<p>Price &gt; 100 &amp; quality</p><p>Price > 100 & quality again</p>"
        count = comments_mixin._count_text_matches(html_with_entities, "Price > 100 & quality")
        assert count == 2

    def test_get_inline_comment_children_success(self, comments_mixin):
        """Test successful retrieval of child inline comments."""
        mock_child_response = {
            "results": [
                {
                    "id": "child1",
                    "status": "current",
                    "parentCommentId": "parent123",
                    "body": {
                        "view": {
                            "value": "<p>This is a child comment</p>"
                        }
                    },
                    "version": {
                        "createdAt": "2023-01-01T00:00:00.000Z",
                        "number": 1,
                        "authorId": "user123"
                    },
                    "resolutionStatus": "open"
                },
                {
                    "id": "child2",
                    "status": "current",
                    "parentCommentId": "parent123",
                    "body": {
                        "view": {
                            "value": "<p>Another child comment</p>"
                        }
                    },
                    "version": {
                        "createdAt": "2023-01-02T00:00:00.000Z",
                        "number": 1,
                        "authorId": "user456"
                    },
                    "resolutionStatus": "resolved"
                }
            ],
            "_links": {
                "next": "/wiki/api/v2/inline-comments/parent123/children?cursor=xyz123"
            }
        }

        # Mock the preprocessor
        comments_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed markdown"
        )

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_child_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute the method
            result = comments_mixin.get_inline_comment_children("parent123")

            # Verify results
            assert len(result) == 2
            assert isinstance(result[0], ConfluenceInlineComment)
            assert result[0].id == "child1"
            assert result[0].body == "Processed markdown"
            assert result[0].parent_comment_id == "parent123"
            assert result[0].resolution_status == "open"

            assert result[1].id == "child2"
            assert result[1].parent_comment_id == "parent123"
            assert result[1].resolution_status == "resolved"

            # Verify the API call was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "parent123/children" in call_args[0][0]
            assert call_args[1]['params']['limit'] == 25

    def test_get_inline_comment_children_with_pagination(self, comments_mixin):
        """Test child comment retrieval with pagination."""
        mock_response_data = {"results": []}

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute with pagination parameters
            result = comments_mixin.get_inline_comment_children(
                comment_id="parent123",
                limit=10,
                cursor="abc123"
            )

            # Verify pagination parameters were passed
            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['limit'] == 10
            assert params['cursor'] == "abc123"
            assert result == []

    def test_get_inline_comment_children_network_error(self, comments_mixin):
        """Test handling of network errors when fetching child comments."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            # Execute the method
            result = comments_mixin.get_inline_comment_children("parent123")

            # Should return empty list on error
            assert result == []

    def test_get_inline_comment_children_empty_response(self, comments_mixin):
        """Test handling of empty child comments response."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Execute the method
            result = comments_mixin.get_inline_comment_children("parent123")

            # Should return empty list
            assert result == []