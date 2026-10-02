"""
FastAPI Web Application for Multilingual NL-to-SQL Generator.
Provides RESTful APIs and serves the interactive user interface.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import process_query_pipeline

app = FastAPI(
    title="Multilingual Natural Language to SQL Query Generator",
    description="Ask database questions in English, Hindi, and Marathi.",
    version="1.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure static and templates exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = "auto"


SAMPLE_EXAMPLES = [
    {
        "id": "mr_1",
        "language": "mr",
        "language_name": "मराठी",
        "category": "Students",
        "query": "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा",
        "description": "Show all students from Computer department"
    },
    {
        "id": "mr_2",
        "language": "mr",
        "language_name": "मराठी",
        "category": "Students & Aggregations",
        "query": "पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?",
        "description": "Average GPA of students living in Pune"
    },
    {
        "id": "mr_3",
        "language": "mr",
        "language_name": "मराठी",
        "category": "Employees & Ranking",
        "query": "सर्वोच्च पगार असणारा कर्मचारी कोणता?",
        "description": "Employee with the highest salary"
    },
    {
        "id": "mr_4",
        "language": "mr",
        "language_name": "मराठी",
        "category": "Departments",
        "query": "सिव्हिल विभागाचे प्रमुख कोण आहेत?",
        "description": "Head of Department (HOD) for Civil engineering"
    },
    {
        "id": "hi_1",
        "language": "hi",
        "language_name": "हिन्दी",
        "category": "Employees & Conditions",
        "query": "उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है",
        "description": "Employees with salary greater than 80,000"
    },
    {
        "id": "hi_2",
        "language": "hi",
        "language_name": "हिन्दी",
        "category": "Students",
        "query": "कंप्यूटर विभाग के सभी छात्र दिखाओ",
        "description": "Show all students in Computer department"
    },
    {
        "id": "hi_3",
        "language": "hi",
        "language_name": "हिन्दी",
        "category": "Departments",
        "query": "सभी विभागों की संकाय संख्या और बजट दिखाएं",
        "description": "Show faculty count and budget for all departments"
    },
    {
        "id": "en_1",
        "language": "en",
        "language_name": "English",
        "category": "Students",
        "query": "Show all students with GPA greater than 9.0",
        "description": "High achieving students filter"
    },
    {
        "id": "en_2",
        "language": "en",
        "language_name": "English",
        "category": "Employees",
        "query": "Count of employees in IT department",
        "description": "Total headcount in IT department"
    },
    {
        "id": "en_3",
        "language": "en",
        "language_name": "English",
        "category": "Employees & Salary",
        "query": "Average salary of employees in Pune",
        "description": "Location-based compensation aggregate"
    }
]


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Renders the main application dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/examples")
async def get_examples():
    """Returns categorized multilingual example queries."""
    return {"success": True, "examples": SAMPLE_EXAMPLES}


@app.post("/api/query")
async def process_user_query(req: QueryRequest):
    """
    Converts a multilingual natural-language request into SQL without database access.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        result = process_query_pipeline(
            user_query=req.query,
            language_override=req.language or "auto"
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Error while processing pipeline"
            }
        )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
