"""
Confluence inline comment model (fork-specific).
Extracted from comment.py to isolate fork-specific code from upstream.
"""

import logging
from typing import Any

from ..base import ApiModel, TimestampMixin
from ..constants import (
    CONFLUENCE_DEFAULT_ID,
    EMPTY_STRING,
)

from .common import ConfluenceUser

logger = logging.getLogger(__name__)


class ConfluenceInlineComment(ApiModel, TimestampMixin):
    """
    Model representing a Confluence inline comment (API v2).
    """

    id: str = CONFLUENCE_DEFAULT_ID
    status: str = "current"  # "current", etc.
    title: str | None = None
    body: str = EMPTY_STRING
    created: str = EMPTY_STRING
    updated: str = EMPTY_STRING
    author: ConfluenceUser | None = None
    type: str = "comment"
    page_id: str | None = None
    blog_post_id: str | None = None
    parent_comment_id: str | None = None
    resolution_status: str = "open"  # "open", "resolved"
    resolution_last_modifier_id: str | None = None
    resolution_last_modified_at: str | None = None

    # Text selection properties (API v2 standard)
    text_selection: str | None = None
    text_selection_match_count: int = 1
    text_selection_match_index: int = 0

    # Legacy properties (for backward compatibility)
    inline_marker_ref: str | None = None
    inline_original_selection: str | None = None

    # Version information
    version_number: int | None = None
    version_message: str | None = None
    version_minor_edit: bool = False
    version_author_id: str | None = None
    version_created_at: str | None = None

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

        # Extract inline comment specific properties from API v2 response
        properties = data.get("properties", {})
        inline_comment_props = data.get("inlineCommentProperties", {})

        # Handle properties that can be in different structures based on API v2 spec
        # For GET responses, properties may be in the "properties" object or direct fields
        # For POST responses, inlineCommentProperties are typically returned as direct fields

        # API v2 standard fields - try multiple locations for compatibility
        text_selection = (
            inline_comment_props.get("textSelection") or
            properties.get("textSelection") or
            data.get("textSelection")
        )

        text_selection_match_count = (
            inline_comment_props.get("textSelectionMatchCount") or
            properties.get("textSelectionMatchCount") or
            data.get("textSelectionMatchCount") or
            1
        )

        text_selection_match_index = (
            inline_comment_props.get("textSelectionMatchIndex") or
            properties.get("textSelectionMatchIndex") or
            data.get("textSelectionMatchIndex") or
            0
        )

        # Legacy fields (for backward compatibility) - check both naming conventions
        inline_marker_ref = (
            properties.get("inlineMarkerRef") or
            properties.get("inline-marker-ref") or
            data.get("inlineMarkerRef") or
            data.get("inline-marker-ref")
        )

        inline_original_selection = (
            properties.get("inlineOriginalSelection") or
            properties.get("inline-original-selection") or
            data.get("inlineOriginalSelection") or
            data.get("inline-original-selection")
        )

        # Version information
        version_data = data.get("version", {})
        version_number = version_data.get("number")
        version_message = version_data.get("message")
        version_minor_edit = version_data.get("minorEdit", False)
        version_author_id = version_data.get("authorId")
        version_created_at = version_data.get("createdAt")

        # Use version.createdAt for created timestamp if available, fallback to direct created
        created_timestamp = version_created_at or data.get("created", EMPTY_STRING)
        updated_timestamp = data.get("updated", created_timestamp)

        # Try to get body content from different formats
        body_content = EMPTY_STRING
        body = data.get("body", {})
        if "view" in body and body["view"].get("value"):
            body_content = body["view"]["value"]
        elif "storage" in body and body["storage"].get("value"):
            body_content = body["storage"]["value"]
        elif "atlas_doc_format" in body and body["atlas_doc_format"].get("value"):
            body_content = body["atlas_doc_format"]["value"]

        # Resolution status:
        # - Cloud (API v2): returned as top-level "resolutionStatus" field
        # - Server/DC (API v1): stored in extensions.resolution.status ("resolved"/"open")
        #   requires expand=extensions.resolution in the API request
        resolution_status = data.get("resolutionStatus")
        if not resolution_status:
            resolution_status = (
                data.get("extensions", {})
                .get("resolution", {})
                .get("status", "open")
            )

        return cls(
            id=str(data.get("id", CONFLUENCE_DEFAULT_ID)),
            status=data.get("status", "current"),
            title=title,
            body=body_content,
            created=created_timestamp,
            updated=updated_timestamp,
            author=author,
            type=data.get("type", "comment"),
            page_id=data.get("pageId"),
            blog_post_id=data.get("blogPostId"),
            parent_comment_id=data.get("parentCommentId"),
            resolution_status=resolution_status,
            resolution_last_modifier_id=data.get("resolutionLastModifierId"),
            resolution_last_modified_at=data.get("resolutionLastModifiedAt"),
            text_selection=text_selection,
            text_selection_match_count=text_selection_match_count,
            text_selection_match_index=text_selection_match_index,
            inline_marker_ref=inline_marker_ref,
            inline_original_selection=inline_original_selection,
            version_number=version_number,
            version_message=version_message,
            version_minor_edit=version_minor_edit,
            version_author_id=version_author_id,
            version_created_at=version_created_at,
        )

    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for API response."""
        result = {
            "id": self.id,
            "status": self.status,
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

        if self.parent_comment_id:
            result["parent_comment_id"] = self.parent_comment_id

        if self.resolution_last_modifier_id:
            result["resolution_last_modifier_id"] = self.resolution_last_modifier_id

        if self.resolution_last_modified_at:
            result["resolution_last_modified_at"] = self.resolution_last_modified_at

        # Text selection properties
        if self.text_selection:
            result["text_selection"] = self.text_selection

        result["text_selection_match_count"] = self.text_selection_match_count
        result["text_selection_match_index"] = self.text_selection_match_index

        # Legacy properties (if available)
        if self.inline_marker_ref:
            result["inline_marker_ref"] = self.inline_marker_ref

        if self.inline_original_selection:
            result["inline_original_selection"] = self.inline_original_selection

        # Version information
        if self.version_number is not None:
            result["version_number"] = self.version_number

        if self.version_message:
            result["version_message"] = self.version_message

        if self.version_minor_edit:
            result["version_minor_edit"] = self.version_minor_edit

        if self.version_author_id:
            result["version_author_id"] = self.version_author_id

        if self.version_created_at:
            result["version_created_at"] = self.version_created_at

        return result
