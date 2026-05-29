"""
Simple test to verify DataGod API v2 is working
"""

import json
from datetime import datetime

import requests


# Test the API
def test_api():
    print("🧪 Testing DataGod API v2...")

    # Test root endpoint
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("✅ Root endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")

    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

    # Test authentication
    try:
        auth_data = {"username": "admin", "password": "admin123"}
        response = requests.post("http://localhost:8000/api/v2/token", data=auth_data)
        if response.status_code == 200:
            print("✅ Authentication working")
            token_data = response.json()
            print(f"   Access token: {token_data['access_token'][:20]}...")
            print(f"   Expires in: {token_data['expires_in']} seconds")

            # Test protected endpoint with token
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            response = requests.get(
                "http://localhost:8000/api/v2/users/me", headers=headers
            )
            if response.status_code == 200:
                print("✅ Protected endpoint working")
                print(f"   User: {response.json()['username']}")
            else:
                print(f"❌ Protected endpoint failed: {response.status_code}")
        else:
            print(f"❌ Authentication failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Authentication error: {e}")

    print("🎉 API testing completed!")


if __name__ == "__main__":
    test_api()
