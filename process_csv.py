import pandas as pd
from split_text import split_text_into_sentences
import subprocess
import logging

logger = logging.getLogger(__name__)
    
def process_csv(input_file='header_content.csv', output_file='header_content_processed.csv'):
    df = pd.read_csv(input_file)
    
    all_processed_docs = []
    
    for _, row in df.iterrows():

        title_doc = {
            'title': row['title'],
            'content': '',
            'is_title': True,
            'history': row['history'],
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
                'chunk_index': i,
                'total_chunks': len(content_chunks)
            }
            all_processed_docs.append(content_doc)
        all_processed_docs.append(title_doc)
        
        print(f"Processed notification: {row['title']} with {len(content_chunks)} content chunks")

    new_df = pd.DataFrame(all_processed_docs)
    new_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Process completed: {output_file}")
    print(f"Total {len(new_df)} rows saved.")

def run_next_script():
    try:
        logger.info("Starting chroma_table.py")
        subprocess.run(
            ['python', 'chroma_vector.py'],
            check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running chroma_vector.py: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    process_csv()
    run_next_script()
