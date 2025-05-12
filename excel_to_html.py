from bs4 import BeautifulSoup
import requests
import time
import os
import subprocess
import logging
from celery import Celery
from config import config
import json
from celery.schedules import crontab
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from client import ClientWrapper

app = Celery('excel_to_html', broker=config.REDIS_URL, backend=config.REDIS_URL)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LAST_PROCESSED_TABLE = config.LAST_PROCESSED_TABLE_PATH

def load_last_processed():
    try:
        if os.path.exists(LAST_PROCESSED_TABLE):
            with open(LAST_PROCESSED_TABLE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading last processed file: {e}")
        return {}

def save_last_processed(notification_id):
    try:
        os.makedirs(os.path.dirname(LAST_PROCESSED_TABLE), exist_ok=True)
        with open(LAST_PROCESSED_TABLE, 'w') as f:
            json.dump({'last_id': notification_id}, f)
        logger.info(f"Successfully saved last processed ID: {notification_id}")
    except Exception as e:
        logger.error(f"Error saving last processed file: {e}")

@app.task(name='excel_to_html.get_notification_content')
def get_notification_content(notification_id):
    url = f"https://www.kap.org.tr/en/api/notification/export/excel/{notification_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Referer': 'https://www.kap.org.tr/tr/bildirim-sorgu-sonuc'
    }
    
    try:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = session.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        
        os.makedirs('notification_htmls', exist_ok=True)
        with open(f'notification_htmls/{notification_id}.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"HTML content saved for notification {notification_id}")
        
        return response.text
            
    except Exception as e:
        logger.error(f"Notification content not fetched (ID: {notification_id}): {e}")
        return None

@app.task(name='excel_to_html.parse_notifications')
def parse_notifications(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    notifications = []
    last_processed = load_last_processed()
    last_id = last_processed.get('last_id', None)
    
    notification_rows = soup.find_all('tr', class_=lambda x: x and ('notification-row' in x or 'cursor-pointer' in x))
    logger.info(f"Total {len(notification_rows)} notifications found")
    
    notification_rows.reverse()
    
    last_id_index = None
    if last_id:
        for i, row in enumerate(notification_rows):
            checkbox = row.find('input', {'type': 'checkbox'})
            if checkbox and 'id' in checkbox.attrs and checkbox['id'] == last_id:
                last_id_index = i
                break
    
    if last_id_index is not None:
        new_notifications = notification_rows[last_id_index + 1:]
        logger.info(f"Found {len(new_notifications)} new notifications after last processed ID")
        
        for row in new_notifications:
            try:
                checkbox = row.find('input', {'type': 'checkbox'})
                if not checkbox or 'id' not in checkbox.attrs:
                    continue
                    
                notification_id = checkbox['id']
                logger.info(f"Processing notification ID: {notification_id}")
                
                html_content = get_notification_content(notification_id)
                if html_content:
                    notifications.append({
                        'id': notification_id,
                        'html_content': html_content
                    })
                    save_last_processed(notification_id)
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                continue
    else:
        logger.info("No last processed ID found, processing all notifications")
        for row in notification_rows:
            try:
                checkbox = row.find('input', {'type': 'checkbox'})
                if not checkbox or 'id' not in checkbox.attrs:
                    continue
                    
                notification_id = checkbox['id']
                logger.info(f"Processing notification ID: {notification_id}")
                
                html_content = get_notification_content(notification_id)
                if html_content:
                    notifications.append({
                        'id': notification_id,
                        'html_content': html_content
                    })
                    save_last_processed(notification_id)
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                continue
    
    return notifications

@app.task(name='excel_to_html.fetch_html_content')
def fetch_html_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        logger.info(f"URL is being accessed: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"URL connection error: {e}")
        return None
    
def chroma_connection_error():
    try:
        client = ClientWrapper()
        collections = client.client.list_collections()
        if collections is not None:
            return True
        return "CONNECTION_ERROR"
    except Exception as e:
        logger.error(f"Chroma connection error: {e}")
        return "CONNECTION_ERROR"

@app.task(name='excel_to_html.run_next_script')
def run_next_script_table():
    try:
        logger.info("Starting table_scraper.py")
        subprocess.run(['python', 'table_scraper.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running table_scraper.py: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

@app.task(name='excel_to_html.run_scraper')
def run_scraper():
    try:
        if chroma_connection_error() == "CONNECTION_ERROR":
            logger.error("Chrome connection error - skipping last_id update")
            return False
        url = "https://www.kap.org.tr/en/bildirim-sorgu-sonuc?srcbar=Y&cmp=Y&cat=4&s=4028328c594bfdca01594c0af9aa0057&st=Finansal%20Rapor&kw=bilan%C3%A7o&slf=FR"
        
        html_content = fetch_html_content(url)
        if html_content:
            notifications = parse_notifications(html_content)
            if notifications:
                logger.info(f"Total {len(notifications)} new notifications processed and saved as HTML")
                run_next_script_table.delay()
            else:
                logger.info("No new notifications found")
            return True
        else:
            logger.error("HTML is not fetched")
            return False
    except Exception as e:
        logger.error(f"Error in run_scraper: {e}")
        return False

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute=56),
        run_scraper.s()

    )


app.autodiscover_tasks()

if __name__ == "__main__":
    app.worker_main() 