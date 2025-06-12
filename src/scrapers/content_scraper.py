import pandas as pd
from bs4 import BeautifulSoup
import requests
import time
import logging
import json
import os
from ..core.config import config
from ..processors.csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class ContentScraper:
    def __init__(self):
        self.csv_processor = CSVProcessor()
        self.last_processed_file = config.LAST_PROCESSED_PATH
    def process_content(self):
        url = self.process_content()
        logger.info("Starting content scraper")
        logger.info(f"Last processed file path: {self.last_processed_file}")
        html_content = self.fetch_html_content(url)
        if not html_content:
            logger.error("Failed to fetch HTML content")
            return
                  
        logger.info("Successfully fetched HTML content")
        notifications = self.parse_notifications(html_content)
        if notifications:
            logger.info(f"Found {len(notifications)} new notifications")
            self.save_to_files(notifications)
            self.csv_processor.process_csv()
        else:
            logger.info("No new notifications found") 

    def load_last_processed(self):
        if not os.path.exists(self.last_processed_file):
            return {}
            
        try:
            with open(self.last_processed_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading last processed file: {e}")
            return {}


    def get_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': 'https://www.kap.org.tr/tr/bildirim-sorgu-sonuc'
        }

    def extract_history_info(self, soup):
        history_info = ''
        history_div = soup.find('div', class_='text-15 font-normal leading-4 lg:w-auto w-1/2')
        if history_div:
            spans = history_div.find_all('span')
            if len(spans) >= 2:
                date = spans[0].get_text(strip=True)
                history_info = f"{date}"
        return history_info
    def extract_period_info(self, soup):
        period_info = ''
        period_div = soup.find_all('div', class_='text-15 font-normal leading-4 lg:w-auto w-1/2')
        if len(period_div) >= 4:
            period_info = period_div[3].get_text(strip=True)
        
        return period_info
    
    def extract_code_info(self, row):
        code_info = ''
        code_cell = row.find('td', class_='px-2 py-1 lg:text-13 text-dark font-normal text-left lg:table-cell hidden max-w-36 min-w-36 break-words')
        if code_cell:
            code_info = code_cell.get_text(strip=True)
        return code_info

    def extract_header_info(self, soup):
        header_info = {}
        header_div = soup.find('div', class_='flex flex-row justify-between text-danger font-semibold text-xl pb-9')
        if header_div:
            header_info['title'] = header_div.find('div').get_text(strip=True)
        return header_info

    def extract_content_info(self, soup):
        content_info = ''
        content_div = soup.find('div', class_='modal-infosub audit-opinion overflow-auto')
        if content_div:
            content_info += content_div.get_text(strip=True) + '\n\n'
        return content_info

    def get_notification_content(self, notification_id):
        url = f"https://www.kap.org.tr/tr/Bildirim/{notification_id}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'header_info': self.extract_header_info(soup),
                'content_info': self.extract_content_info(soup),
                'history_info': self.extract_history_info(soup),
                'period_info': self.extract_period_info(soup)
            }
        except Exception as e:
            logger.error(f"Notification content not found (ID: {notification_id}): {e}")
            return None

    def process_notification_row(self, row):
        checkbox = row.find('input', {'type': 'checkbox'})
        if not checkbox or 'id' not in checkbox.attrs:
            return None
                
        notification_id = checkbox['id']
        logger.info(f"Processing notification ID: {notification_id}")

        title = row.find('td', {'class': 'min-w-30'})
        title = title.text.strip() if title else ''
            
        code_info = self.extract_code_info(row)
            
        content = self.get_notification_content(notification_id)
        if not content:
            return None
                
        result = {
            'id': notification_id,
            'title': f"{title} {code_info}".strip(),
            'header_info': content['header_info'],
            'content_info': content['content_info'],
            'history_info': content['history_info'],
            'period_info': content['period_info']
        }
        return result

    def parse_notifications(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        notifications = []
        last_processed = self.load_last_processed()
        last_id = last_processed.get('last_id', None)
        
        notification_rows = soup.find_all('tr', class_=lambda x: x and ('notification-row' in x or 'cursor-pointer' in x))
        logger.info(f"Total {len(notification_rows)} notifications found")
        
        last_id_index = None
        if last_id:
            for i, row in enumerate(notification_rows):
                checkbox = row.find('input', {'type': 'checkbox'})
                if checkbox and 'id' in checkbox.attrs and int(checkbox['id']) == last_id:
                    last_id_index = i
                    break
        

        target_rows = notification_rows[:last_id_index] if last_id_index is not None else notification_rows
        logger.info(f"Processing {len(target_rows)} notifications")
        
        for row in reversed(target_rows):
            result = self.process_notification_row(row)
            if result:
                notifications.append(result)
            time.sleep(0.5)
        
        return notifications

    def save_to_files(self, notifications):
        if not notifications:
            logger.info("No data to save")
            return
        
        header_content_data = [{
            'id': notification['id'],
            'title': notification['title'],
            'content': notification['content_info'],
            'history': pd.to_datetime(notification['history_info'], format='%d.%m.%Y').strftime('%Y-%m-%d'),
            'period': notification['period_info']
        } for notification in notifications]
        
        header_content_df = pd.DataFrame(header_content_data)
        header_content_df.to_csv('header_content.csv', index=False, encoding='utf-8-sig')

    def fetch_html_content(self, url):
        logger.info(f"URL is being accessed: {url}")
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.text

    def process_content(self):
        url = "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc?srcbar=Y&cmp=Y&cat=4&s=4028328c594bfdca01594c0af9aa0057&st=Finansal%20Rapor&kw=bilan%C3%A7o&slf=FR"
        
        logger.info("Starting content scraper")
        logger.info(f"Last processed file path: {self.last_processed_file}")
        
        html_content = self.fetch_html_content(url)
        if not html_content:
            logger.error("Failed to fetch HTML content")
            return
            
        logger.info("Successfully fetched HTML content")
        notifications = self.parse_notifications(html_content)
        
        if notifications:
            logger.info(f"Found {len(notifications)} new notifications")
            self.save_to_files(notifications)
            self.csv_processor.process_csv()
        else:
            logger.info("No new notifications found") 