from ..core.celery_app import celery_app
from ..processors.excel_processor import ExcelProcessor
from ..processors.csv_processor import CSVProcessor
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name='process_excel_files')
def process_excel_files():
    try:
        processor = ExcelProcessor()
        processor.process_tables()
        return {"status": "success", "message": "Excel processing completed"}
    except Exception as e:
        logger.error(f"Excel processing error: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name='process_csv_files')
def process_csv_files():
    try:
        processor = CSVProcessor()
        processor.process_csv()
        return {"status": "success", "message": "CSV processing completed"}
    except Exception as e:
        logger.error(f"CSV processing error: {e}")
        return {"status": "error", "message": str(e)} 