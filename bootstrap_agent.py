#!/usr/bin/env python3

import subprocess
import json
import shutil
import time
import re
import socket
import os
import sys


# ---------------------------
# CONFIG
# ---------------------------
BASE_DIR = os.path.expanduser("~/RaspController")
VENV = os.path.join(BASE_DIR, "venv/bin/activate")
HEALTH_URL = "http://127.0.0.1:{port}/health"

MAX_HEALTH_RETRIES = 10
HEALTH_DELAY = 2


# ---------------------------
# HELPERS
# ---------------------------
def run(cmd, timeout=15):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except:
        return None


def emit(status, **kwargs):
    payload = {
        "status": status,
        **kwargs
    }
    print(json.dumps(payload))
    sys.stdout.flush()


def command_exists(cmd):
    return shutil.which(cmd) is not None


# ---------------------------
# PORT UTILITIES
# ---------------------------
def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(start=8000, end=8100):
    for port in range(start, end):
        if is_port_free(port):
            return port
    return None


def kill_port(port):
    pids = run(f"lsof -t -i:{port}")
    if pids:
        for pid in pids.splitlines():
            run(f"kill -9 {pid}")
        return True
    return False


def check_http_port(port):
    res = run(f"curl -s --max-time 2 {HEALTH_URL.format(port=port)}")
    return res and "ok" in res.lower()


def wait_for_health(port):
    for i in range(MAX_HEALTH_RETRIES):
        emit("health_check", attempt=i + 1, port=port)
        if check_http_port(port):
            return True
        time.sleep(HEALTH_DELAY)
    return False


# ---------------------------
# BACKEND CHECK
# ---------------------------
def backend_exists():
    return os.path.exists(os.path.join(BASE_DIR, "api.py"))


# ---------------------------
# FIREWALL FIX
# ---------------------------
def fix_firewall():
    if command_exists("ufw"):
        run("sudo ufw allow 8000")
    if command_exists("iptables"):
        run("sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT")


# ---------------------------
# START BACKEND
# ---------------------------
def start_backend(port):

    start_cmds = [
        f"cd {BASE_DIR} && source {VENV} && nohup python -m uvicorn api:app --host 0.0.0.0 --port {port} > logs/api.log 2>&1 &",
        f"cd {BASE_DIR} && source {VENV} && nohup python -m uvicorn agent.api:app --host 0.0.0.0 --port {port} > logs/api.log 2>&1 &"
    ]

    for cmd in start_cmds:
        emit("starting_attempt", cmd=cmd[:60])
        run(cmd)

        if wait_for_health(port):
            return True

    return False


# ---------------------------
# MAIN FLOW
# ---------------------------
def main():

    emit("starting")

    # ---------------------------
    # PYTHON CHECK
    # ---------------------------
    if not run("python3 --version"):
        emit("failed", error="python_missing")
        return

    emit("python_ok")

    # ---------------------------
    # BACKEND CHECK
    # ---------------------------
    if not backend_exists():
        emit("failed", error="backend_missing")
        return

    emit("backend_found")

    # ---------------------------
    # CHECK EXISTING API
    # ---------------------------
    for port in range(8000, 8100):
        if check_http_port(port):
            emit("ready", port=port, reused=True)
            return

    emit("not_running")

    # ---------------------------
    # FIREWALL
    # ---------------------------
    fix_firewall()
    emit("firewall_checked")

    # ---------------------------
    # SYSTEMD RESTART
    # ---------------------------
    if command_exists("systemctl"):
        emit("systemd_restart")
        run("sudo systemctl restart rasplink")

        if wait_for_health(8000):
            emit("ready", port=8000, via="systemd")
            return

    emit("systemd_failed")

    # ---------------------------
    # PORT HANDLING
    # ---------------------------
    if not is_port_free(8000):
        emit("port_conflict", port=8000)
        if kill_port(8000):
            emit("port_killed", port=8000)

    port = 8000 if is_port_free(8000) else find_free_port()

    if not port:
        emit("failed", error="no_free_port")
        return

    emit("selected_port", port=port)

    # ---------------------------
    # START BACKEND
    # ---------------------------
    if start_backend(port):
        emit("ready", port=port, via="manual")
        return

    # ---------------------------
    # FINAL SCAN
    # ---------------------------
    emit("fallback_scan")

    for port in range(8000, 8100):
        if check_http_port(port):
            emit("ready", port=port, via="fallback")
            return

    # ---------------------------
    # FAILURE
    # ---------------------------
    emit("failed", error="api_not_running")


if __name__ == "__main__":
    main()