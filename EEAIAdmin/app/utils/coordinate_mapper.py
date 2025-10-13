"""
Coordinate Mapper Utility
Maps extracted field values to OCR bounding box coordinates
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class FieldCoordinateMapper:
    """Maps extracted field values to their original OCR bounding box coordinates"""
    
    def __init__(self):
        self.similarity_threshold = 0.6  # Minimum similarity score for text matching
        self.exact_match_bonus = 0.3      # Bonus for exact substring matches
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        if not text:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', str(text).lower().strip())
        
        # Remove common punctuation that might interfere with matching
        normalized = re.sub(r'[.,;:!?()"\'-]', '', normalized)
        
        return normalized
    
    def calculate_similarity(self, field_value: str, ocr_text: str) -> float:
        """Calculate similarity between field value and OCR text"""
        if not field_value or not ocr_text:
            return 0.0
            
        norm_field = self.normalize_text(field_value)
        norm_ocr = self.normalize_text(ocr_text)
        
        if not norm_field or not norm_ocr:
            return 0.0
        
        # Check for exact substring match (case-insensitive)
        if norm_field in norm_ocr or norm_ocr in norm_field:
            base_similarity = SequenceMatcher(None, norm_field, norm_ocr).ratio()
            return min(1.0, base_similarity + self.exact_match_bonus)
        
        # Use sequence matcher for fuzzy matching
        return SequenceMatcher(None, norm_field, norm_ocr).ratio()
    
    def find_best_ocr_match(self, field_value: str, ocr_data: List[Dict]) -> Optional[Dict]:
        """Find the best matching OCR text entry for a field value"""
        if not field_value or not ocr_data:
            return None
        
        best_match = None
        best_score = 0.0
        
        field_str = str(field_value).strip()
        if len(field_str) < 2:  # Skip very short values
            return None
        
        for ocr_entry in ocr_data:
            ocr_text = ocr_entry.get('text', '')
            if not ocr_text:
                continue
                
            similarity = self.calculate_similarity(field_str, ocr_text)
            
            if similarity > best_score and similarity >= self.similarity_threshold:
                best_score = similarity
                best_match = {
                    'ocr_entry': ocr_entry,
                    'similarity': similarity,
                    'field_value': field_str,
                    'matched_text': ocr_text
                }
                
        if best_match:
            logger.debug(f"Found match for '{field_str[:50]}...': '{best_match['matched_text'][:50]}...' (similarity: {best_match['similarity']:.2f})")
            
        return best_match
    
    def extract_coordinates_from_match(self, match: Dict) -> List[int]:
        """Extract bounding box coordinates from a matched OCR entry"""
        ocr_entry = match.get('ocr_entry', {})
        bounding_box = ocr_entry.get('bounding_box', [])
        
        if isinstance(bounding_box, list) and len(bounding_box) >= 4:
            # Ensure coordinates are integers
            try:
                coords = [int(float(coord)) for coord in bounding_box[:4]]
                return coords
            except (ValueError, TypeError):
                logger.warning(f"Invalid bounding box format: {bounding_box}")
                return [0, 0, 0, 0]
        
        logger.warning(f"No valid bounding box found in OCR entry: {ocr_entry}")
        return [0, 0, 0, 0]
    
    def map_field_coordinates(self, extracted_fields: Dict, ocr_data: List[Dict]) -> Dict:
        """
        Map extracted fields to their OCR coordinates
        
        Args:
            extracted_fields: Dictionary of extracted field data from LLM
            ocr_data: List of OCR text entries with bounding boxes
            
        Returns:
            Dictionary with updated bounding box coordinates
        """
        if not extracted_fields or not ocr_data:
            logger.warning("No extracted fields or OCR data provided for coordinate mapping")
            return extracted_fields
        
        logger.info(f"Mapping coordinates for {len(extracted_fields)} fields using {len(ocr_data)} OCR entries")
        
        mapped_fields = {}
        mapping_stats = {
            'total_fields': len(extracted_fields),
            'mapped_fields': 0,
            'unmapped_fields': 0,
            'mapping_details': []
        }
        
        for field_name, field_data in extracted_fields.items():
            if not isinstance(field_data, dict):
                mapped_fields[field_name] = field_data
                continue
                
            # Get the field value
            field_value = field_data.get('value', '')
            
            # Skip empty or null values
            if not field_value or str(field_value).lower() in ['null', 'none', '', 'n/a']:
                mapped_fields[field_name] = field_data
                mapping_stats['unmapped_fields'] += 1
                mapping_stats['mapping_details'].append({
                    'field': field_name,
                    'reason': 'Empty or null value',
                    'value': field_value
                })
                continue
            
            # Find best OCR match
            best_match = self.find_best_ocr_match(field_value, ocr_data)
            
            if best_match:
                # Extract coordinates from the match
                coordinates = self.extract_coordinates_from_match(best_match)
                
                # Update field with real coordinates
                updated_field = field_data.copy()
                updated_field['bounding_box'] = coordinates
                updated_field['bounding_page'] = best_match['ocr_entry'].get('bounding_page', 1)
                updated_field['coordinate_confidence'] = best_match['similarity']
                updated_field['matched_ocr_text'] = best_match['matched_text']
                
                mapped_fields[field_name] = updated_field
                mapping_stats['mapped_fields'] += 1
                mapping_stats['mapping_details'].append({
                    'field': field_name,
                    'value': str(field_value)[:100],
                    'matched_text': best_match['matched_text'][:100],
                    'similarity': best_match['similarity'],
                    'coordinates': coordinates
                })
                
                logger.debug(f"✅ Mapped {field_name}: {coordinates} (similarity: {best_match['similarity']:.2f})")
            else:
                # Keep original field with default coordinates
                mapped_fields[field_name] = field_data
                mapping_stats['unmapped_fields'] += 1
                mapping_stats['mapping_details'].append({
                    'field': field_name,
                    'reason': 'No OCR match found',
                    'value': str(field_value)[:100]
                })
                
                logger.debug(f"❌ No match for {field_name}: '{str(field_value)[:50]}...'")
        
        # Log mapping statistics
        success_rate = (mapping_stats['mapped_fields'] / mapping_stats['total_fields'] * 100) if mapping_stats['total_fields'] > 0 else 0
        logger.info(f"📊 Coordinate mapping complete: {mapping_stats['mapped_fields']}/{mapping_stats['total_fields']} fields mapped ({success_rate:.1f}% success rate)")
        
        # Add mapping metadata
        mapped_fields['_coordinate_mapping_stats'] = mapping_stats
        
        return mapped_fields
    
    def map_document_coordinates(self, document_result: Dict, ocr_data: List[Dict]) -> Dict:
        """
        Map coordinates for all field categories in a document result
        
        Args:
            document_result: Complete document processing result
            ocr_data: OCR data for coordinate mapping
            
        Returns:
            Document result with updated coordinates
        """
        if not document_result.get('extraction'):
            return document_result
        
        extraction = document_result['extraction']
        updated_extraction = extraction.copy()
        
        # Map coordinates for each field category
        for category in ['mandatory', 'optional', 'conditional']:
            if category in extraction and extraction[category]:
                logger.info(f"🔗 Mapping coordinates for {category} fields")
                updated_extraction[category] = self.map_field_coordinates(
                    extraction[category], 
                    ocr_data
                )
        
        # Update the document result
        updated_result = document_result.copy()
        updated_result['extraction'] = updated_extraction
        
        return updated_result

# Global instance for easy import
coordinate_mapper = FieldCoordinateMapper()