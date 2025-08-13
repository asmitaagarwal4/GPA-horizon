import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
from models import Course, ExtractedGradeInfo, GradePointMap
from utils import validate_cgpa

load_dotenv()
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

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
    if USE_MOCK:
        _ = await file.read()  # consume upload
        mock = {
            "status": False,
            "message": "CGPA validated",
            "extracted_courses": {
                "courses": [
                    {"course_code": "CS101", "grade": "A",  "credits": 4},
                    {"course_code": "MA102", "grade": "B+", "credits": 3},
                    {"course_code": "PH103", "grade": "A-", "credits": 3},
                    {"course_code": "HS104", "grade": "B",  "credits": 2},
                    {"course_code": "CS105", "grade": "A",  "credits": 4},
                    {"course_code": "EE106", "grade": "B+", "credits": 3},
                    {"course_code": "ME107", "grade": "B",  "credits": 3},
                    {"course_code": "CS201", "grade": "A-", "credits": 4},
                    {"course_code": "MA202", "grade": "A",  "credits": 3},
                    {"course_code": "CS203", "grade": "B+", "credits": 4},
                    {"course_code": "CS204", "grade": "B",  "credits": 3},
                    {"course_code": "EC205", "grade": "A-", "credits": 3},
                    {"course_code": "CS206", "grade": "A",  "credits": 4},
                    {"course_code": "CS207", "grade": "B+", "credits": 3},
                    {"course_code": "CS208", "grade": "A",  "credits": 4},
                    {"course_code": "DS209", "grade": "A-", "credits": 3},
                    {"course_code": "AI210", "grade": "A",  "credits": 3},
                    {"course_code": "CS301", "grade": "B",  "credits": 4},
                    {"course_code": "CS302", "grade": "A-", "credits": 3},
                    {"course_code": "CS303", "grade": "B+", "credits": 3},
                    {"course_code": "CS304", "grade": "A",  "credits": 4},
                    {"course_code": "CS305", "grade": "B",  "credits": 3},
                    {"course_code": "CS306", "grade": "A-", "credits": 4},
                    {"course_code": "CS307", "grade": "A",  "credits": 3},
                    {"course_code": "CS308", "grade": "B+", "credits": 3},
                    {"course_code": "PR309", "grade": "A",  "credits": 2}
                ]
            },
            "grade_point_map": {
                "grade_to_point": {
                    "A": 10.0,
                    "A-": 9.0,
                    "B+": 8.0,
                    "B": 7.0
                }
            },
            "calculated_cgpa": 8.92,
            "extracted_cgpa": 8.96
        }
        return JSONResponse(content=mock)
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

@app.post("/validate-grade-point-map/")
async def validate_grade_point_map_endpoint(
    grade_map: Dict[str, float] = Body(...),
    courses: List[Course] = Body(...),
    extracted_cgpa: Optional[float] = Body(None),
):
    """
    Validates the provided grade point map with the course and extracted cgpa to get the correct calculated cgpa
    """
    if not grade_map:
        raise HTTPException(status_code=400, detail="Grade point map cannot be empty.")
    if courses is None or len(courses) == 0:
        raise HTTPException(status_code=400, detail="Courses list cannot be empty.")

    # Build Pydantic models expected by utils.validate_cgpa
    extracted_info = ExtractedGradeInfo(courses=courses, extracted_cgpa=extracted_cgpa)
    grade_map_model = GradePointMap(grade_to_point=grade_map)

    result = validate_cgpa({
        "extracted_info": extracted_info,
        "grade_map": grade_map_model,
    })

    return {
        "status": bool(result.get("is_correct", False)),
        "message": result.get("reason", "Validation complete."),
        "calculated_cgpa": result.get("calculated_cgpa"),
        "extracted_cgpa": result.get("extracted_cgpa"),
    }

@app.get("/recalculate-cgpa/")
async def recalculate_cgpa_endpoint(    grade_map: Dict[str, float] = Body(...),
    courses: List[Course] = Body(...)):
   """
   takes the grade point map and course list to return newly calculated cgpa
   """
   # Basic validations
   if not grade_map:
       raise HTTPException(status_code=400, detail="Grade point map cannot be empty.")
   if courses is None or len(courses) == 0:
       raise HTTPException(status_code=400, detail="Courses list cannot be empty.")

   # Ensure all grades are present in the provided map
   missing_grades = sorted({c.grade for c in courses if c.grade not in grade_map})
   if missing_grades:
       raise HTTPException(
           status_code=400,
           detail=f"Grade(s) missing in grade_map: {', '.join(missing_grades)}",
       )

   total_credits = sum(c.credits for c in courses)
   if total_credits <= 0:
       raise HTTPException(status_code=400, detail="Total credits must be greater than zero.")

   weighted_sum = sum(grade_map[c.grade] * c.credits for c in courses)
   calculated_cgpa = round(weighted_sum / total_credits, 2)

   return {"calculated_cgpa": calculated_cgpa}


    
    