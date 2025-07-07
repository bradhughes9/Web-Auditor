import asyncio
import json
from collections import deque
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from axe_playwright_python.async_playwright import Axe


async def fetch_html(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return None
            ctype = response.headers.get('content-type', '')
            if 'text/html' not in ctype:
                return None
            return await response.text()
    except Exception:
        return None


def should_skip(url: str) -> bool:
    lower = url.lower()
    skip_ext = ('.pdf', '.doc', '.docx', '.ppt', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.zip')
    return lower.endswith(skip_ext)


async def collect_links(base_url: str, html: str):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        if urlparse(href).scheme in {'http', 'https'} and not should_skip(href):
            links.add(href.split('#')[0])
    return links


async def crawl(start_url: str, max_pages: int = 20):
    visited = set()
    queue = deque([start_url])
    pages = []
    async with aiohttp.ClientSession() as session:
        while queue and len(visited) < max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            html = await fetch_html(session, url)
            if html is None:
                visited.add(url)
                continue
            visited.add(url)
            pages.append(url)
            for link in await collect_links(url, html):
                if link not in visited:
                    queue.append(link)
    return pages


async def audit_page(axe: Axe, page, url: str):
    await page.goto(url, wait_until='networkidle')
    results = await axe.run(page)
    return {'url': url, 'violations': results['violations']}


async def audit_pages(urls, concurrency: int = 2):
    axe = Axe()
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        sem = asyncio.Semaphore(concurrency)

        async def worker(url: str):
            async with sem:
                page = await browser.new_page()
                res = await audit_page(axe, page, url)
                await page.close()
                results.append(res)

        tasks = [asyncio.create_task(worker(url)) for url in urls]
        await asyncio.gather(*tasks)
        await browser.close()
    return results


async def main(start_url: str, max_pages: int, concurrency: int, output: str):
    pages = await crawl(start_url, max_pages)
    print(f"Crawled {len(pages)} pages")
    results = await audit_pages(pages, concurrency)
    with open(output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Async web accessibility auditor')
    parser.add_argument('url', help='Start URL to crawl')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum pages to crawl')
    parser.add_argument('--concurrency', type=int, default=2, help='Number of parallel audits')
    parser.add_argument('--output', default='results.json', help='JSON output file')

    args = parser.parse_args()
    asyncio.run(main(args.url, args.max_pages, args.concurrency, args.output))
