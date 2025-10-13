"""
Azure OpenAI Helper using LangChain Framework
Provides the same interface as the original but uses LangChain internally
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, wait_random_exponential, stop_after_attempt

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import get_openai_callback
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class LangChainOpenAIWrapper:
    """
    Wrapper class that maintains the same interface as the original
    but uses LangChain internally for all operations
    """
    
    def __init__(self):
        """Initialize the LangChain-based OpenAI client"""
        self.llm = self._initialize_llm()
        self.json_parser = JsonOutputParser()
        
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on environment configuration"""
        if os.getenv('OPENAI_API_TYPE') == 'azure' or os.getenv('AZURE_OPENAI_ENDPOINT'):
            # Azure OpenAI configuration
            return AzureChatOpenAI(
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
                api_key=os.getenv('AZURE_OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', '')),
                api_version=os.getenv('OPENAI_API_VERSION', '2023-05-15'),
                deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o'),
                temperature=0.7,
                max_tokens=500
            )
        else:
            # Standard OpenAI configuration
            return ChatOpenAI(
                api_key=os.getenv('OPENAI_API_KEY', ''),
                model=os.getenv('OPENAI_MODEL', 'gpt-4'),
                temperature=0.7,
                max_tokens=500
            )
    
    @property
    def chat(self):
        """Compatibility property for chat interface"""
        return self
    
    @property
    def completions(self):
        """Compatibility property for completions interface"""
        return self
    
    def create(self, model: str, messages: List[Dict], temperature: float = 0.7, 
               max_tokens: int = 500, **kwargs) -> Dict:
        """
        Create chat completion using LangChain, maintaining original interface
        
        Args:
            model: Model name (for compatibility, actual model is set in initialization)
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Dict: Response in OpenAI format for compatibility
        """
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    langchain_messages.append(SystemMessage(content=msg['content']))
                elif msg['role'] == 'user':
                    langchain_messages.append(HumanMessage(content=msg['content']))
                # Note: Assistant messages would need AIMessage if used
            
            # Update LLM parameters if different from defaults
            self.llm.temperature = temperature
            self.llm.max_tokens = max_tokens
            
            # Invoke the LLM with callback for token tracking
            with get_openai_callback() as cb:
                response = self.llm.invoke(langchain_messages)
                
                # Log token usage for monitoring
                logger.debug(f"Tokens used: {cb.total_tokens}, Cost: ${cb.total_cost}")
            
            # Format response to match original OpenAI structure
            return {
                'choices': [{
                    'message': {
                        'content': response.content,
                        'role': 'assistant'
                    },
                    'index': 0,
                    'finish_reason': 'stop'
                }],
                'usage': {
                    'prompt_tokens': cb.prompt_tokens if 'cb' in locals() else 0,
                    'completion_tokens': cb.completion_tokens if 'cb' in locals() else 0,
                    'total_tokens': cb.total_tokens if 'cb' in locals() else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in LangChain OpenAI call: {str(e)}")
            # Return error in compatible format
            return {
                'choices': [{
                    'message': {
                        'content': f"Error in OpenAI call: {str(e)}. Please check your configuration.",
                        'role': 'assistant'
                    }
                }]
            }

def get_openai_client():
    """
    Get LangChain-based OpenAI client that's compatible with original interface
    
    Returns:
        LangChainOpenAIWrapper: A wrapper that maintains compatibility
    """
    return LangChainOpenAIWrapper()

# Define Pydantic models for structured output
class SyntheticRecord(BaseModel):
    """Model for synthetic record generation"""
    record_type: str = Field(description="Type of record")
    data: Dict[str, Any] = Field(description="Record data")

class RecordsList(BaseModel):
    """Model for list of synthetic records"""
    records: List[SyntheticRecord] = Field(description="List of generated records")

@retry(wait=wait_random_exponential(min=2, max=10), stop=stop_after_attempt(6))
def generate_records_azure_robust(prompt: str, deployment_name: str, 
                                 max_records: int = 50) -> List[Dict[str, Any]]:
    """
    Generate synthetic records using LangChain with robust JSON parsing
    
    Args:
        prompt: The prompt for record generation
        deployment_name: Deployment name (for compatibility)
        max_records: Maximum number of records to generate
        
    Returns:
        List[Dict[str, Any]]: List of generated records
    """
    try:
        # Initialize LangChain LLM
        if os.getenv('OPENAI_API_TYPE') == 'azure':
            llm = AzureChatOpenAI(
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
                api_key=os.getenv('AZURE_OPENAI_API_KEY', ''),
                api_version=os.getenv('OPENAI_API_VERSION', '2023-05-15'),
                deployment_name=deployment_name,
                temperature=0.7,
                max_tokens=4000
            )
        else:
            llm = ChatOpenAI(
                api_key=os.getenv('OPENAI_API_KEY', ''),
                model='gpt-4',
                temperature=0.7,
                max_tokens=4000
            )
        
        # Create a structured output chain
        json_parser = JsonOutputParser()
        
        # Enhanced prompt template for JSON generation
        template = ChatPromptTemplate.from_messages([
            ("system", "You are a data generation assistant. Generate synthetic records as requested. Always return valid JSON."),
            ("user", "{prompt}\n\nGenerate up to {max_records} records. Return as a JSON array.")
        ])
        
        # Create the chain
        chain = template | llm | json_parser
        
        # Generate records
        with get_openai_callback() as cb:
            result = chain.invoke({
                "prompt": prompt,
                "max_records": max_records
            })
            logger.info(f"Generated {len(result) if isinstance(result, list) else 1} records. Tokens: {cb.total_tokens}")
        
        # Ensure result is a list
        if isinstance(result, dict):
            result = [result]
        elif not isinstance(result, list):
            result = []
        
        # Limit to max_records
        return result[:max_records]
        
    except Exception as e:
        logger.error(f"Error generating records with LangChain: {str(e)}")
        return []

def parse_incomplete_json_robust(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse potentially incomplete JSON responses using LangChain's JSON repair capabilities
    
    Args:
        response_text: Potentially incomplete JSON string
        
    Returns:
        List[Dict[str, Any]]: Parsed records or empty list
    """
    try:
        # First try standard JSON parsing
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Use LangChain's JSON repair chain
        try:
            llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            
            repair_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a JSON repair assistant. Fix the malformed JSON and return valid JSON only."),
                ("user", "Fix this JSON:\n{json_text}")
            ])
            
            repair_chain = repair_prompt | llm | JsonOutputParser()
            
            result = repair_chain.invoke({"json_text": response_text})
            
            if isinstance(result, dict):
                return [result]
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to repair JSON with LangChain: {str(e)}")
            return []

# Additional utility functions for backward compatibility
def classify_intent_with_llm(query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Classify user query intent using LangChain
    
    Args:
        query: User query to classify
        context: Optional context for classification
        
    Returns:
        Dict containing intent classification
    """
    try:
        llm = get_openai_client().llm
        
        # Create classification prompt
        template = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classification assistant for a banking application.
            Classify the user's intent into one of these categories:
            - data_query: Requesting data or reports
            - transaction: Performing a transaction
            - compliance: Compliance or regulation related
            - document_analysis: Document processing or analysis
            - general_inquiry: General questions or help"""),
            ("user", "Query: {query}\nContext: {context}\n\nProvide classification as JSON with 'intent' and 'confidence' fields.")
        ])
        
        chain = template | llm | JsonOutputParser()
        
        result = chain.invoke({
            "query": query,
            "context": context or "No additional context"
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Intent classification failed: {str(e)}")
        return {"intent": "general_inquiry", "confidence": 0}