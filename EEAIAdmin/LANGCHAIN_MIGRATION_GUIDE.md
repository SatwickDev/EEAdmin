# EEAI LangChain & LangGraph Migration Guide

## Overview
This document describes the migration of the EEAI backend from direct OpenAI API calls to LangChain and LangGraph frameworks, with support for both internal tools and external microservices via MCP (Model Context Protocol).

## Architecture Design

### 1. **Microservices Architecture**
Each intent is implemented as a separate tool/microservice that can run:
- **Internally**: As LangChain tools within the application
- **Externally**: As standalone microservices accessible via HTTP
- **Via MCP**: Through the Model Context Protocol for AI assistants

### 2. **Intent-Based Tools**

#### Available Tools/Microservices:
1. **DataQueryTool** (Port 8001)
   - Handles database queries
   - Generates SQL using LangChain
   - Returns structured data

2. **TransactionTool** (Port 8002)
   - Processes financial transactions
   - Supports LC, Bank Guarantees, Payments, Transfers
   - Full transaction lifecycle management

3. **ComplianceTool** (Port 8003)
   - Checks regulatory compliance
   - Validates against UCP600, SWIFT rules
   - Document compliance verification

4. **DocumentAnalysisTool** (Port 8004)
   - OCR and document extraction
   - Classification and analysis
   - Structured data extraction

5. **TradeFinanceTool** (Port 8005)
   - Trade finance specific operations
   - LC management
   - Export/Import documentation

6. **TreasuryTool** (Port 8006)
   - FX operations
   - Investment management
   - Risk analytics

7. **CashManagementTool** (Port 8007)
   - Cash flow management
   - Liquidity analysis
   - Payment processing

8. **RAGTool** (Port 8008)
   - Vector search using ChromaDB
   - Knowledge base queries
   - Context-aware responses

### 3. **LangGraph Orchestration**

The `IntentOrchestrator` uses LangGraph to create a workflow:

```
User Query → Intent Classification → Tool Routing → Tool Execution → Response Synthesis
```

#### Graph Nodes:
- **classify_intent**: Determines user intent using LLM
- **route_to_tools**: Maps intent to appropriate tools
- **execute_tools**: Runs selected tools (parallel when possible)
- **synthesize_response**: Combines tool outputs into coherent response
- **handle_error**: Graceful error handling

### 4. **MCP Integration**

The MCP server exposes all tools through the Model Context Protocol:

```python
# Start MCP server (stdio mode for Claude)
python -m appv2.mcp_server --mode stdio

# Start MCP server (WebSocket for web clients)
python -m appv2.mcp_server --mode websocket --port 8765
```

## Migration Path

### Phase 1: Setup (Complete)
✅ Created appv2 directory structure
✅ Implemented base tool architecture
✅ Created LangChain wrappers for Azure OpenAI
✅ Designed LangGraph orchestration

### Phase 2: Tool Implementation (In Progress)
✅ DataQueryTool - Database queries
✅ TransactionTool - Financial transactions
✅ MCP Server - Protocol implementation
⏳ ComplianceTool - Compliance checking
⏳ DocumentAnalysisTool - Document processing
⏳ TradeFinanceTool - Trade operations
⏳ TreasuryTool - Treasury management
⏳ CashManagementTool - Cash operations
⏳ RAGTool - Vector search

### Phase 3: Integration
⏳ Update routes.py to use orchestrator
⏳ Maintain backward compatibility
⏳ Add async support throughout
⏳ Implement caching layer

### Phase 4: Testing
⏳ Unit tests for each tool
⏳ Integration tests for orchestrator
⏳ End-to-end API tests
⏳ Performance benchmarking

## Running the System

### 1. **Standalone Mode** (All tools internal)
```python
from appv2 import create_app

app = create_app()
app.run(port=5001)
```

### 2. **Microservices Mode** (Tools as separate services)

Start each tool as a microservice:
```bash
# Terminal 1: Data Query Service
python -m appv2.tools.data_query_tool

# Terminal 2: Transaction Service
python -m appv2.tools.transaction_tool

# Terminal 3: Main Application
python run_appv2.py --use-microservices
```

### 3. **Hybrid Mode** (Mix of internal and external)
Configure in `mcp_config.json`:
```json
{
  "orchestration": {
    "mode": "hybrid",
    "options": {
      "use_microservices": false,
      "fallback_to_local": true
    }
  }
}
```

## API Compatibility

All existing endpoints remain unchanged:
- `/chat` - Chat interface
- `/api/repository/*` - Repository operations
- `/api/compliance/*` - Compliance checks
- `/document_classification` - Document processing
- `/trade_finance_*` - Trade finance forms

The migration is transparent to frontend applications.

## Configuration

### Environment Variables
```env
# LangChain Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-api-key
LANGCHAIN_PROJECT=eeai-production

# Tool Configuration
USE_MICROSERVICES=false
TOOL_TIMEOUT=30
ENABLE_MCP=true

# Existing variables remain unchanged
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
```

### Tool Microservice Deployment

Each tool can be containerized:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_v2.txt .
RUN pip install -r requirements_v2.txt

COPY appv2/tools/data_query_tool.py .
CMD ["python", "data_query_tool.py"]
```

Docker Compose for all services:
```yaml
version: '3.8'

services:
  data-query:
    build: 
      context: .
      dockerfile: Dockerfile.data-query
    ports:
      - "8001:8001"
    environment:
      - DB_CONNECTION=${DB_CONNECTION}
  
  transaction:
    build:
      context: .
      dockerfile: Dockerfile.transaction
    ports:
      - "8002:8002"
    environment:
      - DB_CONNECTION=${DB_CONNECTION}
  
  # ... other services
```

## Benefits of the New Architecture

### 1. **Modularity**
- Each intent is a separate, deployable unit
- Easy to maintain and update individual components
- Clear separation of concerns

### 2. **Scalability**
- Tools can be scaled independently
- Horizontal scaling of high-demand services
- Load balancing across tool instances

### 3. **Flexibility**
- Run internally for simplicity
- Deploy as microservices for scale
- Mix and match based on requirements

### 4. **Observability**
- LangChain tracing for debugging
- Individual tool metrics
- Centralized logging

### 5. **Extensibility**
- Easy to add new tools
- MCP support for AI assistants
- Plugin architecture for custom tools

### 6. **Performance**
- Parallel tool execution
- Caching at multiple levels
- Async support throughout

## Monitoring and Debugging

### LangChain Tracing
```python
from langchain.callbacks import LangChainTracer

tracer = LangChainTracer(project_name="eeai-production")
orchestrator.process(query, callbacks=[tracer])
```

### Tool Health Checks
```bash
# Check all tool health endpoints
for port in {8001..8008}; do
  curl http://localhost:$port/health
done
```

### MCP Debugging
```bash
# Test MCP server
echo '{"method":"tools/list","id":1}' | python -m appv2.mcp_server --mode stdio
```

## Next Steps

1. Complete remaining tool implementations
2. Add comprehensive test suite
3. Implement caching layer with Redis
4. Add rate limiting and authentication
5. Deploy to production with monitoring
6. Create Kubernetes manifests for cloud deployment

## Support

For questions or issues with the migration:
1. Check the logs in `appv2/logs/`
2. Review LangChain traces in LangSmith
3. Test individual tools before orchestration
4. Use MCP test client for debugging

The migration maintains 100% backward compatibility while providing a modern, scalable architecture for future growth.