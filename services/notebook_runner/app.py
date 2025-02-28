from fastapi import FastAPI, BackgroundTasks, HTTPException
import os
import uuid
import yaml
import papermill as pm
from minio import Minio
from minio.commonconfig import Tags
import tempfile
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
import nbformat

app = FastAPI(title="Backtester Notebook Runner")

# Job tracking
jobs = {}


class NotebookRunRequest(BaseModel):
    market: str = Field(..., example="FTSE100")
    notebook_name: str = Field(default="02_apcluster_zscore_evo", example="02_apcluster_zscore_evo")
    parameters: Dict[str, Any] = Field(..., example={
        "p_threshold": 0.05,
        "min_pairs": 20,
        "window_shifts": 12,
        "shift_size": 1,
        "entry_threshold": 2.0,
        "exit_threshold": 0.5,
        "window1": 5,
        "window2": 60
    })
    strategy_type: str = Field(default="Z-Score", example="Correlation")
    pair_finding: str = Field(default="Clustering", example="KMeans")
    description: str = Field(default="Automatically generated strategy", example="KMeans Strategy for FTSE100")
    output_filename: Optional[str] = Field(default=None, example="ftse100_apcluster_zscore_v2.parquet")


class MarketInfo(BaseModel):
    name: str
    data_file: str


class ParameterInfo(BaseModel):
    name: str
    type: str
    default: Any
    description: Optional[str] = None


