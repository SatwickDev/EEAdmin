import requests
import json

# Test login endpoint to verify isAdmin flag
url = "http://localhost:5001/auth/login"

# Test with admin email
data = {
    "email": "ilyashussain9@gmail.com",
    "password": "Test@123"  # You'll need to use the correct password
}

print("Testing login for admin user: ilyashussain9@gmail.com")
print("=" * 50)

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nLogin Response:")
        print(json.dumps(result, indent=2))
        
        if 'user' in result:
            user = result['user']
            print("\n✓ User Data:")
            print(f"  - Email: {user.get('email')}")
            print(f"  - isAllowed: {user.get('isAllowed')}")
            print(f"  - isAdmin: {user.get('isAdmin')}")
            
            if not user.get('isAdmin'):
                print("\n⚠️ WARNING: isAdmin flag is not True!")
                print("This user should be an admin but isAdmin is:", user.get('isAdmin'))
        else:
            print("\n⚠️ No user data in response")
    else:
        print(f"\nError Response: {response.text}")
        
except Exception as e:
    print(f"\nRequest failed: {e}")

print("\n" + "=" * 50)
print("ALLOWED_EMAILS list check:")
print("If isAdmin is missing or False, check that:")
print("1. The email is in ALLOWED_EMAILS list in routes.py")
print("2. The Flask app has been restarted after changes")
print("3. Clear browser cache and localStorage")