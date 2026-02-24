import subprocess
import sys
from flask import Flask, Response, render_template_string
import threading
import queue

app = Flask(__name__)

# Change this to your actual script
SCRIPT_PATH = "/Users/kavya/Desktop/DEV_MODE/ai_digest/ai-digest.py"

output_queue = queue.Queue()
process_done = False

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Digest Output</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0d0d0d;
      color: #33ff33;
      font-family: 'Courier New', Courier, monospace;
      font-size: 14px;
      padding: 20px;
      min-height: 100vh;
    }
    #header {
      color: #888;
      border-bottom: 1px solid #222;
      padding-bottom: 10px;
      margin-bottom: 16px;
      font-size: 12px;
    }
    #terminal {
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.6;
    }
    .line { display: block; }
    .line::before { content: '> '; color: #555; }
    #cursor {
      display: inline-block;
      width: 8px;
      height: 14px;
      background: #33ff33;
      animation: blink 1s step-end infinite;
      vertical-align: middle;
    }
    @keyframes blink { 50% { opacity: 0; } }
    #status {
      margin-top: 16px;
      color: #555;
      font-size: 12px;
      border-top: 1px solid #222;
      padding-top: 10px;
    }
    .done { color: #33ff33; }
  </style>
</head>
<body>
  <div id="header">AI DIGEST — live output &nbsp;|&nbsp; <span id="ts"></span></div>
  <div id="terminal"></div>
  <span id="cursor"></span>
  <div id="status">Running...</div>

  <script>
    document.getElementById('ts').textContent = new Date().toLocaleTimeString();

    const terminal = document.getElementById('terminal');
    const cursor = document.getElementById('cursor');
    const status = document.getElementById('status');
    const evtSource = new EventSource('/stream');

    evtSource.onmessage = function(e) {
      if (e.data === '__DONE__') {
        cursor.style.display = 'none';
        status.textContent = 'Process finished.';
        status.className = 'done';
        evtSource.close();
        return;
      }
      const line = document.createElement('span');
      line.className = 'line';
      line.textContent = e.data;
      terminal.appendChild(line);
      window.scrollTo(0, document.body.scrollHeight);
    };

    evtSource.onerror = function() {
      status.textContent = 'Connection lost or process ended.';
      evtSource.close();
      cursor.style.display = 'none';
    };
  </script>
</body>
</html>
"""

def run_script():
    global process_done
    process = subprocess.Popen(
        [sys.executable, "-u", SCRIPT_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in process.stdout:
        output_queue.put(line.rstrip("\n"))
    process.wait()
    output_queue.put("__DONE__")
    process_done = True

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/stream")
def stream():
    def generate():
        while True:
            try:
                line = output_queue.get(timeout=30)
                yield f"data: {line}\n\n"
                if line == "__DONE__":
                    break
            except queue.Empty:
                yield "data: \n\n"  # keepalive

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/run")
def rerun():
    global process_done
    process_done = False
    with output_queue.mutex:
        output_queue.queue.clear()
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    return ("", 204)

if __name__ == "__main__":
    # Start the script immediately on server launch
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=3000, threaded=True)