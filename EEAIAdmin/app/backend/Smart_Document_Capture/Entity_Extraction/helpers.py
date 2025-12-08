"""
Helper functions for entity extraction module.

These are utility functions used by the extraction service and page processor.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional

import tiktoken

logger = logging.getLogger(__name__)


def calculate_text_token_count(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    """
    Calculate the token count for a given text using tiktoken.
    
    Args:
        text: The text to count tokens for
        model_name: The model name to use for tokenization
        
    Returns:
        Number of tokens in the text
    """
    enc = tiktoken.encoding_for_model(model_name)
    return len(enc.encode(text))


def format_ocr_data_for_llm_prompt(ocr_data: List[Dict]) -> str:
    """
    Format OCR data into a structured string for LLM prompts.
    
    Args:
        ocr_data: List of OCR entries with text, bounding_box, and bounding_page
        
    Returns:
        Formatted string representation of OCR data
    """
    formatted = ""
    for i, entry in enumerate(ocr_data):
        text = entry.get("text", "").replace("\n", " ")
        box = entry.get("bounding_box", [])
        page = entry.get("bounding_page", 0)
        formatted += f"{i + 1}. Text: \"{text}\"\n   Box: {box}, Page: {page}\n"
    return formatted


def parse_json_from_llm_response(text: str) -> Optional[Dict]:
    """
    Parse JSON from an LLM response text.
    
    Args:
        text: The raw LLM response text containing JSON
        
    Returns:
        Parsed JSON as a dictionary, or None if parsing fails
    """
    try:
        json_str = re.search(r'\{[\s\S]+\}', text).group()
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Could not parse JSON from LLM response: {e}")
        return None


def load_prompt_config() -> Optional[Dict[str, Any]]:
    """
    Load the prompt configuration from YAML file.
    
    Returns:
        Dictionary containing prompt configuration, or None if loading fails
    """
    import os
    import yaml
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'prompts.yaml')
        # Normalize path
        config_path = os.path.normpath(config_path)
        
        # Try alternate paths if primary doesn't exist
        if not os.path.exists(config_path):
            config_path = os.path.join('config', 'prompts.yaml')
        
        if not os.path.exists(config_path):
            # Try from app root
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'prompts.yaml')
            config_path = os.path.normpath(config_path)
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded prompt config from: {config_path}")
            return config
        else:
            logger.warning(f"Prompt config not found at any expected location")
            return None
            
    except Exception as e:
        logger.error(f"Error loading prompt config: {e}")
        return None
