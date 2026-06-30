import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from pathlib import Path

# Add project root to path if needed for imports
from knowledge import rebuild_unified_index

def safe_print(msg, file=sys.stdout):
    """Safely print strings containing unicode characters on Windows terminals."""
    try:
        print(msg, file=file)
    except UnicodeEncodeError:
        enc = getattr(file, 'encoding', 'utf-8') or 'utf-8'
        safe_msg = msg.encode(enc, errors='replace').decode(enc)
        print(safe_msg, file=file)

class WebScraper:
    def __init__(self, start_url="https://mbcet.ac.in/", max_pages=150, delay=0.5):
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        # Ensure max_pages is an integer and delay is a float to avoid type errors
        self.max_pages = int(max_pages)
        self.delay = float(delay)
        self.visited = set()
        self.pages_data = []

        # File extensions to ignore
        self.ignored_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.zip', '.tar', 
            '.gz', '.mp4', '.mp3', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx'
        }

    def is_valid_url(self, url):
        parsed = urlparse(url)
        # Check domain matches
        if parsed.netloc != self.domain:
            return False

        # Check file extension
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in self.ignored_extensions):
            return False

        # Exclude anchor links and queries that might lead to duplicate pages
        if '#' in url:
            url = url.split('#')[0]

        return url not in self.visited

    def clean_html(self, soup):
        # Remove navigation, headers, footers, scripts, and styles to extract pure body context
        for element in soup(["script", "style", "nav", "header", "footer", "noscript", "iframe"]):
            element.decompose()
        return soup

    def scrape_page(self, url):
        try:
            safe_print(f"[SCRAPE] Fetching: {url} ...")
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            if response.status_code != 200:
                safe_print(f"[WARN] Failed to load {url} (Status: {response.status_code})")
                return []

            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                safe_print(f"[WARN] Skipping non-HTML page {url} (Content-Type: {content_type})")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else "Web Page"
            
            # Clean and get text
            cleaned_soup = self.clean_html(soup)
            text_content = cleaned_soup.get_text(separator=' ').strip()
            
            # Remove excessive whitespace
            text_content = ' '.join(text_content.split())

            if len(text_content) > 100:
                self.pages_data.append({
                    "url": url,
                    "title": title,
                    "text": f"Source Web Page: {title} ({url})\n\n{text_content}"
                })
                safe_print(f"[OK] Scraped: {title} ({len(text_content)} chars)")
            else:
                safe_print(f"[INFO] Skipping page {url} - too little content")

            # Extract child links
            links = []
            for anchor in cleaned_soup.find_all('a', href=True):
                href = anchor['href']
                absolute_url = urljoin(url, href)
                # Clean up anchor fragments
                absolute_url = absolute_url.split('#')[0]
                if self.is_valid_url(absolute_url):
                    links.append(absolute_url)

            return list(set(links))

        except Exception as e:
            safe_print(f"[ERROR] Failed scraping page {url}: {e}", file=sys.stderr)
            return []

    def start(self):
        queue = [self.start_url]
        self.visited.add(self.start_url)
        
        safe_print(f"[START] Crawling domain '{self.domain}' starting from '{self.start_url}' (Max limit: {self.max_pages} pages)")
        
        while queue and len(self.visited) <= self.max_pages:
            url = queue.pop(0)
            new_links = self.scrape_page(url)
            time.sleep(self.delay)
            
            for link in new_links:
                if len(self.visited) >= self.max_pages:
                    break
                if link not in self.visited:
                    self.visited.add(link)
                    queue.append(link)

        safe_print(f"[FINISH] Crawl complete. Total visited pages: {len(self.visited)}. Total scraped pages: {len(self.pages_data)}")
        return self.pages_data

if __name__ == "__main__":
    scraper = WebScraper(start_url="https://mbcet.ac.in/", max_pages=150)
    scraped_pages = scraper.start()
    
    if scraped_pages:
        safe_print("[BUILD] Merging scraped web pages and admissions prospectus into hybrid FAISS cache...")
        rebuild_unified_index(scraped_pages)
        safe_print("[SUCCESS] Web scraping & FAISS rebuilding complete!")
    else:
        safe_print("[WARN] No pages scraped. FAISS index was not rebuilt.")
