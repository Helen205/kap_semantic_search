from pydantic import BaseModel
from typing import Optional, Dict

class Query(BaseModel):
    question: str
    max_results: Optional[int] = 3
    distance: Optional[float] = 0.86
    start_date:  Optional[str] = "2025-01-01"
    end_date: Optional[str] = "2025-05-01"
    period: Optional[str] = "3 Aylık"

class CompanySearch(BaseModel):
    company: str

class CompanySearchResponse(BaseModel):
    question: str
    answers: Dict

class Response(BaseModel):
    question: Dict
    answers: Dict 