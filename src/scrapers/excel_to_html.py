from bs4 import BeautifulSoup
import requests
import time
import os
import logging
from ..core.config import config
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..core.client import ClientWrapper
from ..processors.excel_processor import ExcelProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExcelToHtml:
    def __init__(self):
        self.LAST_PROCESSED_TABLE = config.LAST_PROCESSED_TABLE_PATH
        self.excel_processor = ExcelProcessor()
    def load_last_processed_to_table(self):
        if not os.path.exists(self.LAST_PROCESSED_TABLE):
            return {}
        
        with open(self.LAST_PROCESSED_TABLE, 'r') as f:
            return json.load(f)

    def create_session(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def get_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': 'https://www.kap.org.tr/tr/bildirim-sorgu-sonuc'
        }

    def get_notification_content(self, notification_id):
        url = f"https://www.kap.org.tr/en/api/notification/export/excel/{notification_id}"
        

        session = self.create_session()
        response = session.get(url, headers=self.get_headers(), stream=True, timeout=30)
        response.raise_for_status()

        os.makedirs('notification_htmls', exist_ok=True)
        with open(f'notification_htmls/{notification_id}.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"HTML content saved for notification {notification_id}")
            
        return response.text

    def process_notification_row(self, row):
        checkbox = row.find('input', {'type': 'checkbox'})
        if not checkbox or 'id' not in checkbox.attrs:
            return None
                
        notification_id = checkbox['id']
        logger.info(f"Processing notification ID: {notification_id}")
            
        html_content = self.get_notification_content(notification_id)
        if not html_content:
            return None
                
        time.sleep(0.5)   
        result = {
            'id': notification_id,
            'html_content': html_content
        }
        return result


    def parse_notifications(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        notifications = []
        last_processed = self.load_last_processed_to_table()
        last_id = last_processed.get('last_id', None)
        
        notification_rows = soup.find_all('tr', class_=lambda x: x and ('notification-row' in x or 'cursor-pointer' in x))
        logger.info(f"Total {len(notification_rows)} notifications found")
        
        notification_rows.reverse()
        
        last_id_index = None
        if last_id:
            for i, row in enumerate(notification_rows):
                checkbox = row.find('input', {'type': 'checkbox'})
                if checkbox and 'id' in checkbox.attrs and int(checkbox['id']) == last_id:
                    last_id_index = i
                    break
        
        target_rows = notification_rows[last_id_index + 1:] if last_id_index is not None else notification_rows
        logger.info(f"Processing {len(target_rows)} notifications")
        
        for row in target_rows:
            result = self.process_notification_row(row)
            if result:
                notifications.append(result)
            time.sleep(0.5)
        
        return notifications

    def fetch_html_content(self, url):
        logger.info(f"URL is being accessed: {url}")
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.text


    def chroma_connection_error(self):
        try:
            client_wrapper = ClientWrapper()
            client = client_wrapper.client 
            return True
        except Exception as e:
            logger.error(f"Chroma connection error: {e}")
            return "CONNECTION_ERROR"

    def run_scraper(self):
        if self.chroma_connection_error() == "CONNECTION_ERROR":
            logger.error("Chrome connection error - skipping last_id update")
            return False
            
        url = "https://www.kap.org.tr/en/bildirim-sorgu-sonuc?srcbar=Y&cmp=Y&cat=4&s=4028328c594bfdca01594c0af9aa0057&st=Finansal%20Rapor&kw=bilan%C3%A7o&slf=FR"
        
        html_content = self.fetch_html_content(url)
        if not html_content:
            logger.error("HTML is not fetched")
            return False
            
        notifications = self.parse_notifications(html_content)
        if notifications:
            logger.info(f"Total {len(notifications)} new notifications processed and saved as HTML")
            result = self.excel_processor.process_tables()
            if result["status"] == "error":
                logger.error(f"Error processing tables: {result['message']}")
                return False
            return True
        else:
            logger.info("No new notifications found")
            return True

