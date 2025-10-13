"""
Data Query Tool - Microservice for handling data queries
"""

from typing import Dict, Any, Optional, List
import json
import logging
from sqlalchemy import text
from pydantic import Field

from .base_tool import BaseIntentTool, ToolOutput, ToolInput
from appv2.utils.app_config import get_database_engine
from appv2.chains.sql_chain import SQLGenerationChain

logger = logging.getLogger(__name__)

class DataQueryInput(ToolInput):
    """Input model for data query tool"""
    output_format: str = Field(default="table", description="Output format (table, json, chart)")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Query filters")
    
class DataQueryTool(BaseIntentTool):
    """
    Tool/Microservice for handling data queries
    Can be deployed separately or used internally
    """
    
    name: str = "data_query_tool"
    description: str = """Tool for querying databases and returning structured data.
    Use this when users ask for reports, data tables, analytics, or specific information from the database."""
    args_schema = DataQueryInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sql_chain = SQLGenerationChain()
        self.engine = None
    
    def _get_engine(self, repository: Optional[str] = None):
        """Get appropriate database engine based on repository"""
        if not self.engine:
            self.engine = get_database_engine(repository)
        return self.engine
    
    def _process_intent(self,
                       query: str,
                       context: Optional[Dict[str, Any]],
                       user_id: str,
                       repository: Optional[str],
                       session_id: Optional[str]) -> ToolOutput:
        """
        Process data query intent
        """
        try:
            logger.info(f"Processing data query for repository: {repository}")
            
            # Determine which database/collection to query based on repository
            engine = self._get_engine(repository)
            
            # Generate SQL using LangChain
            sql_result = self.sql_chain.generate_sql(
                query=query,
                repository=repository,
                context=context
            )
            
            if not sql_result.get('success'):
                return ToolOutput(
                    success=False,
                    data=None,
                    error=sql_result.get('error', 'Failed to generate SQL')
                )
            
            sql_query = sql_result['sql']
            logger.info(f"Generated SQL: {sql_query}")
            
            # Execute the query
            with engine.connect() as connection:
                result = connection.execute(text(sql_query))
                rows = []
                for row in result:
                    row_dict = {}
                    for key, value in zip(result.keys(), row):
                        # Handle different data types
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        elif isinstance(value, (int, float, str, bool, type(None))):
                            row_dict[key] = value
                        else:
                            row_dict[key] = str(value)
                    rows.append(row_dict)
            
            # Format the output based on request
            output_format = context.get('output_format', 'table') if context else 'table'
            
            if output_format == 'table':
                formatted_data = self._format_as_table(rows)
            elif output_format == 'json':
                formatted_data = rows
            elif output_format == 'chart':
                formatted_data = self._prepare_chart_data(rows, query)
            else:
                formatted_data = rows
            
            # Add metadata
            metadata = {
                'query': query,
                'sql': sql_query,
                'row_count': len(rows),
                'repository': repository,
                'format': output_format
            }
            
            return ToolOutput(
                success=True,
                data=formatted_data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error in data query processing: {str(e)}")
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _format_as_table(self, rows: List[Dict]) -> Dict[str, Any]:
        """Format rows as table structure"""
        if not rows:
            return {"headers": [], "rows": []}
        
        headers = list(rows[0].keys()) if rows else []
        table_rows = []
        for row in rows:
            table_rows.append([row.get(h) for h in headers])
        
        return {
            "headers": headers,
            "rows": table_rows,
            "total": len(rows)
        }
    
    def _prepare_chart_data(self, rows: List[Dict], query: str) -> Dict[str, Any]:
        """Prepare data for chart visualization"""
        if not rows:
            return {"type": "empty", "data": []}
        
        # Analyze data to determine best chart type
        numeric_cols = []
        categorical_cols = []
        
        if rows:
            sample_row = rows[0]
            for key, value in sample_row.items():
                if isinstance(value, (int, float)):
                    numeric_cols.append(key)
                else:
                    categorical_cols.append(key)
        
        # Determine chart type based on data
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            chart_type = "bar"
            x_axis = categorical_cols[0]
            y_axis = numeric_cols[0]
        elif len(numeric_cols) >= 2:
            chart_type = "line"
            x_axis = numeric_cols[0]
            y_axis = numeric_cols[1]
        else:
            chart_type = "table"
            return self._format_as_table(rows)
        
        # Prepare chart data
        chart_data = {
            "type": chart_type,
            "data": {
                "labels": [row.get(x_axis) for row in rows],
                "datasets": [{
                    "label": y_axis,
                    "data": [row.get(y_axis) for row in rows]
                }]
            },
            "options": {
                "title": query,
                "x_axis": x_axis,
                "y_axis": y_axis
            }
        }
        
        return chart_data

# Microservice endpoint if running standalone
if __name__ == "__main__":
    tool = DataQueryTool()
    # Run as microservice on port 8001
    tool.as_microservice(port=8001)