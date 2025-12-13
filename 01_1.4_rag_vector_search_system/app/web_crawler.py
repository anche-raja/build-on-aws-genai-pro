"""
Phase 4: Web Crawler for Public Documentation
Crawls and extracts content from web pages
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Set, Optional
import logging
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebCrawler:
    """Crawls websites and extracts documentation"""
    
    def __init__(
        self,
        delay: float = 1.0,
        user_agent: str = "AWS-RAG-Bot/1.0",
        max_depth: int = 3
    ):
        """
        Initialize web crawler
        
        Args:
            delay: Delay between requests (politeness)
            user_agent: User agent string
            max_depth: Maximum crawl depth
        """
        self.delay = delay
        self.user_agent = user_agent
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """
        Check if URL is valid and within the same domain
        
        Args:
            url: URL to check
            base_domain: Base domain to restrict crawling
            
        Returns:
            True if URL is valid
        """
        parsed = urlparse(url)
        
        # Check if same domain
        if parsed.netloc != base_domain:
            return False
        
        # Skip non-HTML files
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.tar', '.gz']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
        
        return True
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract all links from a page
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        links = []
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            absolute_url = urljoin(base_url, href)
            
            # Remove fragments
            absolute_url = absolute_url.split('#')[0]
            
            links.append(absolute_url)
        
        return links
    
    def extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Extract content and metadata from a page
        
        Args:
            soup: BeautifulSoup object
            url: Page URL
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        # Extract title
        title = soup.find('title')
        title_text = title.string if title else urlparse(url).path
        
        # Extract main content (try common content containers)
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.documentation',
            '#content',
            'body'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.find('body')
        
        # Remove unwanted elements
        if main_content:
            for element in main_content.select('script, style, nav, header, footer, .nav, .sidebar'):
                element.decompose()
        
        # Extract text
        text = main_content.get_text(separator='\n', strip=True) if main_content else ''
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n\n'.join(lines)
        
        # Extract metadata
        metadata = {
            'url': url,
            'title': title_text.strip() if isinstance(title_text, str) else str(title_text),
            'crawled_at': datetime.utcnow().isoformat()
        }
        
        # Try to extract author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            metadata['author'] = author_meta.get('content', 'Unknown')
        
        # Try to extract description
        description_meta = soup.find('meta', attrs={'name': 'description'})
        if description_meta:
            metadata['description'] = description_meta.get('content', '')
        
        # Try to extract publish date
        date_meta = soup.find('meta', attrs={'property': 'article:published_time'})
        if date_meta:
            metadata['published_date'] = date_meta.get('content', '')
        
        # Generate content hash
        metadata['content_hash'] = hashlib.md5(text.encode()).hexdigest()
        
        return {
            'text': text,
            'metadata': metadata
        }
    
    def crawl_page(self, url: str) -> Optional[Dict]:
        """
        Crawl a single page
        
        Args:
            url: URL to crawl
            
        Returns:
            Dictionary containing page content and metadata, or None if failed
        """
        try:
            # Respect politeness delay
            time.sleep(self.delay)
            
            # Fetch page
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract content
            result = self.extract_content(soup, url)
            
            # Extract links for further crawling
            links = self.extract_links(soup, url)
            result['links'] = links
            
            logger.info(f"Successfully crawled: {url}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {str(e)}")
            return None
    
    def crawl_website(
        self,
        start_url: str,
        max_pages: int = 100,
        url_patterns: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Crawl a website starting from a URL
        
        Args:
            start_url: Starting URL
            max_pages: Maximum number of pages to crawl
            url_patterns: Optional list of URL patterns to include
            
        Returns:
            List of crawled pages with content and metadata
        """
        base_domain = urlparse(start_url).netloc
        to_visit = [(start_url, 0)]  # (url, depth)
        crawled_pages = []
        
        while to_visit and len(crawled_pages) < max_pages:
            url, depth = to_visit.pop(0)
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            # Skip if max depth exceeded
            if depth > self.max_depth:
                continue
            
            # Skip if not valid
            if not self.is_valid_url(url, base_domain):
                continue
            
            # Apply URL pattern filters if provided
            if url_patterns:
                if not any(pattern in url for pattern in url_patterns):
                    continue
            
            # Mark as visited
            self.visited_urls.add(url)
            
            # Crawl page
            result = self.crawl_page(url)
            
            if result:
                result['depth'] = depth
                crawled_pages.append(result)
                
                # Add links to visit queue
                for link in result.get('links', []):
                    if link not in self.visited_urls:
                        to_visit.append((link, depth + 1))
        
        logger.info(f"Crawled {len(crawled_pages)} pages from {start_url}")
        return crawled_pages
    
    def crawl_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Extract URLs from sitemap
        
        Args:
            sitemap_url: URL of the sitemap
            
        Returns:
            List of URLs found in sitemap
        """
        try:
            response = self.session.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')]
            
            logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls
            
        except Exception as e:
            logger.error(f"Error parsing sitemap: {str(e)}")
            return []


if __name__ == "__main__":
    # Example usage
    crawler = WebCrawler(delay=2.0)
    
    # Example: Crawl AWS documentation (limited)
    start_url = "https://docs.aws.amazon.com/bedrock/"
    pages = crawler.crawl_website(start_url, max_pages=5)
    
    print(f"Crawled {len(pages)} pages")
    for page in pages[:3]:
        print(f"\nTitle: {page['metadata']['title']}")
        print(f"URL: {page['metadata']['url']}")
        print(f"Content length: {len(page['text'])} characters")





