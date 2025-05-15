import pandas as pd
from bs4 import BeautifulSoup
import requests
import time
import subprocess
import logging
from config import config
import json
import os

logger = logging.getLogger(__name__)

LAST_PROCESSED_FILE = config.LAST_PROCESSED_PATH

def load_last_processed_to_content():
    if not os.path.exists(LAST_PROCESSED_FILE):
        return {}
        
    try:
        with open(LAST_PROCESSED_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading last processed file: {e}")
        return {}

def save_last_processed_to_content(notification_id):
    try:
        os.makedirs(os.path.dirname(LAST_PROCESSED_FILE), exist_ok=True)
        with open(LAST_PROCESSED_FILE, 'w') as f:
            json.dump({'last_id': notification_id}, f)
        logger.info(f"Successfully saved last processed ID: {notification_id}")
    except Exception as e:
        logger.error(f"Error saving last processed file: {e}")

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Referer': 'https://www.kap.org.tr/tr/bildirim-sorgu-sonuc'
    }

def extract_history_info(soup):
    history_info = ''
    history_div = soup.find('div', class_='text-15 font-normal leading-4 lg:w-auto w-1/2')
    if history_div:
        spans = history_div.find_all('span')
        if len(spans) >= 2:
            date = spans[0].get_text(strip=True)
            time = spans[1].get_text(strip=True)
            history_info = f"Date: {date}, Time: {time}"
    return history_info

def extract_header_info(soup):
    header_info = {}
    header_div = soup.find('div', class_='flex flex-row justify-between text-danger font-semibold text-xl pb-9')
    if header_div:
        header_info['title'] = header_div.find('div').get_text(strip=True)
    return header_info

def extract_content_info(soup):
    content_info = ''
    content_div = soup.find('div', class_='modal-infosub audit-opinion overflow-auto')
    if content_div:
        content_info += content_div.get_text(strip=True) + '\n\n'
    return content_info

def get_notification_content(notification_id):
    url = f"https://www.kap.org.tr/tr/Bildirim/{notification_id}"
    
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return {
            'header_info': extract_header_info(soup),
            'content_info': extract_content_info(soup),
            'history_info': extract_history_info(soup)
        }
    except Exception as e:
        logger.error(f"Notification content not found (ID: {notification_id}): {e}")
        return None

def process_notification_row(row):
    try:
        checkbox = row.find('input', {'type': 'checkbox'})
        if not checkbox or 'id' not in checkbox.attrs:
            return None
            
        notification_id = checkbox['id']
        logger.info(f"Processing notification ID: {notification_id}")

        title = row.find('td', {'class': 'min-w-30'})
        title = title.text.strip() if title else ''
        
        content = get_notification_content(notification_id)
        if not content:
            return None
            
        result = {
            'id': notification_id,
            'title': title,
            'header_info': content['header_info'],
            'content_info': content['content_info'],
            'history_info': content['history_info']
        }
        save_last_processed_to_content(notification_id)
        return result
    except Exception as e:
        logger.error(f"Error processing notification: {e}")
        return None

def parse_notifications(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    notifications = []
    last_processed = load_last_processed_to_content()
    last_id = last_processed.get('last_id', None)
    
    notification_rows = soup.find_all('tr', class_=lambda x: x and ('notification-row' in x or 'cursor-pointer' in x))
    logger.info(f"Total {len(notification_rows)} notifications found")
    
    last_id_index = None
    if last_id:
        for i, row in enumerate(notification_rows):
            checkbox = row.find('input', {'type': 'checkbox'})
            if checkbox and 'id' in checkbox.attrs and checkbox['id'] == last_id:
                last_id_index = i
                break
    
    target_rows = notification_rows[:last_id_index] if last_id_index is not None else notification_rows
    logger.info(f"Processing {len(target_rows)} notifications")
    
    for row in reversed(target_rows):
        result = process_notification_row(row)
        if result:
            notifications.append(result)
        time.sleep(0.5)
    
    return notifications

def save_to_files(notifications):
    if not notifications:
        logger.info("No data to save")
        return
    
    header_content_data = [{
        'id': notification['id'],
        'title': notification['title'],
        'content': notification['content_info'],
        'history': notification['history_info']
    } for notification in notifications]
    
    header_content_df = pd.DataFrame(header_content_data)
    header_content_df.to_csv('header_content.csv', index=False, encoding='utf-8-sig')

def fetch_html_content(url):
    try:
        logger.info(f"URL is being accessed: {url}")
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"URL connection error: {e}")
        return None

def run_next_script_content_process():
    try:
        logger.info("Starting process_csv.py")
        subprocess.run(['python', 'process_csv.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running process_csv.py: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    url = "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc?srcbar=Y&cmp=Y&cat=4&s=4028328c594bfdca01594c0af9aa0057&st=Finansal%20Rapor&kw=bilan%C3%A7o&slf=FR"
    
    logger.info("Starting content scraper")
    logger.info(f"Last processed file path: {LAST_PROCESSED_FILE}")
    
    html_content = fetch_html_content(url)
    if not html_content:
        logger.error("Failed to fetch HTML content")
        exit(1)
        
    logger.info("Successfully fetched HTML content")
    notifications = parse_notifications(html_content)
    
    if notifications:
        logger.info(f"Found {len(notifications)} new notifications")
        save_to_files(notifications)
        run_next_script_content_process()
    else:
        logger.info("No new notifications found") 