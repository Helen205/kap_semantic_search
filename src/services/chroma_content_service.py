import pandas as pd
import logging
from ..core.client import ClientWrapper
from ..core.config import config
import os


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ChromaContentService:
    def __init__(self): 
        self.collection_name = getattr(config, "CHROMA_COLLECTION", "content")
        self.client = ClientWrapper()

    def setup_chroma_content(self):
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

    def _read_csv_file(self, csv_file):
        if not os.path.exists(csv_file):
            logger.error(f"CSV file {csv_file} not found")
            return None
            
        try:
            df = pd.read_csv(csv_file)
            logger.info(f"Read {len(df)} records from CSV")
            return df
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return None

    def _create_metadata(self, row):
        return {
            'title': str(row['title']) if pd.notna(row['title']) else '',
            'content': str(row['content']) if pd.notna(row['content']) else '',
            'is_title': bool(row['is_title']),
            'notification_id': int(row['notification_id']),
            'history': str(row['history']) if pd.notna(row['history']) else '',
            'chunk_index': int(row['chunk_index']),
            'total_chunks': int(row['total_chunks'])
        }

    def _process_document(self, row, collection):
        try:
            doc_id = f"{row['notification_id']}_{row['chunk_index']}"
            document_text = row['title'] if row['is_title'] else row['content']
            metadata = self._create_metadata(row)
            
            collection.add(
                documents=[document_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added document {doc_id} to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {row.get('notification_id', 'unknown')}: {e}")
            return False

    def _cleanup_csv_file(self, csv_file):
        try:
            os.remove(csv_file)
            logger.info(f"Deleted source CSV file: {csv_file}")
        except Exception as e:
            logger.error(f"Error deleting CSV file: {e}")

    def save_to_chroma_content(self):
        try:
            csv_file = 'header_content_processed.csv'
            df = self._read_csv_file(csv_file)
            if df is None:
                return

            collection = self.setup_chroma_content()
            processed_count = 0
            
            for _, row in df.iterrows():
                if self._process_document(row, collection):
                    processed_count += 1
            
            logger.info(f"Successfully processed {processed_count} out of {len(df)} documents")
            self._cleanup_csv_file(csv_file)
            
        except Exception as e:
            logger.error(f"Error in save_to_chroma: {e}")
            raise
