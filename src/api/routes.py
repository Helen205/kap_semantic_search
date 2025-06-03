from fastapi import FastAPI, HTTPException
import logging
from .models import Query, CompanySearch, CompanySearchResponse, Response
from ..services.chatbot_service import KAPChatbot
from ..core.prompts import prompt as base_prompt
import json
from ..services.chroma_content_service import ChromaContentService
from ..services.chroma_table_service import ChromaTableService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="KAP Chatbot API",
    description="KAP notifications chatbot API",
    version="1.0.0"
)

chroma_content_service = ChromaContentService()
chroma_table_service = ChromaTableService()

def _parse_gemini_response(results):
    try:
        if results.startswith('```json'):
            results = results[7:]
        if results.endswith('```'):
            results = results[:-3]
        results = results.strip()
        
        query_data = json.loads(results)
        company = query_data.get('args', {}).get('company')
        search_query = query_data.get('args', {}).get('query')
        query_type = query_data.get('query_type')
        
        return query_data, company, search_query, query_type
    except json.JSONDecodeError:
        return None, None, results, None

def _process_query(chatbot, search_query, company, query_type, distance, max_results, start_date, end_date, period):
    search_results = chatbot.search_disclosures(
        response=search_query,
        company=company,
        distance_threshold=distance,
        query_type=query_type,
        start_date=start_date,
        end_date=end_date,
        period=period
        )
        
    return chatbot.format_response(results=search_results, query=search_query, limit=max_results)


@app.post("/query", response_model=Response)
async def query_kap(query: Query):
    try:
        chatbot = KAPChatbot()
        logger.info(f"Received query: {query}")
        
        full_prompt = base_prompt.format(query=query)
        results = chatbot.generate_response(full_prompt)
        
        query_data, company, search_query, query_type = _parse_gemini_response(results)
        
        formatted_response = _process_query(
            chatbot=chatbot,
            search_query=search_query,
            company=company,
            query_type=query_type,
            distance=query.distance,
            max_results=query.max_results,
            start_date=query.start_date,
            end_date=query.end_date,
            period=query.period
        )
        
        return Response(
            question=query_data or {"query": search_query},
            answers=formatted_response
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return Response(
            question={"query": query.question},
            answers={"disclosures": []}
        )

@app.post("/company_search", response_model=CompanySearchResponse)
async def company_search(query: CompanySearch):
    try:
        chatbot = KAPChatbot()
        search_results = chatbot.company_search(company=query.company)
        formatted_response = chatbot.format_response_company(search_results, query=query.company)
        
        return CompanySearchResponse(
            question=query.company,
            answers=formatted_response
        )
    except Exception as e:
        logger.error(f"Error processing company search: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    
@app.get("/health")
async def health_check():
    try:
        chroma_content_service.setup_chroma_content()
        chroma_table_service.setup_chroma_table()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        ) 