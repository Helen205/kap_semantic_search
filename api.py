from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional
import logging
from kap_chatbot import KAPChatbot
from kap_chatbot import generate_response
from prompts import prompt as base_prompt
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KAP Chatbot API",
    description="KAP notifications chatbot API",
    version="1.0.0"
)

class Query(BaseModel):
    question: str
    max_results: Optional[int] = 3
    distance: Optional[float] = 0.86

class CompanySearch(BaseModel):
    company: str

class CompanySearchResponse(BaseModel):
    question: str
    answers: dict

class Response(BaseModel):
    question: dict
    answers: dict

@app.post("/query", response_model=Response)
async def query_kap(query: Query):
    try:
        chatbot = KAPChatbot()
        print(f"Received query: {query}")
        
        full_prompt = base_prompt.format(query=query)
        results = generate_response(full_prompt)
        
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
        except json.JSONDecodeError:
            company = None
            search_query = results

        search_results = chatbot.search_disclosures(
            query=search_query,
            company=company,
            distance_threshold=query.distance,
            query_type=query_type
        )
        
        formatted_response = chatbot.format_response(results=search_results, query=results, limit=query.max_results)
        
        return Response(
            question=query_data,
            answers=formatted_response
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/company_search", response_model=CompanySearchResponse)
async def company_search(query: CompanySearch):
    try:
        chatbot = KAPChatbot()

        search_results = chatbot.company_search(
            company=query.company,
        )
        
        formatted_response = chatbot.format_response(search_results, query=query.company)
        
        return CompanySearchResponse(
            question=query.company,
            answers=formatted_response
        )
    except Exception as e:
        logger.error(f"Error processing company search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="debug"
    ) 