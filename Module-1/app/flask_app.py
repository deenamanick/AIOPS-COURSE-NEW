"""
AIOps Lab — Sample Flask Application
Runs on app-server (192.168.56.11), behind Nginx reverse proxy.
Endpoints: /, /health, /api/status

(This is a docstring, a multi-line comment. In Python, anything between triple quotes 
is ignored by the computer. It explains what this script does for humans to read.)
"""

# 'import' brings in external tools (called "modules") that are built into Python.
# 'socket' allows the code to interact with the network (like finding out the computer's name).
import socket

# 'time' allows the code to work with dates, times, and measure how long the program has been running.
import time

# This imports specific tools from an external library called 'flask', used to build web applications.
# We grab 'Flask' (to create the web server) and 'jsonify' (to format data nicely for other computers).
from flask import Flask, jsonify

# This line creates our web application! We take the Flask tool and give it the name 'app'.
# '__name__' is a special Python variable that tells Flask where to look for files.
app = Flask(__name__)

# This records the exact moment the application starts running. 
# We save it in 'START_TIME' so we can calculate how long the server has been "up" later.
START_TIME = time.time()


# '@app.route("/")' is a "decorator". It tells our web server: "If a user visits 
# the main homepage (the root path '/'), run the function directly below this line."
@app.route("/")
def home():
    # This function returns HTML code that displays a simple message on the user's web browser.
    return "<h1>AIOps Lab — App Server</h1><p>Flask is running on app-server.</p>"


# This says: "If a user goes to the '/health' URL, run the health() function."
@app.route("/health")
def health():
    # It simply returns the text "OK". Automated systems use this to check if the server is alive.
    return "OK"


# This sets up another URL path: '/api/status'. When a user visits this link, the status() function runs.
@app.route("/api/status")
def status():
    # Calculates how long the server has been running by subtracting START_TIME from the current time.
    # It rounds the answer to 2 decimal places and stores it in 'uptime'.
    uptime = round(time.time() - START_TIME, 2)
    
    # 'jsonify()' packages data into "JSON" format (easily readable by other computer programs).
    # It sends back the computer's hostname, a healthy status, the uptime, and the service name.
    return jsonify({
        "hostname": socket.gethostname(),
        "status": "healthy",
        "uptime_seconds": uptime,
        "service": "flask-app"
    })


# This is a standard Python safeguard: "Only run the code below if I am running this specific file directly."
if __name__ == "__main__":
    # This turns the web server on!
    # host="0.0.0.0" means listen to connections from ANY computer.
    # port=5000 is the specific "door" the server will listen at.
    # debug=True turns on helpful error messages and automatically restarts on code changes.
    app.run(host="0.0.0.0", port=5000, debug=True)
