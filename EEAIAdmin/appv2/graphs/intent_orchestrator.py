"""
Intent Orchestrator using LangGraph
Coordinates multiple tools/microservices based on user intent
"""

from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.checkpoint import MemorySaver
import logging
import json

from appv2.tools import (
    DataQueryTool,
    TransactionTool,
    ComplianceTool,
    DocumentAnalysisTool,
    TradeFinanceTool,
    TreasuryTool,
    CashManagementTool,
    RAGTool
)
from appv2.chains.intent_classifier import IntentClassificationChain
from appv2.utils.azure_openai_langchain import get_openai_client

logger = logging.getLogger(__name__)

# Define the state for the graph
class OrchestratorState(TypedDict):
    """State that flows through the orchestrator graph"""
    messages: Sequence[BaseMessage]
    user_query: str
    user_id: str
    repository: Optional[str]
    session_id: Optional[str]
    intent: Optional[str]
    confidence: Optional[float]
    tools_to_use: Optional[List[str]]
    results: Optional[Dict[str, Any]]
    error: Optional[str]
    final_response: Optional[str]

class IntentOrchestrator:
    """
    Main orchestrator that routes queries to appropriate tools/microservices
    """
    
    def __init__(self, use_microservices: bool = False):
        """
        Initialize the orchestrator
        
        Args:
            use_microservices: If True, tools will call external microservices
        """
        self.use_microservices = use_microservices
        self.tools = self._initialize_tools()
        self.intent_classifier = IntentClassificationChain()
        self.llm = get_openai_client().llm
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize all available tools"""
        tools = {
            'data_query': DataQueryTool(),
            'transaction': TransactionTool(),
            'compliance': ComplianceTool(),
            'document_analysis': DocumentAnalysisTool(),
            'trade_finance': TradeFinanceTool(),
            'treasury': TreasuryTool(),
            'cash_management': CashManagementTool(),
            'rag_search': RAGTool()
        }
        
        # Configure tools for microservice mode if enabled
        if self.use_microservices:
            service_urls = {
                'data_query': 'http://localhost:8001/process',
                'transaction': 'http://localhost:8002/process',
                'compliance': 'http://localhost:8003/process',
                'document_analysis': 'http://localhost:8004/process',
                'trade_finance': 'http://localhost:8005/process',
                'treasury': 'http://localhost:8006/process',
                'cash_management': 'http://localhost:8007/process',
                'rag_search': 'http://localhost:8008/process'
            }
            
            for tool_name, tool in tools.items():
                if tool_name in service_urls:
                    tool.service_url = service_urls[tool_name]
        
        return tools
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("route_to_tools", self.route_to_tools)
        workflow.add_node("execute_tools", self.execute_tools)
        workflow.add_node("synthesize_response", self.synthesize_response)
        workflow.add_node("handle_error", self.handle_error)
        
        # Add edges
        workflow.set_entry_point("classify_intent")
        
        # Conditional routing based on intent classification
        workflow.add_conditional_edges(
            "classify_intent",
            self.should_continue,
            {
                "route": "route_to_tools",
                "error": "handle_error",
                "end": END
            }
        )
        
        workflow.add_edge("route_to_tools", "execute_tools")
        workflow.add_edge("execute_tools", "synthesize_response")
        workflow.add_edge("synthesize_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def classify_intent(self, state: OrchestratorState) -> OrchestratorState:
        """Classify the user's intent"""
        try:
            logger.info(f"Classifying intent for query: {state['user_query']}")
            
            # Use the intent classification chain
            classification = self.intent_classifier.classify(
                query=state['user_query'],
                repository=state.get('repository'),
                context=self._get_context_from_messages(state.get('messages', []))
            )
            
            state['intent'] = classification.get('intent')
            state['confidence'] = classification.get('confidence', 0)
            
            # Determine which tools to use based on intent
            state['tools_to_use'] = self._map_intent_to_tools(
                classification.get('intent'),
                state.get('repository')
            )
            
            logger.info(f"Intent: {state['intent']}, Confidence: {state['confidence']}, Tools: {state['tools_to_use']}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            state['error'] = str(e)
            return state
    
    def should_continue(self, state: OrchestratorState) -> str:
        """Determine next step based on classification"""
        if state.get('error'):
            return "error"
        elif state.get('confidence', 0) < 50:
            # Low confidence, might need clarification
            return "end"
        else:
            return "route"
    
    def route_to_tools(self, state: OrchestratorState) -> OrchestratorState:
        """Route to appropriate tools based on intent"""
        try:
            tools_to_use = state.get('tools_to_use', [])
            
            if not tools_to_use:
                # Default to RAG search if no specific tools identified
                state['tools_to_use'] = ['rag_search']
            
            # Prepare tool invocations
            tool_invocations = []
            for tool_name in tools_to_use:
                if tool_name in self.tools:
                    tool_invocations.append({
                        'tool': tool_name,
                        'input': {
                            'query': state['user_query'],
                            'user_id': state['user_id'],
                            'repository': state.get('repository'),
                            'session_id': state.get('session_id'),
                            'context': self._get_context_from_messages(state.get('messages', []))
                        }
                    })
            
            state['tool_invocations'] = tool_invocations
            return state
            
        except Exception as e:
            logger.error(f"Error routing to tools: {str(e)}")
            state['error'] = str(e)
            return state
    
    def execute_tools(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the selected tools"""
        try:
            results = {}
            tool_invocations = state.get('tool_invocations', [])
            
            for invocation in tool_invocations:
                tool_name = invocation['tool']
                tool_input = invocation['input']
                
                if tool_name in self.tools:
                    tool = self.tools[tool_name]
                    
                    logger.info(f"Executing tool: {tool_name}")
                    
                    # Execute tool (will use microservice if configured)
                    result = tool._run(
                        query=tool_input['query'],
                        context=tool_input.get('context'),
                        user_id=tool_input['user_id'],
                        repository=tool_input.get('repository'),
                        session_id=tool_input.get('session_id')
                    )
                    
                    results[tool_name] = result
                    logger.info(f"Tool {tool_name} completed")
            
            state['results'] = results
            return state
            
        except Exception as e:
            logger.error(f"Error executing tools: {str(e)}")
            state['error'] = str(e)
            return state
    
    def synthesize_response(self, state: OrchestratorState) -> OrchestratorState:
        """Synthesize final response from tool results"""
        try:
            results = state.get('results', {})
            
            if not results:
                state['final_response'] = "I couldn't process your request. Please try again."
                return state
            
            # Use LLM to synthesize a coherent response from tool outputs
            synthesis_prompt = f"""
            User Query: {state['user_query']}
            Intent: {state.get('intent', 'unknown')}
            
            Tool Results:
            {json.dumps(results, indent=2)}
            
            Please provide a clear, concise response to the user's query based on the tool results.
            Format the response appropriately for the type of request.
            """
            
            response = self.llm.invoke([
                SystemMessage(content="You are a helpful banking assistant. Synthesize tool results into a clear response."),
                HumanMessage(content=synthesis_prompt)
            ])
            
            state['final_response'] = response.content
            
            # Add response to message history
            messages = state.get('messages', [])
            messages.append(AIMessage(content=response.content))
            state['messages'] = messages
            
            return state
            
        except Exception as e:
            logger.error(f"Error synthesizing response: {str(e)}")
            state['error'] = str(e)
            return state
    
    def handle_error(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors gracefully"""
        error = state.get('error', 'An unexpected error occurred')
        state['final_response'] = f"I apologize, but I encountered an error: {error}. Please try again or contact support."
        return state
    
    def _map_intent_to_tools(self, intent: str, repository: Optional[str]) -> List[str]:
        """Map intent to appropriate tools"""
        intent_tool_mapping = {
            'data_query': ['data_query'],
            'transaction': ['transaction'],
            'compliance': ['compliance'],
            'document_analysis': ['document_analysis'],
            'trade_finance_query': ['trade_finance', 'rag_search'],
            'treasury_query': ['treasury', 'rag_search'],
            'cash_management_query': ['cash_management', 'rag_search'],
            'general': ['rag_search']
        }
        
        # If repository is specified, add repository-specific tool
        if repository:
            repo_tools = {
                'trade_finance': 'trade_finance',
                'treasury': 'treasury',
                'cash_management': 'cash_management'
            }
            
            if repository in repo_tools:
                tools = intent_tool_mapping.get(intent, [])
                if repo_tools[repository] not in tools:
                    tools.append(repo_tools[repository])
                return tools
        
        return intent_tool_mapping.get(intent, ['rag_search'])
    
    def _get_context_from_messages(self, messages: Sequence[BaseMessage]) -> Dict[str, Any]:
        """Extract context from message history"""
        context = {
            'history': []
        }
        
        for msg in messages[-10:]:  # Last 10 messages for context
            if isinstance(msg, HumanMessage):
                context['history'].append({'role': 'user', 'content': msg.content})
            elif isinstance(msg, AIMessage):
                context['history'].append({'role': 'assistant', 'content': msg.content})
        
        return context
    
    async def aprocess(self, 
                       query: str,
                       user_id: str,
                       repository: Optional[str] = None,
                       session_id: Optional[str] = None,
                       message_history: Optional[List[BaseMessage]] = None) -> Dict[str, Any]:
        """
        Async process a user query through the orchestrator
        
        Args:
            query: User query
            user_id: User identifier
            repository: Active repository
            session_id: Session identifier
            message_history: Previous messages for context
            
        Returns:
            Dict with response and metadata
        """
        initial_state = OrchestratorState(
            messages=message_history or [],
            user_query=query,
            user_id=user_id,
            repository=repository,
            session_id=session_id,
            intent=None,
            confidence=None,
            tools_to_use=None,
            results=None,
            error=None,
            final_response=None
        )
        
        # Run the graph
        config = {"configurable": {"thread_id": session_id or user_id}}
        final_state = await self.graph.ainvoke(initial_state, config)
        
        return {
            'response': final_state.get('final_response'),
            'intent': final_state.get('intent'),
            'confidence': final_state.get('confidence'),
            'tools_used': final_state.get('tools_to_use'),
            'error': final_state.get('error')
        }
    
    def process(self,
                query: str,
                user_id: str,
                repository: Optional[str] = None,
                session_id: Optional[str] = None,
                message_history: Optional[List[BaseMessage]] = None) -> Dict[str, Any]:
        """
        Synchronous process a user query through the orchestrator
        """
        initial_state = OrchestratorState(
            messages=message_history or [],
            user_query=query,
            user_id=user_id,
            repository=repository,
            session_id=session_id,
            intent=None,
            confidence=None,
            tools_to_use=None,
            results=None,
            error=None,
            final_response=None
        )
        
        # Run the graph
        config = {"configurable": {"thread_id": session_id or user_id}}
        final_state = self.graph.invoke(initial_state, config)
        
        return {
            'response': final_state.get('final_response'),
            'intent': final_state.get('intent'),
            'confidence': final_state.get('confidence'),
            'tools_used': final_state.get('tools_to_use'),
            'error': final_state.get('error')
        }

# Singleton instance
_orchestrator_instance = None

def get_orchestrator(use_microservices: bool = False) -> IntentOrchestrator:
    """Get or create the orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = IntentOrchestrator(use_microservices=use_microservices)
    return _orchestrator_instance