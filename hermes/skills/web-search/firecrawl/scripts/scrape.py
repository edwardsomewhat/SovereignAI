import sys
import json
import urllib.request
import urllib.error

def scrape(url, mode="main", extract_prompt=None):
    """Scrape a URL via Firecrawl.

    Modes:
      main   - full markdown (default)
      summary - LLM-extracted summary, limited to ~token_budget
      extract - LLM extraction with a custom prompt
    """
    api_url = "http://127.0.0.1:3002/v1/scrape"

    payload = {
        "url": url,
        "formats": ["markdown"],
    }

    if mode == "summary":
        # Ask Firecrawl's LLM extractor to summarize
        payload["extract"] = {
            "prompt": extract_prompt or "Provide a concise summary of this page's key points in bullet form.",
            "schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"}
                }
            }
        }
    elif mode == "extract":
        if not extract_prompt:
            print("Error: --extract requires a prompt string.")
            sys.exit(1)
        payload["extract"] = {
            "prompt": extract_prompt,
        }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer empty'}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode())
            if data.get("success"):
                d = data.get("data", {})
                if mode in ("summary", "extract"):
                    # Extracted/summarized output lives under "extract"
                    extracted = d.get("extract", {})
                    if isinstance(extracted, dict):
                        for k, v in extracted.items():
                            print(f"{v}")
                    else:
                        print(str(extracted))
                else:
                    print(d.get("markdown", "No markdown content returned."))
            else:
                print(f"Firecrawl failed: {data.get('error', 'unknown error')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
    except Exception as e:
        print(f"Error querying Firecrawl: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scrape.py 'URL' [--summary|--extract 'prompt']")
        sys.exit(1)

    url = sys.argv[1]
    mode = "main"
    prompt = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--summary":
            mode = "summary"
            if i + 1 < len(sys.argv) and not sys.argv[i+1].startswith("--"):
                prompt = sys.argv[i+1]
                i += 2
            else:
                i += 1
        elif sys.argv[i] == "--extract":
            mode = "extract"
            if i + 1 < len(sys.argv) and not sys.argv[i+1].startswith("--"):
                prompt = sys.argv[i+1]
                i += 2
            else:
                print("Error: --extract requires a prompt argument.")
                sys.exit(1)
        else:
            i += 1

    scrape(url, mode=mode, extract_prompt=prompt)

if __name__ == "__main__":
    main()
