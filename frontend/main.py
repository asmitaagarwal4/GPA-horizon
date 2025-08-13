import streamlit as st
import requests
import os


st.set_page_config(
    page_title="GPA Horizon",
    page_icon="🎓",
    layout="centered"
)

BASE_URL = st.secrets["api"]["backend_url"]
BACKEND_URL = f"{BASE_URL}/process-gradesheet/"

# --- UI Components ---
st.title("🎓 GPA Horizon: Your AI Academic Advisor")
st.write(
    "Upload your grade sheet in PDF format. "
    "The AI-powered backend will analyze the document, extract your courses, "
    "and prepare the data for CGPA calculation."
)

# Add a check to inform the user if the secret is missing (useful for deployment)
if "backend_url" not in st.secrets["api"]:
    st.warning("Warning: BACKEND_URL secret not found. The app is currently configured to connect to a local backend. Please set the secret in your Streamlit Cloud settings for deployed apps.")

# File uploader widget
uploaded_file = st.file_uploader(
    "Choose your grade sheet PDF",
    type="pdf",
    help="Please upload a text-based PDF for the best results."
)

# --- Logic to handle the file upload and API call ---
if uploaded_file is not None:
    if st.button("Analyze Grade Sheet"):
        with st.spinner("Uploading file and processing with the AI... Please wait."):
            try:
                # --- Prepare the file for the POST request ---
                # The 'files' parameter in requests expects a dictionary where the key ('file')
                # matches the parameter name in your FastAPI endpoint (def process_gradesheet(file: UploadFile = File(...)))
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")
                }

                # --- Make the API call to the backend ---
                response = requests.post(BACKEND_URL, files=files, timeout=300) # 5 minute timeout

                # --- Handle the response from the backend ---
                if response.status_code == 200:
                    st.success("✅ Analysis Complete!")
                    
                    # The backend should return a JSON object. We display it.
                    json_response = response.json()
                    
                    st.subheader("Extracted Information:")
                    st.json(json_response)
                    
                    # You can also access specific parts of the JSON
                    if json_response.get("status") == True:
                        st.metric("Validated CGPA", f"{json_response.get('calculated_cgpa', 'N/A'):.2f}")
                        st.write("Courses Found:")
                        st.dataframe(json_response.get('extracted_courses', []))

                else:
                    # Show an error if the backend returned a non-200 status code
                    st.error(f"API Error: Status Code {response.status_code}")
                    try:
                        # Try to display the error detail from the backend's JSON response
                        st.json(response.json())
                    except requests.exceptions.JSONDecodeError:
                        # If the response is not JSON, display the raw text
                        st.text(response.text)

            except requests.exceptions.RequestException as e:
                # Handle network-related errors (e.g., connection timeout)
                st.error(f"A network error occurred: {e}")
                st.info("Please check your internet connection and ensure the backend server is running.")

