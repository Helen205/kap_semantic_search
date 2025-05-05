from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional
import logging
from kap_chatbot import KAPChatbot
from kap_chatbot import generate_response

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KAP Chatbot API",
    description="KAP notifications chatbot API",
    version="1.0.0"
)

chatbot = KAPChatbot()

class Query(BaseModel):
    question: str
    max_results: Optional[int] = 3
    distance: Optional[float] = 0.86

class Response(BaseModel):
    question: str
    answers: list

@app.post("/query", response_model=Response)
async def query_kap(query: Query):
    try:
        results = generate_response(query.question)
        search_results = chatbot.search_disclosures(results, query.question, n_results=query.max_results, distance_threshold=query.distance)
        formatted_response = chatbot.format_response(search_results, query.question)
        
        parts = formatted_response.split('\n\n')
        answers = []
        
        for part in parts:
            if part.strip():
                answers.append(part.strip())
        
        return Response(
            question=query.question,
            answers=answers
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="debug"
    ) 