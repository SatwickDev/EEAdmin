"""
Base Tool Class for Intent-Based Microservices
Provides common functionality for all intent tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ToolInput(BaseModel):
    """Base input model for all tools"""
    query: str = Field(description="The user query or request")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    user_id: str = Field(description="User identifier")
    repository: Optional[str] = Field(default=None, description="Active repository (trade_finance, treasury, cash)")
    session_id: Optional[str] = Field(default=None, description="Session identifier for context")

class ToolOutput(BaseModel):
    """Base output model for all tools"""
    success: bool = Field(description="Whether the operation was successful")
    data: Any = Field(description="The result data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    error: Optional[str] = Field(default=None, description="Error message if any")

class BaseIntentTool(BaseTool, ABC):
    """
    Base class for all intent-based tools/microservices
    Can be deployed as separate microservices or used as internal tools
    """
    
    name: str = "base_intent_tool"
    description: str = "Base tool for intent processing"
    args_schema: Type[BaseModel] = ToolInput
    return_direct: bool = False
    
    # Configuration for microservice deployment
    service_url: Optional[str] = None
    timeout: int = 30
    executor: ThreadPoolExecutor = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    @abstractmethod
    def _process_intent(self, 
                       query: str,
                       context: Optional[Dict[str, Any]],
                       user_id: str,
                       repository: Optional[str],
                       session_id: Optional[str]) -> ToolOutput:
        """
        Process the specific intent - to be implemented by subclasses
        
        Args:
            query: User query
            context: Additional context
            user_id: User identifier
            repository: Active repository
            session_id: Session identifier
            
        Returns:
            ToolOutput with results
        """
        pass
    
    def _run(self,
             query: str,
             context: Optional[Dict[str, Any]] = None,
             user_id: str = None,
             repository: Optional[str] = None,
             session_id: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """
        Execute the tool synchronously
        """
        try:
            # Log the intent processing
            logger.info(f"Processing {self.name} for user {user_id}")
            
            # If configured as microservice, make remote call
            if self.service_url:
                result = self._call_microservice(query, context, user_id, repository, session_id)
            else:
                # Process locally
                result = self._process_intent(query, context, user_id, repository, session_id)
            
            # Convert to string for LangChain compatibility
            if isinstance(result, ToolOutput):
                return str(result.data) if result.success else f"Error: {result.error}"
            return str(result)
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}")
            return f"Error processing {self.name}: {str(e)}"
    
    async def _arun(self,
                    query: str,
                    context: Optional[Dict[str, Any]] = None,
                    user_id: str = None,
                    repository: Optional[str] = None,
                    session_id: Optional[str] = None,
                    run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """
        Execute the tool asynchronously
        """
        try:
            logger.info(f"Async processing {self.name} for user {user_id}")
            
            if self.service_url:
                result = await self._acall_microservice(query, context, user_id, repository, session_id)
            else:
                # Run in executor for async compatibility
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    self._process_intent,
                    query, context, user_id, repository, session_id
                )
            
            if isinstance(result, ToolOutput):
                return str(result.data) if result.success else f"Error: {result.error}"
            return str(result)
            
        except Exception as e:
            logger.error(f"Async error in {self.name}: {str(e)}")
            return f"Error processing {self.name}: {str(e)}"
    
    def _call_microservice(self, 
                          query: str,
                          context: Optional[Dict[str, Any]],
                          user_id: str,
                          repository: Optional[str],
                          session_id: Optional[str]) -> ToolOutput:
        """
        Call external microservice for this intent
        """
        import requests
        
        try:
            payload = {
                "query": query,
                "context": context,
                "user_id": user_id,
                "repository": repository,
                "session_id": session_id
            }
            
            response = requests.post(
                self.service_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return ToolOutput(
                    success=True,
                    data=data.get('result'),
                    metadata=data.get('metadata', {})
                )
            else:
                return ToolOutput(
                    success=False,
                    data=None,
                    error=f"Microservice returned {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"Microservice call failed: {str(e)}")
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
    
    async def _acall_microservice(self,
                                  query: str,
                                  context: Optional[Dict[str, Any]],
                                  user_id: str,
                                  repository: Optional[str],
                                  session_id: Optional[str]) -> ToolOutput:
        """
        Async call to external microservice
        """
        import aiohttp
        
        try:
            payload = {
                "query": query,
                "context": context,
                "user_id": user_id,
                "repository": repository,
                "session_id": session_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.service_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return ToolOutput(
                            success=True,
                            data=data.get('result'),
                            metadata=data.get('metadata', {})
                        )
                    else:
                        return ToolOutput(
                            success=False,
                            data=None,
                            error=f"Microservice returned {response.status}"
                        )
                        
        except Exception as e:
            logger.error(f"Async microservice call failed: {str(e)}")
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
    
    def as_microservice(self, host: str = "localhost", port: int = 8000) -> None:
        """
        Run this tool as a standalone microservice
        """
        from flask import Flask, request, jsonify
        
        app = Flask(self.name)
        
        @app.route('/process', methods=['POST'])
        def process():
            data = request.json
            result = self._process_intent(
                query=data.get('query'),
                context=data.get('context'),
                user_id=data.get('user_id'),
                repository=data.get('repository'),
                session_id=data.get('session_id')
            )
            
            return jsonify({
                'success': result.success,
                'result': result.data,
                'metadata': result.metadata,
                'error': result.error
            })
        
        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy', 'service': self.name})
        
        app.run(host=host, port=port)

class MCPToolAdapter:
    """
    Adapter to expose tools as MCP (Model Context Protocol) servers
    """
    
    def __init__(self, tool: BaseIntentTool):
        self.tool = tool
    
    def to_mcp_tool(self) -> Dict[str, Any]:
        """
        Convert tool to MCP tool specification
        """
        return {
            "name": self.tool.name,
            "description": self.tool.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "context": {"type": "object"},
                    "user_id": {"type": "string"},
                    "repository": {"type": "string"},
                    "session_id": {"type": "string"}
                },
                "required": ["query", "user_id"]
            },
            "handler": self._mcp_handler
        }
    
    async def _mcp_handler(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP-compatible handler for the tool
        """
        result = await self.tool._arun(
            query=arguments.get('query'),
            context=arguments.get('context'),
            user_id=arguments.get('user_id'),
            repository=arguments.get('repository'),
            session_id=arguments.get('session_id')
        )
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }