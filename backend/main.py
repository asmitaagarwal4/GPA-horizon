from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Initialize the FastAPI app
app = FastAPI(title="My Agent API")

origins = [
    # In production, you would restrict this to your Streamlit app's domain
    "https://your-streamlit-app-name.streamlit.app",
    "*" # For development, the wildcard allows all origins.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# Define the data model for the incoming request using Pydantic
# This ensures the data sent from Streamlit is in the correct format
class QueryRequest(BaseModel):
    name: str

# Define a simple endpoint at the URL path "/greet"
# It only accepts POST requests
@app.post("/greet")
async def greet_user(request: QueryRequest):
    """
    Receives a name and returns a personalized greeting.
    This is where your LangChain agent logic would go.
    """
    user_name = request.name
    
    # In a real app, you would call your LangChain agent here:
    # response_text = agent.run(user_name)
    
    # For this example, we'll just create a simple greeting
    response_text = f"Hello, {user_name}! It's great to see you. This response came from the FastAPI backend."
    
    return {"message": response_text}
