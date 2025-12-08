"""
Page Grouping Service Module

This module provides the main grouping service for organizing classified pages
into document groups based on document type and handling continuation pages.

Step 5: Groups consecutive pages of the same document type together
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)


# Document types to skip during grouping
SKIP_DOCUMENT_TYPES = {'Empty/Insufficient Text', 'Unknown'}


@dataclass
class DocumentGroup:
    """
    Data class representing a group of pages belonging to the same document.
    
    Attributes:
        document_type: The type/category of the document
        pages: List of page numbers in this group
        confidence: Highest confidence score among grouped pages
        text: Combined OCR text from all pages
        ocr_data: Combined OCR data entries from all pages
        individual_pages: List of individual page classification dictionaries
        page_range: Human-readable page range string (e.g., "Pages 1-3")
    """
    document_type: str
    pages: List[int] = field(default_factory=list)
    confidence: float = 0.0
    text: str = ""
    ocr_data: List[Dict[str, Any]] = field(default_factory=list)
    individual_pages: List[Dict[str, Any]] = field(default_factory=list)
    page_range: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert group to dictionary."""
        return {
            'document_type': self.document_type,
            'pages': self.pages,
            'confidence': self.confidence,
            'text': self.text,
            'ocr_data': self.ocr_data,
            'individual_pages': self.individual_pages,
            'page_range': self.page_range
        }
    
    @classmethod
    def from_page_classification(cls, page_class: Dict[str, Any]) -> 'DocumentGroup':
        """Create a new group from a page classification."""
        return cls(
            document_type=page_class['document_type'],
            pages=[page_class['page']],
            confidence=page_class['confidence'],
            text=page_class.get('text', ''),
            ocr_data=page_class.get('ocr_data', []).copy(),
            individual_pages=[page_class]
        )
    
    def add_page(self, page_class: Dict[str, Any]) -> None:
        """Add a page to this group."""
        self.pages.append(page_class['page'])
        self.text += "\n" + page_class.get('text', '')
        self.ocr_data.extend(page_class.get('ocr_data', []))
        self.confidence = max(self.confidence, page_class['confidence'])
        self.individual_pages.append(page_class)
    
    def merge_continuation(self, page_class: Dict[str, Any]) -> None:
        """Merge a continuation page into this group."""
        self.pages.append(page_class['page'])
        self.text += "\n" + page_class.get('text', '')
        self.ocr_data.extend(page_class.get('ocr_data', []))
        self.confidence = max(self.confidence, page_class['confidence'])
        self.individual_pages.append(page_class)
        # Sort pages to maintain order
        self.pages.sort()
    
    def has_merged_duplicates(self) -> bool:
        """Check if this group contains merged duplicate pages."""
        return any(p.get('is_duplicate_filtered') for p in self.individual_pages)


@dataclass
class GroupingResult:
    """
    Data class representing the result of page grouping.
    
    Attributes:
        document_groups: List of DocumentGroup objects
        total_pages_processed: Number of pages processed
        pages_skipped: Number of pages skipped (empty/unknown)
        continuation_pages_merged: Number of continuation pages merged
        processing_time: Time taken for grouping in seconds
    """
    document_groups: List[DocumentGroup] = field(default_factory=list)
    total_pages_processed: int = 0
    pages_skipped: int = 0
    continuation_pages_merged: int = 0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'document_groups': [g.to_dict() for g in self.document_groups],
            'total_pages_processed': self.total_pages_processed,
            'pages_skipped': self.pages_skipped,
            'continuation_pages_merged': self.continuation_pages_merged,
            'processing_time': self.processing_time,
            'group_count': len(self.document_groups)
        }
    
    def get_groups_as_dicts(self) -> List[Dict[str, Any]]:
        """Get document groups as list of dictionaries."""
        return [g.to_dict() for g in self.document_groups]


def generate_page_range(pages: List[int]) -> str:
    """
    Generate a human-readable page range string from a list of page numbers.
    
    Handles:
    - Single pages: "Page 1"
    - Two pages: "Pages 1, 2"
    - Consecutive ranges: "Pages 1-5"
    - Non-consecutive pages: "Pages 1-3, 5, 7-9"
    
    Args:
        pages: List of page numbers
        
    Returns:
        Human-readable page range string
    """
    if not pages:
        return ""
    
    pages = sorted(pages)
    
    if len(pages) == 1:
        return f"Page {pages[0]}"
    elif len(pages) == 2:
        return f"Pages {pages[0]}, {pages[1]}"
    
    # Check if pages are consecutive
    consecutive = True
    for i in range(1, len(pages)):
        if pages[i] - pages[i-1] != 1:
            consecutive = False
            break
    
    if consecutive:
        return f"Pages {pages[0]}-{pages[-1]}"
    
    # Non-consecutive pages - build ranges
    ranges = []
    start = pages[0]
    end = pages[0]
    
    for i in range(1, len(pages)):
        if pages[i] == end + 1:
            end = pages[i]
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = pages[i]
    
    # Add the last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return f"Pages {', '.join(ranges)}"


def merge_continuation_page(
    page_class: Dict[str, Any],
    current_group: Optional[DocumentGroup],
    completed_groups: List[DocumentGroup]
) -> bool:
    """
    Merge a continuation page into its parent document group.
    
    Args:
        page_class: The continuation page classification dictionary
        current_group: The current group being built (may be None)
        completed_groups: List of already completed groups
        
    Returns:
        True if the page was successfully merged, False otherwise
    """
    original_type = page_class.get('original_type')
    page_num = page_class['page']
    
    # First check the current group (in progress)
    if current_group and current_group.document_type == original_type:
        logger.info(f"➕ Found parent in current group: {original_type}")
        current_group.merge_continuation(page_class)
        logger.info(f"➕ Merged continuation page {page_num} into {original_type} group")
        return True
    
    # Check completed groups
    for group in completed_groups:
        if group.document_type == original_type:
            logger.info(f"➕ Found parent in completed groups: {original_type}")
            group.merge_continuation(page_class)
            logger.info(f"➕ Merged continuation page {page_num} into {original_type} group")
            return True
    
    return False


