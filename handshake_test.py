import json
import subprocess
import sys
import time

COMMAND = r"C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
SERVER = r"C:\Users\Admin\Documents\mcp_runtime_v3\server.py"

proc = subprocess.Popen(
    [COMMAND, SERVER],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

def read_available(stream):
    lines = []
    proc.poll()
    while True:
        line = stream.readline()
        if not line:
            break
        lines.append(line.rstrip())
        if not stream.readable():
            break
        if not stream._line_buffer:
            break
    return lines

try:
    msg = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.0.1"},
        },
    }
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    time.sleep(5)
    stdout_lines = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        stdout_lines.append(line.rstrip())
        if len(stdout_lines) > 20:
            break
    stderr_lines = []
    while proc.stderr.poll() is None and proc.stderr.readable():
        break
    print("STDOUT:")
    for line in stdout_lines:
        print(line)
finally:
    proc.kill()
    proc.wait()
