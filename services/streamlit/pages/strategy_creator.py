import streamlit as st
import pandas as pd
import requests
import time
import json
from api import APIClient
from config import Config


st.set_page_config(page_title="Strategy Creator", page_icon="🚀", layout="wide")


def get_status_pill(status):
    if status == "pending":
        return f'<span style="background-color: #FFC107; color: #212121; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.8rem;">pending</span>'
    elif status == "running":
        return f'<span style="background-color: #2196F3; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.8rem;">running</span>'
    elif status == "completed":
        return f'<span style="background-color: #4CAF50; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.8rem;">completed</span>'
    elif status == "failed":
        return f'<span style="background-color: #F44336; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.8rem;">failed</span>'
    else:
        return f'<span style="background-color: #9E9E9E; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.8rem;">{status}</span>'


st.title("Strategy Creator")


api_client = APIClient()
config = Config(api_client)

notebook_runner_url = "http://localhost:8080"  # Ändern zu localhost für lokale Entwicklung

jobs_container = None


def update_jobs_table():
    global jobs_container
    try:
        jobs_response = requests.get(f"{notebook_runner_url}/jobs")
        if jobs_response.status_code == 200:
            jobs_data = jobs_response.json()
            if jobs_data:
                jobs_list = []
                for job_id, job_info in jobs_data.items():
                    status = job_info.get('status', 'unknown')

                    job_entry = {
                        'Job ID': job_id,
                        'Status': get_status_pill(status),
                        'Progress': f"{job_info.get('progress', 0) * 100:.0f}%",
                        'Message': job_info.get('message', '')
                    }
                    jobs_list.append(job_entry)

                jobs_df = pd.DataFrame(jobs_list)

                if jobs_container is not None:
                    jobs_container.write(jobs_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                if jobs_container is not None:
                    jobs_container.info("No active jobs")
        else:
            if jobs_container is not None:
                jobs_container.error("Failed to fetch jobs data")
    except Exception as e:
        if jobs_container is not None:
            jobs_container.error(f"Connection error: {str(e)}")


st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Strategy Configuration")

    try:
        markets_response = requests.get(f"{notebook_runner_url}/markets")
        if markets_response.status_code == 200:
            markets_data = markets_response.json()
            market_options = [market["name"] for market in markets_data.get("markets", [])]
        else:
            st.error(f"Server responded with status code {markets_response.status_code}")
            market_options = []
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        market_options = []

    selected_market = st.selectbox("Select Market", options=market_options if market_options else [""])

    try:
        notebooks_response = requests.get(f"{notebook_runner_url}/notebooks")
        if notebooks_response.status_code == 200:
            notebooks_data = notebooks_response.json()
            notebook_options = [nb["name"] for nb in notebooks_data.get("notebooks", [])]
        else:
            st.error(f"Server responded with status code {notebooks_response.status_code}")
            notebook_options = []
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        notebook_options = []

    selected_notebook = st.selectbox("Select Strategy Template", options=notebook_options if notebook_options else [""])

    strategy_type = st.text_input("Strategy Type", value="Z-Score")
    pair_finding = st.text_input("Pair Finding Method", value="Clustering")

    description = st.text_area("Strategy Description", value="Automatically generated strategy")
    output_filename = st.text_input(
        "Output Filename",
        value=f"{selected_market.lower()}_strategy.parquet" if selected_market and selected_market != "" else ""
    )

    start_button = st.button("🚀 Run Strategy Creation", use_container_width=True)

with col2:
    st.subheader("Strategy Parameters")

    if selected_notebook and selected_notebook != "":
        try:
            params_response = requests.get(f"{notebook_runner_url}/notebook_parameters/{selected_notebook}")
            if params_response.status_code == 200:
                params_data = params_response.json()
                parameters = params_data.get("parameters", [])
            else:
                st.error(f"Server responded with status code {params_response.status_code}")
                parameters = []
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
            parameters = []

        param_values = {}

        if parameters:
            for param in parameters:
                param_name = param["name"]
                param_type = param["type"]
                param_default = param["default"]
                param_desc = param.get("description", "")

                if param_desc:
                    param_label = f"{param_name} ({param_desc})"
                else:
                    param_label = param_name

                if param_type == "float":
                    param_values[param_name] = st.number_input(param_label, value=float(param_default), format="%.5f")
                elif param_type == "integer":
                    param_values[param_name] = st.number_input(param_label, value=int(param_default))
                elif param_type == "boolean":
                    param_values[param_name] = st.checkbox(param_label, value=bool(param_default))
                elif param_type == "object":
                    param_values[param_name] = st.text_area(param_label, value=json.dumps(param_default))
                else:  # string and others
                    param_values[param_name] = st.text_input(param_label, value=str(param_default))
        else:
            st.info("No parameters available for this notebook")
    else:
        st.info("Select a notebook template to configure parameters")

    if start_button:
        if not selected_market or not selected_notebook or selected_market == "" or selected_notebook == "":
            st.error("Please select both market and strategy template")
        else:
            # Create request payload
            request_data = {
                "market": selected_market,
                "notebook_name": selected_notebook,
                "parameters": param_values,
                "strategy_type": strategy_type,
                "pair_finding": pair_finding,
                "description": description,
                "output_filename": output_filename if output_filename else None
            }

            # Submit job
            try:
                run_response = requests.post(f"{notebook_runner_url}/run", json=request_data)
                if run_response.status_code == 200:
                    run_data = run_response.json()
                    job_id = run_data.get("job_id")

                    if job_id:
                        # Update jobs table immediately
                        update_jobs_table()
                    else:
                        st.error("Failed to start strategy creation: No job ID returned")
                else:
                    st.error(f"Failed to start strategy creation: {run_response.status_code}")
            except Exception as e:
                update_jobs_table()

st.markdown("---")
st.subheader("Active Jobs")

jobs_container = st.empty()

if st.button("⟳ Refresh Jobs"):
    update_jobs_table()

if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

st.session_state.refresh_counter += 1

if st.session_state.refresh_counter % 10 == 0:
    time.sleep(1)
    update_jobs_table()
else:
    update_jobs_table()