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
- LLM pipeline: LangChain + Google Gemini (gemini-2.5-flash) with structured output parsing.

## Diagrams
workflow
```mermaid
graph TB
    Start([User Starts])
    
    subgraph "FLOW 1: PDF-Based CGPA Calculation"
        Upload[Upload PDF]
        Extract[Extract Text from PDF]
        Parse[AI Extracts:<br/>Courses, Grades, Credits]
        InferMap[AI Infers:<br/>Grade Point Mapping]
        Calc1[Calculate CGPA]
        Display1[Display Result +<br/>Grade Point Map]
        Decision1{Grade Point<br/>Map Correct?}
        CorrectMap[User Corrects<br/>Grade Point Map]
        Recalc1[Recalculate with<br/>Corrected Map]
    end
    
    subgraph "FLOW 2: Course Modification"
        ModifyStart[User Wants to<br/>Modify Grades]
        EnterChanges[Enter Course Code<br/>+ New Grade]
        CheckExists{Course<br/>Exists?}
        UpdateGrade[Update Grade<br/>for Course]
        AddCourse[Add New Course<br/>with Grade & Credits]
        Recalc2[Recalculate CGPA]
        ShowComparison[Show Before/After<br/>Comparison]
    end
    
    subgraph "FLOW 3: Manual Entry"
        ManualStart[Manual Entry Mode]
        EnterData[Enter Courses:<br/>Code, Grade, Credits]
        EnterMap[Enter Grade<br/>Point Map]
        Validate[Validate Input<br/>Completeness]
        Calc3[Calculate CGPA]
        Display3[Display Result]
    end
    
    subgraph "Error Handling"
        Error[Validation Error<br/>Detected]
        ErrorType{Error Type?}
        MapError[Grade Point<br/>Map Issue]
        DataError[Course Data<br/>Issue]
        UserFix[User Corrects<br/>Error]
    end
    
    %% Flow 1 connections
    Start --> Upload
    Upload --> Extract
    Extract --> Parse
    Parse --> InferMap
    InferMap --> Calc1
    Calc1 --> Display1
    Display1 --> Decision1
    Decision1 -->|No| CorrectMap
    CorrectMap --> Recalc1
    Recalc1 --> Display1
    Decision1 -->|Yes| ModifyStart
    
    %% Flow 2 connections
    ModifyStart --> EnterChanges
    EnterChanges --> CheckExists
    CheckExists -->|Yes| UpdateGrade
    CheckExists -->|No| AddCourse
    UpdateGrade --> Recalc2
    AddCourse --> Recalc2
    Recalc2 --> ShowComparison
    ShowComparison --> ModifyStart
    
    %% Flow 3 connections
    Start --> ManualStart
    ManualStart --> EnterData
    EnterData --> EnterMap
    EnterMap --> Validate
    Validate --> Calc3
    Calc3 --> Display3
    
    %% Error handling connections
    Parse -.->|Error| Error
    InferMap -.->|Error| Error
    Calc1 -.->|Error| Error
    Validate -.->|Error| Error
    
    Error --> ErrorType
    ErrorType -->|Map Issue| MapError
    ErrorType -->|Data Issue| DataError
    MapError --> UserFix
    DataError --> UserFix
    UserFix --> CorrectMap
    
    %% Exit points
    ShowComparison --> End([End])
    Display3 --> End
    
    %% Styling
    classDef startEnd fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    classDef flow1 fill:#4caf50,stroke:#1976d2,stroke-width:2px
    classDef flow2 fill:#4caf50,stroke:#f57c00,stroke-width:2px
    classDef flow3 fill:#4caf50,stroke:#7b1fa2,stroke-width:2px
    classDef decision fill:#4caf50,stroke:#c62828,stroke-width:2px
    classDef error fill:#4caf50,stroke:#b71c1c,stroke-width:2px
    
    class Start,End startEnd
    class Upload,Extract,Parse,InferMap,Calc1,Display1,CorrectMap,Recalc1 flow1
    class ModifyStart,EnterChanges,UpdateGrade,AddCourse,Recalc2,ShowComparison flow2
    class ManualStart,EnterData,EnterMap,Validate,Calc3,Display3 flow3
    class Decision1,CheckExists,ErrorType decision
    class Error,MapError,DataError,UserFix error
```
Architecture-
```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[Web/Mobile Interface]
        FileUpload[PDF Upload]
        Verify[Verification Interface]
        Modify[Course Modification Interface]
        Manual[Manual Entry Interface]
    end

    subgraph "API Gateway Layer"
        API1[API 1: PDF Upload & Calculate]
        API2[API 2: Correct Grade Map]
        API3[API 3: Modify Courses]
        API4[API 4: Manual Calculator]
        API5[API 5: Validation Check]
    end

    subgraph "PDF Processing Service"
        PDFExtract[PDF Text Extractor]
        TextStore[Store Raw Text]
    end

    subgraph "AI Extraction & Validation Service"
        LLM1[LLM 1: Extract Courses<br/>Code, Name, Grade, Credits]
        UniqueGrades[Function: Create<br/>Unique Grade Set]
        LLM2[LLM 2: Infer<br/>Grade Point Map]
        ConfScore[Calculate<br/>Confidence Score]
    end

    subgraph "Validation Engine"
        V1[Validate Course Data<br/>Completeness]
        V2[Validate Grade Point Map<br/>Consistency & Coverage]
        V3[Pre-Calculation<br/>Validation]
        ErrorDetect[Error Type Detection<br/>Map vs Data Issue]
    end

    subgraph "CGPA Calculation Engine"
        CalcCore[Core Calculator<br/>CGPA Formula]
        Breakdown[Generate Course-wise<br/>Breakdown]
        Comparison[Before/After<br/>Comparison Generator]
    end

    subgraph "Data Storage Layer"
        SessionDB[(Session Store<br/>- Session ID<br/>- PDF Reference<br/>- Raw Text<br/>- Status)]
        CourseDB[(Course Data<br/>- Course Code<br/>- Grade<br/>- Credits)]
        MapDB[(Grade Point Maps<br/>- AI Inferred<br/>- User Corrected)]
        CalcDB[(Calculation History<br/>- CGPA Values<br/>- Timestamps)]
    end

    subgraph "User Correction Service"
        MapEditor[Grade Point Map<br/>Editor]
        CourseEditor[Course Grade<br/>Editor]
        MapValidator[Validate User<br/>Corrections]
    end

    %% Flow 1: PDF Upload and Initial Calculation
    UI --> FileUpload
    FileUpload --> API1
    API1 --> PDFExtract
    PDFExtract --> TextStore
    TextStore --> LLM1
    LLM1 --> UniqueGrades
    UniqueGrades --> LLM2
    LLM2 --> ConfScore
    
    LLM1 --> SessionDB
    LLM1 --> CourseDB
    LLM2 --> MapDB
    ConfScore --> MapDB

    %% Validation Flow
    LLM1 --> V1
    LLM2 --> V2
    V1 --> V3
    V2 --> V3
    CourseDB --> V3
    MapDB --> V3
    
    V3 --> ErrorDetect
    ErrorDetect -.->|Grade Map Issue| API5
    ErrorDetect -.->|Data Issue| API5

    %% Calculation Flow
    V3 --> CalcCore
    CourseDB --> CalcCore
    MapDB --> CalcCore
    CalcCore --> Breakdown
    Breakdown --> CalcDB
    CalcCore --> UI

    %% User Verification Branch
    UI --> Verify
    Verify -->|Map Incorrect| API2
    Verify -->|Map Correct, Modify Courses| API3

    %% Flow 2: Grade Point Map Correction
    API2 --> MapEditor
    MapEditor --> MapValidator
    MapValidator --> MapDB
    MapValidator --> CalcCore

    %% Flow 3: Course Modification
    API3 --> CourseEditor
    CourseEditor -->|Check if Exists| CourseDB
    CourseEditor -->|Update/Add| CourseDB
    CourseEditor --> CalcCore
    CalcCore --> Comparison

    %% Flow 4: Manual Entry
    Manual --> API4
    API4 --> CourseDB
    API4 --> MapDB
    API4 --> V3

    %% Validation Check API
    API5 --> ErrorDetect
    ErrorDetect --> UI

    %% Feedback loops
    CalcDB -.-> Comparison
    Comparison --> UI

    %% Styling
    classDef uiStyle fill:#4caf50,stroke:#01579b,stroke-width:2px
    classDef apiStyle fill:#4caf50,stroke:#e65100,stroke-width:2px
    classDef processStyle fill:#4caf50,stroke:#4a148c,stroke-width:2px
    classDef aiStyle fill:#4caf50,stroke:#1b5e20,stroke-width:2px
    classDef dbStyle fill:#4caf50,stroke:#880e4f,stroke-width:2px
    classDef calcStyle fill:#4caf50,stroke:#f57f17,stroke-width:2px
    classDef validateStyle fill:#4caf50,stroke:#b71c1c,stroke-width:2px

    class UI,FileUpload,Verify,Modify,Manual uiStyle
    class API1,API2,API3,API4,API5 apiStyle
    class PDFExtract,TextStore processStyle
    class LLM1,LLM2,UniqueGrades,ConfScore aiStyle
    class SessionDB,CourseDB,MapDB,CalcDB dbStyle
    class CalcCore,Breakdown,Comparison calcStyle
    class V1,V2,V3,ErrorDetect,MapValidator validateStyle
    class MapEditor,CourseEditor processStyle
```
dataflow -
```mermaid
graph LR
    subgraph "Client Layer"
        Client[Web/Mobile Client]
    end
    
    subgraph "API Layer"
        direction TB
        API1["API 1<br/>POST /pdf/calculate<br/>Input: PDF File<br/>Output: CGPA + Grade Map"]
        API2["API 2<br/>PUT /session/{id}/grade-map<br/>Input: Corrected Map<br/>Output: Updated CGPA"]
        API3["API 3<br/>PUT /session/{id}/courses<br/>Input: Course Changes<br/>Output: Updated CGPA"]
        API4["API 4<br/>POST /calculate/manual<br/>Input: Courses + Map<br/>Output: CGPA"]
        API5["API 5<br/>GET /session/{id}/validate<br/>Output: Validation Report"]
    end
    
    subgraph "Service Layer"
        direction TB
        PDFService[PDF Processing<br/>Service]
        AIService[AI Extraction<br/>Service]
        CalcService[Calculation<br/>Service]
        ValidationService[Validation<br/>Service]
    end
    
    subgraph "Data Layer"
        direction TB
        SessionData[("Session<br/>Storage")]
        CourseData[("Course<br/>Storage")]
        MapData[("Grade Map<br/>Storage")]
        CalcHistory[("Calculation<br/>History")]
    end
    
    %% Client to API connections
    Client -->|1. Upload PDF| API1
    Client -->|2. Correct Map| API2
    Client -->|3. Modify Courses| API3
    Client -->|4. Manual Entry| API4
    Client -->|5. Check Validation| API5
    
    %% API 1 Flow
    API1 --> PDFService
    PDFService --> AIService
    AIService --> ValidationService
    ValidationService --> CalcService
    
    %% API 2 Flow
    API2 --> ValidationService
    API2 --> CalcService
    
    %% API 3 Flow
    API3 --> ValidationService
    API3 --> CalcService
    
    %% API 4 Flow
    API4 --> ValidationService
    API4 --> CalcService
    
    %% API 5 Flow
    API5 --> ValidationService
    
    %% Service to Data connections
    PDFService <--> SessionData
    AIService <--> CourseData
    AIService <--> MapData
    CalcService <--> CourseData
    CalcService <--> MapData
    CalcService <--> CalcHistory
    ValidationService <--> CourseData
    ValidationService <--> MapData
    
    %% Response flows
    CalcService -.->|Response| API1
    CalcService -.->|Response| API2
    CalcService -.->|Response| API3
    CalcService -.->|Response| API4
    ValidationService -.->|Response| API5
    
    API1 -.->|Response| Client
    API2 -.->|Response| Client
    API3 -.->|Response| Client
    API4 -.->|Response| Client
    API5 -.->|Response| Client
    
    %% Styling
    classDef clientStyle fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    classDef apiStyle fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    classDef serviceStyle fill:#ff9800,stroke:#e65100,stroke-width:2px
    classDef dataStyle fill:#9c27b0,stroke:#4a148c,stroke-width:2px,color:#fff
    
    class Client clientStyle
    class API1,API2,API3,API4,API5 apiStyle
    class PDFService,AIService,CalcService,ValidationService serviceStyle
    class SessionData,CourseData,MapData,CalcHistory dataStyle
```

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


## Quick start

Prereqs: Python 3.13

Backend (PowerShell)
```
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
$env:GOOGLE_GEMINI_API = "your-api-key"
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
# backend_url = "you url"

streamlit run main.py
```


## CGPA calculation

- Weighted average of grade points by credits
- Result rounded to 2 decimals
