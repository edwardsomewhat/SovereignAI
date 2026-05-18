import sys
import json
import urllib.request
import urllib.parse
import re

def search(query):
    # Kiwix serve search endpoint (HTML)
    url = f"http://127.0.0.1:8081/search?pattern={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # Simple regex to extract search results from Kiwix HTML
            results = re.findall(r'<a href="([^"]+)">([^<]+)</a>', html)
            
            articles = []
            for href, title in results:
                if "/A/" in href or "/I/" in href or "wikipedia" in href:
                    if "search?pattern=" not in href and "kiwix" not in title.lower():
                        articles.append((title, href))
            
            if not articles:
                print("No results found in offline Wikipedia.")
                return
                
            print(f"Top results for '{query}':")
            seen = set()
            count = 0
            for title, href in articles:
                if title not in seen:
                    seen.add(title)
                    article_id = href.split('/')[-1].replace('.html', '')
                    print(f"- {title} (ID: {article_id})")
                    count += 1
                    if count >= 5:
                        break
    except Exception as e:
        print(f"Error querying Kiwix search: {e}")

def read(article_id):
    url = f"http://127.0.0.1:8081/search?pattern={urllib.parse.quote(article_id)}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            results = re.findall(r'<a href="([^"]+)">([^<]+)</a>', html)
            
            target_href = None
            for href, title in results:
                if article_id.lower() in href.lower() or article_id.lower() in title.lower():
                    target_href = href
                    break
            
            if not target_href:
                print(f"Could not find exact article for ID: {article_id}")
                return
                
            article_url = f"http://127.0.0.1:8081{target_href}"
            article_req = urllib.request.Request(article_url)
            with urllib.request.urlopen(article_req) as article_res:
                article_html = article_res.read().decode('utf-8')
                
                text = re.sub(r'<style.*?</style>', '', article_html, flags=re.DOTALL)
                text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                print(f"Content of {article_id}:\n")
                # Truncate at 8000 chars instead of 5000 for more detail
                print(text[:8000] + "\n...[truncated]")
                
    except Exception as e:
        print(f"Error reading article: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 kiwix.py [search|read] 'query'")
        sys.exit(1)
        
    action = sys.argv[1]
    query = sys.argv[2]
    
    if action == "search":
        search(query)
    elif action == "read":
        read(query)
    else:
        print("Unknown action. Use 'search' or 'read'.")
