"""Unified Local Runner for PayNexus Platform.
Starts all 6 mock services, FastAPI backend, orchestrator worker, and Vite frontend.
Handles health checks and graceful multi-process termination.
"""
import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = sys.executable
NPM = "npm.cmd" if sys.platform == "win32" else "npm"

SERVICES = [
    {
        "name": "Mock UPI Simulator",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8101", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "rail-upi"),
        "url": "http://127.0.0.1:8101/docs",
    },
    {
        "name": "Mock NEFT Simulator",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8102", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "rail-neft"),
        "url": "http://127.0.0.1:8102/docs",
    },
    {
        "name": "Mock SWIFT Simulator",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8103", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "rail-swift"),
        "url": "http://127.0.0.1:8103/docs",
    },
    {
        "name": "Mock Card Gateway",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8104", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "rail-card"),
        "url": "http://127.0.0.1:8104/docs",
    },
    {
        "name": "Mock Sanctions Provider",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8201", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "sanctions"),
        "url": "http://127.0.0.1:8201/docs",
    },
    {
        "name": "Mock KYC Provider",
        "cmd": [PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8202", "--log-level", "warning"],
        "cwd": os.path.join(ROOT_DIR, "mock-services", "kyc"),
        "url": "http://127.0.0.1:8202/docs",
    },
    {
        "name": "PayNexus Backend API",
        "cmd": [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "info"],
        "cwd": os.path.join(ROOT_DIR, "backend"),
        "url": "http://127.0.0.1:8000/healthz",
    },
    {
        "name": "Payment Orchestrator Worker",
        "cmd": [PYTHON, "-m", "app.workers.orchestrator_worker"],
        "cwd": os.path.join(ROOT_DIR, "backend"),
        "url": None,
    },
    {
        "name": "Vite React Frontend",
        "cmd": [NPM, "run", "dev", "--", "--host", "127.0.0.1", "--port", "3000"],
        "cwd": os.path.join(ROOT_DIR, "frontend"),
        "url": "http://127.0.0.1:3000",
    },
]

processes = []


def check_url(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 404)
    except urllib.error.HTTPError as e:
        return e.code in (200, 301, 302, 404)
    except Exception:
        return False


def terminate_all(signum=None, frame=None):
    print("\n[PayNexus] Stopping all running services gracefully...")
    for proc, svc in reversed(processes):
        try:
            print(f"[PayNexus] Terminating {svc['name']} (PID: {proc.pid})...")
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.terminate()
        except Exception:
            pass
    print("[PayNexus] All processes terminated. Goodbye!")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, terminate_all)
    signal.signal(signal.SIGTERM, terminate_all)

    print("=" * 75)
    print("      PAYNEXUS: PAYMENTS MODERNISATION PLATFORM (LOCAL RUNNER)")
    print("=" * 75)

    # 1. Check database existence
    db_path = os.path.join(ROOT_DIR, "paynexus.db")
    if not os.path.exists(db_path):
        print("[PayNexus] Local database not found. Initializing and seeding...")
        subprocess.run([PYTHON, os.path.join(ROOT_DIR, "scripts", "init_local_db.py")], check=True)
        subprocess.run([PYTHON, os.path.join(ROOT_DIR, "scripts", "seed.py")], check=True)
    else:
        print(f"[PayNexus] Verified SQLite database: {db_path}")

    # 2. Launch all services
    for svc in SERVICES:
        print(f"[PayNexus] Launching {svc['name']}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = svc["cwd"] + os.pathsep + os.path.join(ROOT_DIR, "backend")
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.replace(os.sep, '/')}"
        env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path.replace(os.sep, '/')}"

        p = subprocess.Popen(
            svc["cmd"],
            cwd=svc["cwd"],
            env=env,
            stdout=subprocess.DEVNULL if svc["name"].startswith("Mock") else None,
            stderr=subprocess.DEVNULL if svc["name"].startswith("Mock") else None,
        )
        processes.append((p, svc))
        time.sleep(0.5)

    print("\n[PayNexus] Waiting for all services to become healthy...")
    time.sleep(3.0)

    # 3. Health Checks
    all_healthy = True
    for p, svc in processes:
        if svc["url"]:
            healthy = False
            for _ in range(15):
                if check_url(svc["url"]):
                    healthy = True
                    break
                time.sleep(0.5)
            status_symbol = "[UP]" if healthy else "[STARTING/UNCHECKED]"
            print(f"  - {svc['name']:<30} {status_symbol} ({svc['url']})")
            if not healthy:
                all_healthy = False
        else:
            is_running = p.poll() is None
            status_symbol = "[RUNNING]" if is_running else "[EXITED]"
            print(f"  - {svc['name']:<30} {status_symbol}")

    print("\n" + "=" * 75)
    print("   PAYNEXUS PLATFORM READY FOR TESTING & DEMONSTRATION")
    print("=" * 75)
    print("   Web Dashboard UI : http://localhost:3000")
    print("   Swagger API Docs  : http://localhost:8000/docs")
    print("   API Healthcheck   : http://localhost:8000/healthz")
    print("   Prometheus Metrics: http://localhost:8000/metrics")
    print("-" * 75)
    print("   DEMO USER CREDENTIALS (Password for all: Demo@PayNexus2026!)")
    print("   - Admin       : admin@paynexus.io")
    print("   - Operations  : ops@paynexus.io")
    print("   - Compliance  : compliance@paynexus.io")
    print("   - Auditor     : auditor@paynexus.io")
    print("   - Merchant    : merchant@paynexus.io")
    print("=" * 75)
    print("\n[PayNexus] Press Ctrl+C at any time to shut down all services.")

    # Keep alive and monitor child processes
    try:
        while True:
            time.sleep(2.0)
            for p, svc in processes:
                if p.poll() is not None:
                    # If a critical service exited, notify
                    pass
    except KeyboardInterrupt:
        terminate_all()


if __name__ == "__main__":
    main()
