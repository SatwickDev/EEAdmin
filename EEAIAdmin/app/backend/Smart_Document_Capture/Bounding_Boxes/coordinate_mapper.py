"""
Coordinate Mapper Service
=========================

This module provides the FieldCoordinateMapper class for mapping extracted
field values to their corresponding OCR bounding box coordinates.

Author: EEAdmin Team
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FieldCoordinateMapper:
    """
    Maps extracted field values to their corresponding OCR bounding box coordinates.
    
    This class provides intelligent matching between extracted field values
    and OCR text entries, supporting fuzzy matching and date normalization.
    
    Attributes:
        similarity_threshold (float): Minimum similarity ratio for fuzzy matching
        exact_match_bonus (float): Bonus added to exact matches
    """
    
    def __init__(self, similarity_threshold: float = 0.6, exact_match_bonus: float = 0.3):
        """
        Initialize the FieldCoordinateMapper.
        
        Args:
            similarity_threshold: Minimum similarity ratio for fuzzy matching (default: 0.6)
            exact_match_bonus: Bonus added to exact matches (default: 0.3)
        """
        self.similarity_threshold = similarity_threshold
        self.exact_match_bonus = exact_match_bonus
        logger.info(f"FieldCoordinateMapper initialized with threshold={similarity_threshold}")
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison by converting to lowercase and removing extra whitespace.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        return ' '.join(text.lower().split())
    
    def normalize_date_for_matching(self, text: str) -> List[str]:
        """
        Generate multiple date format variations for matching.
        
        Handles various date formats including:
        - yyyy-mm-dd, dd-mm-yyyy, mm-dd-yyyy
        - Separators: -, /, .
        - Compact formats: 210429, 20210429
        
        Args:
            text: Input text that may contain a date
            
        Returns:
            List of possible date format variations
        """
        if not text or not isinstance(text, str):
            return []
        
        text = text.strip()
        variations = [text]
        
        # Extract date patterns
        date_patterns = [
            r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',  # yyyy-mm-dd
            r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})',  # dd-mm-yyyy or mm-dd-yyyy
            r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{2})',  # dd-mm-yy or mm-dd-yy
            r'(\d{6})',  # yymmdd or ddmmyy
            r'(\d{8})',  # yyyymmdd or ddmmyyyy
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    parts = list(match)
                else:
                    parts = [match]
                
                # Generate variations with different separators
                if len(parts) == 3:
                    for sep in ['-', '/', '.', '']:
                        variations.append(sep.join(parts))
                        variations.append(sep.join(reversed(parts)))
        
        return list(set(variations))
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.
        
        Uses SequenceMatcher for fuzzy matching and adds bonus for exact matches.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity ratio (0.0 to 1.0+)
        """
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Exact match bonus
        if norm1 == norm2:
            return 1.0 + self.exact_match_bonus
        
        # Substring match
        if norm1 in norm2 or norm2 in norm1:
            return 0.9
        
        # Fuzzy match using SequenceMatcher
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        
        return ratio
    
    def find_best_ocr_match(
        self, 
        field_value: str, 
        ocr_data: List[Dict[str, Any]],
        page_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best matching OCR entry for a field value.
        
        Args:
            field_value: The extracted field value to search for
            ocr_data: List of OCR entries with text and bounding box data
            page_number: Optional page number to filter results
            
        Returns:
            Best matching OCR entry or None if no match found
        """
        if not field_value or not ocr_data:
            return None
        
        date_variations = self.normalize_date_for_matching(field_value)
        
        best_match = None
        best_score = 0.0
        
        for ocr_entry in ocr_data:
            # Filter by page if specified
            if page_number is not None:
                entry_page = ocr_entry.get('bounding_page', 1)
                if entry_page != page_number:
                    continue
            
            ocr_text = ocr_entry.get('text', '')
            if not ocr_text:
                continue
            
            # Calculate base similarity
            score = self.calculate_similarity(field_value, ocr_text)
            
            # Check date variations
            for date_var in date_variations:
                date_score = self.calculate_similarity(date_var, ocr_text)
                if date_score > score:
                    score = date_score
            
            # Update best match
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = {
                    'ocr_entry': ocr_entry,
                    'matched_text': ocr_text,
                    'similarity_score': score,
                    'bounding_box': ocr_entry.get('bounding_box', []),
                    'bounding_page': ocr_entry.get('bounding_page', 1)
                }
        
        if best_match:
            logger.debug(f"Found match for '{field_value}': '{best_match['matched_text']}' (score={best_score:.2f})")
        else:
            logger.debug(f"No match found for '{field_value}'")
        
        return best_match
    
    def extract_coordinates_from_match(
        self, 
        match: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract coordinate information from a match result.
        
        Args:
            match: Match result from find_best_ocr_match
            
        Returns:
            Dictionary with coordinate information or None
        """
        if not match:
            return None
        
        bbox = match.get('bounding_box', [])
        if not bbox or len(bbox) < 4:
            return None
        
        # Convert to standard format (8 coordinates for quadrilateral)
        if len(bbox) == 4:
            # [x1, y1, x2, y2] -> [x1, y1, x2, y1, x2, y2, x1, y2]
            x1, y1, x2, y2 = bbox
            bbox = [x1, y1, x2, y1, x2, y2, x1, y2]
        
        return {
            'bounding_box': bbox,
            'bounding_page': match.get('bounding_page', 1),
            'matched_text': match.get('matched_text', ''),
            'similarity_score': match.get('similarity_score', 0.0)
        }
    
    def map_field_coordinates(
        self, 
        field_name: str, 
        field_value: str, 
        ocr_data: List[Dict[str, Any]],
        page_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Map a field to its corresponding bounding box coordinates.
        
        This is the main entry point for coordinate mapping.
        
        Args:
            field_name: Name of the field
            field_value: Extracted value of the field
            ocr_data: List of OCR entries
            page_number: Optional page number filter
            
        Returns:
            Dictionary with field coordinates or None
        """
        logger.debug(f"Mapping coordinates for field '{field_name}': '{field_value}'")
        
        match = self.find_best_ocr_match(field_value, ocr_data, page_number)
        
        if not match:
            return None
        
        coordinates = self.extract_coordinates_from_match(match)
        
        if coordinates:
            coordinates['field_name'] = field_name
            coordinates['field_value'] = field_value
        
        return coordinates
    
    def map_document_coordinates(
        self, 
        extracted_fields: Dict[str, str], 
        ocr_data: List[Dict[str, Any]],
        page_filter: Optional[List[int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Map all extracted fields to their coordinates.
        
        Args:
            extracted_fields: Dictionary of field_name -> field_value
            ocr_data: List of OCR entries
            page_filter: Optional list of page numbers to filter
            
        Returns:
            Dictionary mapping field names to coordinate information
        """
        logger.info(f"Mapping coordinates for {len(extracted_fields)} fields")
        
        result = {}
        
        for field_name, field_value in extracted_fields.items():
            if not field_value or not isinstance(field_value, str):
                continue
            
            # Try each page if filter specified
            if page_filter:
                for page in page_filter:
                    coords = self.map_field_coordinates(
                        field_name, field_value, ocr_data, page
                    )
                    if coords:
                        result[field_name] = coords
                        break
            else:
                coords = self.map_field_coordinates(
                    field_name, field_value, ocr_data
                )
                if coords:
                    result[field_name] = coords
        
        logger.info(f"Successfully mapped {len(result)}/{len(extracted_fields)} fields")
        return result


# Global instance for convenience
coordinate_mapper = FieldCoordinateMapper()
