import requests
import json

# Test document classification endpoint
url = "http://localhost:5001/api/document/classify"

# Create a simple test text file
test_content = """
LETTER OF CREDIT

LC Number: LC-2024-001
Issue Date: January 15, 2024
Expiry Date: March 15, 2024

Beneficiary: ABC Trading Company
Applicant: XYZ Importers Ltd
Amount: USD 100,000.00

This is a test letter of credit document.
"""

# Save test content to a file
with open("test_lc.txt", "w") as f:
    f.write(test_content)

# Prepare the request
files = [
    ('files', ('test_lc.txt', open('test_lc.txt', 'rb'), 'text/plain'))
]

data = {
    'query': 'Classify and check compliance',
    'checkCompliance': 'false'  # Disable compliance check for quick test
}

print("Sending test document for classification...")
print("URL:", url)

try:
    response = requests.post(url, files=files, data=data)
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("SUCCESS! Classification completed")
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
finally:
    # Clean up
    import os
    if os.path.exists("test_lc.txt"):
        os.remove("test_lc.txt")