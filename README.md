# Web Auditor

This is a simple asynchronous web accessibility auditor written in Python. It crawls a website starting from a URL and checks each discovered page with the axe-core rules via Playwright.

## Requirements

- Python 3.8+
- The packages listed in `requirements.txt`
- Playwright browser binaries (install with `playwright install chromium`)

## Usage

```bash
pip install -r requirements.txt
playwright install chromium
python auditor.py https://example.com --max-pages 5 --concurrency 2 --output results.json
```

The script will crawl up to `--max-pages` pages from the start URL and perform accessibility audits in parallel using the specified `--concurrency`. Results are saved to the JSON file given by `--output`.