def load_config(config_path="/app/config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_minio_client():
    config = load_config()
    return Minio(
        "minio:9000",
        access_key=config["minio"]["user"],
        secret_key=config["minio"]["password"],
        secure=False
    )


def extract_parameters_from_notebook(notebook_path):
    parameters = []

    try:
        nb = nbformat.read(notebook_path, as_version=4)

        for cell in nb.cells:
            if cell.cell_type == "code" and "tags" in cell.metadata and "parameters" in cell.metadata.tags:
                lines = cell.source.split("\n")
                for line in lines:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        param_name = parts[0].strip()
                        param_value = parts[1].strip()

                        # Determine parameter type
                        param_type = "string"
                        try:
                            if param_value.startswith('"') or param_value.startswith("'"):
                                param_type = "string"
                            elif param_value == "True" or param_value == "False":
                                param_type = "boolean"
                            elif "." in param_value and float(param_value):
                                param_type = "float"
                            elif param_value.isdigit():
                                param_type = "integer"
                            elif param_value.startswith("[") or param_value.startswith("{"):
                                param_type = "object"
                        except:
                            pass

                        # Get description from preceding comment if exists
                        description = None
                        idx = lines.index(line)
                        if idx > 0 and lines[idx - 1].strip().startswith("#"):
                            description = lines[idx - 1].strip("# ")

                        # Clean up param_value (remove quotes, etc)
                        try:
                            if param_type == "string" and (param_value.startswith('"') or param_value.startswith("'")):
                                param_value = param_value.strip("\"'")
                            elif param_type == "boolean":
                                param_value = param_value == "True"
                            elif param_type == "float":
                                param_value = float(param_value)
                            elif param_type == "integer":
                                param_value = int(param_value)
                            elif param_type == "object":
                                param_value = json.loads(param_value.replace("'", "\""))
                        except:
                            pass

                        parameters.append({
                            "name": param_name,
                            "type": param_type,
                            "default": param_value,
                            "description": description
                        })
    except Exception as e:
        print(f"Error extracting parameters: {str(e)}")

    return parameters


@app.get("/markets")
async def list_markets():
    """List all available markets"""
    config = load_config()
    markets = []

    for market in config["storage"]["markets"]:
        markets.append({
            "name": market["name"],
            "data_file": market["data_file"]
        })

    return {"markets": markets}


@app.get("/notebooks")
async def list_notebooks():
    """List all available notebooks"""
    notebook_dir = "/app/notebooks"
    strategies_dir = os.path.join(notebook_dir, "strategies")
    notebooks = []

    if os.path.exists(strategies_dir):
        for file in os.listdir(strategies_dir):
            if file.endswith(".ipynb"):
                notebooks.append({
                    "name": os.path.splitext(file)[0],
                    "path": f"strategies/{file}"
                })

    return {"notebooks": notebooks}

@app.get("/notebook_parameters/{notebook_name}")
async def get_notebook_parameters(notebook_name: str):
    """Get available parameters for a specific notebook"""
    notebook_path = f"/app/notebooks/strategies/{notebook_name}.ipynb"

    if not os.path.exists(notebook_path):
        raise HTTPException(status_code=404, detail=f"Notebook not found: {notebook_name}")

    parameters = extract_parameters_from_notebook(notebook_path)

    return {
        "notebook_name": notebook_name,
        "parameters": parameters
    }


def run_notebook(job_id: str, market: str, notebook_name: str, parameters: Dict[str, Any],
                 strategy_type: str, pair_finding: str, description: str, output_filename: Optional[str] = None):
    try:
        config = load_config()
        minio_client = get_minio_client()
        bucket_name = config["storage"]["base_bucket"]

        # Find market configuration
        market_config = None
        for m in config["storage"]["markets"]:
            if m["name"] == market:
                market_config = m
                break

        if not market_config:
            raise ValueError(f"Market {market} not found")

        # Update job status
        jobs[job_id] = {"status": "running", "progress": 0.1, "message": "Job started"}

        # Notebook path
        notebook_path = f"/app/notebooks/strategies/{notebook_name}.ipynb"
        if not os.path.exists(notebook_path):
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")

        # Temp directory for input/output files
        temp_dir = tempfile.mkdtemp()

        # Download market data from MinIO
        data_file = market_config["data_file"]
        market_data_path = f"{market}/{data_file}"
        local_data_path = f"{temp_dir}/{data_file}"

        jobs[job_id]["progress"] = 0.15
        jobs[job_id]["message"] = "Downloading market data"

        minio_client.fget_object(
            bucket_name,
            market_data_path,
            local_data_path
        )

        # Output file configuration
        timestamp = uuid.uuid4().hex[:8]
        output_file = output_filename or f"strategy_{timestamp}.parquet"
        local_output_path = f"{temp_dir}/{output_file}"

        # Parameters with corrected paths
        params = parameters.copy()
        params["base_input_path"] = f"{temp_dir}/"
        params["input_filename"] = data_file
        params["base_output_path"] = f"{temp_dir}/"
        params["output_filename"] = output_file

        # Update progress
        jobs[job_id]["progress"] = 0.2
        jobs[job_id]["message"] = "Running notebook"

        # Execute notebook
        pm.execute_notebook(
            notebook_path,
            f"/tmp/executed_{job_id}.ipynb",
            parameters=params,
            kernel_name="python3"
        )

        # Update progress
        jobs[job_id]["progress"] = 0.7
        jobs[job_id]["message"] = "Notebook executed, uploading results"

        # Check if output file exists
        if not os.path.exists(local_output_path):
            raise FileNotFoundError(f"Output file not found: {local_output_path}")

        # Upload strategy to MinIO
        minio_path = f"{market}/strategies/{output_file}"
        minio_client.fput_object(
            bucket_name,
            minio_path,
            local_output_path
        )

        # Create Tags object instead of string
        tags = Tags()
        tags["strategy_type"] = strategy_type
        tags["version_description"] = description
        tags["pair_finding"] = pair_finding

        # Set tags using the Tags object
        minio_client.set_object_tags(
            bucket_name,
            minio_path,
            tags
        )
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = f"Strategy successfully uploaded: {output_file}"

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["progress"] = 0.0
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Error: {str(e)}"


@app.post("/run")
async def run_notebook_endpoint(request: NotebookRunRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "progress": 0.0, "message": "Job queued"}

    background_tasks.add_task(
        run_notebook,
        job_id,
        request.market,
        request.notebook_name,
        request.parameters,
        request.strategy_type,
        request.pair_finding,
        request.description,
        request.output_filename
    )

    return {"job_id": job_id, "message": "Notebook execution started"}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check the status of a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/jobs")
async def list_jobs():
    """List all jobs and their status"""
    return jobs