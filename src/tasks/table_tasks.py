from ..core.celery_app import celery_app
from ..scrapers.excel_to_html import ExcelToHtml
from ..services.chroma_table_service import ChromaTableService
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name='process_tables')
def process_tables():
    scraper = ExcelToHtml()
    scraper.run_scraper()
    return {"status": "success", "message": "Table processing completed"}

@celery_app.task(name='save_tables_to_chroma')
def save_tables_to_chroma():
    scraper = ChromaTableService()
    scraper.save_to_chroma_table()
    return {"status": "success", "message": "Tables saved to ChromaDB"}
