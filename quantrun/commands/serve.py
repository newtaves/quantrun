"""Serve command — start API server and frontend dev server."""

import subprocess
import sys
import signal
import os
from pathlib import Path

import click


@click.command()
@click.option("--port", "-p", default=8000, type=int, help="API server port (default: 8000)")
@click.option("--frontend-port", default=5173, type=int, help="Frontend dev server port (default: 5173)")
@click.option("--no-frontend", is_flag=True, help="Start API server only")
def serve(port, frontend_port, no_frontend):
    """Start the API server and React frontend."""
    root = Path(__file__).resolve().parent.parent.parent
    frontend_dir = root / "frontend"

    procs = []

    def shutdown(sig, frame):
        click.echo("\nShutting down...")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start API server
    api_cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", str(port)]
    click.echo(f"API server:  http://localhost:{port}")
    procs.append(subprocess.Popen(api_cmd, cwd=str(root)))

    # Start frontend
    if not no_frontend:
        if frontend_dir.exists() and (frontend_dir / "package.json").exists():
            click.echo(f"Frontend:    http://localhost:{frontend_port}")
            procs.append(subprocess.Popen(["npm", "run", "dev", "--", "--port", str(frontend_port)], cwd=str(frontend_dir), shell=True))
        else:
            click.echo("Frontend directory not found, skipping.", err=True)

    click.echo("\nPress Ctrl+C to stop.\n")

    # Wait for any process to exit
    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    shutdown(None, None)
                    return
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)
