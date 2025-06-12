import logging
import os
import pandas as pd
from ..utils.file_handler import delete_file
from ..utils.split_text import split_text_into_sentences
from ..services.chroma_content_service import ChromaContentService

logger = logging.getLogger(__name__)

class CSVProcessor:
    def __init__(self):
        self.chroma_service = ChromaContentService()

    def process_csv(self):
        processed_file = 'header_content_processed.csv'
        if os.path.exists(processed_file):
            logger.info("Found existing processed file. Skipping processing to avoid duplicates.")
            return

        csv_file = 'header_content.csv'
        if not os.path.exists(csv_file):
            logger.info("No CSV file to process")
            return

        df = pd.read_csv(csv_file)
        if df.empty:
            logger.info("CSV file is empty")
            return
            
        last_processed_id = self.chroma_service.load_last_processed()
            
        if last_processed_id:
            df = df[df['id'] > last_processed_id]
            if df.empty:
                logger.info("No new notifications to process")
                return

        all_processed_docs = []
            
        for _, row in df.iterrows():
            title_doc = {
                'title': row['title'],
                'content': '',
                'is_title': True,
                'history': row['history'],
                'period': row['period'],
                'notification_id': row['id'],
                'chunk_index': 0,
                'total_chunks': 0
            }

            content_chunks = split_text_into_sentences(row['content'])
                
            for i, chunk in enumerate(content_chunks, 1):
                content_doc = {
                    'title': row['title'],
                    'content': chunk,
                    'is_title': False,
                    'notification_id': row['id'],
                    'history': row['history'],
                    'period': row['period'],
                    'chunk_index': i,
                    'total_chunks': len(content_chunks)
                }
                all_processed_docs.append(content_doc)
            all_processed_docs.append(title_doc)

        if all_processed_docs:
            processed_df = pd.DataFrame(all_processed_docs)
            processed_df.to_csv('header_content_processed.csv', index=False, encoding='utf-8-sig')

            logger.info(f"Processed {len(all_processed_docs)} chunks from {len(df)} notifications")

            self.chroma_service.save_to_chroma_content()

            delete_file(csv_file)
        else:
            logger.info("No data to process")


