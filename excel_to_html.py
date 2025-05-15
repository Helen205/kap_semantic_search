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

def load_last_processed_to_table():
    if not os.path.exists(LAST_PROCESSED_TABLE):
        return {}
    
    try:
        with open(LAST_PROCESSED_TABLE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading last processed file: {e}")
        return {}

def save_last_processed_to_table(notification_id):
    try:
        os.makedirs(os.path.dirname(LAST_PROCESSED_TABLE), exist_ok=True)
        with open(LAST_PROCESSED_TABLE, 'w') as f:
            json.dump({'last_id': notification_id}, f)
        logger.info(f"Successfully saved last processed ID: {notification_id}")
    except Exception as e:
        logger.error(f"Error saving last processed file: {e}")

def create_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Referer': 'https://www.kap.org.tr/tr/bildirim-sorgu-sonuc'
    }

@app.task(name='excel_to_html.get_notification_content')
def get_notification_content(notification_id):
    url = f"https://www.kap.org.tr/en/api/notification/export/excel/{notification_id}"
    
    try:
        session = create_session()
        response = session.get(url, headers=get_headers(), stream=True, timeout=30)
        response.raise_for_status()

        os.makedirs('notification_htmls', exist_ok=True)
        with open(f'notification_htmls/{notification_id}.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"HTML content saved for notification {notification_id}")
        
        return response.text
    except Exception as e:
        logger.error(f"Notification content not fetched (ID: {notification_id}): {e}")
        return None

def process_notification_row(row):
    try:
        checkbox = row.find('input', {'type': 'checkbox'})
        if not checkbox or 'id' not in checkbox.attrs:
            return None
            
        notification_id = checkbox['id']
        logger.info(f"Processing notification ID: {notification_id}")
        
        html_content = get_notification_content(notification_id)
        if not html_content:
            return None
            
        time.sleep(0.5)   
        result = {
            'id': notification_id,
            'html_content': html_content
        }
        save_last_processed_to_table(notification_id)
        return result
    except Exception as e:
        logger.error(f"Error processing notification: {e}")
        return None

@app.task(name='excel_to_html.parse_notifications')
def parse_notifications(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    notifications = []
    last_processed = load_last_processed_to_table()
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
    
    target_rows = notification_rows[last_id_index + 1:] if last_id_index is not None else notification_rows
    logger.info(f"Processing {len(target_rows)} notifications")
    
    for row in target_rows:
        result = process_notification_row(row)
        if result:
            notifications.append(result)
        time.sleep(0.5)
    
    return notifications

@app.task(name='excel_to_html.fetch_html_content')
def fetch_html_content(url):
    try:
        logger.info(f"URL is being accessed: {url}")
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"URL connection error: {e}")
        return None

def chroma_connection_error():
    try:
        client_wrapper = ClientWrapper()
        client = client_wrapper.client 
        return True
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
    if chroma_connection_error() == "CONNECTION_ERROR":
        logger.error("Chrome connection error - skipping last_id update")
        return False
        
    url = "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc?srcbar=Y&cmp=Y&cat=4&s=4028328c594bfdca01594c0af9aa0057&st=Finansal%20Rapor&kw=bilan%C3%A7o&slf=FR"
    
    html_content = fetch_html_content(url)
    if not html_content:
        logger.error("HTML is not fetched")
        return False
        
    notifications = parse_notifications(html_content)
    if notifications:
        logger.info(f"Total {len(notifications)} new notifications processed and saved as HTML")
        run_next_script_table.delay()
    else:
        logger.info("No new notifications found")
    return True

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    run_scraper.delay()
    
    sender.add_periodic_task(
        crontab(minute=54, hour='*/2'),
        run_scraper.s()
    )

app.autodiscover_tasks()

if __name__ == "__main__":
    app.worker_main() 