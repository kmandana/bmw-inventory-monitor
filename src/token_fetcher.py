"""
BMW Token Fetcher using Playwright
Automatically extracts the Bearer token from BMW CPO website network requests
"""
import json
from playwright.sync_api import sync_playwright
from typing import Optional
import logging


class TokenFetcher:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.captured_token: Optional[str] = None
        
    def extract_token_from_request(self, request):
        """
        Callback function to capture network requests and extract the token
        """
        # Check if this is the BMW inventory API request
        if "inventoryservices.bmwdealerprograms.com/vehicle" in request.url:
            headers = request.headers
            auth_header = headers.get("authorization", "")
            
            # Extract Bearer token
            if auth_header.startswith("Bearer "):
                self.captured_token = auth_header.replace("Bearer ", "")
                self.logger.info(f"Token captured successfully: {self.captured_token[:20]}...")
    
    def fetch_token(self, headless: bool = True, timeout: int = 30000) -> Optional[str]:
        """
        Fetches the BMW API token by loading the CPO website and capturing network traffic
        
        Args:
            headless: Whether to run browser in headless mode (default: True)
            timeout: Maximum time to wait for page load in milliseconds (default: 30000)
            
        Returns:
            str: The Bearer token if found, None otherwise
        """
        self.logger.info("Starting token fetch process...")
        
        try:
            with sync_playwright() as p:
                # Launch browser
                self.logger.info(f"Launching browser (headless={headless})...")
                browser = p.chromium.launch(headless=headless)
                
                # Create new page
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                # Set up request interception to capture the token
                page.on("request", self.extract_token_from_request)
                
                # Navigate directly to BMW CPO search results with zipcode
                zipcode = "90717"  # Default zipcode from main.py
                bmw_cpo_url = f"https://www.bmwusa.com/certified-preowned-search/results?zipCode={zipcode}"
                self.logger.info(f"Navigating to {bmw_cpo_url}...")
                
                # Go to the page and wait for it to load
                page.goto(bmw_cpo_url, wait_until="load", timeout=timeout)
                
                # Wait for the page to make API calls
                self.logger.info("Waiting for API requests to be made...")
                page.wait_for_timeout(5000)
                
                # Close browser
                browser.close()
                
                if self.captured_token:
                    self.logger.info("Token successfully extracted!")
                    return self.captured_token
                else:
                    self.logger.warning("Token not found in network requests")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching token: {e}")
            return None


def get_bmw_token(headless: bool = True, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Convenience function to fetch BMW API token
    
    Args:
        headless: Whether to run browser in headless mode
        logger: Optional logger instance
        
    Returns:
        str: The Bearer token if found, None otherwise
    """
    fetcher = TokenFetcher(logger=logger)
    return fetcher.fetch_token(headless=headless)


if __name__ == "__main__":
    # Test the token fetcher
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("Testing BMW Token Fetcher...")
    print("-" * 50)
    
    token = get_bmw_token(headless=False, logger=logger)
    
    if token:
        print(f"\n✓ Token fetched successfully!")
        print(f"Token (first 30 chars): {token[:30]}...")
        print(f"Token length: {len(token)} characters")
        
        # Try to decode JWT to see expiration
        try:
            import base64
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) == 3:
                # Decode payload (add padding if needed)
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                payload_data = json.loads(decoded)
                print(f"\nToken payload:")
                print(json.dumps(payload_data, indent=2))
                
                if 'exp' in payload_data:
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(payload_data['exp'])
                    print(f"\nToken expires at: {exp_date}")
        except Exception as e:
            print(f"\nCouldn't decode token: {e}")
    else:
        print("\n✗ Failed to fetch token")

