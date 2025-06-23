from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.pipeline import process_file_pipeline

app = FastAPI()

class FileShareRequest(BaseModel):
    directory_path: str  # local mount or SMB path

@app.post("/process/")
async def process_documents(req: FileShareRequest):
    try:
        results = process_file_pipeline(req.directory_path)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.pipeline import process_file_pipeline

app = FastAPI()
jobs = {}  # In-memory job tracking (for now)

class FileShareRequest(BaseModel):
    job_id: str
    directory_path: str

@app.post("/process/")
async def process_documents(req: FileShareRequest, background_tasks: BackgroundTasks):
    # Register job as running
    jobs[req.job_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(run_processing_job, req.job_id, req.directory_path)
    return {"message": "Processing started", "job_id": req.job_id}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

def run_processing_job(job_id: str, directory: str):
    try:
        result = process_file_pipeline(directory)
        jobs[job_id] = {"status": "complete", "result": result}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}