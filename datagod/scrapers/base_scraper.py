import requests
import time
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, base_url: str, delay: float = 1.0, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DataGod-Scraper/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """Main scraping method - must be implemented by subclasses"""
        pass
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            time.sleep(self.delay)  # Respect rate limiting
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, timeout=self.timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Log request
            logger.info(f"Scraped {url} - Status: {response.status_code}")
            
            # Try to parse JSON, fallback to text
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Scraping request failed for {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract links from HTML content"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/'):
                href = f"{base_url}{href}"
            elif not href.startswith('http'):
                href = f"{base_url}/{href}"
            links.append(href)
        
        return links
    
    def _parse_json_data(self, data: Any) -> Dict[str, Any]:
        """Parse and validate JSON data"""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON data")
                return {}
        return data
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data"""
        # Basic validation - can be extended
        if not data:
            return False
        
        # Check for required fields
        required_fields = ['source', 'scraped_at', 'data']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def save_data(self, data: List[Dict[str, Any]], filename: str) -> bool:
        """Save scraped data to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save data to {filename}: {str(e)}")
            return False
