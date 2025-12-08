"""
Refinement Service Module
=========================

This module provides coordinate refinement functionality using word-level
OCR data to improve bounding box accuracy through spatial clustering.

Author: EEAdmin Team
Version: 1.0.0
"""

import logging
import itertools
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# ============================================
# UTILITIES
# ============================================

def fuzzy_match(str1: str, str2: str) -> float:
    """Calculate similarity ratio"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def strip_punctuation(text: str) -> str:
    """Remove leading/trailing punctuation"""
    import string
    return text.strip(string.punctuation + string.whitespace)


def merge_bboxes(bboxes: List[List[float]], padding: float = 0.01) -> List[float]:
    """Merge multiple bboxes"""
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
    """Get center point of bbox"""
    if not bbox or len(bbox) < 8:
        return (0, 0)
    x = (bbox[0] + bbox[2] + bbox[4] + bbox[6]) / 4
    y = (bbox[1] + bbox[3] + bbox[5] + bbox[7]) / 4
    return (x, y)


def calculate_distance(bbox1: List[float], bbox2: List[float]) -> float:
    """Calculate Euclidean distance between two bboxes"""
    x1, y1 = get_bbox_center(bbox1)
    x2, y2 = get_bbox_center(bbox2)
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)



def are_words_on_same_line(words: List[Dict], y_tolerance: float = 0.2) -> bool:
    """Check if words are on same horizontal line (for normal pages)"""
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
    """Check if words are on same line for ROTATED page (similar X, varying Y)"""
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
    """Sort words left to right (by X position) - for normal pages"""
    return sorted(words, key=lambda w: (w['bounding_box'][0] + w['bounding_box'][2]) / 2)


def sort_words_for_rotated_page(words: List[Dict]) -> List[Dict]:
    """Sort words for rotated page (by Y coordinate, descending = right to left)"""
    return sorted(words, 
                key=lambda w: (w['bounding_box'][1] + w['bounding_box'][5]) / 2,
                reverse=True)


def sort_words_reading_order(words: List[Dict]) -> List[Dict]:
    """Sort words in reading order (top to bottom, left to right)"""
    return sorted(words, key=lambda w: (
        (w['bounding_box'][1] + w['bounding_box'][5]) / 2,  # Y
        (w['bounding_box'][0] + w['bounding_box'][2]) / 2   # X
    ))


# ============================================
# ROTATED PAGE DETECTION
# ============================================

def detect_page_rotation(word_pool: List[Dict]) -> bool:
    """
    Detect if page is rotated 90° counter-clockwise
    Rotated page: Y-range >> X-range for most words (text flows on Y-axis)
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
    """Check if word is just punctuation"""
    import string
    return all(c in string.punctuation + string.whitespace for c in word_text)


