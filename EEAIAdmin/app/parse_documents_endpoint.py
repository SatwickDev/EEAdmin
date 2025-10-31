# Add this to document_routes.py

@document_bp.route('/api/document/parse-required-documents', methods=['POST'])
def parse_required_documents():
    """Parse required documents from LC text using LLM"""
    try:
        data = request.get_json()
        documents_text_list = data.get('documents_text', [])
        
        if not documents_text_list:
            return jsonify({'success': False, 'error': 'No documents text provided'}), 400
        
        # Combine all text for LLM processing
        combined_text = "\n\n".join([
            f"Source: {item['source']}\nPriority: {item['priority']}\nText: {item['text']}"
            for item in documents_text_list
        ])
        
        # Create prompt for LLM
        prompt = f"""Analyze the following Letter of Credit required documents section and extract a structured checklist of required documents.

{combined_text}

Extract each document requirement and provide:
1. Document name (clear, standardized name)
2. Description (what the document is for)
3. Priority (Mandatory or Optional)
4. Number of copies required (if mentioned)
5. Special conditions or requirements (if any)

Return a JSON array with this structure:
[
  {{
    "name": "Commercial Invoice",
    "description": "Invoice showing goods description and value",
    "priority": "Mandatory",
    "copies": 3,
    "conditions": ["Must be signed", "Must match LC value"]
  }}
]

Be thorough and extract all documents mentioned, even if they are in paragraph form or clubbed together.
"""
        
        # Call OpenAI API
        import openai
        import os
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in Letter of Credit documentation. Parse and structure document requirements clearly and accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        import json
        parsed_data = json.loads(result_text)
        
        # Extract documents array (handle different response formats)
        documents = parsed_data.get('documents', [])
        if not documents and isinstance(parsed_data, list):
            documents = parsed_data
        
        return jsonify({
            'success': True,
            'documents': documents,
            'raw_response': result_text
        })
        
    except Exception as e:
        logger.error(f"Error parsing required documents: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
