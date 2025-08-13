import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from chain import create_full_chain

chain_container = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting up...")
    chain_container["full_chain"] = create_full_chain()
    print("LangChain pipeline created and ready.")
    yield
    print("Server shutting down...")
    chain_container.clear()


# FastAPI Application Setup
app = FastAPI(title="GPA Horizon Backend", lifespan=lifespan)

# CORS Middleware
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/process-gradesheet/")
async def process_gradesheet_endpoint(file: UploadFile = File(...)):
    """
    Receives a PDF file, saves it temporarily, runs the full LangChain pipeline,
    and returns the structured result.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found on the server.")
    if "full_chain" not in chain_container:
        raise HTTPException(status_code=503, detail="Service not ready. The LangChain pipeline is still initializing.")

    temp_filename = f"{uuid.uuid4()}.pdf"
    temp_file_path = os.path.join(TEMP_DIR, temp_filename)

    try:
        with open(temp_file_path, "wb") as f:
            while chunk := await file.read(1024):
                f.write(chunk)

        result = chain_container["full_chain"].invoke(temp_file_path)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred in the pipeline: {str(e)}")

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
