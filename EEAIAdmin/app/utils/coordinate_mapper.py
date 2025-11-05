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
    
    def normalize_date_for_matching(self, date_str: str) -> list:
        """
        Generate multiple date format variations for matching
        
        Args:
            date_str: Date string in any format
            
        Returns:
            List of normalized date variations for matching
        """
        variations = []
        
        # Try to parse as ISO date (YYYY-MM-DD)
        iso_date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(date_str))
        if iso_date_match:
            year, month, day = iso_date_match.groups()
            
            # Add variations:
            variations.append(f"{year}{month}{day}")  # YYYYMMDD: 20210817
            variations.append(f"{year[2:]}{month}{day}")  # YYMMDD: 210817
            variations.append(f"{day}{month}{year}")  # DDMMYYYY: 17082021
            variations.append(f"{day}{month}{year[2:]}")  # DDMMYY: 170821
            variations.append(f"{month}{day}{year}")  # MMDDYYYY: 08172021
            variations.append(f"{month}{day}{year[2:]}")  # MMDDYY: 081721
            variations.append(f"{day}/{month}/{year}")  # DD/MM/YYYY: 17/08/2021
            variations.append(f"{day}/{month}/{year[2:]}")  # DD/MM/YY: 17/08/21
            variations.append(f"{month}/{day}/{year}")  # MM/DD/YYYY: 08/17/2021
            variations.append(f"{day}-{month}-{year}")  # DD-MM-YYYY: 17-08-2021
            variations.append(date_str)  # Original format
        
        # Try to parse compact date formats (YYMMDD, YYYYMMDD)
        compact_date_match = re.match(r'(\d{6}|\d{8})', str(date_str).replace('-', '').replace('/', '').replace(' ', ''))
        if compact_date_match:
            date_digits = compact_date_match.group(1)
            
            if len(date_digits) == 6:  # YYMMDD format
                yy, mm, dd = date_digits[0:2], date_digits[2:4], date_digits[4:6]
                # Assume 20xx for years
                yyyy = f"20{yy}"
                variations.append(f"{yyyy}-{mm}-{dd}")  # 2021-08-17
                variations.append(f"{yyyy}{mm}{dd}")  # 20210817
                variations.append(date_digits)  # 210817
                
            elif len(date_digits) == 8:  # YYYYMMDD format
                yyyy, mm, dd = date_digits[0:4], date_digits[4:6], date_digits[6:8]
                variations.append(f"{yyyy}-{mm}-{dd}")  # 2021-08-17
                variations.append(f"{yyyy[2:]}{mm}{dd}")  # 210817
                variations.append(date_digits)  # 20210817
        
        # Always add the original value
        if str(date_str) not in variations:
            variations.append(str(date_str))
        
        return variations
    
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
        
        # Check if this looks like a date field (contains YYYY-MM-DD pattern)
        is_date_field = bool(re.match(r'\d{4}-\d{2}-\d{2}', field_str))
        date_variations = []
        
        if is_date_field:
            # Generate date variations for better matching
            date_variations = self.normalize_date_for_matching(field_str)
            logger.info(f"🗓️ Date field detected: '{field_str}' → Generated {len(date_variations)} variations: {date_variations[:3]}...")
        
        for ocr_entry in ocr_data:
            ocr_text = ocr_entry.get('text', '')
            if not ocr_text:
                continue
            
            # Normalize OCR text for comparison
            ocr_text_clean = re.sub(r'[^a-zA-Z0-9]', '', str(ocr_text))
            
            # For date fields, try matching against all variations
            if is_date_field and date_variations:
                for variation in date_variations:
                    variation_clean = re.sub(r'[^a-zA-Z0-9]', '', str(variation))
                    
                    # Check for exact substring match (ignoring punctuation)
                    if variation_clean in ocr_text_clean or ocr_text_clean in variation_clean:
                        similarity = 1.0  # Perfect match for date variation
                        if similarity > best_score:
                            best_score = similarity
                            best_match = {
                                'ocr_entry': ocr_entry,
                                'similarity': similarity,
                                'field_value': field_str,
                                'matched_text': ocr_text,
                                'date_variation_used': variation
                            }
                            logger.info(f"✅ Date match SUCCESS: '{field_str}' → OCR: '{ocr_text}' using variation '{variation}'")
                            break  # Found perfect match, no need to check more variations
                    
                    # Also try fuzzy matching for each variation (with lower threshold for dates)
                    variation_similarity = self.calculate_similarity(variation, ocr_text)
                    if variation_similarity > best_score and variation_similarity >= 0.5:  # Lower threshold for dates
                        best_score = variation_similarity
                        best_match = {
                            'ocr_entry': ocr_entry,
                            'similarity': variation_similarity,
                            'field_value': field_str,
                            'matched_text': ocr_text,
                            'date_variation_used': variation
                        }
                        logger.info(f"✅ Date fuzzy match: '{field_str}' → OCR: '{ocr_text}' (similarity: {variation_similarity:.2f}, variation: '{variation}')")
                
                # If we found a match for this OCR entry, stop checking other entries
                if best_match and best_match['ocr_entry'] == ocr_entry:
                    break
            else:
                # Regular text matching (non-date fields)
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
            if is_date_field:
                logger.info(f"📅 Date match FINAL: '{field_str}' → '{best_match['matched_text'][:50]}' (score: {best_match['similarity']:.2f})")
            else:
                logger.debug(f"Found match for '{field_str[:50]}...': '{best_match['matched_text'][:50]}...' (similarity: {best_match['similarity']:.2f})")
        else:
            if is_date_field:
                logger.warning(f"❌ NO DATE MATCH for '{field_str}' - tried {len(date_variations)} variations")
            
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