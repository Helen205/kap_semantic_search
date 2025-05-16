import uvicorn
import logging
from src.tasks.content_tasks import process_content, save_content_to_chroma
from src.tasks.table_tasks import process_tables, save_tables_to_chroma
from src.tasks.processing_tasks import process_excel_files, process_csv_files

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def process_data():
    try:
        content_task = process_content.delay()
        content_task.get()  
        
        save_content_task = save_content_to_chroma.delay()
        save_content_task.get()
        
        table_task = process_tables.delay()
        table_task.get()
        
        save_table_task = save_tables_to_chroma.delay()
        save_table_task.get()
        
        excel_task = process_excel_files.delay()
        excel_task.get()
        
        csv_task = process_csv_files.delay()
        csv_task.get()
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise

def main():
    try:
        process_data()
        logger.info("Starting FastAPI server...")
        uvicorn.run(
            "api.routes:app",
            host="0.0.0.0",
            port=8001,
            reload=False,
            log_level="debug"
        )
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 