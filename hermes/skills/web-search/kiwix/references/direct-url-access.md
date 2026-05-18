# Kiwix Direct URL Access

The `read` script's article ID matching is brittle. The reliable fallback is direct URL access.

## URL Format

```
http://127.0.0.1:8081/content/{database_name}/{Article_Name}
```

Where:
- `database_name` = `wikipedia_en_all_maxi_2025-08` (the loaded ZIM file)
- `Article_Name` = underscores instead of spaces, exact Wikipedia page title

## Examples

```bash
# Fetch and extract text from an article
curl -s "http://127.0.0.1:8081/content/wikipedia_en_all_maxi_2025-08/Francis_Bacon" | python3 -c "
import sys, re
html = sys.stdin.read()
text = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(text[:8000])
"
```

## Finding the Database Name

```bash
# List available ZIM content directories
curl -s "http://127.0.0.1:8081/" | grep -oP 'href="/content/[^"]+"' | head -5
```

## Container Info

- Image: `ghcr.io/kiwix/kiwix-serve:latest`
- Port: 8081
- Network: `kiwix_default` (Docker bridge)
- Database: `wiki_en_all_maxi_2025-08`
