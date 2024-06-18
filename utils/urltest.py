import requests
import time

def fetch_url(url):
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 429:
            print("Rate limited. Retrying after delay...")
            retry_after = response.headers.get("Retry-After", 60)  # default to 60 seconds if not provided
            time.sleep(int(retry_after))
            return fetch_url(url)
        elif response.status_code == 403:
            print("Access forbidden. You might be blocked.")
        elif response.status_code == 503:
            print("Service unavailable. Retrying after delay...")
            time.sleep(60)
            return fetch_url(url)
        else:
            # Check for rate limit headers
            rate_limit_limit = response.headers.get("X-RateLimit-Limit")
            rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
            retry_after = response.headers.get("Retry-After")

            if rate_limit_limit:
                print(f"Rate Limit: {rate_limit_limit}")
            if rate_limit_remaining:
                print(f"Rate Limit Remaining: {rate_limit_remaining}")
            if retry_after:
                print(f"Retry After: {retry_after}")

            return response.content

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

url = input("Enter URL to test: ")
content = fetch_url(url)
if content:
    print("Fetched content successfully")
