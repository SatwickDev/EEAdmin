import json
import os
import openai
import numpy as np
from flask import Flask, request, jsonify
from sklearn.metrics.pairwise import cosine_similarity
import threading
import requests

# === Flask setup ===
app = Flask(__name__)

# === Azure OpenAI setup ===
openai.api_type = "azure"
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2023-05-15"

EMBEDDING_DEPLOYMENT_NAME = "text-embedding-3-large"
GPT_DEPLOYMENT = "gpt-4-0"

# === Load clause library ===
def load_clause_library(path="C:\\Users\\vijayan\\PycharmProjects\\PythonProject_Copy\\app\\utils\\prompts\\clause_library.json"):
    with open(path, "r") as f:
        return json.load(f)

# === Load custom rules ===
def load_custom_rules(path="C:\\Users\\vijayan\\PycharmProjects\\PythonProject_Copy\\app\\utils\\prompts\\urdg758_custom_rules.json"):
    with open(path, "r") as f:
        return json.load(f)

# === Embedding ===
def get_embedding(text):
    response = openai.Embedding.create(input=[text], engine=EMBEDDING_DEPLOYMENT_NAME)
    return response["data"][0]["embedding"]

# === Clause Classification ===
def classify_clauses_with_embeddings(guarantee_text, threshold=0.75):
    clauses = [line.strip() for line in guarantee_text.split('\n') if line.strip()]
    clause_library = load_clause_library()

    category_embeddings = {
        entry["category"]: get_embedding(entry["description"])
        for entry in clause_library
    }

    classified = []
    for clause in clauses:
        clause_embedding = get_embedding(clause)
        similarities = {
            category: cosine_similarity([clause_embedding], [embedding])[0][0]
            for category, embedding in category_embeddings.items()
        }

        best_match = max(similarities.items(), key=lambda x: x[1])
        category, score = best_match

        classified.append({
            "clause": clause,
            "category": category if score >= threshold else "Unclassified",
            "similarity": round(score, 3)
        })

    return classified

# === Compliance Analysis ===
def analyze_compliance(fields, original_text, rule_label="URDG 758"):
    try:
        rule_path = r"C:\\Users\\vijayan\\PycharmProjects\\PythonProject_Copy\\app\\utils\\prompts\\urdg758_custom_rules.json"
        custom_rules = load_custom_rules(rule_path)
        field_entries = [{"field": k, "value": v.get("value", "")} for k, v in fields.items()]

        prompt = f"""
You are a trade finance compliance expert. Evaluate the following guarantee fields and clauses for compliance under **{rule_label}** using the custom rules.

### Fields:
{json.dumps(field_entries, indent=2)}

### Custom Rules:
{json.dumps(custom_rules, indent=2)}

### Guarantee Text:
\"\"\"
{original_text}
\"\"\"

1. Evaluate each field using custom rules. For each field:
```json
[
  {{
    "field": "<field key>",
    "value": "<field value>",
    "{rule_label.lower().replace(' ', '')}": {{
      "compliance": true | false,
      "severity": "high" | "medium" | "low",
      "reason": "Reference any violated custom rule."
    }}
  }}
]
```

2. Identify which custom rules were triggered or missed:

Replace with double braces for JSON code example:
{
  "applied_rules": [
    { "rule_id": "...", "used": true, "reason": "..." }
  ],
  "unused_rules": [
    { "rule_id": "...", "used": false, "reason": "..." }
  ]
}
```
"""

        response = openai.ChatCompletion.create(
            engine=GPT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        reply = response.choices[0].message["content"]
        parts = reply.strip().split('\n', 1)
        compliance_part = json.loads(parts[0])
        rule_summary = json.loads(parts[1])

        compliance_result = {
            item["field"]: {
                "field": item["field"],
                "value": item["value"],
                **item[rule_label.lower().replace(' ', '')]
            }
            for item in compliance_part
        }

        clause_classification = classify_clauses_with_embeddings(original_text)

        return {
            "compliance_framework": rule_label,
            "compliance_result": compliance_result,
            "clause_classification": clause_classification,
            "rule_application_summary": rule_summary
        }

    except Exception as e:
        return {
            "error": str(e),
            "compliance_result": {k: {"error": str(e)} for k in fields},
            "clause_classification": [],
            "rule_application_summary": {"applied_rules": [], "unused_rules": []}
        }

# === Flask API Endpoint ===
@app.route("/AICheck", methods=["POST"])
def getAICheck():
    try:
        data = request.get_json()
        fields = data.get("fields", {})
        text = data.get("original_text", "")
        result = analyze_compliance(fields, text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# === Test client (without exposing port) ===
def run_test():
    test_data = {
        "original_text": "This guarantee is governed by URDG758. It shall expire on 31 December 2025. Any demand must be submitted in writing. English law shall apply. The guarantee is not transferable.",
        "fields": {
            "expiry_date": {"value": "31 December 2025"},
            "jurisdiction": {"value": "English law"},
            "transferability": {"value": "This guarantee is transferable."}
        }
    }
    with app.test_client() as client:
        response = client.post("/AICheck", json=test_data)
        print("Status Code:", response.status_code)
        print("Response:", response.get_json())

# Run test when script is run directly
if __name__ == "__main__":
    print("Running internal test...")
    run_test()
