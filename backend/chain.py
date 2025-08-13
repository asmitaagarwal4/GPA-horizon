import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableBranch
from dotenv import load_dotenv

load_dotenv()
# --- IMPORTS from our other files ---
from models import ExtractedGradeInfo, GradePointMap
from utils import read_pdf_content, extract_grades_list, validate_cgpa

# --- Building the LangChain Components ---
# --- EDITED: Explicitly pass the API key to the constructor ---
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Chain 1: Extract Course Info
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

# Chain 2: Determine Grade Point Map
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


def debug_print(label):
    return RunnableLambda(lambda x: print(f"{label}: {x} \n") or x)

# Assembling the Full Workflow
full_chain = (
    {
        "document_text": RunnableLambda(read_pdf_content),
        "format_instructions": lambda x: extract_parser.get_format_instructions(),
    } | RunnableLambda(
        lambda x: {"extracted_info": chain_one.invoke(x)}
    ) | RunnablePassthrough.assign(
        grades_list= lambda x: extract_grades_list(x['extracted_info'])
    ) | RunnablePassthrough.assign(
        grade_map=({"grades_list": lambda x: x['grades_list'], "format_instructions": lambda x: map_parser.get_format_instructions()}) | chain_two
    ) | RunnablePassthrough.assign(
        validation_result=RunnableLambda(validate_cgpa)
    ) | RunnableLambda(
        lambda x: {
            "status": x['validation_result']['is_correct'] , 
            "message": x['validation_result']['reason'] , 
            "extracted_courses": x['extracted_info'].model_dump(),
            "grade_point_map": x['grade_map'].model_dump(),
            "calculated_cgpa": x['validation_result']['calculated_cgpa'],
            "extracted_cgpa": x['validation_result']['extracted_cgpa']
        } 
    )
)



# result = full_chain.invoke("W:/codes/GPA-horizon/backend/temp_upload/pdf1.pdf")
# print(result)