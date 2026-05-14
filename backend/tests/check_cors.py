import requests
import sys

def check_cors(base_url, origin):
    print(f"Testing CORS for: {base_url}")
    print(f"Simulating Origin: {origin}")
    
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    
    try:
        # 1. Preflight (OPTIONS) check
        print("\n--- 1. Preflight (OPTIONS) Request ---")
        response_options = requests.options(f"{base_url}/api/health", headers=headers)
        
        print(f"Status: {response_options.status_code}")
        allow_origin = response_options.headers.get("Access-Control-Allow-Origin")
        print(f"Access-Control-Allow-Origin: {allow_origin}")
        
        if allow_origin == origin or allow_origin == "*":
            print("✅ Preflight OK: Origin is allowed.")
        else:
            print("❌ Preflight Failed: Origin is NOT allowed.")
            
        # 2. Actual (GET) check
        print("\n--- 2. Actual (GET) Request ---")
        response_get = requests.get(f"{base_url}/api/health", headers={"Origin": origin})
        
        print(f"Status: {response_get.status_code}")
        allow_origin_get = response_get.headers.get("Access-Control-Allow-Origin")
        print(f"Access-Control-Allow-Origin: {allow_origin_get}")
        
        if allow_origin_get == origin or allow_origin_get == "*":
            print("✅ GET Request OK: CORS headers present.")
        else:
            print("❌ GET Request Failed: CORS headers missing or mismatch.")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    # テストしたいオリジン（VercelのプレビューURLなど）
    test_origin = sys.argv[2] if len(sys.argv) > 2 else "https://stock-trading-tool-test.vercel.app"
    
    check_cors(url, test_origin)
