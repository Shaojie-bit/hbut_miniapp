import requests
import json

# 请替换为你的云函数公网地址
BASE_URL = "https://hbut-backend-whkzceunvo.cn-hangzhou.fcapp.run"

def test_login():
    url = f"{BASE_URL}/api/login"
    
    # payload with empty token/captcha (simulate first login attempt)
    payload = {
        "username": "test_user",
        "password": "test_password",
        "token": None,
        "captcha": None
    }
    
    print(f"Sending POST request to {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"\nStatus Code: {resp.status_code}")
        print(f"Response Text: {resp.text}")
        
        try:
            print(f"Response JSON: {json.dumps(resp.json(), indent=2)}")
        except:
            print("Response is not JSON")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
