import os
import logging
from dotenv import load_dotenv
import openai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Azure OpenAI
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_version = "2024-10-01-preview"
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

print("=== Azure OpenAI Configuration Test ===")
print(f"API Type: {openai.api_type}")
print(f"API Base: {openai.api_base}")
print(f"API Version: {openai.api_version}")
print(f"API Key: {'Set' if openai.api_key else 'Not Set'} (length: {len(openai.api_key) if openai.api_key else 0})")
print(f"Deployment Name: {deployment_name}")
print()

# Test simple completion
try:
    print("Testing Azure OpenAI connection...")
    response = openai.ChatCompletion.create(
        engine=deployment_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, Azure OpenAI is working!' if you can read this."}
        ],
        temperature=0,
        max_tokens=50
    )
    
    print("SUCCESS! Response:")
    print(response["choices"][0]["message"]["content"])
    
except openai.error.AuthenticationError as e:
    print(f"AUTHENTICATION ERROR: {e}")
    print("\nPossible issues:")
    print("1. API key is invalid or expired")
    print("2. API endpoint URL is incorrect")
    print("3. Check if the key matches the endpoint region")
    
except openai.error.InvalidRequestError as e:
    print(f"INVALID REQUEST ERROR: {e}")
    print("\nPossible issues:")
    print("1. Deployment name doesn't exist")
    print("2. API version is incompatible")
    print("3. Model is not deployed in your Azure resource")
    
except Exception as e:
    print(f"UNEXPECTED ERROR: {e}")
    print(f"Error Type: {type(e).__name__}")