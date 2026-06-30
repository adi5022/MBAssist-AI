import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

def safe_print(msg, file=sys.stdout):
    try:
        print(msg, file=file)
    except Exception:
        pass

class SyllabusScraper:
    def __init__(self, base_url="https://mbcet.ac.in/", save_dir="data/syllabus"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        # Resolve save directory relative to workspace root (assuming running in project root)
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.visited = set()
        self.downloaded_count = 0
        
        # User-Agent header to avoid request blockings
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def start(self):
        safe_print(f"[START] Crawling department pages to find syllabus PDFs on {self.base_url}...")
        
        # Discover department links from base page and common departments menu
        dept_urls = self.discover_department_urls()
        
        safe_print(f"[INFO] Discovered {len(dept_urls)} departments. Checking syllabus pages...")
        
        for dept_url in dept_urls:
            syllabus_url = dept_url.rstrip('/') + '/syllabus/'
            self.scrape_syllabus_page(syllabus_url)
            
        safe_print(f"[FINISH] Crawl complete. Downloaded {self.downloaded_count} syllabus PDF files into {self.save_dir.absolute()}")

    def discover_department_urls(self):
        urls = set()
        # Default list of common departments to try directly for quick access
        default_depts = [
            "computer-science-engineering",
            "mechanical-engineering",
            "electronics-communication-engineering",
            "civil-engineering",
            "electrical-electronics-engineering",
            "science-humanities"
        ]
        for dept in default_depts:
            urls.add(urljoin(self.base_url, f"/departments/{dept}/"))
            
        # Dynamically discover others from the home page
        try:
            resp = requests.get(self.base_url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    absolute_url = urljoin(self.base_url, href)
                    parsed = urlparse(absolute_url)
                    if parsed.netloc == self.domain and "/departments/" in parsed.path:
                        # Normalize to main department URL
                        parts = parsed.path.strip('/').split('/')
                        if len(parts) >= 2 and parts[0] == "departments":
                            dept_name = parts[1]
                            urls.add(urljoin(self.base_url, f"/departments/{dept_name}/"))
        except Exception as e:
            safe_print(f"[WARN] Error scanning home page for departments: {e}")
            
        return list(urls)

    def scrape_syllabus_page(self, url):
        if url in self.visited:
            return
        self.visited.add(url)
        
        safe_print(f"[SCRAPE] Checking syllabus page: {url}")
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                # Try without trailing slash
                alt_url = url.rstrip('/')
                resp = requests.get(alt_url, headers=self.headers, timeout=10)
                if resp.status_code != 200:
                    safe_print(f"[WARN] Syllabus page not found: {url} (Code: {resp.status_code})")
                    return
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            pdf_links = []
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.lower().endswith('.pdf'):
                    absolute_pdf_url = urljoin(url, href)
                    pdf_links.append((absolute_pdf_url, a.get_text().strip()))
                    
            if pdf_links:
                safe_print(f"[OK] Found {len(pdf_links)} PDF files on {url}")
                for pdf_url, link_text in pdf_links:
                    self.download_pdf(pdf_url, link_text)
            else:
                safe_print(f"[INFO] No PDF files found on {url}")
                
        except Exception as e:
            safe_print(f"[ERROR] Failed scraping syllabus page {url}: {e}", file=sys.stderr)

    def download_pdf(self, url, link_text):
        try:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename.endswith('.pdf'):
                filename += ".pdf"
                
            # Clean up filename or prepend department context
            # Get department name from URL path
            parts = parsed.path.strip('/').split('/')
            dept_prefix = "syllabus"
            if "departments" in parts:
                idx = parts.index("departments")
                if idx + 1 < len(parts):
                    dept_prefix = parts[idx + 1]
                    
            # Combine to prevent collisions (e.g. computer-science-engineering_S5.pdf)
            full_filename = f"{dept_prefix}_{filename}"
            save_path = self.save_dir / full_filename
            
            if save_path.exists():
                # Already downloaded, skip
                return
            
            safe_print(f"   [DOWNLOAD] Fetching PDF: {filename} ({link_text or 'No description'})")
            pdf_resp = requests.get(url, headers=self.headers, timeout=30)
            if pdf_resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(pdf_resp.content)
                self.downloaded_count += 1
                time.sleep(0.3) # politeness delay
            else:
                safe_print(f"   [WARN] Failed downloading PDF: {url} (Code: {pdf_resp.status_code})")
                
        except Exception as e:
            safe_print(f"   [ERROR] Failed to download PDF {url}: {e}", file=sys.stderr)

if __name__ == "__main__":
    scraper = SyllabusScraper()
    scraper.start()
