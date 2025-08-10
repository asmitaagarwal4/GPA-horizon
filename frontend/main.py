import streamlit as st
import requests  


st.set_page_config(
    page_title="API Caller",
    page_icon="🤖",
    layout="centered"
)


st.title("Streamlit Frontend for FastAPI")
st.write("This app sends a request to a FastAPI backend.")

FASTAPI_BACKEND_URL = st.secrets["api"]["backend_url"]

# --- User Input ---
st.subheader("Send a Name to the Backend")
user_name = st.text_input("Enter your name:", "World")

# --- Button to Trigger API Call ---
if st.button("Send to Backend"):
    if user_name:
        # Display a spinner while waiting for the API response
        with st.spinner("Calling API..."):
            try:
                # --- The API Call ---
                # We send a POST request to the backend URL.
                # The `json` parameter contains the data we want to send,
                # matching the Pydantic model in FastAPI.
                response = requests.post(
                    FASTAPI_BACKEND_URL, 
                    json={"name": user_name}
                )

                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    # Parse the JSON response from the backend
                    backend_response = response.json()
                    message = backend_response.get("message")
                    
                    st.success("API Call Successful!")
                    st.write(message)
                else:
                    # Show an error if the request failed
                    st.error(f"API Error: Status Code {response.status_code}")
                    st.write(response.text)

            except requests.exceptions.ConnectionError as e:
                st.error("Connection Error: Could not connect to the FastAPI backend.")
                st.write("Please make sure the backend server is running.")
    else:
        st.warning("Please enter a name.")

