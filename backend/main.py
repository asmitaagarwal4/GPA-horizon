# import streamlit as st # This is a placeholder, not needed in FastAPI
import os
import uuid
from typing import List, Optional, Dict

# --- FastAPI Imports ---
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- LangChain Core Components ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableBranch

# --- Pydantic Models for Structured Output ---
from pydantic import BaseModel, Field

# --- PDF Parsing and Environment Setup ---
import pymupdf as fitz # Use pymupdf as fitz
from dotenv import load_dotenv
load_dotenv()

# --- 1. Pydantic Models (Defining our Data Structures) ---


class Course(BaseModel):
    """A model for a single extracted course."""
    course_code: str = Field(description="The official code of the course, e.g., 'CS101'.")
    grade: str = Field(description="The grade received for the course, e.g., 'A+', 'S'.")
    credits: Optional[int] = Field(description="The credits for the course. If not found, this must be null.")

class ExtractedGradeInfo(BaseModel):
    """The structured data extracted from the grade sheet by the first LLM call."""
    courses: List[Course] = Field(description="A list of all courses extracted from the document.")
    extracted_cgpa: Optional[float] = Field(description="The final CGPA value found in the document. If not found, this must be null.")

class GradePointMap(BaseModel):
    """A dictionary mapping each unique grade to its numeric point value."""
    grade_to_point: Dict[str, float] = Field(description="A dictionary mapping string grades to their float point values, e.g., {'S': 10.0, 'A': 9.0}.")

# --- 2. Helper Functions (Our Custom Logic) ---

def read_pdf_content(pdf_path: str) -> str:
    """Reads and returns the text content of a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_grades_list(extracted_info: ExtractedGradeInfo) -> List[str]:
    """Extracts a unique list of grades from the course data."""
    return list(set(course.grade for course in extracted_info.courses))

def validate_cgpa(data: Dict) -> Dict:
    """Calculates CGPA and validates it against the extracted value."""
    extracted_info = data['extracted_info']
    grade_map = data['grade_map'].grade_to_point
    
    total_points = 0
    total_credits = 0
    
    for course in extracted_info.courses:
        if course.credits is None:
            return {"is_correct": False, "reason": "Missing credit information for one or more courses.", "calculated_cgpa": None}
        
        grade_point = grade_map.get(course.grade.upper())
        if grade_point is None:
            return {"is_correct": False, "reason": f"Grade '{course.grade}' not found in the provided grade map.", "calculated_cgpa": None}

        if grade_point < 0:
            continue
            
        total_points += grade_point * course.credits
        total_credits += course.credits
        
    if total_credits == 0:
        return {"is_correct": False, "reason": "Total credits are zero.", "calculated_cgpa": 0}
        
    calculated_cgpa = round(total_points / total_credits, 2)
    
    if extracted_info.extracted_cgpa is None:
        return {"is_correct": True, "reason": "No CGPA found in PDF to compare against.", "calculated_cgpa": calculated_cgpa}

    is_correct = abs(calculated_cgpa - extracted_info.extracted_cgpa) < 0.05
    
    return {"is_correct": is_correct, "reason": "Validation complete.", "calculated_cgpa": calculated_cgpa}

# --- 3. Building the LangChain Components ---

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

# --- Chain 1: Extract Course Info from PDF Text ---
extract_parser = PydanticOutputParser(pydantic_object=ExtractedGradeInfo)
extract_prompt = ChatPromptTemplate.from_template(
    """
    You are an expert data extraction system. From the provided grade sheet text, extract all course codes, grades, credits, and the final CGPA.
    - If credits are missing for a course, the 'credits' field must be null.
    - If the final CGPA is not found, the 'extracted_cgpa' field must be null.
    - Strictly adhere to the JSON format instructions.

    {format_instructions}

    DOCUMENT_TEXT:
    ```{document_text}```
    """
)
chain_one = extract_prompt | llm | extract_parser

# --- Chain 2: Determine Grade Point Map from a List of Grades ---
map_parser = PydanticOutputParser(pydantic_object=GradePointMap)
map_prompt = ChatPromptTemplate.from_template(
    """
    You are an expert academic system. Based on this list of unique grades, create a JSON dictionary mapping each grade to its standard 10-point scale value.
    - Standard 'letter' grades are S=10, A=9, B=8, C=7, D=6, E=5, F=0 , P=-1.
    - Standard 'plus/minus' grades are A+=10, A=9, A-=8.5, B+=8, B=7.5, B-=7, C+=6.5, C=6, F=0.
    - Infer which system is being used.

    {format_instructions}

    GRADES_LIST:
    {grades_list}
    """
)
chain_two = map_prompt | llm | map_parser

# --- Conditional Chains for the Final Step ---
success_chain = RunnableLambda(lambda x: {
    "status": "SUCCESS",
    "message": "Validation successful! The calculated CGPA matches the one in the document.",
    "calculated_cgpa": x['validation_result']['calculated_cgpa'],
    "extracted_courses": x['extracted_info'].model_dump(),
    "grade_point_map": x['grade_map'].model_dump()
})

failure_chain = RunnableLambda(lambda x: {
    "status": "FAILURE",
    "message": f"Validation failed. The CGPA calculated from the grades ({x['validation_result']['calculated_cgpa']}) does not match the CGPA found in the document ({x['extracted_info'].extracted_cgpa}). Please provide the correct grade-to-point dictionary.",
    "reason": x['validation_result']['reason']
})

# --- 4. Assembling the Full Workflow ---
full_chain = {
    "document_text": RunnableLambda(read_pdf_content),
    "format_instructions": lambda x: extract_parser.get_format_instructions(),
} | RunnablePassthrough.assign(
    extracted_info=chain_one
) | RunnablePassthrough.assign(
    grades_list=lambda x: extract_grades_list(x['extracted_info'])
) | RunnablePassthrough.assign(
    grade_map=({"grades_list": lambda x: x['grades_list'], "format_instructions": lambda x: map_parser.get_format_instructions()}) | chain_two
) | RunnablePassthrough.assign(
    validation_result=RunnableLambda(validate_cgpa)
) | RunnableBranch(
    (lambda x: x['validation_result']['is_correct'], success_chain),
    failure_chain
)

# --- 5. FastAPI Application ---
app = FastAPI(title="GPA Horizon Backend")

# CORS Middleware to allow requests from your Streamlit frontend
origins = ["*"] # In production, you should restrict this to your Streamlit app's domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for temporary file uploads
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/process-gradesheet/")
async def process_gradesheet_endpoint(file: UploadFile = File(...)):
    """
    Receives a PDF file, saves it temporarily, runs the full LangChain pipeline,
    and returns the structured result.
    """
    # Check for Google API Key
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found on the server.")

    temp_filename = f"{uuid.uuid4()}.pdf"
    temp_file_path = os.path.join(TEMP_DIR, temp_filename)

    try:
        # Save the uploaded file to the temporary path
        with open(temp_file_path, "wb") as f:
            while chunk := await file.read(1024):
                f.write(chunk)

        # Invoke the full chain with the path to the saved file
        result = full_chain.invoke(temp_file_path)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred in the pipeline: {str(e)}")

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

