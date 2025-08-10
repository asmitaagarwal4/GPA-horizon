# app.py
import streamlit as st
import pymupdf as fitz
import os
from typing import List, Optional, Dict

# --- LangChain Core Components ---
# --- UPDATED: Import for Google Gemini model ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableBranch

# --- Pydantic Models for Structured Output ---
from pydantic import BaseModel, Field

# --- Environment & Setup ---
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
        # NOTE: For this demo, we'll read the .txt file, but the logic is for PDFs.
        if pdf_path.endswith(".txt"):
             with open(pdf_path, 'r') as f:
                return f.read()
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        return f"Error reading file: {e}"

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

# --- UPDATED: Initialize Gemini LLM ---
# The model is switched to a Gemini model.
# Make sure your GOOGLE_API_KEY is set in your .env file.
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
    - Standard 'letter' grades are S=10, A=9, B=8, C=7, D=6, E=5, F=0.
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
    "message": f"Validation failed. The CGPA calculated from the grades ({x['validation_result']['calculated_cgpa']}) does not match the CGPA found in the document ({x['extracted_info'].extracted_cgpa}). Please provide the correct grade-to-point dictionary (e.g., {{'S': 10, 'A': 9, ...}}).",
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

# --- 5. Streamlit UI ---
st.set_page_config(layout="wide")
st.title("⚙️ Conditional CGPA Validation Pipeline (using Gemini)")

# Create a dummy PDF for demonstration
os.makedirs("temp", exist_ok=True)
dummy_pdf_path = "temp/sample_grades.txt" # Using .txt for simplicity, but logic is for PDF
with open(dummy_pdf_path, "w") as f:
    f.write("""
    Student Grade Report
    Course Code: CS101, Grade: A, Credits: 3
    Course Code: MTH203, Grade: S, Credits: 4
    Course Code: PHY102, Grade: B, Credits: 3
    Final CGPA: 9.10
    """)

st.info("This demo uses a pre-made text file to simulate a PDF.")

if st.button("Process Grade Sheet"):
    # --- UPDATED: Check for Google API Key ---
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not found. Please set it in your .env file.")
    else:
        with st.spinner("Running the full conditional chain with Gemini..."):
            try:
                # We invoke the full chain with the file path.
                result = full_chain.invoke(dummy_pdf_path)
                
                st.subheader("Final Result")
                if result['status'] == "SUCCESS":
                    st.success(result['message'])
                    st.metric("Validated CGPA", f"{result['calculated_cgpa']:.2f}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("Extracted Courses:")
                        st.json(result['extracted_courses'])
                    with col2:
                        st.write("Determined Grade Point Map:")
                        st.json(result['grade_point_map'])
                else:
                    st.error(result['message'])
                    st.warning(f"Reason: {result['reason']}")

            except Exception as e:
                st.error(f"A critical error occurred in the pipeline: {e}")

