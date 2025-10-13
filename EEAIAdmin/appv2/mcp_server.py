"""
MCP (Model Context Protocol) Server for EEAI Tools
Exposes all intent-based tools as MCP-compatible services
"""

import json
import logging
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from appv2.tools import TOOL_REGISTRY
from appv2.tools.base_tool import MCPToolAdapter

logger = logging.getLogger(__name__)

class EEAIMCPServer:
    """
    MCP Server that exposes all EEAI tools through the Model Context Protocol
    """
    
    def __init__(self, name: str = "eeai-mcp-server"):
        """
        Initialize the MCP server
        
        Args:
            name: Server name for identification
        """
        self.name = name
        self.tools = {}
        self.adapters = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize and register all tools"""
        for tool_name, tool_class in TOOL_REGISTRY.items():
            try:
                # Create tool instance
                tool = tool_class()
                self.tools[tool_name] = tool
                
                # Create MCP adapter
                adapter = MCPToolAdapter(tool)
                self.adapters[tool_name] = adapter
                
                logger.info(f"Registered MCP tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to register tool {tool_name}: {str(e)}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get MCP server information
        
        Returns:
            Server metadata and capabilities
        """
        return {
            "name": self.name,
            "version": "1.0.0",
            "description": "EEAI Banking Application MCP Server",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True
            }
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available MCP tools
        
        Returns:
            List of tool specifications
        """
        tools_list = []
        for name, adapter in self.adapters.items():
            tool_spec = adapter.to_mcp_tool()
            tools_list.append(tool_spec)
        return tools_list
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """
        List available resources (repositories, databases)
        
        Returns:
            List of resource specifications
        """
        return [
            {
                "uri": "repository://trade_finance",
                "name": "Trade Finance Repository",
                "description": "LC, Bank Guarantees, Trade Documents",
                "mimeType": "application/json"
            },
            {
                "uri": "repository://treasury",
                "name": "Treasury Repository",
                "description": "FX, Investments, Risk Management",
                "mimeType": "application/json"
            },
            {
                "uri": "repository://cash_management",
                "name": "Cash Management Repository",
                "description": "Cash Flow, Liquidity, Payments",
                "mimeType": "application/json"
            }
        ]
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List available prompt templates
        
        Returns:
            List of prompt specifications
        """
        return [
            {
                "name": "lc_creation",
                "description": "Create a Letter of Credit",
                "arguments": [
                    {"name": "applicant", "description": "LC applicant details", "required": True},
                    {"name": "beneficiary", "description": "LC beneficiary details", "required": True},
                    {"name": "amount", "description": "LC amount", "required": True},
                    {"name": "currency", "description": "Currency code", "required": False}
                ]
            },
            {
                "name": "compliance_check",
                "description": "Check document compliance",
                "arguments": [
                    {"name": "document_type", "description": "Type of document", "required": True},
                    {"name": "content", "description": "Document content", "required": True},
                    {"name": "rules", "description": "Compliance rules to check", "required": False}
                ]
            },
            {
                "name": "data_analysis",
                "description": "Analyze financial data",
                "arguments": [
                    {"name": "query", "description": "Analysis query", "required": True},
                    {"name": "repository", "description": "Data repository", "required": False},
                    {"name": "format", "description": "Output format", "required": False}
                ]
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific tool with arguments
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.adapters:
            return {
                "error": f"Tool {tool_name} not found",
                "available_tools": list(self.adapters.keys())
            }
        
        try:
            adapter = self.adapters[tool_name]
            result = await adapter._mcp_handler(arguments)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return {
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments
            }
    
    def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get a specific resource by URI
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource data
        """
        # Parse URI to determine resource type
        if uri.startswith("repository://"):
            repo_name = uri.replace("repository://", "")
            return self._get_repository_info(repo_name)
        else:
            return {"error": f"Unknown resource URI: {uri}"}
    
    def _get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """Get repository information"""
        repositories = {
            "trade_finance": {
                "name": "Trade Finance",
                "collections": ["letter_of_credit", "bank_guarantee", "export_collection"],
                "document_count": 1500,
                "last_updated": datetime.now().isoformat()
            },
            "treasury": {
                "name": "Treasury Management",
                "collections": ["fx_deals", "investments", "risk_metrics"],
                "document_count": 2300,
                "last_updated": datetime.now().isoformat()
            },
            "cash_management": {
                "name": "Cash Management",
                "collections": ["cash_positions", "liquidity", "payments"],
                "document_count": 3200,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        return repositories.get(repo_name, {"error": f"Repository {repo_name} not found"})
    
    def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        """
        Get a formatted prompt template
        
        Args:
            prompt_name: Name of the prompt template
            arguments: Arguments to fill the template
            
        Returns:
            Formatted prompt string
        """
        prompts = {
            "lc_creation": """
Create a Letter of Credit with the following details:
Applicant: {applicant}
Beneficiary: {beneficiary}
Amount: {amount} {currency}
Please generate the LC with all standard terms and conditions.
            """,
            "compliance_check": """
Check the following {document_type} for compliance:
Content: {content}
Rules to check: {rules}
Provide a detailed compliance report.
            """,
            "data_analysis": """
Analyze the following query: {query}
Repository: {repository}
Output format: {format}
Provide comprehensive analysis with insights.
            """
        }
        
        template = prompts.get(prompt_name, "")
        if template:
            return template.format(**arguments)
        return f"Prompt template {prompt_name} not found"
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP messages
        
        Args:
            message: MCP message
            
        Returns:
            Response message
        """
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        response = {
            "jsonrpc": "2.0",
            "id": msg_id
        }
        
        try:
            if method == "initialize":
                response["result"] = self.get_server_info()
            
            elif method == "tools/list":
                response["result"] = {"tools": self.list_tools()}
            
            elif method == "resources/list":
                response["result"] = {"resources": self.list_resources()}
            
            elif method == "prompts/list":
                response["result"] = {"prompts": self.list_prompts()}
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.call_tool(tool_name, arguments)
                response["result"] = result
            
            elif method == "resources/read":
                uri = params.get("uri")
                response["result"] = self.get_resource(uri)
            
            elif method == "prompts/get":
                prompt_name = params.get("name")
                arguments = params.get("arguments", {})
                response["result"] = {
                    "messages": [
                        {
                            "role": "user",
                            "content": self.get_prompt(prompt_name, arguments)
                        }
                    ]
                }
            
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
        
        except Exception as e:
            response["error"] = {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        
        return response
    
    def run_stdio_server(self):
        """
        Run MCP server using stdio (for command-line integration)
        """
        import sys
        
        logger.info(f"Starting MCP stdio server: {self.name}")
        
        async def stdio_handler():
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol, sys.stdin
            )
            
            while True:
                try:
                    # Read JSON-RPC message from stdin
                    line = await reader.readline()
                    if not line:
                        break
                    
                    message = json.loads(line.decode())
                    response = await self.handle_message(message)
                    
                    # Write response to stdout
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")
        
        asyncio.run(stdio_handler())
    
    def run_websocket_server(self, host: str = "localhost", port: int = 8765):
        """
        Run MCP server using WebSocket (for web integration)
        """
        import websockets
        
        async def websocket_handler(websocket, path):
            logger.info(f"New WebSocket connection from {websocket.remote_address}")
            
            try:
                async for message in websocket:
                    try:
                        msg_data = json.loads(message)
                        response = await self.handle_message(msg_data)
                        await websocket.send(json.dumps(response))
                    except Exception as e:
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": f"Parse error: {str(e)}"
                            }
                        }
                        await websocket.send(json.dumps(error_response))
            
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"WebSocket connection closed")
        
        logger.info(f"Starting MCP WebSocket server on {host}:{port}")
        start_server = websockets.serve(websocket_handler, host, port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

# Entry point for running as standalone MCP server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EEAI MCP Server")
    parser.add_argument("--mode", choices=["stdio", "websocket"], default="stdio",
                      help="Server mode (stdio or websocket)")
    parser.add_argument("--host", default="localhost", help="WebSocket host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    
    args = parser.parse_args()
    
    server = EEAIMCPServer()
    
    if args.mode == "stdio":
        server.run_stdio_server()
    else:
        server.run_websocket_server(args.host, args.port)