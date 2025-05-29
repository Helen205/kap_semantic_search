from pydantic import BaseModel
from typing import Optional, Dict

class Query(BaseModel):
    question: str
    max_results: Optional[int] = 3
    distance: Optional[float] = 0.86
    start_date: str
    end_date: str

class CompanySearch(BaseModel):
    company: str

class CompanySearchResponse(BaseModel):
    question: str
    answers: Dict

class Response(BaseModel):
    question: Dict
    answers: Dict 