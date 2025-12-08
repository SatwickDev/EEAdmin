"""
Extraction Service - Chunk-based and Parallel Entity Extraction

This module provides the core extraction logic for extracting entities from
OCR text using LLM-based processing with chunk-based parallel execution.
"""

import concurrent.futures
import json
import logging
from typing import Dict, List, Any

import openai

from app.utils.app_config import deployment_name
from app.backend.Smart_Document_Capture.Document_Classification import DocumentClassifier
from .helpers import parse_json_from_llm_response

logger = logging.getLogger(__name__)

# Module-level singleton instance of DocumentClassifier
_document_classifier_instance = None

def get_document_classifier():
    """Get or create the singleton DocumentClassifier instance."""
    global _document_classifier_instance
    if _document_classifier_instance is None:
        _document_classifier_instance = DocumentClassifier()
        logger.info("✅ Created DocumentClassifier instance for extraction service")
    return _document_classifier_instance


def extract_entities_in_chunks(
    entity_info: Dict, 
    ocr_text: str, 
    model: str, 
    page_number: int, 
    document_type: str = "Unknown"
) -> List[Dict]:
    """
    Extract entities by dividing them into logical chunks for parallel processing.
    This ensures consistent results by processing specific entity groups in parallel.

    Args:
        entity_info: Dictionary with mandatory_fields, optional_fields, conditional_fields
        ocr_text: OCR text to extract from
        model: LLM model/engine to use
        page_number: Page number being processed
        document_type: Type of document being processed (e.g., "Letter of Credit")
    
    Returns:
        List of extraction results from each chunk
    """
    # DEBUG: Log the document_type parameter at function entry
    logger.info(f"🔍 extract_entities_in_chunks CALLED with document_type='{document_type}'")
    
    logger.info(f"🧩 Starting chunk-based entity extraction for page {page_number}")

    # Get DocumentClassifier instance and load chunking configuration from YAML
    classifier = get_document_classifier()
    chunking_config = classifier.prompt_config.get('chunking', {})
    thresholds = chunking_config.get('entity_count_thresholds', {'small': 10, 'medium': 20, 'large': 30})
    chunk_counts = chunking_config.get('chunk_counts', {'small': 2, 'medium': 3, 'large': 4, 'xlarge': 5})
    base_seed = chunking_config.get('base_seed', 12345)
    seed_increment = chunking_config.get('seed_increment_per_chunk', 1)
    min_entities = chunking_config.get('min_entities_per_chunk', 1)
    prioritize_mandatory = chunking_config.get('prioritize_mandatory_first', True)
    priority_order = chunking_config.get('priority_order', ['Mandatory', 'Optional', 'Conditional'])

    logger.info(f"📋 Chunking Configuration Loaded:")
    logger.info(f"   Thresholds: small≤{thresholds['small']}, medium≤{thresholds['medium']}, large≤{thresholds['large']}")
    logger.info(f"   Chunk Counts: small={chunk_counts['small']}, medium={chunk_counts['medium']}, large={chunk_counts['large']}, xlarge={chunk_counts['xlarge']}")
    logger.info(f"   Base Seed: {base_seed}, Seed Increment: {seed_increment}")
    logger.info(f"   Priority Order: {priority_order}")

    # Calculate total entities
    all_entities = entity_info['mandatory_fields'] + entity_info['optional_fields'] + entity_info['conditional_fields']
    total_entities = len(all_entities)
    logger.info(f"📋 Total entities to extract: {total_entities} (Mandatory: {len(entity_info['mandatory_fields'])}, Optional: {len(entity_info['optional_fields'])}, Conditional: {len(entity_info['conditional_fields'])})")

    # Determine optimal number of chunks based on configuration
    if total_entities <= thresholds['small']:
        num_chunks = chunk_counts['small']
    elif total_entities <= thresholds['medium']:
        num_chunks = chunk_counts['medium']
    elif total_entities <= thresholds['large']:
        num_chunks = chunk_counts['large']
    else:
        num_chunks = chunk_counts['xlarge']

    # Prioritize fields based on configuration
    chunk_size = max(min_entities, total_entities // num_chunks)
    entity_chunks = []
    
    current_chunk = []
    current_chunk_priority = []
    
    # Process entities in configured priority order
    priority_field_map = {
        'Mandatory': entity_info['mandatory_fields'],
        'Optional': entity_info['optional_fields'],
        'Conditional': entity_info['conditional_fields']
    }
    
    for priority_name in priority_order:
        fields = priority_field_map.get(priority_name, [])
        for entity in fields:
            current_chunk.append(entity)
            current_chunk_priority.append(priority_name)
            if len(current_chunk) >= chunk_size and len(entity_chunks) < num_chunks - 1:
                entity_chunks.append({
                    'entities': current_chunk.copy(),
                    'priorities': current_chunk_priority.copy(),
                    'chunk_id': len(entity_chunks) + 1
                })
                current_chunk = []
                current_chunk_priority = []
        if len(current_chunk) >= chunk_size and len(entity_chunks) < num_chunks - 1:
            entity_chunks.append({
                'entities': current_chunk.copy(),
                'priorities': current_chunk_priority.copy(),
                'chunk_id': len(entity_chunks) + 1
            })
            current_chunk = []
            current_chunk_priority = []

    # Add remaining entities to the last chunk
    if current_chunk:
        entity_chunks.append({
            'entities': current_chunk,
            'priorities': current_chunk_priority,
            'chunk_id': len(entity_chunks) + 1
        })

    logger.info(f"📦 Created {len(entity_chunks)} entity chunks:")
    for i, chunk in enumerate(entity_chunks):
        mandatory_count = sum(1 for p in chunk['priorities'] if p == 'Mandatory')
        optional_count = sum(1 for p in chunk['priorities'] if p == 'Optional')
        conditional_count = sum(1 for p in chunk['priorities'] if p == 'Conditional')
        logger.info(f"   Chunk {i+1}: {len(chunk['entities'])} entities (M:{mandatory_count}, O:{optional_count}, C:{conditional_count})")

    def extract_chunk(chunk_info: Dict) -> Dict:
        """Extract entities for a specific chunk."""
        chunk_id = chunk_info['chunk_id']
        entities = chunk_info['entities']
        priorities = chunk_info['priorities']
        
        try:
            logger.info(f"   📤 Chunk {chunk_id}: Processing {len(entities)} entities")
            
            # Build field list for this chunk
            field_list = []
            field_definitions = {}
            
            for entity, priority in zip(entities, priorities):
                field_name = entity['entityName']
                field_desc = entity.get('description', '')
                field_list.append(field_name)
                
                if field_desc:
                    field_definitions[field_name] = f"{field_name} ({priority}) - {field_desc}"
                else:
                    field_definitions[field_name] = f"{field_name} ({priority})"

            # Build extraction prompt for this chunk using the classifier instance
            chunk_classifier = get_document_classifier()
            chunk_prompt = chunk_classifier.build_extraction_prompt_for_entities(
                field_list=field_list,
                field_definitions=field_definitions,
                ocr_text=ocr_text,
                page_number=page_number,
                chunk_id=chunk_id,
                document_type=document_type
            )

            logger.info(f"📋 ENTITY EXTRACTION REQUEST (Chunk {chunk_id}) TO AZURE OPENAI:")
            logger.info(f"  🌐 Endpoint: {openai.api_base}")
            logger.info(f"  🔑 API Key: {openai.api_key[:10]}...{openai.api_key[-4:] if openai.api_key and len(openai.api_key) > 14 else '***'}")
            logger.info(f"  📝 API Version: {openai.api_version}")
            logger.info(f"  🚀 Deployment/Engine: {model}")
            logger.info(f"  🔧 Temperature: 0")
            logger.info(f"  🎲 Seed: {base_seed + (seed_increment * (chunk_id - 1))}")
            logger.info(f"  📊 Max Tokens: (default)")
            logger.info(f"  📄 Prompt Length: {len(chunk_prompt)} characters")
            logger.info(f"  📋 Chunk Fields: {len(field_list)} fields")
            logger.info(f"  📋 COMPLETE PROMPT (FULL - NO TRUNCATION):\\n{chunk_prompt}")
            logger.info(f"📤 Calling Azure OpenAI for chunk {chunk_id} extraction...")

            # System message must contain 'json' when using response_format json_object
            system_message = "You are a document entity extraction assistant. Extract the requested fields from the document text and return your response as a valid JSON object."

            # Make LLM call for this chunk
            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": chunk_prompt}
                ],
                temperature=0,
                seed=base_seed + (seed_increment * (chunk_id - 1)),  # Configured seed per chunk for reproducibility
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            logger.info(f"✅ Azure OpenAI API call successful for chunk {chunk_id}")
            result = response["choices"][0]["message"]["content"].strip()
            logger.info(f"📊 ENTITY EXTRACTION RESPONSE (Chunk {chunk_id} - Raw):")
            logger.info(f"  📄 Content Length: {len(result)} characters")
            logger.info(f"  📋 Full Response (COMPLETE - NO TRUNCATION):\\n{result}")
            
            parsed_json = parse_json_from_llm_response(result)

            if parsed_json and 'extracted_fields' in parsed_json:
                field_count = len(parsed_json.get('extracted_fields', {}))
                logger.info(f"📊 ENTITY EXTRACTION RESPONSE (Chunk {chunk_id} - Parsed):")
                logger.info(f"  ✅ Extracted fields: {field_count}/{len(entities)}")
                logger.info(f"  📋 Extracted fields (COMPLETE):\\n{json.dumps(parsed_json.get('extracted_fields', {}), indent=2)}")
                logger.info(f"   ✅ Chunk {chunk_id}: Extracted {field_count}/{len(entities)} fields")
            else:
                logger.warning(f"   ⚠️  Chunk {chunk_id}: Failed to parse response")

            return parsed_json if parsed_json else {}

        except Exception as e:
            logger.error(f"   ❌ Chunk {chunk_id}: Error - {str(e)}")
            return {}

    # Execute parallel chunk extraction
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(entity_chunks)) as executor:
        # Submit all chunk tasks
        future_to_chunk = {
            executor.submit(extract_chunk, chunk): chunk['chunk_id']
            for chunk in entity_chunks
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_id = future_to_chunk[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"   ❌ Chunk {chunk_id}: Exception - {str(e)}")
                results.append({})

    successful_count = sum(1 for r in results if r and 'extracted_fields' in r)
    total_extracted = sum(len(r.get('extracted_fields', {})) for r in results if r)
    logger.info(f"🏁 Chunk extraction complete: {successful_count}/{len(entity_chunks)} chunks successful, {total_extracted} total fields extracted")

    return results


def extract_entities_parallel(
    prompt: str, 
    model: str, 
    temperature: float, 
    num_attempts: int = 3
) -> List[Dict]:
    """
    Perform parallel entity extraction with multiple concurrent LLM calls.

    Args:
        prompt: The extraction prompt
        model: The model name/engine to use
        temperature: Temperature setting for LLM
        num_attempts: Number of parallel extraction attempts

    Returns:
        List of extraction results from all attempts
    """
    logger.info(f"🚀 Starting parallel extraction with {num_attempts} concurrent attempts")

    def single_extraction_call(attempt_num: int) -> Dict:
        """Single extraction call for parallel execution."""
        try:
            logger.info(f"   📤 Attempt {attempt_num + 1}/{num_attempts}: Sending request to LLM")
            
            # System message must contain 'json' when using response_format json_object
            system_message = "You are a document entity extraction assistant. Extract the requested fields from the document text and return your response as a valid JSON object."
            
            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                seed=12345,  # ✅ Reproducibility
                top_p=0.1,  # ✅ NOT 1.0 (reduces randomness)
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            result = response["choices"][0]["message"]["content"].strip()
            parsed_json = parse_json_from_llm_response(result)

            if parsed_json and 'extracted_fields' in parsed_json:
                field_count = len(parsed_json.get('extracted_fields', {}))
                logger.info(f"   ✅ Attempt {attempt_num + 1}: Extracted {field_count} fields")
            else:
                logger.warning(f"   ⚠️  Attempt {attempt_num + 1}: Failed to parse response")

            return parsed_json if parsed_json else {}

        except Exception as e:
            logger.error(f"   ❌ Attempt {attempt_num + 1}: Error - {str(e)}")
            return {}

    # Execute parallel extraction calls using ThreadPoolExecutor
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_attempts) as executor:
        # Submit all extraction tasks
        future_to_attempt = {
            executor.submit(single_extraction_call, i): i
            for i in range(num_attempts)
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_attempt):
            attempt_num = future_to_attempt[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"   ❌ Attempt {attempt_num + 1}: Exception - {str(e)}")
                results.append({})

    successful_count = sum(1 for r in results if r and 'extracted_fields' in r)
    logger.info(f"🏁 Parallel extraction complete: {successful_count}/{num_attempts} successful attempts")

    return results
