import requests
import os
import subprocess
import time
import signal

def test_security_headers():
    print("Testing security headers...")
    try:
        resp = requests.get("http://localhost:8000/api/health")
        headers = resp.headers
        
        expected = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for h in expected:
            if h in headers:
                print(f"  [OK] {h}: {headers[h]}")
            else:
                print(f"  [FAIL] {h} is missing")
                
    except Exception as e:
        print(f"  [ERROR] Could not connect to API: {e}")

def test_cors():
    print("Testing CORS...")
    try:
        # 許可されていないオリジンからのリクエスト
        headers = {"Origin": "http://evil.com"}
        resp = requests.options("http://localhost:8000/api/health", headers=headers)
        
        allow_origin = resp.headers.get("Access-Control-Allow-Origin")
        if allow_origin == "http://evil.com" or allow_origin == "*":
            print(f"  [FAIL] CORS allowed evil.com: {allow_origin}")
        else:
            print(f"  [OK] CORS restricted evil.com (Header: {allow_origin})")
            
        # 許可されているオリジン
        headers = {"Origin": "http://localhost:5173"}
        resp = requests.options("http://localhost:8000/api/health", headers=headers)
        allow_origin = resp.headers.get("Access-Control-Allow-Origin")
        if allow_origin == "http://localhost:5173":
            print(f"  [OK] CORS allowed localhost:5173")
        else:
            print(f"  [FAIL] CORS restricted localhost:5173 (Header: {allow_origin})")
            
    except Exception as e:
        print(f"  [ERROR] CORS test failed: {e}")

if __name__ == "__main__":
    # サーバーが起動している前提でテスト
    test_security_headers()
    test_cors()