def smart_sort_words(matched_words: List[Dict], line_text: str, is_rotated: bool = False) -> List[Dict]:
    """
    Smart sorting that handles punctuation correctly
    If punctuation is far from main text, it might be misplaced
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
    regular_text = ' '.join([w.get('text', '') for w in sorted_regular])
    
    for punct_word in punctuation_words:
        punct_text = punct_word.get('text', '').strip()
        
        # Find where this punctuation appears in expected text
        expected_before = None
        expected_after = None
        
        # Check if punctuation appears between two words in expected text
        tokens = line_text.split()
        for i, token in enumerate(tokens):
            if punct_text in token:
                # Punctuation is part of a word (e.g., "2021-22/172:")
                # It should be placed with that word
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
                
                # Check if this word matches the context
                if expected_before and fuzzy_match(word_text, expected_before) > 0.8:
                    # Insert after this word
                    result = sorted_regular[:i+1] + [punct_word] + sorted_regular[i+1:]
                    inserted = True
                    break
                elif expected_after and fuzzy_match(word_text, expected_after) > 0.8:
                    # Insert before this word
                    result = sorted_regular[:i] + [punct_word] + sorted_regular[i:]
                    inserted = True
                    break
        
        if inserted:
            break
    
    # If we couldn't place punctuation smartly, use spatial distance
    if not result:
        # Check if punctuation is close to any regular word
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
            
            # If punctuation is far (> 1.0 units), it's probably misplaced - skip it
            if min_distance > 1.0:
                logger.debug(f"Skipping far punctuation '{punct_word.get('text', '')}' (distance: {min_distance:.2f})")
                continue
            
            # Insert punctuation near closest word
            # Decide before/after based on spatial position
            punct_x = punct_center[0]
            closest_x = get_bbox_center(sorted_regular[closest_idx].get('bounding_box', []))[0]
            
            if is_rotated:
                # For rotated, compare Y positions
                punct_y = punct_center[1]
                closest_y = get_bbox_center(sorted_regular[closest_idx].get('bounding_box', []))[1]
                if punct_y > closest_y:  # Punctuation is below (comes before in reading order)
                    result = sorted_regular[:closest_idx] + [punct_word] + sorted_regular[closest_idx:]
                else:
                    result = sorted_regular[:closest_idx+1] + [punct_word] + sorted_regular[closest_idx+1:]
            else:
                # For normal, compare X positions
                if punct_x < closest_x:  # Punctuation is to the left
                    result = sorted_regular[:closest_idx] + [punct_word] + sorted_regular[closest_idx:]
                else:
                    result = sorted_regular[:closest_idx+1] + [punct_word] + sorted_regular[closest_idx+1:]
            
            break
    
    # If still no result, just append punctuation at the end
    if not result:
        result = sorted_regular + punctuation_words
    
    return result


# ============================================
# FIND ALL CANDIDATES FOR EACH LINE
# ============================================

def find_all_candidates_for_line(line_text: str, word_pool: List[Dict], 
                                    fuzzy_threshold: float = 0.90,
                                    is_rotated: bool = False) -> List[Dict]:
        """
        Find ALL possible word matches for a line_text in word_pool using two-phase approach:
        PHASE 1: Collect ALL candidate words for each token (fuzzy >= 0.90)
        PHASE 2: Build ALL valid combinations on the reference line (Y for normal, X for rotated)
        Works for both normal and rotated pages (NO coordinate transformation!)
        """
        import itertools
        
        tokens = line_text.split()
        if not tokens:
            return []
        
        logger.debug(f"Finding candidates for: '{line_text}' ({len(tokens)} tokens, rotated={is_rotated})")
        
        # PHASE 1: Collect ALL words matching each token (entire word_pool, not limited window)
        token_candidates = {}
        for token_idx, token in enumerate(tokens):
            candidates_for_token = []
            for word_idx, word in enumerate(word_pool):
                if not word or not isinstance(word, dict):
                    continue
                    
                word_text = word.get('text', '').strip()
                if not word_text:
                    continue
                
                similarity = fuzzy_match(token, word_text)
                
                if similarity >= fuzzy_threshold:
                    candidates_for_token.append({
                        'word': word,
                        'word_idx': word_idx,
                        'similarity': similarity
                    })
            
            token_candidates[token_idx] = candidates_for_token
            logger.info(f"Token '{token}': {len(candidates_for_token)} candidates found")
        
        # Check if all tokens have at least one candidate
        if any(len(candidates) == 0 for candidates in token_candidates.values()):
            logger.info(f"Not all tokens have candidates for '{line_text}'")
            return []
        
        # PHASE 2: Build combinations using SPATIAL PROXIMITY filtering (token-by-token)
        # Instead of trying ALL combinations (e.g., 3×28×20×10×5×10×12 = 10M),
        # we filter each token's candidates by proximity to the previous token
        # Result: 3×3×3×3×3×3×3 = ~2K combinations
        
        candidates = []
        fallback_candidates = []
        tolerance = 0.2
        
        logger.info(f"🔍 CANDIDATE GENERATION (SPATIAL): '{line_text}'")
        logger.info(f"  Token candidates (before filtering): {[len(token_candidates[i]) for i in range(len(tokens))]}")
        
        rejected_duplicate = 0
        accepted = 0
        fallback_count = 0
        
        # Helper function to get Y-center of bbox (normal pages) or X-center (rotated pages)
        def get_bbox_position(bbox):
            """Get the Y-coordinate (normal) or X-coordinate (rotated) of bbox center"""
            if is_rotated:
                # X-coordinate for rotated pages
                return (bbox[0] + bbox[2] + bbox[4] + bbox[6]) / 4
            else:
                # Y-coordinate for normal pages
                return (bbox[1] + bbox[3] + bbox[5] + bbox[7]) / 4
        
        # Recursive function to build combinations spatially
        def build_spatial_combinations(token_idx, current_combination):
            """Recursively build combinations by filtering next token by proximity"""
            
            # Base case: all tokens processed
            if token_idx == len(tokens):
                # Build candidate from current combination
                matched_words = [cand['word'] for cand in current_combination]
                matched_word_indices = [cand['word_idx'] for cand in current_combination]
                
                # Check for duplicate word usage
                if len(set(matched_word_indices)) != len(matched_words):
                    nonlocal rejected_duplicate
                    rejected_duplicate += 1
                    return
                
                # Sort and build candidate
                matched_words_sorted = smart_sort_words(matched_words, line_text, is_rotated)
                matched_text = ' '.join([w.get('text', '') for w in matched_words_sorted])
                line_bbox = merge_bboxes([w['bounding_box'] for w in matched_words_sorted], padding=0.01)
                
                if not line_bbox:
                    return
                
                avg_confidence = sum(w.get('confidence', 0) for w in matched_words_sorted) / len(matched_words_sorted)
                similarity = fuzzy_match(line_text, matched_text)
                
                candidate = {
                    'matched_text': matched_text,
                    'field_value': line_text,
                    'bounding_box': line_bbox,
                    'bounding_page': matched_words_sorted[0].get('bounding_page', 1),
                    'match_confidence': similarity * 100,
                    'coordinate_confidence': similarity * 100,
                    'match_type': 'word_refined_rotated' if is_rotated else 'word_refined',
                    'ocr_confidence': avg_confidence,
                    'word_count': len(matched_words_sorted),
                    'words': matched_words_sorted
                }
                
                # Check if all words are on same line
                on_same_line = False
                if is_rotated:
                    on_same_line = are_words_on_same_line_rotated(matched_words, x_tolerance=tolerance)
                else:
                    on_same_line = are_words_on_same_line(matched_words, y_tolerance=tolerance)
                
                if on_same_line:
                    nonlocal accepted
                    accepted += 1
                    candidates.append(candidate)
                else:
                    fallback_candidates.append(candidate)
                return
            
            # Recursive case: filter candidates for current token by proximity to previous token
            if token_idx == 0:
                # First token: use all candidates
                candidates_for_token = token_candidates[0]
            else:
                # Filter by proximity to previous token
                prev_candidate = current_combination[token_idx - 1]
                prev_bbox = prev_candidate['word']['bounding_box']
                prev_pos = get_bbox_position(prev_bbox)
                
                # Filter candidates that are spatially close to previous token
                candidates_for_token = []
                for cand in token_candidates[token_idx]:
                    curr_bbox = cand['word']['bounding_box']
                    curr_pos = get_bbox_position(curr_bbox)
                    
                    # Check if within tolerance
                    if abs(curr_pos - prev_pos) <= tolerance:
                        candidates_for_token.append(cand)
                
                # If no spatially close candidates found, use all (will be captured in fallback later)
                if not candidates_for_token:
                    candidates_for_token = token_candidates[token_idx]
            
            # Try each candidate for this token
            for candidate in candidates_for_token:
                build_spatial_combinations(token_idx + 1, current_combination + [candidate])
        
        # Start recursive combination building
        build_spatial_combinations(0, [])
        
        # FALLBACK LOGIC: If NO preferred candidates, use fallback candidates
        if not candidates and fallback_candidates:
            fallback_count = len(fallback_candidates)
            candidates = fallback_candidates
            logger.warning(f"⚠️  No 'on same line' candidates found, using {fallback_count} fallback candidates (position-independent)")
        
        logger.info(f"  ✅ Accepted (on-line): {accepted}, 📦 Fallback: {fallback_count}, ✗ Duplicate: {rejected_duplicate}")
        logger.info(f"Found {len(candidates)} valid combinations for '{line_text}'")
        return candidates


# ============================================
# SPATIAL CLUSTERING - FIND BEST GROUP
# ============================================

def find_best_spatial_cluster(expected_lines: List[str], word_pool: List[Dict], 
                            fuzzy_threshold: float = 0.90,
                            is_rotated: bool = False) -> List[Dict]:
    """
    Find the best spatial cluster of lines
    Works for both normal and rotated pages
    """
    
    logger.info(f"Finding best spatial cluster for {len(expected_lines)} lines (rotated={is_rotated})")
    
    # Find all candidates for each line
    all_candidates = {}
    
    for line_text in expected_lines:
        candidates = find_all_candidates_for_line(line_text, word_pool, fuzzy_threshold, is_rotated)
        
        if not candidates:
            logger.warning(f"No candidates found for: '{line_text}'")
            return []
        
        all_candidates[line_text] = candidates
        logger.info(f"Found {len(candidates)} valid combinations for '{line_text}'")
    
    # Try to find best combination - TRY ALL COMBINATIONS, NOT GREEDY
    all_complete_clusters = []  # Store all complete clusters with their scores
    
    first_line = expected_lines[0]
    
    # Get all possible combinations using itertools.product
    all_candidate_lists = [all_candidates[line_text] for line_text in expected_lines]
    
    logger.info(f"🔄 EXHAUSTIVE CLUSTERING: Trying all combinations")
    logger.info(f"  Candidate counts: {[len(all_candidates[line]) for line in expected_lines]}")
    total_combos = 1
    for line_text in expected_lines:
        total_combos *= len(all_candidates[line_text])
    logger.info(f"  Total cluster combinations to try: {total_combos}")
    
    valid_cluster_count = 0
    
    # Try all combinations of candidates
    for combo in itertools.product(*all_candidate_lists):
        cluster = list(combo)
        
        # Check for word reuse across lines
        all_word_ids = set()
        has_reuse = False
        
        for candidate in cluster:
            candidate_word_ids = set(id(w) for w in candidate.get('words', []))
            if candidate_word_ids & all_word_ids:
                has_reuse = True
                break
            all_word_ids.update(candidate_word_ids)
        
        if has_reuse:
            continue  # Skip this combination
        
        # This is a valid cluster
        valid_cluster_count += 1
        score = score_cluster(cluster, expected_lines)
        
        # Log cluster details
        cluster_text = ' + '.join([c.get('matched_text', '?') for c in cluster])
        logger.info(f"  ✅ Cluster combo {valid_cluster_count}: '{cluster_text}' → score={score:.2f}")
        
        all_complete_clusters.append({'cluster': cluster, 'score': score})
    
    # Select best cluster with reading order as tiebreaker
    if not all_complete_clusters:
        logger.warning("No complete cluster found")
        return []
    
    logger.info(f"🏁 EXHAUSTIVE CLUSTERING DONE: Found {len(all_complete_clusters)} valid clusters (out of {total_combos} attempted)")
    logger.info(f"📊 SELECTION PHASE: Evaluating {len(all_complete_clusters)} complete cluster(s)")
    
    # Filter clusters with score > 50%
    good_clusters = [c for c in all_complete_clusters if c['score'] >= 50.0]
    logger.info(f"  Clusters with score >= 50%: {len(good_clusters)}")
    
    if not good_clusters:
        # If no clusters with score >= 50%, use the highest scored one
        logger.info("No clusters with score >= 50%, using highest scored cluster")
        best_cluster = max(all_complete_clusters, key=lambda x: x['score'])['cluster']
    else:
        # Among good clusters, apply reading order check on first 2 lines
        def check_reading_order_first_two_lines(cluster):
            """Check if first 2 lines follow correct reading order"""
            if len(cluster) < 2:
                return True
            
            line1_bbox = cluster[0]['bounding_box']
            line2_bbox = cluster[1]['bounding_box']
            
            # Get Y centers for normal pages, X centers for rotated pages
            if is_rotated:
                line1_center = (line1_bbox[0] + line1_bbox[4]) / 2
                line2_center = (line2_bbox[0] + line2_bbox[4]) / 2
                correct_order = line2_center > line1_center  # Right of line1
            else:
                line1_center = (line1_bbox[1] + line1_bbox[3] + line1_bbox[5] + line1_bbox[7]) / 4
                line2_center = (line2_bbox[1] + line2_bbox[3] + line2_bbox[5] + line2_bbox[7]) / 4
                correct_order = line2_center > line1_center  # Below line1
            
            return correct_order
        
        # Log reading order for each cluster
        logger.info(f"  Applying reading order check on {len(good_clusters)} good clusters:")
        for cluster_idx, cluster_data in enumerate(good_clusters):
            is_correct = check_reading_order_first_two_lines(cluster_data['cluster'])
            status = "✅ CORRECT" if is_correct else "❌ WRONG"
            logger.info(f"    Cluster {cluster_idx}: score={cluster_data['score']:.2f}, reading_order={status}")
        
        # Sort by: correct reading order (first 2 lines), then by score
        good_clusters.sort(key=lambda x: (
            not check_reading_order_first_two_lines(x['cluster']),  # False (correct) comes first
            -x['score']  # Then highest score
        ))
        
        best_cluster = good_clusters[0]['cluster']
        best_score = good_clusters[0]['score']
        logger.info(f"✅ SELECTED BEST CLUSTER: score={best_score:.2f}")
    
    return best_cluster


def score_cluster(cluster: List[Dict], expected_lines: List[str]) -> float:
    """Score a cluster based on spatial compactness, match quality, and completeness
    
    KEY: Strongly prefer TIGHTLY PACKED clusters with minimal bounding box area
    """
    
    if not cluster:
        return 0
    
    # Spatial compactness score - CRITICAL FACTOR
    all_bboxes = [item['bounding_box'] for item in cluster]
    merged = merge_bboxes(all_bboxes, padding=0)
    
    if not merged or len(merged) < 8:
        return 0
    
    width = max(merged[2], merged[4]) - min(merged[0], merged[6])
    height = max(merged[5], merged[7]) - min(merged[1], merged[3])
    area = width * height
    
    # Check if this is a single-token field
    is_single_token = len(expected_lines) == 1 and len(expected_lines[0].split()) == 1
    
    if is_single_token:
        # FOR SINGLE-WORD FIELDS: PREFER LARGEST AREA (most visible rendered text)
        # Larger area = better (user sees more of the word)
        # Area 1.0 = ~1 point, Area 5.0 = ~5 points, Area 10+ = ~10+ points
        compactness_score = area
        logger.debug(f"🎯 SINGLE-TOKEN field: area={area:.2f}, compactness={compactness_score:.1f} (LARGE IS BETTER)")
    else:
        # FOR MULTI-LINE FIELDS: PREFER SMALLEST AREA (most compact cluster)
        # TIGHTER IS BETTER: inverse relationship for area penalty
        # Small area (e.g., 1.0) = ~50 points
        # Medium area (e.g., 5.0) = ~17 points  
        # Large area (e.g., 10+) = ~9 points
        # This STRONGLY favors compact clusters
        compactness_score = 100 / (1 + area)
        logger.debug(f"🎯 MULTI-LINE field: area={area:.2f}, compactness={compactness_score:.1f} (SMALL IS BETTER)")
    
    # Match quality score
    avg_confidence = sum(item['match_confidence'] for item in cluster) / len(cluster)
    
    # Completeness score
    completeness_score = (len(cluster) / len(expected_lines)) * 100
    
    # Combined score - COMPACTNESS IS NOW 70% WEIGHT (was 50%)
    # This makes tightly packed boxes strongly preferred over loose ones
    total_score = (
        compactness_score * 0.7 +    # INCREASED from 0.5 - spatial compactness is primary
        avg_confidence * 0.2 +        # DECREASED from 0.3
        completeness_score * 0.1      # DECREASED from 0.2
    )
    
    logger.debug(f"  → Final score: {compactness_score:.1f}*0.7 + {avg_confidence:.1f}*0.2 + {completeness_score:.1f}*0.1 = {total_score:.1f}")
    
    return total_score


# ============================================
# FALLBACK STRATEGIES
# ============================================

def fallback_rotated_page_search(expected_lines: List[str], word_pool: List[Dict],
                                fuzzy_threshold: float = 0.90) -> List[Dict]:
    """
    Fallback for rotated pages: Use rotated page logic (NO coordinate transformation!)
    """
    logger.info("FALLBACK: Trying rotated page search")
    
    # Check if page is actually rotated
    if not detect_page_rotation(word_pool):
        logger.info("Page not rotated, skipping this fallback")
        return []
    
    # Use spatial clustering with is_rotated=True
    result = find_best_spatial_cluster(expected_lines, word_pool, fuzzy_threshold, is_rotated=True)
    
    if result:
        logger.info(f"✓ Rotated page search found {len(result)} lines")
    
    return result


def fallback_fuzzy_search(expected_lines: List[str], word_pool: List[Dict], 
                        fuzzy_threshold: float = 0.75) -> List[Dict]:
    """Fallback: Fuzzy search with punctuation stripping"""
    
    logger.info("FALLBACK: Trying fuzzy search with punctuation stripping")
    
    result_lines = []
    search_start_idx = 0
    
    for line_text in expected_lines:
        clean_line = strip_punctuation(line_text)
        
        if not clean_line:
            clean_line = line_text
        
        logger.debug(f"Searching for: '{clean_line}'")
        
        best_match = None
        best_score = 0
        best_end_idx = search_start_idx
        
        for start_idx in range(search_start_idx, len(word_pool)):
            tokens = clean_line.split()
            if not tokens:
                continue
            
            matched_words = []
            current_idx = start_idx
            
            for token in tokens:
                found = False
                
                for look_idx in range(current_idx, min(current_idx + 20, len(word_pool))):
                    word = word_pool[look_idx]
                    if not word or not isinstance(word, dict):
                        continue
                        
                    word_text = strip_punctuation(word.get('text', ''))
                    
                    if fuzzy_match(token, word_text) >= fuzzy_threshold:
                        matched_words.append(word)
                        current_idx = look_idx + 1
                        found = True
                        break
                
                if not found:
                    break
            
            if len(matched_words) == len(tokens):
                y_tolerance = 0.35
                if are_words_on_same_line(matched_words, y_tolerance=y_tolerance):
                    matched_words_sorted = sort_words_left_to_right(matched_words)
                    matched_text = ' '.join([w.get('text', '') for w in matched_words_sorted])
                    score = fuzzy_match(clean_line, matched_text)
                    
                    if score > best_score:
                        best_score = score
                        best_match = matched_words_sorted
                        best_end_idx = current_idx
        
        if best_match:
            matched_text = ' '.join([w.get('text', '') for w in best_match])
            line_bbox = merge_bboxes([w['bounding_box'] for w in best_match], padding=0.01)
            
            if line_bbox:
                avg_confidence = sum(w.get('confidence', 0) for w in best_match) / len(best_match)
                
                result = {
                    'matched_text': matched_text,
                    'field_value': line_text,
                    'bounding_box': line_bbox,
                    'bounding_page': best_match[0].get('bounding_page', 1),
                    'match_confidence': best_score * 100,
                    'coordinate_confidence': best_score * 100,
                    'match_type': 'word_refined_fallback',
                    'ocr_confidence': avg_confidence,
                    'word_count': len(best_match)
                }
                
                result_lines.append(result)
                search_start_idx = best_end_idx
                logger.info(f"✓ Fuzzy found: '{line_text}' → '{matched_text}'")
    
    return result_lines


def fallback_expand_existing_match(best_match: Dict, expected_lines: List[str], 
                                word_pool: List[Dict]) -> List[Dict]:
    """Fallback: Expand around existing partial match"""
    
    logger.info("FALLBACK: Trying to expand existing partial match")
    
    if not best_match or not isinstance(best_match, dict) or 'bounding_box' not in best_match:
        return []
    
    match_bbox = best_match['bounding_box']
    match_page = best_match.get('bounding_page', 1)
    
    nearby_words = []
    
    for word in word_pool:
        if not word or not isinstance(word, dict):
            continue
            
        if word.get('bounding_page') != match_page:
            continue
        
        word_bbox = word.get('bounding_box', [])
        if not word_bbox or len(word_bbox) < 8:
            continue
        
        distance = calculate_distance(match_bbox, word_bbox)
        
        if distance <= 1.0:
            nearby_words.append(word)
    
    if not nearby_words:
        logger.warning("No nearby words found")
        return []
    
    sorted_nearby = sort_words_reading_order(nearby_words)
    
    logger.info(f"Found {len(sorted_nearby)} nearby words")
    
    return fallback_fuzzy_search(expected_lines, sorted_nearby, fuzzy_threshold=0.70)



# ============================================
# SMART LINE SPLITTER FOR LONG LINES
# ============================================

def split_long_line_smart(line_text: str, max_tokens: int = 8, max_chars: int = 100) -> List[str]:
    """
    Split long individual lines intelligently to prevent exponential combinations.
    
    Strategy:
    - If line has >= max_tokens OR >= max_chars: split it
    - Find split point near middle (by character count)
    - Prefer LONGEST words at split point (longer words = fewer candidates in pool)
    - Recursively split if parts are still too long
    
    Args:
        line_text: Single line to potentially split (no newlines)
        max_tokens: Split if line has more tokens than this
        max_chars: Split if line has more characters than this
        
    Returns:
        List of lines (may be 1 if no split needed, or 2+ if split)
    """
    tokens = line_text.split()
    
    # Check if split is needed
    if len(tokens) < max_tokens and len(line_text) < max_chars:
        logger.debug(f"✂️  split_long_line_smart: NO SPLIT NEEDED ({len(tokens)} tokens < {max_tokens}, {len(line_text)} chars < {max_chars})")
        return [line_text]  # No split needed
    
    logger.info(f"✂️  split_long_line_smart: SPLITTING '{line_text[:70]}...' ({len(tokens)} tokens, {len(line_text)} chars)")
    
    # Find optimal split point by character position
    mid_char = len(line_text) // 2
    char_pos = 0
    best_split_idx = 0
    best_token_length = 0
    
    logger.debug(f"✂️  Looking for split point near mid_char={mid_char}")
    
    for idx, token in enumerate(tokens):
        char_pos += len(token) + 1  # +1 for space
        
        # Check if this token is near mid point (±20 chars tolerance)
        distance_to_mid = abs(char_pos - mid_char)
        
        if distance_to_mid <= 20:
            # Prefer LONGEST tokens (they have fewer candidates in pool)
            token_clean = token.strip('.,!?;:')
            token_length = len(token_clean)
            
            if token_length > best_token_length:
                best_split_idx = idx + 1
                best_token_length = token_length
                logger.debug(f"✂️  Found good split point at token {idx}: '{token}' ({token_length} chars, distance={distance_to_mid})")
    
    # If no good split found, use mid point
    if best_split_idx == 0:
        best_split_idx = len(tokens) // 2
        logger.debug(f"✂️  No good split near middle, using mid point: token {best_split_idx}")
    
    part1 = ' '.join(tokens[:best_split_idx])
    part2 = ' '.join(tokens[best_split_idx:])
    
    logger.info(f"✂️  Split result: Part1({len(part1.split())} tokens) + Part2({len(part2.split())} tokens)")
    logger.debug(f"✂️    Part1: '{part1[:60]}...'")
    logger.debug(f"✂️    Part2: '{part2[:60]}...'")
    
    result = [part1, part2]
    
    # Recursively split if part2 is still too long
    if len(part2.split()) >= max_tokens or len(part2) >= max_chars:
        logger.info(f"✂️  Part2 still too long ({len(part2.split())} tokens >= {max_tokens} OR {len(part2)} chars >= {max_chars}), recursively splitting...")
        result = result[:-1] + split_long_line_smart(part2, max_tokens, max_chars)
    
    logger.info(f"✂️  Final result: {len(result)} parts")
    return result

# ============================================
# MAIN REFINER
# ============================================

def refine_coordinate_response(field_value: str, matches: List[Dict], 
                            best_match: Optional[Dict], 
                            word_ocr_data: List[Dict],
                            bounding_page_list: List[int] = None) -> Dict:
    """
    Main refiner function with spatial clustering + rotated page support
    
    Args:
        bounding_page_list: List of pages to try as fallbacks (e.g., [3, 4])
                            Will try anchor page first, then others in list order
    """
    
    logger.info("=" * 60)
    logger.info("OCR REFINER - Starting")
    logger.info(f"Field value: '{field_value}'")
    logger.info(f"Matches: {len(matches) if matches else 0}")
    logger.info(f"Best match: {best_match is not None}")
    logger.info("=" * 60)
    
    if not word_ocr_data:
        logger.error("No word_ocr_data!")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    # Safety check
    if not field_value:
        logger.error("No field_value!")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    # Skip if TOTAL field_value length is too long (>80 chars)
    if len(field_value) > 250:
        logger.info(f"Field value too long ({len(field_value)} chars > 80) - skipping refinement")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    # Parse lines from field_value (split by \n)
    expected_lines = [line.strip() for line in field_value.split('\n') if line.strip()]
    
    # SMART HEURISTIC: For long multi-line fields, skip refinement
    # Long fields (200+ chars) with few lines (3 or less) are already correctly 
    # grouped by search phase into encompassing bbox - refinement just breaks them apart
    if len(field_value) >= 200 and len(expected_lines) <= 3:
        logger.info(f"⏭️  SKIPPING REFINER: Long multi-line field detected")
        logger.info(f"   Length: {len(field_value)} chars >= 200, Lines: {len(expected_lines)} <= 3")
        logger.info(f"   Search phase already has correct encompassing bbox - returning as-is")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    if not expected_lines:
        logger.error("No expected lines after parsing!")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    # SMART SPLITTING: Split long individual lines to avoid exponential combinations
    # logger.info(f"🔍 SMART SPLIT START: Processing {len(expected_lines)} lines, checking for long lines to split...")
    # split_lines = []
    # line_split_map = {}  # Track which split lines came from which original line
    
    # for line_idx, line in enumerate(expected_lines):
    #     token_count = len(line.split())
    #     char_count = len(line)
    #     needs_split = token_count >= 8 or char_count >= 100
        
    #     logger.info(f"🔍 Line {line_idx + 1}: {token_count} tokens, {char_count} chars - NEEDS_SPLIT={needs_split}")
        
    #     if needs_split:
    #         logger.info(f"✂️  SPLITTING Line {line_idx + 1}: '{line[:70]}...'")
    #         try:
    #             split_parts = split_long_line_smart(line, max_tokens=8, max_chars=100)
    #             logger.info(f"✂️  Split result: {len(split_parts)} parts")
                
    #             for part_idx, part in enumerate(split_parts):
    #                 split_lines.append(part)
    #                 line_split_map[len(split_lines) - 1] = (line_idx, part_idx, len(split_parts))
    #                 logger.info(f"    ✂️  Part {part_idx + 1}/{len(split_parts)}: '{part[:60]}...'")
    #         except Exception as e:
    #             logger.error(f"❌ Error splitting line {line_idx + 1}: {str(e)}")
    #             split_lines.append(line)
    #             line_split_map[len(split_lines) - 1] = (line_idx, 0, 1)
    #     else:
    #         logger.info(f"✅ Line {line_idx + 1} is short enough, keeping as-is")
    #         split_lines.append(line)
    #         line_split_map[len(split_lines) - 1] = (line_idx, 0, 1)
    
    # logger.info(f"🔍 SMART SPLIT DONE: After splitting: {len(split_lines)} lines (from {len(expected_lines)} original lines)")
    # expected_lines = split_lines
    
    # logger.info(f"🔍 Now processing {len(expected_lines)} lines")
    
    # Get anchor page - search through ALL pages to find words matching any of the expected lines
    anchor_page = None
    word_pool = None
    
    # Try to find page with words matching expected lines
    all_pages = set()
    for word in word_ocr_data:
        if word and isinstance(word, dict):
            all_pages.add(word.get('bounding_page', 1))
    
    logger.info(f"Document has pages: {sorted(all_pages)}")
    
    # Try each page and find the one with best matches for our expected lines
    best_page_score = -1
    best_anchor_page = None
    
    for page_num in sorted(all_pages):
        page_words = [w for w in word_ocr_data if w and isinstance(w, dict) and w.get('bounding_page') == page_num]
        
        # Score this page based on how many expected line tokens appear on it
        page_score = 0
        for line_text in expected_lines:
            tokens = line_text.split()
            for token in tokens:
                for word in page_words:
                    if fuzzy_match(token, word.get('text', '')) >= 0.75:
                        page_score += 1
                        break
        
        logger.debug(f"Page {page_num}: score={page_score} ({len(page_words)} words)")
        
        if page_score > best_page_score:
            best_page_score = page_score
            best_anchor_page = page_num
    
    # Filter to best anchor page
    if best_anchor_page:
        anchor_page = best_anchor_page
        word_pool = [w for w in word_ocr_data if w and isinstance(w, dict) and w.get('bounding_page') == anchor_page]
        logger.info(f"Using {len(word_pool)} words from page {anchor_page} (score={best_page_score})")
    else:
        # Fallback: use all words
        word_pool = [w for w in word_ocr_data if w and isinstance(w, dict)]
        if word_pool:
            anchor_page = word_pool[0].get('bounding_page', 1)
            logger.info(f"Fallback: using all pages, first page is {anchor_page}")
    
    if not word_pool:
        logger.error("No valid words in word_pool!")
        return {'best_match': best_match, 'matches': matches if matches else []}
    
    # Sort word pool
    sorted_word_pool = sort_words_reading_order(word_pool)
    logger.info(f"Sorted {len(sorted_word_pool)} words in reading order")
    
    # PRIMARY: Normal spatial clustering on anchor page
    result_lines = find_best_spatial_cluster(expected_lines, sorted_word_pool, fuzzy_threshold=0.90, is_rotated=False)
    
    # FALLBACK LOGIC - Try other pages from bounding_page_list
    if not result_lines and bounding_page_list:
        logger.warning(f"❌ Spatial clustering on page {anchor_page} failed")
        logger.info(f"Trying fallback pages from bounding_page_list: {bounding_page_list}")
        
        # Get list of pages to try (all pages in bounding_page_list except anchor_page)
        fallback_pages = [p for p in bounding_page_list if p != anchor_page]
        logger.info(f"Fallback pages to try (in order): {fallback_pages}")
        
        for fallback_page in fallback_pages:
            logger.info(f"  FALLBACK: Trying page {fallback_page}...")
            fallback_word_pool = [w for w in word_ocr_data if w and isinstance(w, dict) and w.get('bounding_page') == fallback_page]
            
            if fallback_word_pool:
                fallback_sorted = sort_words_reading_order(fallback_word_pool)
                result_lines = find_best_spatial_cluster(expected_lines, fallback_sorted, fuzzy_threshold=0.90, is_rotated=False)
                
                if result_lines:
                    logger.info(f"  ✓ Found cluster on page {fallback_page}!")
                    break
            else:
                logger.info(f"  No words found on page {fallback_page}")
    
    # If still no results, try other fallback strategies
    if not result_lines:
        logger.warning("❌ All bounding_page fallbacks failed - trying other strategies")
        
        # Fallback 1: Rotated page search
        logger.info("Trying rotated page fallback...")
        result_lines = fallback_rotated_page_search(expected_lines, sorted_word_pool, fuzzy_threshold=0.80)
        
        if not result_lines:
            # Fallback 2: Fuzzy search
            logger.info("Trying fuzzy search fallback...")
            result_lines = fallback_fuzzy_search(expected_lines, sorted_word_pool, fuzzy_threshold=0.75)
            
            if not result_lines and best_match:
                # Fallback 3: Expand existing match
                logger.warning("Trying to expand existing match...")
                result_lines = fallback_expand_existing_match(best_match, expected_lines, sorted_word_pool)
        
        if not result_lines:
            logger.error("❌ ALL FALLBACKS FAILED - returning original")
            return {
                'best_match': best_match, 
                'matches': matches if matches else []
            }
    
    # Build final result
    if len(result_lines) == 1:
        refined_best_match = result_lines[0]
    else:
        all_bboxes = [line.get('bounding_box') for line in result_lines if line.get('bounding_box')]
        
        if not all_bboxes:
            logger.error("No valid bboxes in result_lines!")
            return {
                'best_match': best_match,
                'matches': matches if matches else []
            }
        
        merged_bbox = merge_bboxes(all_bboxes, padding=0.02)
        
        combined_text = '\n'.join([line['matched_text'] for line in result_lines])
        avg_confidence = sum(line['ocr_confidence'] for line in result_lines) / len(result_lines)
        page = result_lines[0]['bounding_page']
        
        refined_best_match = {
            'matched_text': combined_text,
            'field_value': field_value,
            'bounding_box': merged_bbox,
            'bounding_page': page,
            'match_confidence': 85,
            'coordinate_confidence': 85,
            'match_type': 'word_refined_multiline',
            'ocr_confidence': avg_confidence,
            'line_count': len(result_lines),
            'lines': result_lines
        }
    
    logger.info("=" * 60)
    logger.info(f"✅ SUCCESS - {len(result_lines)}/{len(expected_lines)} lines found")
    logger.info(f"Result: '{refined_best_match.get('matched_text', '')[:100]}...'")
    logger.info("=" * 60)
    
    return {
        'best_match': refined_best_match,
        'matches': result_lines
    }


# ============================================
# WRAPPER FOR API RESPONSE
# ============================================

def process_coordinate_response(response_data: Dict, word_ocr_data: List[Dict], 
                                bounding_page_list: List[int] = None) -> Dict:
    """Process full API response
    
    Args:
        bounding_page_list: List of pages for intelligent fallback (e.g., [3, 4])
    """
    
    if not response_data.get('success'):
        return response_data
    
    field_value = response_data.get('field_value', '')
    matches = response_data.get('matches', [])
    best_match = response_data.get('best_match')
    
    if not field_value or not word_ocr_data:
        return response_data
    
    try:
        refined = refine_coordinate_response(field_value, matches, best_match, word_ocr_data, bounding_page_list)
        
        response_data['best_match'] = refined['best_match']
        response_data['matches'] = refined['matches']
        response_data['total_matches'] = len(refined['matches'])
        response_data['message'] = f"Refined match for \"{field_value[:50]}...\""
        
        logger.info("✅ Response refined successfully")
    
    except Exception as e:
        logger.error(f"Refinement error: {e}", exc_info=True)
    
    return response_data
