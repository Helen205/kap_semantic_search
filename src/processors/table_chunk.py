import pandas as pd
import os
import glob
import logging
from ..services.chroma_table_service import ChromaTableService

logger = logging.getLogger(__name__)

class TableChunk:
    def __init__(self):
        self.chroma_service = ChromaTableService()

    def process_table_chunks(self):
        table_files = [f for f in glob.glob('notification_htmls/*_table_*.xlsx') if '_chunk_' not in f]
            
        for file_path in table_files:
            self.process_table(file_path)


    def process_table(self,file_path):
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
        
        self.chroma_service.save_to_chroma_table()

