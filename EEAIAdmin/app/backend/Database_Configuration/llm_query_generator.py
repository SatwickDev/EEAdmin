"""
LLM Query Generator Helpers

Provides helper functions for generating SQL queries using LLM providers (OpenAI, Anthropic, Azure OpenAI).
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


def generate_sql_with_openai(user_query: str, schema_context: str, api_key: str) -> str:
    """
    Generate SQL using OpenAI GPT-4
    
    Args:
        user_query: Natural language query from user
        schema_context: Database schema information
        api_key: OpenAI API key
        
    Returns:
        Generated SQL query string
    """
    try:
        import openai
        openai.api_key = api_key

        system_prompt = """You are a SQL expert. Generate PostgreSQL queries based on user requests.

Rules:
1. Generate ONLY the SQL query, no explanations or markdown
2. Use proper PostgreSQL syntax
3. Use parameterized queries with $1, $2, etc. for values
4. Include appropriate WHERE, JOIN, ORDER BY, and LIMIT clauses
5. Use table aliases (t0, t1, t2, etc.)
6. Return only SELECT queries (no INSERT, UPDATE, DELETE)

Available Schema:
{schema}
"""

        user_prompt = f"Generate a SQL query for: {user_query}"

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt.format(schema=schema_context)},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            seed=12345,
            top_p=0.1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        sql_query = response.choices[0].message.content.strip()

        # Clean up markdown code blocks if present
        if sql_query.startswith('```sql'):
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        elif sql_query.startswith('```'):
            sql_query = sql_query.replace('```', '').strip()

        return sql_query

    except ImportError:
        raise Exception("OpenAI library not installed. Run: pip install openai")
    except Exception as e:
        raise Exception(f"OpenAI error: {str(e)}")


def generate_sql_with_anthropic(user_query: str, schema_context: str, api_key: str) -> str:
    """
    Generate SQL using Anthropic Claude
    
    Args:
        user_query: Natural language query from user
        schema_context: Database schema information
        api_key: Anthropic API key
        
    Returns:
        Generated SQL query string
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """You are a SQL expert. Generate PostgreSQL queries based on user requests.

Rules:
1. Generate ONLY the SQL query, no explanations or markdown
2. Use proper PostgreSQL syntax
3. Use parameterized queries with $1, $2, etc. for values
4. Include appropriate WHERE, JOIN, ORDER BY, and LIMIT clauses
5. Use table aliases (t0, t1, t2, etc.)
6. Return only SELECT queries (no INSERT, UPDATE, DELETE)

Available Schema:
{schema}
"""

        user_prompt = f"Generate a SQL query for: {user_query}"

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.1,
            system=system_prompt.format(schema=schema_context),
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        sql_query = message.content[0].text.strip()

        # Clean up markdown code blocks if present
        if sql_query.startswith('```sql'):
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        elif sql_query.startswith('```'):
            sql_query = sql_query.replace('```', '').strip()

        return sql_query

    except ImportError:
        raise Exception("Anthropic library not installed. Run: pip install anthropic")
    except Exception as e:
        raise Exception(f"Anthropic error: {str(e)}")


def generate_query_recipe_with_ai(
    prompt: str,
    module: str,
    module_name: str,
    tables: list,
    openai_client,
    deployment_name: str = 'gpt-4o-mini'
) -> dict:
    """
    Generate a query recipe using Azure OpenAI
    
    Args:
        prompt: Natural language description of the query
        module: Module ID
        module_name: Module display name
        tables: List of table definitions
        openai_client: Configured OpenAI client
        deployment_name: Azure OpenAI deployment name
        
    Returns:
        Dictionary with 'recipe' and 'explanation' keys
    """
    # Build schema context for LLM
    schema_context = f"Module: {module_name}\n\nAvailable Tables:\n"
    for table in tables:
        schema_context += f"\n{table['name']} (ID: {table['id']}):\n"
        schema_context += "Columns:\n"
        for col in table.get('columns', []):
            schema_context += f"  - {col.get('name', '')} ({col.get('type', 'text')})\n"

    system_prompt = """You are an advanced SQL query recipe generator. Given a natural language query description and database schema, 
generate a structured, optimized query recipe in JSON format.

**Recipe Structure:**

1. **name**: Short descriptive name (e.g., "Expired Documentary Collections")
2. **description**: Clear description of query purpose
3. **base**: Primary table ID from schema
4. **select**: Column references ["table_id.column_name"] or aggregates ["SUM(table.amount) as total"]
5. **joins**: Auto-detect relationships from query
   Format: [{"type": "INNER|LEFT", "alias": "short_name", "table": "table_id", "from": "base.fk_column", "to": "other.pk_column"}]
6. **where**: Default filter conditions (always applied)
   Format: [{"field": "table.column", "op": "eq|gt|lt|like|between|in", "value": "value"}]
7. **allowed_filters**: Dynamic filters users can apply
   Format: [{"field": "table.column", "type": "text|number|date", "ops": ["eq", "gt", "lt"], "required": false}]
8. **default_limit**: Result limit (10-1000)

**Smart Detection Rules:**

**JOINs** - Detect from keywords:
- "with customer" → LEFT JOIN customers ON base.customer_id = customers.id
- "including bank" → LEFT JOIN banks ON base.bank_id = banks.id  
- "and products" → LEFT JOIN products ON base.product_id = products.id

**WHERE conditions** - Auto-generate from status words:
- "expired" → {"field": "table.expiry_date", "op": "lt", "value": "NOW()"}
- "active" → {"field": "table.status", "op": "eq", "value": "active"}
- "pending" → {"field": "table.status", "op": "in", "value": ["pending", "submitted"]}
- "overdue" → {"field": "table.due_date", "op": "lt", "value": "NOW()"}
- "high value" → {"field": "table.amount", "op": "gt", "value": 100000}

**Operators by type:**
- text: ["eq", "like", "in", "not_eq"]
- number: ["eq", "gt", "lt", "gte", "lte", "between"]
- date: ["eq", "gt", "lt", "between"]

**Response (JSON only, no markdown):**
{
  "recipe": {
    "name": "Query Name",
    "description": "What it does",
    "base": "table_id",
    "select": ["table.col1", "table.col2"],
    "joins": [{"type": "LEFT", "alias": "alias", "table": "other_table", "from": "base.fk", "to": "other.id"}],
    "where": [{"field": "table.status", "op": "eq", "value": "active"}],
    "allowed_filters": [{"field": "table.date", "type": "date", "ops": ["gt", "lt"], "required": false}],
    "default_limit": 100
  },
  "explanation": "Detailed explanation of query logic"
}"""

    user_prompt = f"""Schema Context:
{schema_context}

User Query Request:
{prompt}

Generate a query recipe for this request."""

    response = openai_client.ChatCompletion.create(
        engine=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2000,
        seed=12345,
        top_p=0.1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={"type": "json_object"}
    )

    llm_output = response["choices"][0]["message"]["content"].strip()

    # Try to extract JSON if wrapped in markdown code blocks
    if '```json' in llm_output:
        llm_output = llm_output.split('```json')[1].split('```')[0].strip()
    elif '```' in llm_output:
        llm_output = llm_output.split('```')[1].split('```')[0].strip()

    result = json.loads(llm_output)
    
    logger.info(f"AI generated query recipe for module {module}: {result.get('recipe', {}).get('name', 'Unknown')}")
    
    return result
