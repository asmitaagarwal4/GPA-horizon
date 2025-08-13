import pymupdf as fitz
from typing import List, Dict
# --- IMPORT ---
# We import the Pydantic models we defined in models.py
from models import ExtractedGradeInfo

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
    # (This function's code remains the same as before)
    extracted_info = data['extracted_info']
    grade_map = data['grade_map'].grade_to_point
    if extracted_info.extracted_cgpa is not None:
        extracted_cgpa = extracted_info.extracted_cgpa
    else:
        extracted_cgpa = None

    total_points = 0
    total_credits = 0
    
    for course in extracted_info.courses:
        if course.credits is None:
            return {"is_correct": False, "reason": "Missing credit information for one or more courses.", "calculated_cgpa": None, "extracted_cgpa": extracted_cgpa}

        grade_point = grade_map.get(course.grade.upper())
        if grade_point is None:
            return {"is_correct": False, "reason": f"Grade '{course.grade}' not found in the provided grade map.", "calculated_cgpa": None, "extracted_cgpa": extracted_cgpa}

        if grade_point < 0:
            continue

        total_points += grade_point * course.credits
        total_credits += course.credits
        
    if total_credits == 0:
        return {"is_correct": False, "reason": "Total credits are zero.", "calculated_cgpa": 0, "extracted_cgpa": extracted_cgpa}
        
    calculated_cgpa = round(total_points / total_credits, 2)
    
    if extracted_cgpa is None:
        return {"is_correct": True, "reason": "No CGPA found in PDF to compare against.", "calculated_cgpa": calculated_cgpa, "extracted_cgpa": extracted_cgpa}

    is_correct = abs(calculated_cgpa - extracted_cgpa) == 0.00

    return {"is_correct": is_correct, "reason": "Validation complete.", "calculated_cgpa": calculated_cgpa, "extracted_cgpa": extracted_cgpa}
