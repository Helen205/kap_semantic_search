import pandas as pd
import os
import glob
import subprocess
import logging

logger = logging.getLogger(__name__)

def process_table(file_path):
    try:
        filename = os.path.basename(file_path)
        parts = filename.split('_')
        notification_id = parts[0]
        table_num = parts[2].replace('.xlsx', '')  
        
        df = pd.read_excel(file_path)
        
        first_three_rows = df.iloc[:2]
        remaining_rows = df.iloc[2:]
        
        chunk_size = 15
        chunks = [remaining_rows[i:i+chunk_size] for i in range(0, len(remaining_rows), chunk_size)]
        
        for idx, chunk in enumerate(chunks):
            combined_chunk = pd.concat([first_three_rows, chunk])
            output_filename = f"notification_htmls/{notification_id}_table_{table_num}_chunk_{idx+1}.xlsx"
            combined_chunk.to_excel(output_filename, index=False)
            
        print(f"Processed {filename} - created {len(chunks)} chunks")

        if '_chunk_' not in filename:
            os.remove(file_path)
            print(f"Deleted original file: {filename}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def run_next_script():
    try:
        logger.info("Starting chroma_table.py")
        subprocess.run(
            ['python', 'chroma_table.py'],
            check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running chroma_table.py: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

def main():
    table_files = [f for f in glob.glob('notification_htmls/*_table_*.xlsx') if '_chunk_' not in f]
    
    for file_path in table_files:
        process_table(file_path)
    
    logger.info("All tables have been processed and chunked. Original files deleted.")
    run_next_script()

if __name__ == "__main__":
    main()
