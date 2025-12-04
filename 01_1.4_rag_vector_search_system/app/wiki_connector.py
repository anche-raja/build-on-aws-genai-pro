"""
Phase 4: Wiki System Connector (Confluence, MediaWiki)
Integrates with internal wiki systems
"""

import requests
import json
from typing import Dict, List, Optional
import logging
from datetime import datetime
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WikiConnector:
    """Base class for wiki connectors"""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize wiki connector
        
        Args:
            base_url: Base URL of the wiki
            auth_token: Authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = requests.Session()
    
    def get_page(self, page_id: str) -> Dict:
        """Get a single page (to be implemented by subclasses)"""
        raise NotImplementedError
    
    def list_pages(self, space: Optional[str] = None) -> List[Dict]:
        """List pages (to be implemented by subclasses)"""
        raise NotImplementedError
    
    def search_pages(self, query: str) -> List[Dict]:
        """Search pages (to be implemented by subclasses)"""
        raise NotImplementedError


class ConfluenceConnector(WikiConnector):
    """Connector for Atlassian Confluence"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """
        Initialize Confluence connector
        
        Args:
            base_url: Confluence base URL
            username: Confluence username (email)
            api_token: API token from Confluence
        """
        super().__init__(base_url)
        
        # Set up basic auth
        auth_str = f"{username}:{api_token}"
        auth_bytes = auth_str.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        self.session.headers.update({
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_page(self, page_id: str, expand: str = 'body.storage,version') -> Dict:
        """
        Get a Confluence page
        
        Args:
            page_id: Page ID
            expand: Fields to expand (body.storage for content)
            
        Returns:
            Page data including content and metadata
        """
        url = f"{self.base_url}/rest/api/content/{page_id}"
        params = {'expand': expand}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            page_data = response.json()
            
            # Extract relevant information
            result = {
                'id': page_data['id'],
                'title': page_data['title'],
                'type': page_data['type'],
                'space': page_data['space']['name'] if 'space' in page_data else None,
                'version': page_data['version']['number'] if 'version' in page_data else None,
                'created_at': page_data['history']['createdDate'] if 'history' in page_data else None,
                'updated_at': page_data['version']['when'] if 'version' in page_data else None,
                'creator': page_data['history']['createdBy']['displayName'] if 'history' in page_data else None,
                'content': page_data['body']['storage']['value'] if 'body' in page_data else None,
                'url': f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            }
            
            logger.info(f"Retrieved Confluence page: {result['title']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving page {page_id}: {str(e)}")
            raise
    
    def list_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 100,
        start: int = 0
    ) -> List[Dict]:
        """
        List pages from Confluence
        
        Args:
            space_key: Optional space key to filter by
            limit: Maximum number of results
            start: Starting index for pagination
            
        Returns:
            List of page summaries
        """
        url = f"{self.base_url}/rest/api/content"
        params = {
            'type': 'page',
            'limit': limit,
            'start': start,
            'expand': 'space,version'
        }
        
        if space_key:
            params['spaceKey'] = space_key
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = []
            
            for page in data.get('results', []):
                pages.append({
                    'id': page['id'],
                    'title': page['title'],
                    'space': page['space']['name'] if 'space' in page else None,
                    'version': page['version']['number'] if 'version' in page else None,
                    'url': f"{self.base_url}/pages/viewpage.action?pageId={page['id']}"
                })
            
            logger.info(f"Retrieved {len(pages)} pages from Confluence")
            return pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing pages: {str(e)}")
            raise
    
    def search_pages(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search pages in Confluence
        
        Args:
            query: Search query (CQL)
            limit: Maximum number of results
            
        Returns:
            List of matching pages
        """
        url = f"{self.base_url}/rest/api/content/search"
        params = {
            'cql': f'type=page AND text~"{query}"',
            'limit': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = []
            
            for page in data.get('results', []):
                pages.append({
                    'id': page['id'],
                    'title': page['title'],
                    'url': f"{self.base_url}/pages/viewpage.action?pageId={page['id']}"
                })
            
            logger.info(f"Found {len(pages)} pages matching query: {query}")
            return pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching pages: {str(e)}")
            raise
    
    def get_spaces(self) -> List[Dict]:
        """
        Get list of spaces
        
        Returns:
            List of spaces
        """
        url = f"{self.base_url}/rest/api/space"
        params = {'limit': 500}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            spaces = []
            
            for space in data.get('results', []):
                spaces.append({
                    'key': space['key'],
                    'name': space['name'],
                    'type': space['type']
                })
            
            logger.info(f"Retrieved {len(spaces)} spaces")
            return spaces
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving spaces: {str(e)}")
            raise


class MediaWikiConnector(WikiConnector):
    """Connector for MediaWiki"""
    
    def __init__(self, base_url: str, api_token: Optional[str] = None):
        """
        Initialize MediaWiki connector
        
        Args:
            base_url: MediaWiki base URL
            api_token: Optional API token for authentication
        """
        super().__init__(base_url, api_token)
        self.api_url = f"{base_url}/api.php"
        
        if api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {api_token}'
            })
    
    def get_page(self, title: str) -> Dict:
        """
        Get a MediaWiki page
        
        Args:
            title: Page title
            
        Returns:
            Page data including content and metadata
        """
        params = {
            'action': 'query',
            'prop': 'revisions|info',
            'titles': title,
            'rvprop': 'content|timestamp|user',
            'rvslots': 'main',
            'format': 'json'
        }
        
        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = data['query']['pages']
            
            # MediaWiki returns pages with page_id as key
            page_data = next(iter(pages.values()))
            
            if 'missing' in page_data:
                raise ValueError(f"Page not found: {title}")
            
            revision = page_data['revisions'][0]
            
            result = {
                'id': str(page_data['pageid']),
                'title': page_data['title'],
                'content': revision['slots']['main']['*'],
                'timestamp': revision['timestamp'],
                'user': revision['user'],
                'url': f"{self.base_url}/wiki/{title.replace(' ', '_')}"
            }
            
            logger.info(f"Retrieved MediaWiki page: {result['title']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving page {title}: {str(e)}")
            raise
    
    def list_pages(self, namespace: int = 0, limit: int = 100) -> List[Dict]:
        """
        List pages from MediaWiki
        
        Args:
            namespace: Namespace ID (0 = main)
            limit: Maximum number of results
            
        Returns:
            List of page summaries
        """
        params = {
            'action': 'query',
            'list': 'allpages',
            'apnamespace': namespace,
            'aplimit': limit,
            'format': 'json'
        }
        
        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = []
            
            for page in data['query']['allpages']:
                pages.append({
                    'id': str(page['pageid']),
                    'title': page['title'],
                    'url': f"{self.base_url}/wiki/{page['title'].replace(' ', '_')}"
                })
            
            logger.info(f"Retrieved {len(pages)} pages from MediaWiki")
            return pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing pages: {str(e)}")
            raise
    
    def search_pages(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search pages in MediaWiki
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching pages
        """
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'format': 'json'
        }
        
        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = []
            
            for page in data['query']['search']:
                pages.append({
                    'id': str(page['pageid']),
                    'title': page['title'],
                    'snippet': page.get('snippet', ''),
                    'url': f"{self.base_url}/wiki/{page['title'].replace(' ', '_')}"
                })
            
            logger.info(f"Found {len(pages)} pages matching query: {query}")
            return pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching pages: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    print("Wiki Connector initialized")
    
    # Example for Confluence
    # confluence = ConfluenceConnector(
    #     "https://your-domain.atlassian.net/wiki",
    #     "your-email@example.com",
    #     "your-api-token"
    # )
    # pages = confluence.list_pages(space_key="SPACE")
    
    # Example for MediaWiki
    # mediawiki = MediaWikiConnector("https://en.wikipedia.org")
    # page = mediawiki.get_page("Amazon Web Services")

