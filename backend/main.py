from fastapi import FastAPI
from pydantic import BaseModel

# Initialize the FastAPI app
app = FastAPI(title="My Agent API")

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
