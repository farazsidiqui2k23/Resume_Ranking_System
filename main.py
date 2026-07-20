from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from ingestion_pipeline import run_ingestion
from retrieval_pipeline import run_retrieval
from typing import List
import json


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def home():
    return {"message": "Rankly API is running"}

@app.post("/rank")
async def rank_resumes(
    resumes : List[UploadFile] = File(...),
    jd_data : str = Form(...),
    mode : str = Form(...)
):
    
    pdf_files = []
    for file in resumes:
        file_bytes = await file.read()
        pdf_files.append(file.filename, file_bytes)
    
    
    jd = json.loads(jd_data)
      
    vectorstore, rejected_resume = run_ingestion(pdf_files)
    
    ranked_resumes = run_retrieval(mode=mode, vector_store=vectorstore, jd=jd)
    
    return {
        "ranked": ranked_resumes,
        "rejected": rejected_resume
    }