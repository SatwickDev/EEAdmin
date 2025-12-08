"""
Search Service Module
=====================

This module provides text search functionality in OCR data, including
date/amount normalization and intelligent matching algorithms.

Author: EEAdmin Team
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalize_date_for_search(text: str) -> List[str]:
    """
    Normalize different date formats to a common format for comparison.
    
    Handles formats like:
    - 2025-05-15, 15-05-2025, 15/05/2025, 15.05.2025
    - Different orders: yyyy-mm-dd, dd-mm-yyyy, mm-dd-yyyy, etc.
    - Compact formats like: 210817, 170821, 20210817
    
    Args:
        text: Text that may contain a date
        
    Returns:
        List of all possible normalized date representations
    """
    if not text or not isinstance(text, str):
        return []
    
    text = text.strip()
    date_patterns = []
    
    # Pattern 1: Dates WITH separators
    date_regex = r'(\d{1,4})[\/\-\.\s](\d{1,2})[\/\-\.\s](\d{1,4})'
    matches = re.finditer(date_regex, text)
    
    for match in matches:
        part1, part2, part3 = match.groups()
        
        try:
            p1, p2, p3 = int(part1), int(part2), int(part3)
        except ValueError:
            continue
        
        normalized_dates = []
        
        # Case 1: First part is year (yyyy-mm-dd format)
        if p1 >= 1900 and p1 <= 2100:
            if 1 <= p2 <= 12 and 1 <= p3 <= 31:
                normalized_dates.append(f"{p1:04d}-{p2:02d}-{p3:02d}")
                normalized_dates.append(f"{p3:02d}-{p2:02d}-{p1:04d}")
                normalized_dates.append(f"{p3:02d}/{p2:02d}/{p1:04d}")
                normalized_dates.append(f"{p3:02d}.{p2:02d}.{p1:04d}")
                normalized_dates.append(f"{p1:04d}{p2:02d}{p3:02d}")
                normalized_dates.append(f"{str(p1)[2:]}{p2:02d}{p3:02d}")
                normalized_dates.append(f"{p3:02d}{p2:02d}{str(p1)[2:]}")
                normalized_dates.append(f"{p3:02d}{p2:02d}{p1:04d}")
        
        # Case 2: Last part is year (dd-mm-yyyy or mm-dd-yyyy format)
        if p3 >= 1900 and p3 <= 2100:
            if 1 <= p1 <= 31 and 1 <= p2 <= 12:
                normalized_dates.append(f"{p3:04d}-{p2:02d}-{p1:02d}")
                normalized_dates.append(f"{p1:02d}-{p2:02d}-{p3:04d}")
                normalized_dates.append(f"{p1:02d}/{p2:02d}/{p3:04d}")
                normalized_dates.append(f"{p1:02d}.{p2:02d}.{p3:04d}")
                normalized_dates.append(f"{p3:04d}{p2:02d}{p1:02d}")
                normalized_dates.append(f"{str(p3)[2:]}{p2:02d}{p1:02d}")
                normalized_dates.append(f"{p1:02d}{p2:02d}{str(p3)[2:]}")
                normalized_dates.append(f"{p1:02d}{p2:02d}{p3:04d}")
            
            if 1 <= p1 <= 12 and 1 <= p2 <= 31:
                normalized_dates.append(f"{p3:04d}-{p1:02d}-{p2:02d}")
                normalized_dates.append(f"{p2:02d}-{p1:02d}-{p3:04d}")
                normalized_dates.append(f"{p2:02d}/{p1:02d}/{p3:04d}")
                normalized_dates.append(f"{p2:02d}.{p1:02d}.{p3:04d}")
                normalized_dates.append(f"{p3:04d}{p1:02d}{p2:02d}")
                normalized_dates.append(f"{str(p3)[2:]}{p1:02d}{p2:02d}")
                normalized_dates.append(f"{p2:02d}{p1:02d}{str(p3)[2:]}")
                normalized_dates.append(f"{p2:02d}{p1:02d}{p3:04d}")
        
        # Case 3: Year in middle (rare)
        if p2 >= 1900 and p2 <= 2100:
            if 1 <= p1 <= 31 and 1 <= p3 <= 12:
                normalized_dates.append(f"{p2:04d}-{p3:02d}-{p1:02d}")
                normalized_dates.append(f"{p1:02d}-{p3:02d}-{p2:04d}")
                normalized_dates.append(f"{p1:02d}/{p3:02d}/{p2:04d}")
                normalized_dates.append(f"{p1:02d}.{p3:02d}.{p2:04d}")
                normalized_dates.append(f"{p2:04d}{p3:02d}{p1:02d}")
                normalized_dates.append(f"{str(p2)[2:]}{p3:02d}{p1:02d}")
                normalized_dates.append(f"{p1:02d}{p3:02d}{str(p2)[2:]}")
                normalized_dates.append(f"{p1:02d}{p3:02d}{p2:04d}")
        
        date_patterns.extend(normalized_dates)
    
    # Pattern 2: Compact dates WITHOUT separators (6 or 8 digits)
    compact_regex = r'(\d{6}|\d{8})'
    compact_matches = re.finditer(compact_regex, text)
    
    for match in compact_matches:
        compact_date = match.group(1)
        
        if len(compact_date) == 6:
            try:
                yy = int(compact_date[0:2])
                mm = int(compact_date[2:4])
                dd = int(compact_date[4:6])
                
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    yyyy = 2000 + yy
                    date_patterns.append(f"{yyyy:04d}-{mm:02d}-{dd:02d}")
                    date_patterns.append(f"{dd:02d}-{mm:02d}-{yyyy:04d}")
                    date_patterns.append(f"{yyyy:04d}{mm:02d}{dd:02d}")
                    date_patterns.append(f"{yy:02d}{mm:02d}{dd:02d}")
                    date_patterns.append(f"{dd:02d}{mm:02d}{yy:02d}")
                
                dd2 = int(compact_date[0:2])
                mm2 = int(compact_date[2:4])
                yy2 = int(compact_date[4:6])
                
                if 1 <= mm2 <= 12 and 1 <= dd2 <= 31:
                    yyyy2 = 2000 + yy2
                    date_patterns.append(f"{yyyy2:04d}-{mm2:02d}-{dd2:02d}")
                    date_patterns.append(f"{dd2:02d}-{mm2:02d}-{yyyy2:04d}")
                    date_patterns.append(f"{yyyy2:04d}{mm2:02d}{dd2:02d}")
                    date_patterns.append(f"{yy2:02d}{mm2:02d}{dd2:02d}")
                    date_patterns.append(f"{dd2:02d}{mm2:02d}{yy2:02d}")
            except (ValueError, IndexError):
                pass
        
        elif len(compact_date) == 8:
            try:
                yyyy = int(compact_date[0:4])
                mm = int(compact_date[4:6])
                dd = int(compact_date[6:8])
                
                if 1900 <= yyyy <= 2100 and 1 <= mm <= 12 and 1 <= dd <= 31:
                    yy = int(str(yyyy)[2:])
                    date_patterns.append(f"{yyyy:04d}-{mm:02d}-{dd:02d}")
                    date_patterns.append(f"{dd:02d}-{mm:02d}-{yyyy:04d}")
                    date_patterns.append(f"{yyyy:04d}{mm:02d}{dd:02d}")
                    date_patterns.append(f"{yy:02d}{mm:02d}{dd:02d}")
                    date_patterns.append(f"{dd:02d}{mm:02d}{yy:02d}")
                
                dd2 = int(compact_date[0:2])
                mm2 = int(compact_date[2:4])
                yyyy2 = int(compact_date[4:8])
                
                if 1 <= mm2 <= 12 and 1 <= dd2 <= 31 and 1900 <= yyyy2 <= 2100:
                    yy2 = int(str(yyyy2)[2:])
                    date_patterns.append(f"{yyyy2:04d}-{mm2:02d}-{dd2:02d}")
                    date_patterns.append(f"{dd2:02d}-{mm2:02d}-{yyyy2:04d}")
                    date_patterns.append(f"{yyyy2:04d}{mm2:02d}{dd2:02d}")
                    date_patterns.append(f"{yy2:02d}{mm2:02d}{dd2:02d}")
                    date_patterns.append(f"{dd2:02d}{mm2:02d}{yy2:02d}")
                    date_patterns.append(f"{dd2:02d}{mm2:02d}{yyyy2:04d}")
            except (ValueError, IndexError):
                pass
    
    return list(set(date_patterns))


def normalize_amount_for_search(text: str) -> List[str]:
    """
    Normalize different amount formats to extract the numeric value.
    
    Handles formats like:
    - $6789.00, $6,789, 6789.00$, #6789.00#, %6,789%
    
    Args:
        text: Text that may contain an amount
        
    Returns:
        List of all possible numeric representations of the amount
    """
    if not text or not isinstance(text, str):
        return []
    
    amount_patterns = []
    
    amount_regex = r'[\$#%€£¥₹₽¢]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,4})?|\d+(?:\.\d{1,4})?)\s*[\$#%€£¥₹₽¢]?'
    matches = re.finditer(amount_regex, text)
    
    for match in matches:
        amount_str = match.group(1)
        
        if not amount_str:
            continue
        
        clean_amount = amount_str.replace(',', '').replace(' ', '')
        
        try:
            amount_value = float(clean_amount)
            
            amount_patterns.append(clean_amount)
            
            if '.' in clean_amount:
                without_decimal = clean_amount.replace('.', '')
                amount_patterns.append(without_decimal)
                
                integer_part = clean_amount.split('.')[0]
                amount_patterns.append(integer_part)
                
                decimal_part = clean_amount.split('.')[1]
                if decimal_part == '00' or decimal_part == '0':
                    amount_patterns.append(integer_part)
            
            if amount_value >= 1000:
                formatted_with_comma = f"{amount_value:,.2f}".rstrip('0').rstrip('.')
                amount_patterns.append(formatted_with_comma)
                formatted_int = f"{int(amount_value):,}"
                amount_patterns.append(formatted_int)
            
            amount_patterns.append(str(amount_value))
            amount_patterns.append(str(int(amount_value)))
        
        except (ValueError, IndexError):
            continue
    
    return list(set(amount_patterns))


def is_amount_field(text: str) -> bool:
    """
    Check if the search text looks like an amount/number.
    
    Args:
        text: The search text
        
    Returns:
        True if it looks like an amount
    """
    amount_pattern = r'^\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,4})?$|^\d+(?:\.\d{1,4})?$'
    return bool(re.match(amount_pattern, text.strip()))


def is_date_in_valid_context(text: str, date_pattern: str) -> bool:
    """
    Check if a date pattern appears in a valid context (not part of SWIFT codes,
    reference numbers, or other structured identifiers).
    
    Args:
        text: The OCR text containing the date
        date_pattern: The date pattern to check
        
    Returns:
        True if date is in valid context, False otherwise
    """
    # If the date is the entire text or very close to it, it's valid
    text_clean = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    date_clean = re.sub(r'[^a-zA-Z0-9]', '', date_pattern.lower())
    
    # If date is 80%+ of the text content, it's standalone (GOOD)
    if len(date_clean) >= len(text_clean) * 0.8:
        return True
    
    # Find the position of the date in the text
    pos = text.lower().find(date_pattern.lower())
    if pos == -1:
        return False
    
    # Check characters around the date
    before_date = text[:pos] if pos > 0 else ""
    after_date = text[pos + len(date_pattern):] if pos + len(date_pattern) < len(text) else ""
    
    # SWIFT-specific patterns (very strict)
    swift_patterns = [
        r'[A-Z]{3}[A-Z]{2}[A-Z]{2}XXX',
        r'XXX[0-9]{10,}',
        r'F21[A-Z]{6}[A-Z]{2}XXX',
    ]
    
    for pattern in swift_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    # Structured SWIFT message format
    if re.search(r'\{[0-9]+:\s*[0-9]+\}', text):
        return False
    
    # Check what comes immediately after the date
    if after_date and len(after_date.strip()) > 0:
        after_stripped = after_date.strip()
        
        if pos + len(date_pattern) < len(text) and text[pos + len(date_pattern)] != ' ':
            next_segment_match = re.match(r'^([A-Z0-9]+)', after_date, re.IGNORECASE)
            if next_segment_match:
                next_segment = next_segment_match.group(1)
                
                if next_segment.isupper() and 'XXX' in next_segment:
                    return False
                
                if len(next_segment) >= 10:
                    vowels = sum(1 for c in next_segment.lower() if c in 'aeiou')
                    if len(next_segment) > 10 and vowels < len(next_segment) * 0.2:
                        return False
    
    # Good context patterns
    good_patterns = [
        r'date[:\s]*$',
        r'dated[:\s]*$',
        r'on[:\s]*$',
        r'from[:\s]*$',
        r'to[:\s]*$',
        r'due[:\s]*$',
        r'value[:\s]*$',
        r'issued[:\s]*$',
        r'expire[:\s]*$',
        r'valid[:\s]*$',
    ]
    
    before_lower = before_date.lower().strip()
    for pattern in good_patterns:
        if re.search(pattern, before_lower):
            return True
    
    if after_date and after_date[0] in [' ', '\t', '\n', ':', '-', '/']:
        return True
    
    if ':' in before_date or (':' in after_date[:5] if len(after_date) >= 5 else False):
        return True
    
    if len(text) < 50 and not re.search(r'XXX[0-9]{5,}', text):
        return True
    
    return True


def calculate_match_priority_score(match_text: str, field_value: str, 
                                   match_confidence: float, match_type: str) -> float:
    """
    Calculate a priority score for a match to rank field values higher than narrative text.
    
    Args:
        match_text: The matched OCR text
        field_value: The search query
        match_confidence: The match confidence percentage
        match_type: Type of match (exact, contains, etc.)
        
    Returns:
        Priority score (higher = better priority)
    """
    priority_score = match_confidence
    
    # Factor 1: Text length - shorter is better
    text_len = len(match_text)
    if text_len <= 20:
        priority_score += 15
    elif text_len <= 40:
        priority_score += 10
    elif text_len <= 60:
        priority_score += 5
    else:
        priority_score -= 10
    
    # Factor 2: Field value is near the start of the text
    field_pos = match_text.lower().find(field_value.lower())
    if field_pos == 0:
        priority_score += 10
    elif field_pos <= 3:
        priority_score += 5
    
    # Factor 3: Format patterns indicating field definitions
    if re.search(rf'\b{re.escape(field_value)}\s*\([^)]+\)', match_text, re.IGNORECASE):
        priority_score += 20
    
    # Factor 4: Detect sentence patterns (narrative text indicators)
    sentence_indicators = [
        r'\b(we|will|shall|must|should|may|can)\b',
        r'\b(the|a|an)\b.*\b(the|a|an)\b',
        r'\b(of|with|for|from|by)\b',
        r'[.!?]\s',
        r'^\d+\.',
    ]
    
    for pattern in sentence_indicators:
        if re.search(pattern, match_text, re.IGNORECASE):
            priority_score -= 15
            break
    
    # Factor 5: Detect amount mentions
    amount_patterns = [
        rf'\b{re.escape(field_value)}\s*\d+',
        rf'\d+\s*{re.escape(field_value)}\b',
    ]
    for pattern in amount_patterns:
        if re.search(pattern, match_text, re.IGNORECASE):
            priority_score -= 10
            break
    
    # Factor 6: Field value ratio
    field_ratio = len(field_value) / len(match_text) if len(match_text) > 0 else 0
    if field_ratio > 0.5:
        priority_score += 15
    elif field_ratio > 0.3:
        priority_score += 8
    
    # Factor 7: Exact match type bonus
    if match_type == 'exact':
        priority_score += 5
    elif match_type in ['date_exact', 'date_contains', 'amount_exact', 'amount_contains']:
        priority_score += 3
    
    return priority_score


def search_text_in_ocr(field_value: str, ocr_data: List[Dict], 
                       search_mode: str = 'exact') -> List[Dict]:
    """
    Search for text in OCR data and return matching entries with coordinates.
    
    Args:
        field_value: The text to search for
        ocr_data: List of OCR entries with text and bounding box data
        search_mode: Search strategy - 'exact', 'fuzzy', or 'contains'
        
    Returns:
        List of matching OCR entries with coordinates and confidence scores
    """
    logger.info("SEARCH: === STARTING OCR TEXT SEARCH ===")
    logger.info(f"TARGET: Target field value: '{field_value}'")
    logger.info(f" Search mode: {search_mode}")
    logger.info(f" OCR entries to search: {len(ocr_data)}")
    
    if not field_value or not field_value.strip():
        logger.warning("ERROR: Empty field value provided")
        return []
    
    if not ocr_data:
        logger.warning("ERROR: No OCR data provided")
        return []
    
    field_value_lower = field_value.lower().strip()
    matches = []
    
    # Check if field_value looks like a date
    field_date_patterns = normalize_date_for_search(field_value)
    is_date_search = len(field_date_patterns) > 0
    
    # Check if field_value is a LONG numeric identifier
    is_numeric_identifier = False
    if not is_date_search:
        numeric_value = field_value.strip()
        if numeric_value.isdigit() and len(numeric_value) > 10:
            is_numeric_identifier = True
            logger.info(f"🔢 Detected numeric identifier search: '{numeric_value}'")
    
    # Check if field_value is a simple number (period)
    is_numeric_period = False
    if not is_date_search and not is_numeric_identifier:
        numeric_value = field_value.strip()
        if numeric_value.isdigit() and len(numeric_value) <= 3:
            is_numeric_period = True
            logger.info(f"📅 Detected numeric period search: '{numeric_value}'")
    
    # Check if field_value looks like an amount
    field_amount_patterns = []
    is_amount_search = False
    if not is_date_search and not is_numeric_identifier and not is_numeric_period:
        is_amount_search = is_amount_field(field_value)
        if is_amount_search:
            field_amount_patterns = normalize_amount_for_search(field_value)
    
    if is_date_search:
        logger.info(f"Detected date search. Normalized patterns: {field_date_patterns}")
    elif is_amount_search:
        logger.info(f"💰 Detected amount search. Normalized patterns: {field_amount_patterns}")
    
    # Search statistics
    exact_matches = 0
    fuzzy_matches = 0
    contains_matches = 0
    partial_matches = 0
    date_matches = 0
    amount_matches = 0
    numeric_period_matches = 0
    no_matches = 0
    
    for i, ocr_entry in enumerate(ocr_data):
        ocr_text = ocr_entry.get('text', '').strip()
        
        if not ocr_text:
            continue
        
        ocr_text_lower = ocr_text.lower()
        match_confidence = 0
        match_type = 'none'
        
        # Date matching logic
        if is_date_search and match_confidence < 100:
            ocr_date_patterns = normalize_date_for_search(ocr_text)
            if ocr_date_patterns:
                for field_pattern in field_date_patterns:
                    for ocr_pattern in ocr_date_patterns:
                        if field_pattern == ocr_pattern:
                            if is_date_in_valid_context(ocr_text, ocr_pattern):
                                match_confidence = 100
                                match_type = 'date_exact'
                                date_matches += 1
                                break
                    if match_confidence == 100:
                        break
                
                if match_confidence < 100:
                    for field_pattern in field_date_patterns:
                        if field_pattern in ocr_text_lower:
                            if is_date_in_valid_context(ocr_text, field_pattern):
                                match_confidence = 95
                                match_type = 'date_contains'
                                date_matches += 1
                                break
        
        # Amount matching logic
        if is_amount_search and match_confidence < 100:
            ocr_amount_patterns = normalize_amount_for_search(ocr_text)
            if ocr_amount_patterns:
                for field_pattern in field_amount_patterns:
                    for ocr_pattern in ocr_amount_patterns:
                        if field_pattern == ocr_pattern:
                            match_confidence = 100
                            match_type = 'amount_exact'
                            amount_matches += 1
                            break
                    if match_confidence == 100:
                        break
                
                if match_confidence < 100:
                    for field_pattern in field_amount_patterns:
                        if field_pattern in ocr_text:
                            match_confidence = 95
                            match_type = 'amount_contains'
                            amount_matches += 1
                            break
        
        # Numeric period matching
        if is_numeric_period and match_confidence < 100:
            number = re.escape(field_value.strip())
            pattern = rf'\b{number}\s*[/\-\s]?\s*(days?|DAYS?)\b'
            
            if re.search(pattern, ocr_text, re.IGNORECASE):
                match_confidence = 100
                match_type = 'numeric_period'
                numeric_period_matches += 1
        
        # Regular exact/contains/partial match
        if match_confidence < 100 and search_mode in ['exact', 'fuzzy', 'contains'] and not is_numeric_period:
            if field_value_lower == ocr_text_lower:
                match_confidence = 100
                match_type = 'exact'
                exact_matches += 1
            elif field_value_lower in ocr_text_lower:
                if is_numeric_identifier:
                    match_confidence = 100
                    match_type = 'contains'
                    contains_matches += 1
                elif len(field_value_lower) <= 20:
                    pattern = r'^' + re.escape(field_value_lower) + r'(?:$|[\s\-,./;:()\[\]{}|])'
                    match_start = re.match(pattern, ocr_text_lower)
                    pattern_with_punct = r'(?:^|[^\w])' + re.escape(field_value_lower) + r'(?:$|[\s\-,./;:()\[\]{}|])'
                    match_punct = re.search(pattern_with_punct, ocr_text_lower)
                    
                    if match_start or (match_punct and not re.search(r'\w+\s+' + re.escape(field_value_lower), ocr_text_lower)):
                        match_confidence = 90
                        match_type = 'contains'
                        contains_matches += 1
                else:
                    match_confidence = 90
                    match_type = 'contains'
                    contains_matches += 1
            elif ocr_text_lower in field_value_lower and not is_numeric_identifier:
                if len(ocr_text_lower) <= 20:
                    pattern = r'^' + re.escape(ocr_text_lower) + r'(?:$|[\s\-,./;:()\[\]{}|])'
                    match_start = re.match(pattern, field_value_lower)
                    pattern_with_punct = r'(?:^|[^\w])' + re.escape(ocr_text_lower) + r'(?:$|[\s\-,./;:()\[\]{}|])'
                    match_punct = re.search(pattern_with_punct, field_value_lower)
                    
                    if match_start or (match_punct and not re.search(r'\w+\s+' + re.escape(ocr_text_lower), field_value_lower)):
                        match_confidence = 85
                        match_type = 'partial'
                        partial_matches += 1
                else:
                    match_confidence = 85
                    match_type = 'partial'
                    partial_matches += 1
        
        # Fuzzy matching
        if search_mode in ['fuzzy', 'contains'] and match_confidence < 90 and not is_numeric_period and not is_numeric_identifier:
            similarity = SequenceMatcher(None, field_value_lower, ocr_text_lower).ratio()
            if similarity >= 0.8:
                fuzzy_confidence = similarity * 80
                if fuzzy_confidence > match_confidence:
                    match_confidence = fuzzy_confidence
                    match_type = 'fuzzy'
                    fuzzy_matches += 1
        
        if match_confidence < 80:
            no_matches += 1
        
        # Only include high-confidence matches
        if match_confidence >= 80:
            # Filter small partial matches for long search phrases
            if match_type == 'partial':
                search_length = len(field_value)
                match_length = len(ocr_text.strip())
                skip_match = False
                
                if search_length > 200 and match_length <= 30:
                    skip_match = True
                elif search_length > 100 and match_length <= 20:
                    skip_match = True
                elif search_length > 50 and match_length <= 10:
                    skip_match = True
                elif search_length > 30 and match_length <= 4:
                    skip_match = True
                
                if skip_match:
                    no_matches += 1
                    continue
            
            priority_score = calculate_match_priority_score(
                ocr_text, field_value, match_confidence, match_type
            )
            
            match_data = {
                'ocr_index': i,
                'matched_text': ocr_text,
                'field_value': field_value,
                'match_confidence': round(match_confidence, 1),
                'match_type': match_type,
                'priority_score': round(priority_score, 1),
                'bounding_box': ocr_entry.get('bounding_box', []),
                'bounding_page': ocr_entry.get('bounding_page', 1),
                'ocr_confidence': ocr_entry.get('confidence', 0)
            }
            matches.append(match_data)
            
            logger.info(f"SUCCESS:MATCH #{len(matches)}: '{ocr_text}' -> {match_confidence:.1f}% ({match_type})")
    
    # Sort by priority score first, then confidence
    matches.sort(key=lambda x: (x['priority_score'], x['match_confidence']), reverse=True)
    
    # For multi-line searches, create encompassing bounding boxes
    if len(field_value) >= 200 and len(matches) >= 2:
        logger.info(f"📦 MULTI-LINE: Creating encompassing bounding boxes for {len(matches)} matches")
        
        matches_by_page = {}
        for match in matches:
            page = match['bounding_page']
            if page not in matches_by_page:
                matches_by_page[page] = []
            matches_by_page[page].append(match)
        
        encompassing_matches = []
        for page, page_matches in matches_by_page.items():
            if len(page_matches) < 2:
                encompassing_matches.extend(page_matches)
                continue
            
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            all_texts = []
            
            for match in page_matches:
                bbox = match['bounding_box']
                if not bbox or len(bbox) < 4:
                    continue
                
                all_texts.append(match['matched_text'])
                
                if len(bbox) == 8:
                    xs = [bbox[0], bbox[2], bbox[4], bbox[6]]
                    ys = [bbox[1], bbox[3], bbox[5], bbox[7]]
                else:
                    xs = [bbox[0], bbox[2]]
                    ys = [bbox[1], bbox[3]]
                
                min_x = min(min_x, min(xs))
                max_x = max(max_x, max(xs))
                min_y = min(min_y, min(ys))
                max_y = max(max_y, max(ys))
            
            padding = 0.1
            min_x = max(0, min_x - padding)
            min_y = max(0, min_y - padding)
            max_x += padding
            max_y += padding
            
            encompassing_bbox = [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]
            combined_text = f"[MULTI-LINE SECTION: {len(page_matches)} lines]"
            
            encompassing_match = {
                'ocr_index': page_matches[0]['ocr_index'],
                'matched_text': combined_text,
                'field_value': field_value,
                'match_confidence': 95.0,
                'match_type': 'multiline_block',
                'priority_score': 100.0,
                'bounding_box': encompassing_bbox,
                'bounding_page': page,
                'ocr_confidence': 100,
                'component_matches': len(page_matches),
                'component_texts': all_texts
            }
            
            encompassing_matches.append(encompassing_match)
        
        matches = encompassing_matches
    
    logger.info(f"ANALYTICS: Search complete - {len(matches)} matches found")
    return matches
