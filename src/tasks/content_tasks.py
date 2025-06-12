from ..core.celery_app import celery_app
from ..scrapers.content_scraper import ContentScraper
import logging
from ..services.chroma_content_service import ChromaContentService

logger = logging.getLogger(__name__)

@celery_app.task(name='process_content')
def process_content():
    scraper = ContentScraper()
    scraper.process_content()
    return {"status": "success", "message": "Content processing completed"}


@celery_app.task(name='save_content_to_chroma')
def save_content_to_chroma():
    scraper = ChromaContentService()
    scraper.save_to_chroma_content()
    return {"status": "success", "message": "Content saved to ChromaDB"}
