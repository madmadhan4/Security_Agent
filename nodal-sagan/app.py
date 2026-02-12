from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import time
import random

from mock_github import MockGitHub, MockPR, MockFile
from agents import SupervisorAgent, VulnerabilityFactory

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory storage for simulation state
simulation_state = {
    "status": "IDLE", # IDLE, RUNNING, COMPLETED
    "logs": [],
    "current_step": "",
    "pr_details": {},
    "vulnerabilities": [],
    "fixed_code": {},
    "generated_tests": []
}

github = MockGitHub()
supervisor = SupervisorAgent(github)
vuln_factory = VulnerabilityFactory()

class SimulationRequest(BaseModel):
    language: str # python, javascript, abap, java, go, ruby

async def log_callback(message: str):
    print(message)
    simulation_state["logs"].append(f"[{time.strftime('%H:%M:%S')}] {message}")
    if "Hacker" in message:
        simulation_state["current_step"] = "Hacking..."
    elif "Fixer" in message:
        simulation_state["current_step"] = "Fixing..."
    elif "Supervisor" in message:
         simulation_state["current_step"] = "Orchestrating..."

async def run_simulation_task(language: str):
    simulation_state["status"] = "RUNNING"
    simulation_state["logs"] = []
    simulation_state["vulnerabilities"] = []
    simulation_state["fixed_code"] = {}
    simulation_state["generated_tests"] = []
    
    try:
        # Step 1: Create PR with Random Files (Mixed Vulnerability)
        await log_callback(f"Step 1: Creating a simulated Pull Request for {language}...")
        simulation_state["current_step"] = "Creating PR"
        await asyncio.sleep(1)

        file_data_list = vuln_factory.generate_pr_files(language)
        pr_files = []
        original_contents = {}

        for fname, fcontent in file_data_list:
            pr_files.append(MockFile(filename=fname, content=fcontent, language=language))
            original_contents[fname] = fcontent
            
        pr = github.create_pr(title=f"Feature: Update {language} service", files=pr_files)
        
        simulation_state["pr_details"] = {
            "id": pr.id,
            "title": pr.title,
            "status": pr.status,
            "files": original_contents # Dict of filename -> content
        }
        await log_callback(f"PR #{pr.id} created: {pr.title} ({len(pr_files)} files)")
        
        # Step 2: Delegate to Supervisor
        result = await supervisor.run_mission(pr.id, log_callback)
        
        if result:
            simulation_state["vulnerabilities"] = result["vulnerabilities"]
            simulation_state["generated_tests"] = result["tests"]
            
            # Store fixes as dict: filename -> content
            simulation_state["fixed_code"] = {}
            for fix in result["fixes"]:
                simulation_state["fixed_code"][fix["filename"]] = fix["content"]

        # Step 3: Merge if secure
        if github.get_pr(pr.id).checks.get("Security Check") == "PASS":
            await log_callback("Supervisor: Validated. Merging Pull Request...")
            simulation_state["current_step"] = "Merging"
            github.merge_pr(pr.id)
            await log_callback(f"PR #{pr.id} merged successfully.")
        else:
             await log_callback("Supervisor: PR rejected due to security risks.")

        simulation_state["status"] = "COMPLETED"
        simulation_state["current_step"] = "Done"

    except Exception as e:
        await log_callback(f"Error during simulation: {str(e)}")
        simulation_state["status"] = "ERROR"

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.post("/api/start-simulation")
async def start_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    if simulation_state["status"] == "RUNNING":
         return {"message": "Simulation already running"}
    
    background_tasks.add_task(run_simulation_task, request.language)
    return {"message": "Simulation started"}

@app.get("/api/status")
async def get_status():
    return simulation_state
