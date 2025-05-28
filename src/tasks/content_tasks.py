from ..core.celery_app import celery_app
from ..scrapers.content_scraper import ContentScraper
import logging
from ..services.chroma_content_service import ChromaContentService

logger = logging.getLogger(__name__)

@celery_app.task(name='process_content')
def process_content():
    try:
        scraper = ContentScraper()
        scraper.process_content()
        return {"status": "success", "message": "Content processing completed"}
    except Exception as e:
        logger.error(f"Content processing error: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name='save_content_to_chroma')
def save_content_to_chroma():
    try:
        scraper = ChromaContentService()
        scraper.save_to_chroma_content()
        return {"status": "success", "message": "Content saved to ChromaDB"}
    except Exception as e:
        logger.error(f"Error saving content to ChromaDB: {e}")
        return {"status": "error", "message": str(e)} 