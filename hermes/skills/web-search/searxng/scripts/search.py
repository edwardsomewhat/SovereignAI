import sys
import json
import urllib.request
import urllib.parse

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 search.py 'query'")
        sys.exit(1)
    
    query = sys.argv[1]
    url = f"http://127.0.0.1:8080/search?q={urllib.parse.quote(query)}&format=json"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            results = data.get("results", [])
            if not results:
                print("No results found.")
                return
            for i, res in enumerate(results[:5]):
                print(f"{i+1}. {res.get('title')}")
                print(f"   URL: {res.get('url')}")
                print(f"   Snippet: {res.get('content')}\n")
    except Exception as e:
        print(f"Error querying SearxNG: {e}")

if __name__ == "__main__":
    main()