def group_pages_by_document_type(
    page_classifications: List[Dict[str, Any]],
    skip_types: Optional[Set[str]] = None
) -> GroupingResult:
    """
    Group classified pages by document type.
    
    Step 5: Groups consecutive pages of the same document type together,
    handles continuation pages (duplicates), and generates page ranges.
    
    Args:
        page_classifications: List of page classification dictionaries
        skip_types: Set of document types to skip (default: Empty/Unknown)
        
    Returns:
        GroupingResult with document groups and statistics
    """
    import time
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("📚 STEP 5: PAGE GROUPING BY DOCUMENT TYPE")
    logger.info("=" * 60)
    logger.info(f"📄 Pages to group: {len(page_classifications)}")
    
    if skip_types is None:
        skip_types = SKIP_DOCUMENT_TYPES
    
    result = GroupingResult()
    result.total_pages_processed = len(page_classifications)
    
    document_groups: List[DocumentGroup] = []
    current_group: Optional[DocumentGroup] = None
    
    for page_class in page_classifications:
        doc_type = page_class['document_type']
        page_num = page_class['page']
        
        # Skip empty/insufficient text, unknown types, and unknown classification types
        if doc_type in skip_types or doc_type.startswith('Unknown Classification Type'):
            logger.info(f"⏭️ Skipping page {page_num}: {doc_type}")
            result.pages_skipped += 1
            continue
        
        # Handle continuation pages - merge them with the parent document
        if page_class.get('is_duplicate_filtered', False):
            original_type = page_class.get('original_type')
            logger.info(f"🔗 Processing continuation page {page_num} for {original_type}")
            
            if merge_continuation_page(page_class, current_group, document_groups):
                result.continuation_pages_merged += 1
            else:
                logger.warning(f"⚠️ No parent group found for continuation page {page_num} ({original_type})")
            continue
        
        # Normal grouping logic for consecutive pages
        should_group = (current_group is not None and 
                       current_group.document_type == doc_type)
        
        if not should_group:
            # Complete current group and start new one
            if current_group:
                logger.info(f"✅ Completed group: {current_group.document_type} (Pages: {current_group.pages})")
                document_groups.append(current_group)
            
            logger.info(f"🆕 Starting new group: {doc_type} (Page {page_num})")
            current_group = DocumentGroup.from_page_classification(page_class)
        else:
            # Add to current group
            logger.info(f"➕ Adding page {page_num} to group: {current_group.document_type}")
            current_group.add_page(page_class)
    
    # Don't forget the last group
    if current_group:
        logger.info(f"✅ Completed final group: {current_group.document_type} (Pages: {current_group.pages})")
        document_groups.append(current_group)
    
    # Generate page ranges for all groups
    for group in document_groups:
        group.page_range = generate_page_range(group.pages)
    
    result.document_groups = document_groups
    result.processing_time = time.time() - start_time
    
    # Log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ GROUPING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"📊 Found {len(document_groups)} distinct document types:")
    
    for group in document_groups:
        pages_info = f"({group.page_range}, confidence: {group.confidence:.0f}%)"
        if group.has_merged_duplicates():
            pages_info += " [includes merged duplicates]"
        logger.info(f"   - {group.document_type} {pages_info}")
    
    logger.info(f"   Pages skipped: {result.pages_skipped}")
    logger.info(f"   Continuation pages merged: {result.continuation_pages_merged}")
    logger.info(f"   Processing time: {result.processing_time:.2f}s")
    
    return result


class PageGroupingService:
    """
    Service class for page grouping operations.
    
    Provides a unified interface for:
    - Step 5: Grouping pages by document type
    - Handling continuation pages
    - Generating page ranges
    
    Usage:
        service = PageGroupingService()
        result = service.group(page_classifications)
    """
    
    def __init__(self, skip_types: Optional[Set[str]] = None):
        """
        Initialize the grouping service.
        
        Args:
            skip_types: Optional set of document types to skip
        """
        logger.info("PageGroupingService initialized")
        self.skip_types = skip_types or SKIP_DOCUMENT_TYPES
        logger.info(f"📋 Skip types configured: {self.skip_types}")
    
    def group(self, page_classifications: List[Dict[str, Any]]) -> GroupingResult:
        """
        Group page classifications by document type.
        
        Args:
            page_classifications: List of page classification dictionaries
            
        Returns:
            GroupingResult with document groups and statistics
        """
        return group_pages_by_document_type(page_classifications, self.skip_types)
    
    def add_skip_type(self, doc_type: str) -> None:
        """
        Add a document type to skip during grouping.
        
        Args:
            doc_type: Document type name to skip
        """
        self.skip_types.add(doc_type)
        logger.info(f"➕ Added skip type: '{doc_type}'")
    
    def remove_skip_type(self, doc_type: str) -> None:
        """
        Remove a document type from skip list.
        
        Args:
            doc_type: Document type name to remove from skip list
        """
        self.skip_types.discard(doc_type)
        logger.info(f"➖ Removed skip type: '{doc_type}'")
    
    @staticmethod
    def generate_page_range(pages: List[int]) -> str:
        """
        Generate a human-readable page range string.
        
        Args:
            pages: List of page numbers
            
        Returns:
            Human-readable page range string
        """
        return generate_page_range(pages)
