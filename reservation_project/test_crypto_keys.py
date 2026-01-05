import hmac
import hashlib
import time
import requests
import json
import os

# Keys provided by user
API_KEY = '042e7b74197862cffb10dbbbc28986e6'
API_SECRET = '867d12a3a29858c6ee326f3a4cd56716'

def get_signature(path, body, timestamp):
    message = str(timestamp) + path + body
    return hmac.new(
        API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_endpoint(name, method, path, payload=None):
    print(f"\n--- Testing {name} ---")
    timestamp = str(int(time.time()))
    body = json.dumps(payload) if payload else ""
    
    headers = {
        'X-MKT-APIKEY': API_KEY,
        'X-MKT-SIGNATURE': get_signature(path, body, timestamp),
        'X-MKT-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.exchange.cryptomkt.com{path}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, data=body)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Endpoint accessible.")
        elif response.status_code == 401:
            print("FAILURE: Unauthorized. Check API Key permissions.")
        else:
            print("FAILURE: Other error.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

# 1. Test Get Ticker (Public - should always work even without auth, but we test auth headers too)
test_endpoint("Public Ticker (Auth Header Check)", "GET", "/api/3/public/ticker/ETHCLP")

# 2. Test Get Wallet Balance (Requires 'Wallet' permission)
test_endpoint("Wallet Balance", "GET", "/api/3/wallet/balance")

# 3. Test Generate Address (Requires 'Wallet' write permission)
test_endpoint("Generate ETH Address", "POST", "/api/3/wallet/crypto/address", {"currency": "ETH"})

# 4. Test Get Transaction History (Requires 'History' permission)
test_endpoint("Transaction History", "GET", "/api/3/wallet/transactions")
