from pydantic import BaseModel, Field
from typing import List, Optional, Dict

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
