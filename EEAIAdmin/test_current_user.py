import requests
import json

# Test current-user endpoint
url = "http://localhost:5001/auth/current-user"

print("Testing /auth/current-user endpoint")
print("=" * 50)

# You need to have a valid session/cookie for this to work
# Let's try with the session from browser
headers = {
    'Cookie': 'session=.eJw9kMtuwjAQRf_Fyw4ixq_YyzZQtaKVCqJqF5VljycmJU5CHldV_73pY9Vz7j1npvMOTbKrbAG1SrOqrKGppAMUtgvIytwyLXi0NORyf9yT--TpafxIBmTczrBD6vhWu1DaQutSx40Km8TqWOlgTaqM8dp5nzqfJsl_J58Gn6xyOvP2HBolnLMKnXSRU0LYmJ8cQU7vOOEOcdyiLLJhBMjMq5XNFsoWgHJkEAJ0_dSrfftdq0u3quu2qWu_6a59Mv7y8DwfvM4Xz8vVm7vdLJ82b_f3X9vi8-Nw-CrnP91MESxFJClhnGGOB4yOOBWU4iHHPRYJRChKGR8QkUpMMKJUIoRSKQhOhwLvMQE_NmwJqKiKs29lXRRnMOzLv6L4AXqTdOg.Z0IW0g.Q5xD8MWzR01jCrJf4oXX-Gsjk_U'  # You'll need actual session cookie
}

try:
    # First, let's try without cookies
    print("\n1. Testing without session cookie:")
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 401:
        print("Expected: User not authenticated without session")
    
    # Now let's check what the actual endpoint returns
    print("\n2. Response structure (if authenticated):")
    print("The endpoint should return:")
    print(json.dumps({
        "success": True,
        "user": {
            "id": "user_id",
            "firstName": "string",
            "lastName": "string", 
            "email": "ilyashussain9@gmail.com",
            "isAllowed": True,
            "isAdmin": True  # This should be present now
        }
    }, indent=2))
    
except Exception as e:
    print(f"\nRequest failed: {e}")

print("\n" + "=" * 50)
print("To test properly:")
print("1. Open browser Developer Tools (F12)")
print("2. Go to Network tab")
print("3. Refresh the page while logged in")
print("4. Find the /auth/current-user request")
print("5. Check the Response tab to see if 'isAdmin' is present")