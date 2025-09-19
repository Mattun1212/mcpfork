"""
Confluence comment models.
This module provides Pydantic models for Confluence page comments.
"""

import logging
from typing import Any

from ..base import ApiModel, TimestampMixin
from ..constants import (
    CONFLUENCE_DEFAULT_ID,
    EMPTY_STRING,
)

# Import other necessary models using relative imports
from .common import ConfluenceUser

logger = logging.getLogger(__name__)


class ConfluenceComment(ApiModel, TimestampMixin):
    """
    Model representing a Confluence comment.
    """

    id: str = CONFLUENCE_DEFAULT_ID
    title: str | None = None
    body: str = EMPTY_STRING
    created: str = EMPTY_STRING
    updated: str = EMPTY_STRING
    author: ConfluenceUser | None = None
    type: str = "comment"  # "comment", "page", etc.


class ConfluenceInlineComment(ApiModel, TimestampMixin):
    """
    Model representing a Confluence inline comment.
    """

    id: str = CONFLUENCE_DEFAULT_ID
    title: str | None = None
    body: str = EMPTY_STRING
    created: str = EMPTY_STRING
    updated: str = EMPTY_STRING
    author: ConfluenceUser | None = None
    type: str = "comment"
    page_id: str | None = None
    blog_post_id: str | None = None
    resolution_status: str = "open"  # "open", "resolved"
    inline_marker_ref: str | None = None
    inline_original_selection: str | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "ConfluenceInlineComment":
        """
        Create a ConfluenceInlineComment from a Confluence API response.

        Args:
            data: The inline comment data from the Confluence API

        Returns:
            A ConfluenceInlineComment instance
        """
        if not data:
            return cls()

        author = None
        if author_data := data.get("author"):
            author = ConfluenceUser.from_api_response(author_data)
        # Try to get author from version.by if direct author is not available
        elif version_data := data.get("version"):
            if by_data := version_data.get("by"):
                author = ConfluenceUser.from_api_response(by_data)

        # For title, try to extract from different locations
        title = data.get("title")
        container = data.get("container")
        if not title and container:
            title = container.get("title")

        # Extract inline comment specific properties
        properties = data.get("properties", {})
        inline_marker_ref = properties.get("inlineMarkerRef") or properties.get("inline-marker-ref")
        inline_original_selection = properties.get("inlineOriginalSelection") or properties.get("inline-original-selection")

        # Try to get body content from different formats
        body_content = EMPTY_STRING
        body = data.get("body", {})
        if "view" in body and body["view"].get("value"):
            body_content = body["view"]["value"]
        elif "storage" in body and body["storage"].get("value"):
            body_content = body["storage"]["value"]
        elif "atlas_doc_format" in body and body["atlas_doc_format"].get("value"):
            body_content = body["atlas_doc_format"]["value"]

        return cls(
            id=str(data.get("id", CONFLUENCE_DEFAULT_ID)),
            title=title,
            body=body_content,
            created=data.get("created", EMPTY_STRING),
            updated=data.get("updated", EMPTY_STRING),
            author=author,
            type=data.get("type", "comment"),
            page_id=data.get("pageId"),
            blog_post_id=data.get("blogPostId"),
            resolution_status=data.get("resolutionStatus", "open"),
            inline_marker_ref=inline_marker_ref,
            inline_original_selection=inline_original_selection,
        )

    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for API response."""
        result = {
            "id": self.id,
            "body": self.body,
            "created": self.format_timestamp(self.created),
            "updated": self.format_timestamp(self.updated),
            "resolution_status": self.resolution_status,
        }

        if self.title:
            result["title"] = self.title

        if self.author:
            result["author"] = self.author.display_name

        if self.page_id:
            result["page_id"] = self.page_id

        if self.blog_post_id:
            result["blog_post_id"] = self.blog_post_id

        if self.inline_marker_ref:
            result["inline_marker_ref"] = self.inline_marker_ref

        if self.inline_original_selection:
            result["inline_original_selection"] = self.inline_original_selection

        return result


class ConfluenceComment(ApiModel, TimestampMixin):
    """
    Model representing a Confluence regular comment.
    """

    id: str = CONFLUENCE_DEFAULT_ID
    title: str | None = None
    body: str = EMPTY_STRING
    created: str = EMPTY_STRING
    updated: str = EMPTY_STRING
    author: ConfluenceUser | None = None
    type: str = "comment"  # "comment", "page", etc.

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "ConfluenceComment":
        """
        Create a ConfluenceComment from a Confluence API response.

        Args:
            data: The comment data from the Confluence API

        Returns:
            A ConfluenceComment instance
        """
        if not data:
            return cls()

        author = None
        if author_data := data.get("author"):
            author = ConfluenceUser.from_api_response(author_data)
        # Try to get author from version.by if direct author is not available
        elif version_data := data.get("version"):
            if by_data := version_data.get("by"):
                author = ConfluenceUser.from_api_response(by_data)

        # For title, try to extract from different locations
        title = data.get("title")
        container = data.get("container")
        if not title and container:
            title = container.get("title")

        return cls(
            id=str(data.get("id", CONFLUENCE_DEFAULT_ID)),
            title=title,
            body=data.get("body", {}).get("view", {}).get("value", EMPTY_STRING),
            created=data.get("created", EMPTY_STRING),
            updated=data.get("updated", EMPTY_STRING),
            author=author,
            type=data.get("type", "comment"),
        )

    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for API response."""
        result = {
            "id": self.id,
            "body": self.body,
            "created": self.format_timestamp(self.created),
            "updated": self.format_timestamp(self.updated),
        }

        if self.title:
            result["title"] = self.title

        if self.author:
            result["author"] = self.author.display_name

        return result
