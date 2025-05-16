import pandas as pd
import logging
import os
from ..core.client import ClientWrapper
from ..core.config import config
import re
import json
import subprocess

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ChromaTableService:
    def __init__(self):        
        self.collection_name = getattr(config, "CHROMA_COLLECTION", "table")
        self.client = ClientWrapper()

    def setup_chroma_table(self):
        try:
            logger.info("Chroma connecting...")
            collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
            
            if not collection:
                raise Exception("Collection not created")
                
            logger.info("Successfully connected to Chroma")
            return collection

        except Exception as e:
            logger.error(f"Chroma connection error: {e}")
            raise

    def _get_excel_files(self):
        excel_files = []
        for root, _, files in os.walk('notification_htmls'):
            for file in files:
                if file.endswith(('.xlsx', '.xls')):
                    excel_files.append(os.path.join(root, file))
        logger.info(f"Found {len(excel_files)} Excel files")
        return excel_files

    def _process_excel_file(self, file_path, collection):
        filename = os.path.basename(file_path)
        info = extract_info_from_filename(filename)
        
        if not info:
            logger.warning(f"Could not extract info from filename: {filename}")
            return False
            
        try:
            df = pd.read_excel(file_path)
            content = excel_to_json(df)
            
            table_id = f"{info['notification_id']}_{info['table_num']}_{info['chunk_index']}"
            
            collection.add(
                documents=[content],
                metadatas=[{
                    'notification_id': int(info['notification_id']),
                    'table_num': int(info['table_num']),
                    'chunk_index': int(info['chunk_index']),
                    'filename': str(filename),
                    'content_type': 'excel_json'
                }],
                ids=[table_id]
            )
            
            logger.info(f"Added Excel file {filename} to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
            return False

    def _cleanup_processed_files(self, processed_files):
        for file_path in processed_files:
            try:
                os.remove(file_path)
                logger.info(f"Deleted processed Excel file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting Excel file {file_path}: {e}")

    def save_to_chroma_table(self):
        try:
            collection = self.setup_chroma_table()
            excel_files = self._get_excel_files()
            processed_files = []
            
            for file_path in excel_files:
                if self._process_excel_file(file_path, collection):
                    processed_files.append(file_path)
            
            logger.info("Successfully saved all Excel files to ChromaDB")
            self._cleanup_processed_files(processed_files)
            
        except Exception as e:
            logger.error(f"Error in save_to_chroma: {e}")
            raise

def extract_info_from_filename(filename):
    pattern = r'(\d+)_table_(\d+)_chunk_(\d+)'
    match = re.search(pattern, filename)
    if match:
        return {
            'notification_id': int(match.group(1)),
            'table_num': int(match.group(2)),
            'chunk_index': int(match.group(3))
        }
    return None

def excel_to_json(df):
    records = df.to_dict(orient='records')
    return json.dumps(records, ensure_ascii=False)

def run_next_script_content():
    try:
        logger.info("Starting content_scraper.py")
        subprocess.run(['python', 'content_scraper.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running content_scraper.py: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


