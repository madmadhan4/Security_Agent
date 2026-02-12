import threading
import time
import requests
import uvicorn
from app import app

# Function to run the server in a separate thread
def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8003, log_level="error")
    except Exception as e:
        print(f"Error starting server: {e}")

def test_language_simulation(language: str):
    print(f"\n--- Testing Language: {language} ---")
    try:
        response = requests.post("http://127.0.0.1:8003/api/start-simulation", json={"language": language})
        assert response.status_code == 200
        print(f"Simulation started for {language}.")
    except requests.exceptions.ConnectionError:
        print("Failed to connect to server. Is it running?")
        raise

    max_retries = 30
    for i in range(max_retries):
        try:
            status_res = requests.get("http://127.0.0.1:8003/api/status")
            state = status_res.json()
            
            if state["status"] == "COMPLETED":
                print(f"Simulation for {language} COMPLETED.")
                
                # Assertions
                if not state["vulnerabilities"]:
                     print(f"⚠️ Warning: No random vulnerability generated for {language} (might be bad luck in randomizer if empty)")
                
                # Check status
                logs = str(state["logs"])
                if "merged successfully" in logs:
                    print(f"✅ {language}: PR Merged Successfully")
                    return True
                elif "PR rejected" in logs:
                    print(f"⚠️ {language}: PR Rejected (Fix failed? Check agent logic)")
                    return False
                
            if state["status"] == "ERROR":
                print(f"❌ {language}: Simulation ERROR")
                return False
                
        except requests.exceptions.ConnectionError:
             print("Connection lost...")
            
        time.sleep(1)
    
    print(f"❌ {language}: Timed out")
    return False

def test_all_languages():
    print("Starting server for testing on port 8003...")
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    languages = ["python", "javascript", "abap", "java", "go", "ruby"]
    results = {}
    
    for lang in languages:
        results[lang] = test_language_simulation(lang)
        # Wait a bit between simulations to let server idle
        time.sleep(2)
        
    print("\n\n=== SUMMARY ===")
    all_passed = True
    for lang, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{lang}: {status}")
        if not passed: all_passed = False
        
    if all_passed:
        print("\n✅ ALL TESTS PASSED")
    else:
        raise Exception("Some tests failed")

if __name__ == "__main__":
    try:
        test_all_languages()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
