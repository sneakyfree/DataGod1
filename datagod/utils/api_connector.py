import requests
import time
import logging
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

logger = logging.getLogger(__name__)

class APIConnector:
    def __init__(self, base_url: str, api_key: str = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DataGod-Client/1.0'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            
        return headers
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._prepare_headers()
        
        try:
            response = self.session.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=self.timeout
            )
            
            # Log request
            logger.info(f"GET {url} - Status: {response.status_code}")
            
            response.raise_for_status()
            
            # Handle JSON response
            if response.headers.get('content-type', '').startswith('application/json'):
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API GET request failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._prepare_headers()
        
        try:
            response = self.session.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=self.timeout
            )
            
            # Log request
            logger.info(f"POST {url} - Status: {response.status_code}")
            
            response.raise_for_status()
            
            # Handle JSON response
            if response.headers.get('content-type', '').startswith('application/json'):
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API POST request failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def rate_limit(self, delay: float = 1.0):
        """Add delay to respect rate limits"""
        time.sleep(delay)
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self.get('/health')
            return response['success']
        except Exception:
            return False
