"""
Azure OpenAI Helper Functions with Robust JSON Parsing
Handles incomplete JSON responses and provides fallback mechanisms
"""

import json
import openai
import os
from typing import List, Dict, Any
from tenacity import retry, wait_random_exponential, stop_after_attempt

def get_openai_client():
    """
    Get OpenAI client configured for the current environment
    Returns a compatible client object for both Azure and standard OpenAI
    """
    # Check if we're using Azure OpenAI or standard OpenAI
    if os.getenv('OPENAI_API_TYPE') == 'azure' or os.getenv('AZURE_OPENAI_ENDPOINT'):
        # For Azure OpenAI, return a wrapper that works with the vetting engine
        class AzureOpenAIWrapper:
            def __init__(self):
                # Configure Azure OpenAI
                openai.api_type = os.getenv('OPENAI_API_TYPE', 'azure')
                openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT', '')
                openai.api_version = os.getenv('OPENAI_API_VERSION', '2023-05-15')
                openai.api_key = os.getenv('OPENAI_API_KEY', '')
                
            @property
            def chat(self):
                return self
                
            @property  
            def completions(self):
                return self
                
            def create(self, model, messages, temperature=0.7, max_tokens=500, **kwargs):
                """Create chat completion using Azure OpenAI format"""
                try:
                    response = openai.ChatCompletion.create(
                        engine=model,  # Use engine for Azure
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    return response
                except Exception as e:
                    # Fallback response format
                    return {
                        'choices': [{
                            'message': {
                                'content': f"Error in OpenAI call: {str(e)}. Please check your configuration."
                            }
                        }]
                    }
        
        return AzureOpenAIWrapper()
    else:
        # For standard OpenAI, return a wrapper that's compatible
        class StandardOpenAIWrapper:
            def __init__(self):
                openai.api_key = os.getenv('OPENAI_API_KEY', '')
                
            @property
            def chat(self):
                return self
                
            @property  
            def completions(self):
                return self
                
            def create(self, model, messages, temperature=0.7, max_tokens=500, **kwargs):
                """Create chat completion using standard OpenAI format"""
                try:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    return response
                except Exception as e:
                    # Fallback response format
                    return {
                        'choices': [{
                            'message': {
                                'content': f"Error in OpenAI call: {str(e)}. Please check your configuration."
                            }
                        }]
                    }
        
        return StandardOpenAIWrapper()

@retry(wait=wait_random_exponential(min=2, max=10), stop=stop_after_attempt(6))
def generate_records_azure_robust(prompt: str, deployment_name: str, max_records: int = 50) -> List[Dict[str, Any]]:
    """
    Generate synthetic records using Azure OpenAI with robust JSON parsing
    
    Args:
        prompt: The prompt to send to Azure OpenAI
        deployment_name: The Azure OpenAI deployment name
        max_records: Maximum number of records to generate (reduced to avoid token limits)
    
    Returns:
        List of dictionaries containing the generated records
    """
    # Modify prompt to request fewer records to avoid token limits
    modified_prompt = prompt
    for num in [100, 75, 50]:
        if f"{num} synthetic" in prompt:
            modified_prompt = prompt.replace(f"{num} synthetic", f"{max_records} synthetic")
            break
    
    # Add explicit instructions for valid JSON
    json_prompt = f"""
{modified_prompt}

IMPORTANT: 
1. Return ONLY a valid JSON array, no other text.
2. Ensure all JSON is properly formatted with closing brackets.
3. Each record should be a complete JSON object.
4. Do not include any markdown formatting or code blocks.
"""
    
    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a JSON data generator. Always return valid, complete JSON arrays."},
                {"role": "user", "content": json_prompt}
            ],
            max_tokens=4000,
            temperature=0.6
        )
        
        content = response["choices"][0]["message"]["content"].strip()
        
        # Remove any markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Try to parse the complete response
        try:
            data = json.loads(content)
            if isinstance(data, list):
                print(f"Successfully parsed {len(data)} records")
                return data
            else:
                # If it's not a list, wrap it in a list
                return [data]
        except json.JSONDecodeError as e:
            print(f"Initial JSON parsing failed: {e}")
            
            # Attempt to extract valid JSON array
            start = content.find("[")
            end = content.rfind("]")
            
            if start != -1 and end != -1 and end > start:
                try:
                    json_str = content[start:end+1]
                    # Clean up common issues
                    json_str = fix_common_json_issues(json_str)
                    data = json.loads(json_str)
                    print(f"Extracted and parsed {len(data)} records from partial response")
                    return data
                except json.JSONDecodeError:
                    pass
            
            # If array extraction fails, try to parse individual records
            records = parse_individual_records(content)
            if records:
                print(f"Recovered {len(records)} individual records")
                return records
            
            # Final fallback: return minimal valid data
            print("WARNING: Could not parse response, returning empty list")
            return []
            
    except Exception as e:
        print(f"Error generating records: {e}")
        raise


def fix_common_json_issues(json_str: str) -> str:
    """Fix common JSON formatting issues"""
    # Remove trailing commas before closing brackets
    import re
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Ensure the string ends with a closing bracket if it doesn't
    json_str = json_str.rstrip()
    if not json_str.endswith("]"):
        # Find the last complete object and close the array
        last_brace = json_str.rfind("}")
        if last_brace != -1:
            json_str = json_str[:last_brace+1] + "]"
    
    return json_str


def parse_individual_records(content: str) -> List[Dict[str, Any]]:
    """Try to parse individual JSON records from a potentially malformed response"""
    records = []
    lines = content.split("\n")
    current_record = ""
    brace_count = 0
    in_string = False
    escape_next = False
    
    for line in lines:
        for char in line:
            if escape_next:
                escape_next = False
                current_record += char
                continue
                
            if char == "\\" and in_string:
                escape_next = True
                current_record += char
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    
            current_record += char
            
            # When we have a complete object
            if brace_count == 0 and current_record.strip().endswith("}"):
                try:
                    # Clean and parse the record
                    record_str = current_record.strip()
                    if record_str.endswith(","):
                        record_str = record_str[:-1]
                    
                    record = json.loads(record_str)
                    records.append(record)
                    current_record = ""
                except json.JSONDecodeError:
                    current_record = ""
                    brace_count = 0
    
    return records


def validate_and_fix_data(data: List[Dict[str, Any]], table_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate and fix generated data to ensure required fields exist
    
    Args:
        data: List of generated records
        table_config: Configuration dictionary with table metadata
    
    Returns:
        Fixed list of records
    """
    if not data:
        return data
    
    id_field = table_config.get('id_field')
    module = table_config.get('module', 'Unknown')
    
    # Check if the ID field exists in the first record
    if data and id_field and id_field not in data[0]:
        print(f"Warning: {id_field} not found in {module} records. Adding sequential IDs...")
        
        # Add sequential IDs to all records
        for i, record in enumerate(data):
            if id_field not in record:
                # Generate a unique ID based on module and index
                prefix = module.upper().replace(' ', '_')
                record[id_field] = f"{prefix}_{i+1:04d}"
    
    return data