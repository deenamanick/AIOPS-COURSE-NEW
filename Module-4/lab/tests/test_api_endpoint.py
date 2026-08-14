"""
Integration Test 1: API Health Check Endpoint
This test validates that the Streamlit application starts up correctly and its 
built-in health endpoint responds with HTTP 200. In production Kubernetes deployments,
this is the same endpoint that readiness/liveness probes use to determine if the pod is healthy.
"""

# 'subprocess' lets us start the Streamlit app as a background process from within the test.
import subprocess
# 'time' lets us add delays (sleep) while waiting for the server to boot up.
import time
# 'requests' is the standard Python library for making HTTP calls (like curl).
import requests
# 'pytest' is the testing framework. We use its 'fixture' feature to manage setup/teardown.
import pytest

# The URL where Streamlit will be running during the test.
APP_URL = "http://localhost:8501"


@pytest.fixture(scope="module")
def streamlit_server():
    """
    Start the Streamlit app in a subprocess for testing.
    
    This is a pytest 'fixture' — it runs BEFORE the test function executes,
    and the 'yield' statement pauses it until the test is done. After the test,
    it resumes and cleans up (terminates the server).
    
    scope="module" means this fixture runs once per test file, not once per test function.
    """
    # Start Streamlit as a background process.
    # --server.headless=true prevents it from trying to open a browser window.
    proc = subprocess.Popen(
        ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Streamlit takes a few seconds to boot up (loading the AI model, etc.).
    # We poll the health endpoint every 1 second, up to 30 times (30 seconds max).
    for _ in range(30):
        try:
            resp = requests.get(f"{APP_URL}/_stcore/health", timeout=2)
            if resp.status_code == 200:
                break  # Server is ready!
        except requests.ConnectionError:
            # Server hasn't started yet — wait 1 second and try again.
            time.sleep(1)

    # 'yield' hands control over to the test function.
    # The Streamlit server stays running while the test executes.
    yield proc

    # CLEANUP: After the test is done, terminate the Streamlit process
    # so it doesn't keep running in the background.
    proc.terminate()
    proc.wait()


def test_health_endpoint_returns_ok(streamlit_server):
    """The Streamlit health check endpoint must return HTTP 200."""

    # Make a GET request to Streamlit's built-in health endpoint.
    # This is the same endpoint that Kubernetes liveness probes hit.
    response = requests.get(f"{APP_URL}/_stcore/health", timeout=5)

    # If the server is running correctly, it returns HTTP 200.
    # Any other status code (like 500 or 404) means something is broken.
    assert response.status_code == 200, f"Health check failed with status {response.status_code}"
