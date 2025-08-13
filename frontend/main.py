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
VALIDATE_URL = f"{BASE_URL}/validate-grade-point-map/"
RECALC_URL = f"{BASE_URL}/recalculate-cgpa/"

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

# Initialize persistent state
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "course_page" not in st.session_state:
    st.session_state.course_page = 0

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
                # ...existing code...
                if response.status_code == 200:
                    json_response = response.json()
                    # Persist results and initialize edit state, then rerun
                    st.session_state.analysis_result = json_response
                    extracted_courses_block = json_response.get("extracted_courses", {})
                    st.session_state.grade_map_edit = json_response.get("grade_point_map", {}).get("grade_to_point", {}).copy()
                    st.session_state.courses_edit = extracted_courses_block.get("courses", []).copy()
                    st.session_state.course_page = 0
                    st.rerun()


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




# --- Render results outside the button so UI persists across reruns ---
if st.session_state.get("analysis_result"):
    json_response = st.session_state.analysis_result
    status = json_response.get("status", False)
    message = "CGPA validated" if status else f"CGPA cannot be validated due to {json_response.get('message', 'unknown error')}. Please check the inputs and try again."
    if status:
        st.success(message)
    else:
        st.error(message)

    # Ensure editable state is present
    if "grade_map_edit" not in st.session_state:
        st.session_state.grade_map_edit = json_response.get("grade_point_map", {}).get("grade_to_point", {}).copy()
    if "courses_edit" not in st.session_state:
        extracted_courses_block = json_response.get("extracted_courses", {})
        st.session_state.courses_edit = extracted_courses_block.get("courses", []).copy()

    grade_map = st.session_state.grade_map_edit
    courses = st.session_state.courses_edit

    # Grade Map
    grade_map_expander = st.expander("Grade Point Map", expanded=(not status))
    with grade_map_expander:
        if status:
            st.caption("Edit the numeric point values. Click 'Save Grade Map' to apply.")
        else:
            st.caption("Input the correct grade to point map and try again.")
        with st.form("grade_map_form", clear_on_submit=False):
            new_values = {}
            cols = st.columns(2)
            i = 0
            for grade, value in grade_map.items():
                col = cols[i % 2]
                with col:
                    new_val = col.text_input(f"{grade}", value=str(value))
                    new_values[grade] = new_val
                i += 1
            if st.form_submit_button("Save Grade Map"):
                cleaned = {}
                for k, v in new_values.items():
                    try:
                        cleaned[k] = float(v)
                    except ValueError:
                        st.warning(f"Invalid number for grade {k}, keeping old value.")
                        cleaned[k] = grade_map[k]
                st.session_state.grade_map_edit = cleaned
                # Call backend to validate with updated grade map and current courses
                try:
                    payload = {
                        "grade_map": cleaned,
                        "courses": st.session_state.courses_edit,
                        "extracted_cgpa": json_response.get("extracted_cgpa"),
                    }
                    resp = requests.post(VALIDATE_URL, json=payload, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Update analysis result and reflect new map
                        st.session_state.analysis_result["status"] = data.get("status", False)
                        st.session_state.analysis_result["message"] = data.get("message")
                        st.session_state.analysis_result["calculated_cgpa"] = data.get("calculated_cgpa")
                        st.session_state.analysis_result["extracted_cgpa"] = data.get("extracted_cgpa")
                        if "grade_point_map" not in st.session_state.analysis_result:
                            st.session_state.analysis_result["grade_point_map"] = {}
                        st.session_state.analysis_result["grade_point_map"]["grade_to_point"] = cleaned
                        st.success("Grade map updated and validation complete.")
                        st.rerun()
                    else:
                        st.error(f"Validation failed: {resp.status_code}")
                        try:
                            st.json(resp.json())
                        except requests.exceptions.JSONDecodeError:
                            st.text(resp.text)
                except requests.exceptions.RequestException as e:
                    st.error(f"Network error contacting backend: {e}")

    # Courses with search + pagination
    courses_expander = st.expander("Extracted Courses", expanded=bool(status))
    with courses_expander:
        st.caption(f"Edit grades for any course and apply changes to see updated cgpa. Or add any courses below:")

        # Add a single course at a time
        grade_options = list(st.session_state.get("grade_map_edit", {}).keys())
        with st.form("add_course_form", clear_on_submit=True):
            ac_cols = st.columns([2, 2, 2, 1])
            with ac_cols[0]:
                ac_code = st.text_input("Course code", key="add_course_code")
            with ac_cols[1]:
                ac_credits = st.number_input("Credits", min_value=0, max_value=50, value=3, step=1, key="add_course_credits")
            with ac_cols[2]:
                if grade_options:
                    ac_grade = st.selectbox("Grade", options=grade_options, key="add_course_grade_select")
                else:
                    ac_grade = st.text_input("Grade", key="add_course_grade_text")
            submitted_add = ac_cols[3].form_submit_button("Add Course")

            if submitted_add:
                if not ac_code:
                    st.warning("Please enter a course code.")
                elif ac_grade is None or str(ac_grade).strip() == "":
                    st.warning("Please select or enter a grade.")
                else:
                    st.session_state.courses_edit.append({
                        "course_code": ac_code,
                        "grade": ac_grade,
                        "credits": int(ac_credits),
                    })
                    # Show the new course row: clear search and go to last page
                    st.session_state.course_search = ""
                    total_after = len(st.session_state.courses_edit)
                    page_size_local = 10
                    st.session_state.course_page = max(0, (total_after - 1) // page_size_local)
                    st.success("Course added. It will be included when you Save Visible Edits.")
                    st.rerun()

        def _reset_course_page():
            st.session_state.course_page = 0

        search = st.text_input(
            "Search (course code or grade):",
            key="course_search",
            on_change=_reset_course_page,
        )
        search_val = st.session_state.get("course_search", "")

        filtered = [
            c for c in courses
            if search_val.lower() in c.get("course_code", "").lower()
            or search_val.lower() in c.get("grade", "").lower()
        ] if search_val else courses

        page_size = 10
        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        st.session_state.course_page = max(0, min(st.session_state.course_page, total_pages - 1))

        top_cols = st.columns([1, 1, 6, 1, 1])
        with top_cols[0]:
            if st.button("⏮", disabled=st.session_state.course_page == 0):
                st.session_state.course_page = 0
                st.rerun()
        with top_cols[1]:
            if st.button("◀", disabled=st.session_state.course_page == 0):
                st.session_state.course_page -= 1
                st.rerun()
        with top_cols[3]:
            if st.button("▶", disabled=st.session_state.course_page >= total_pages - 1):
                st.session_state.course_page += 1
                st.rerun()
        with top_cols[4]:
            if st.button("⏭", disabled=st.session_state.course_page >= total_pages - 1):
                st.session_state.course_page = total_pages - 1
                st.rerun()

        st.markdown(f"Page {st.session_state.course_page + 1} / {total_pages} (Showing {page_size} per page)")

        if total == 0:
            st.info("No courses match your search.")
            page_items = []
        else:
            start = st.session_state.course_page * page_size
            end = start + page_size
            page_items = filtered[start:end]

        with st.form("courses_form"):
            updated = []
            for idx, course in enumerate(page_items):
                row_cols = st.columns([3, 2, 2])
                with row_cols[0]:
                    st.write(course.get("course_code", ""))
                with row_cols[1]:
                    new_grade = st.text_input(
                        f"Grade {start + idx}",
                        value=course.get("grade", ""),
                        key=f"grade_{start+idx}"
                    )
                with row_cols[2]:
                    credits_val = "" if course.get("credits") in (None, "") else str(course.get("credits"))
                    new_credits = st.text_input(
                        f"Credits {start + idx}",
                        value=credits_val,
                        key=f"credits_{start+idx}"
                    )
                updated.append({
                    "course_code": course.get("course_code", ""),
                    "grade": new_grade,
                    # Keep previous credits if input is invalid to avoid backend 422
                    "credits": int(new_credits) if new_credits.isdigit() else course.get("credits")
                })
            if st.form_submit_button("Save Visible Edits"):
                for i, upd in enumerate(updated):
                    orig_obj = page_items[i]
                    for master_idx, master_course in enumerate(courses):
                        if master_course is orig_obj:
                            courses[master_idx] = upd
                            break
                st.session_state.courses_edit = courses
                st.success("Visible course edits saved.")
                # Call backend to recalculate CGPA based on edits
                try:
                    payload = {
                        "grade_map": st.session_state.grade_map_edit,
                        "courses": st.session_state.courses_edit,
                    }
                    resp = requests.request("GET", RECALC_URL, json=payload, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.analysis_result["calculated_cgpa"] = data.get("calculated_cgpa")
                        st.success(f"Recalculated CGPA: {data.get('calculated_cgpa')}")
                        st.rerun()
                    else:
                        st.error(f"Recalculation failed: {resp.status_code}")
                        try:
                            st.json(resp.json())
                        except requests.exceptions.JSONDecodeError:
                            st.text(resp.text)
                except requests.exceptions.RequestException as e:
                    st.error(f"Network error contacting backend: {e}")

    st.divider()
    st.metric("Extracted CGPA", f"{json_response.get('extracted_cgpa', 'N/A')}")
    st.metric("Calculated CGPA", f"{json_response.get('calculated_cgpa', 'N/A')}")
