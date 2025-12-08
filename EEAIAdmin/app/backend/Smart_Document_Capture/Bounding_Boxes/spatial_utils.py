"""
Spatial Utilities Module
========================

This module provides utility functions for spatial operations on bounding boxes,
including merging, distance calculation, sorting, and rotation detection.

Author: EEAdmin Team
Version: 1.0.0
"""

import logging
import math
import string
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def fuzzy_match(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings using SequenceMatcher.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity ratio (0.0 to 1.0)
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def strip_punctuation(text: str) -> str:
    """
    Remove leading/trailing punctuation and whitespace from text.
    
    Args:
        text: Input text
        
    Returns:
        Text with punctuation stripped
    """
    return text.strip(string.punctuation + string.whitespace)


def merge_bboxes(bboxes: List[List[float]], padding: float = 0.01) -> List[float]:
    """
    Merge multiple bounding boxes into a single encompassing bounding box.
    
    Args:
        bboxes: List of bounding boxes (8 coordinates each: x1,y1,x2,y2,x3,y3,x4,y4)
        padding: Padding to add around the merged box
        
    Returns:
        Merged bounding box as list of 8 coordinates
    """
    if not bboxes:
        return []
    
    all_x, all_y = [], []
    for bbox in bboxes:
        if bbox and len(bbox) >= 8:
            all_x.extend([bbox[0], bbox[2], bbox[4], bbox[6]])
            all_y.extend([bbox[1], bbox[3], bbox[5], bbox[7]])
    
    if not all_x or not all_y:
        return []
    
    xmin, ymin = min(all_x) - padding, min(all_y) - padding
    xmax, ymax = max(all_x) + padding, max(all_y) + padding
    
    return [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax]


def get_bbox_center(bbox: List[float]) -> Tuple[float, float]:
    """
    Get the center point of a bounding box.
    
    Args:
        bbox: Bounding box coordinates
        
    Returns:
        Tuple of (x_center, y_center)
    """
    if not bbox or len(bbox) < 8:
        return (0, 0)
    x = (bbox[0] + bbox[2] + bbox[4] + bbox[6]) / 4
    y = (bbox[1] + bbox[3] + bbox[5] + bbox[7]) / 4
    return (x, y)


def calculate_distance(bbox1: List[float], bbox2: List[float]) -> float:
    """
    Calculate Euclidean distance between the centers of two bounding boxes.
    
    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        
    Returns:
        Euclidean distance between centers
    """
    x1, y1 = get_bbox_center(bbox1)
    x2, y2 = get_bbox_center(bbox2)
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def are_words_on_same_line(words: List[Dict], y_tolerance: float = 0.2) -> bool:
    """
    Check if words are on the same horizontal line (for normal pages).
    
    Args:
        words: List of word dictionaries with bounding_box
        y_tolerance: Maximum Y-position difference allowed
        
    Returns:
        True if all words are on the same line
    """
    if not words or len(words) < 2:
        return True
    
    y_positions = []
    for word in words:
        bbox = word.get('bounding_box', [])
        if len(bbox) >= 8:
            y_center = (bbox[1] + bbox[3] + bbox[5] + bbox[7]) / 4
            y_positions.append(y_center)
    
    if not y_positions:
        return True
    
    return (max(y_positions) - min(y_positions)) <= y_tolerance


def are_words_on_same_line_rotated(words: List[Dict], x_tolerance: float = 0.2) -> bool:
    """
    Check if words are on the same line for ROTATED page (similar X, varying Y).
    
    Args:
        words: List of word dictionaries with bounding_box
        x_tolerance: Maximum X-position difference allowed
        
    Returns:
        True if all words are on the same line (rotated orientation)
    """
    if not words or len(words) < 2:
        return True
    
    x_positions = []
    for word in words:
        bbox = word.get('bounding_box', [])
        if len(bbox) >= 8:
            x_center = (bbox[0] + bbox[2] + bbox[4] + bbox[6]) / 4
            x_positions.append(x_center)
    
    if not x_positions:
        return True
    
    return (max(x_positions) - min(x_positions)) <= x_tolerance


def sort_words_left_to_right(words: List[Dict]) -> List[Dict]:
    """
    Sort words left to right (by X position) - for normal pages.
    
    Args:
        words: List of word dictionaries with bounding_box
        
    Returns:
        Sorted list of words
    """
    return sorted(words, key=lambda w: (w['bounding_box'][0] + w['bounding_box'][2]) / 2)


def sort_words_for_rotated_page(words: List[Dict]) -> List[Dict]:
    """
    Sort words for rotated page (by Y coordinate, descending = right to left).
    
    Args:
        words: List of word dictionaries with bounding_box
        
    Returns:
        Sorted list of words
    """
    return sorted(words, 
                key=lambda w: (w['bounding_box'][1] + w['bounding_box'][5]) / 2,
                reverse=True)


def sort_words_reading_order(words: List[Dict]) -> List[Dict]:
    """
    Sort words in reading order (top to bottom, left to right).
    
    Args:
        words: List of word dictionaries with bounding_box
        
    Returns:
        Sorted list of words
    """
    return sorted(words, key=lambda w: (
        (w['bounding_box'][1] + w['bounding_box'][5]) / 2,  # Y
        (w['bounding_box'][0] + w['bounding_box'][2]) / 2   # X
    ))


def detect_page_rotation(word_pool: List[Dict]) -> bool:
    """
    Detect if page is rotated 90° counter-clockwise.
    Rotated page: Y-range >> X-range for most words (text flows on Y-axis).
    
    Args:
        word_pool: List of word dictionaries with bounding_box
        
    Returns:
        True if page appears to be rotated
    """
    if not word_pool or len(word_pool) < 5:
        return False
    
    rotated_count = 0
    valid_count = 0
    
    for word in word_pool:
        if not word or not isinstance(word, dict):
            continue
            
        bbox = word.get('bounding_box', [])
        if not bbox or len(bbox) < 8:
            continue
        
        try:
            x_coords = [bbox[0], bbox[2], bbox[4], bbox[6]]
            y_coords = [bbox[1], bbox[3], bbox[5], bbox[7]]
            
            x_range = max(x_coords) - min(x_coords)
            y_range = max(y_coords) - min(y_coords)
            
            valid_count += 1
            
            # If Y-range > X-range * 1.5 → word flows on Y-axis (rotated)
            if y_range > x_range * 1.5:
                rotated_count += 1
        except (TypeError, ValueError, IndexError) as e:
            logger.debug(f"Error processing bbox: {e}")
            continue
    
    if valid_count == 0:
        return False
    
    rotation_ratio = rotated_count / valid_count
    is_rotated = rotation_ratio > 0.7
    
    logger.info(f"Page rotation check: {rotation_ratio*100:.1f}% words rotated → {'ROTATED' if is_rotated else 'NORMAL'}")
    
    return is_rotated


def is_standalone_punctuation(word_text: str) -> bool:
    """
    Check if word consists only of punctuation characters.
    
    Args:
        word_text: Word text to check
        
    Returns:
        True if word is only punctuation
    """
    return all(c in string.punctuation + string.whitespace for c in word_text)


def smart_sort_words(matched_words: List[Dict], line_text: str, is_rotated: bool = False) -> List[Dict]:
    """
    Smart sorting that handles punctuation correctly.
    If punctuation is far from main text, it might be misplaced.
    
    Args:
        matched_words: List of matched word dictionaries
        line_text: Expected line text for context
        is_rotated: Whether page is rotated
        
    Returns:
        Sorted list of words
    """
    if len(matched_words) <= 1:
        return matched_words
    
    # Separate punctuation from regular words
    punctuation_words = []
    regular_words = []
    
    for word in matched_words:
        word_text = word.get('text', '').strip()
        if is_standalone_punctuation(word_text):
            punctuation_words.append(word)
        else:
            regular_words.append(word)
    
    # If no punctuation or all punctuation, sort normally
    if not punctuation_words or not regular_words:
        if is_rotated:
            return sort_words_for_rotated_page(matched_words)
        else:
            return sort_words_left_to_right(matched_words)
    
    # Sort regular words
    if is_rotated:
        sorted_regular = sort_words_for_rotated_page(regular_words)
    else:
        sorted_regular = sort_words_left_to_right(regular_words)
    
    # For each punctuation, find where it should go based on expected text
    result = []
    
    for punct_word in punctuation_words:
        punct_text = punct_word.get('text', '').strip()
        
        # Find where this punctuation appears in expected text
        expected_before = None
        expected_after = None
        
        # Check if punctuation appears between two words in expected text
        tokens = line_text.split()
        for i, token in enumerate(tokens):
            if punct_text in token:
                # Punctuation is part of a word
                if i > 0:
                    expected_before = tokens[i-1]
                if i < len(tokens) - 1:
                    expected_after = tokens[i+1]
                break
        
        # If we found context, insert punctuation in the right place
        inserted = False
        if expected_before or expected_after:
            for i, word in enumerate(sorted_regular):
                word_text = word.get('text', '')
                
                if expected_before and fuzzy_match(word_text, expected_before) > 0.8:
                    result = sorted_regular[:i+1] + [punct_word] + sorted_regular[i+1:]
                    inserted = True
                    break
                elif expected_after and fuzzy_match(word_text, expected_after) > 0.8:
                    result = sorted_regular[:i] + [punct_word] + sorted_regular[i:]
                    inserted = True
                    break
        
        if inserted:
            break
    
    # If we couldn't place punctuation smartly, use spatial distance
    if not result:
        for punct_word in punctuation_words:
            punct_bbox = punct_word.get('bounding_box', [])
            if not punct_bbox or len(punct_bbox) < 8:
                continue
            
            punct_center = get_bbox_center(punct_bbox)
            
            # Find closest regular word
            min_distance = float('inf')
            closest_idx = 0
            
            for i, reg_word in enumerate(sorted_regular):
                reg_bbox = reg_word.get('bounding_box', [])
                if not reg_bbox or len(reg_bbox) < 8:
                    continue
                
                distance = calculate_distance(punct_bbox, reg_bbox)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_idx = i
            
            # If punctuation is far (> 1.0 units), skip it
            if min_distance > 1.0:
                logger.debug(f"Skipping far punctuation '{punct_word.get('text', '')}' (distance: {min_distance:.2f})")
                continue
            
            # Insert punctuation near closest word
            punct_x = punct_center[0]
            closest_x = get_bbox_center(sorted_regular[closest_idx].get('bounding_box', []))[0]
            
            if is_rotated:
                punct_y = punct_center[1]
                closest_y = get_bbox_center(sorted_regular[closest_idx].get('bounding_box', []))[1]
                if punct_y > closest_y:
                    result = sorted_regular[:closest_idx] + [punct_word] + sorted_regular[closest_idx:]
                else:
                    result = sorted_regular[:closest_idx+1] + [punct_word] + sorted_regular[closest_idx+1:]
            else:
                if punct_x < closest_x:
                    result = sorted_regular[:closest_idx] + [punct_word] + sorted_regular[closest_idx:]
                else:
                    result = sorted_regular[:closest_idx+1] + [punct_word] + sorted_regular[closest_idx+1:]
            
            break
    
    # If still no result, just append punctuation at the end
    if not result:
        result = sorted_regular + punctuation_words
    
    return result
