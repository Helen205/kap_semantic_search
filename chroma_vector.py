import pandas as pd
from chromadb.utils import embedding_functions
import logging
from client import ClientWrapper
from config import config
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_chroma():
    try:
        logger.info("Chroma connecting...")
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        collection_name = getattr(config, "CHROMA_COLLECTION", "content")

        collection = ClientWrapper().get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        logger.info(f"Using existing collection: {collection_name}")
    
        if collection:
            logger.info("Successfully connected to Chroma")
            return collection

        raise Exception("Collection not created")

    except Exception as e:
        logger.error(f"Chroma connection error: {e}")
        raise

def save_to_chroma():
    try:
        csv_file = 'header_content_processed.csv'
        if not os.path.exists(csv_file):
            logger.error(f"CSV file {csv_file} not found")
            return

        df = pd.read_csv(csv_file)
        logger.info(f"Read {len(df)} records from CSV")
        
        collection = setup_chroma()
        
        for index, row in df.iterrows():
            try:
                doc_id = f"{row['notification_id']}_{row['chunk_index']}"

                document_text = row['title'] if row['is_title'] else row['content']

                
                collection.add(
                    documents=[document_text],
                    metadatas=[{
                        'title': row['title'],
                        'content': row['content'],
                        'is_title': row['is_title'],
                        'notification_id': row['notification_id'],
                        'history': row['history'],
                        'chunk_index': row['chunk_index'],
                        'total_chunks': row['total_chunks']
                    }],
                    ids=[doc_id]
                )
                
                
                logger.info(f"Added document {doc_id} to ChromaDB")
                
            except Exception as e:
                logger.error(f"Error processing document {row.get('notification_id', 'unknown')}: {e}")
                continue
                
        logger.info("Successfully saved all documents to ChromaDB")
        
        try:
            os.remove(csv_file)
            logger.info(f"Deleted source CSV file: {csv_file}")
        except Exception as e:
            logger.error(f"Error deleting CSV file: {e}")
        
    except Exception as e:
        logger.error(f"Error in save_to_chroma: {e}")
        raise

def main():
    try:
        save_to_chroma()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 