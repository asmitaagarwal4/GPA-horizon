# GPA Horizon

An intelligent assistant for parsing grade transcripts, validating CGPA, and conducting what‑if analyses. It is especially useful for CGPA forecasting, evaluating grade‑improvement exam options, and informing broader academic decisions. Institution‑agnostic by design, it works with any university via a customizable grade‑to‑point map.

## Major features

1) Upload a grade transcript PDF and calculate CGPA automatically
- Frontend lets you upload a PDF transcript.
- Backend extracts courses, credits, and grades and computes CGPA.

2) Custom grade-to-point map (works with any college scheme)
- Edit the grade-to-point mapping (e.g., A+=10, A=9, …) to match your institution.
- Validate the extracted CGPA against your custom map.

3) Add, try, and change course grades to recalculate CGPA
- Add new courses one at a time (code, credits, grade).
- Edit visible course rows and instantly recalculate CGPA.
- Search and paginate through extracted courses.

## How it works

- Streamlit frontend uploads the PDF and calls FastAPI endpoints.
- The backend uses a LangChain pipeline (Google Gemini via langchain-google-genai) to extract structured data from the PDF, or
- A validation utility computes weighted CGPA from courses and the current grade map and compares it to the extracted CGPA.

## Tech stack and tools

- Frontend: Streamlit (Python), requests, session state, pagination UI.
- Backend: FastAPI, Uvicorn, Pydantic v2 models, CORS.
- PDF handling: PyMuPDF (fitz) when using the LLM extraction.
- LLM pipeline: LangChain + Google Gemini (gemini-1.5-flash) with structured output parsing.

### LangChain focus

The pipeline (create_full_chain) prompts Gemini to:
- Read the transcript text
- Extract a list of courses (course_code, grade, credits)
- Propose/normalize a grade-to-point map
- Provide an extracted CGPA

The app then:
- Computes CGPA from the extracted courses and map
- Validates against the extracted CGPA
- Surfaces any mismatch and lets you correct the map or course data

In development, set USE_MOCK=true to skip the LLM and use deterministic sample data.

## API endpoints

- POST /process-gradesheet/
	- Body: multipart/form-data with file (PDF)
	- Response: { status, message, extracted_cgpa, calculated_cgpa, grade_point_map, extracted_courses }

- POST /validate-grade-point-map/
	- Body (JSON): { grade_map: Dict[str, float], courses: List[Course], extracted_cgpa?: number }
	- Response: { status, message, calculated_cgpa, extracted_cgpa }

- GET /recalculate-cgpa/
	- Body (JSON): { grade_map: Dict[str, float], courses: List[Course] }
	- Response: { calculated_cgpa }
	- Note: Uses a GET with JSON body for simplicity; may change to POST later.

## Quick start

Prereqs: Python 3.11+

Backend (PowerShell)
```
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
# Optional: use mock to avoid LLM costs
$env:USE_MOCK = "true"
uvicorn main:app --reload
```

Frontend (PowerShell)
```
cd frontend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

# Configure Streamlit secret for backend base URL
# .streamlit/secrets.toml
# [api]
# backend_url = "http://127.0.0.1:8000"

streamlit run main.py
```

To use Gemini extraction (optional):
- Set GOOGLE_API_KEY in the backend environment
- Ensure quotas are available (429 errors indicate rate limits)

## CGPA calculation

- Weighted average of grade points by credits
- Requires that each course’s grade exists in the grade-to-point map
- Result rounded to 2 decimals

## Notes

- PDF quality matters; text-based PDFs work best.
- USE_MOCK provides a consistent 26-course sample for local testing.
- If you hit Gemini rate limits (429), switch USE_MOCK on or add billing/quota.
