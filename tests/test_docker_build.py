import subprocess, pathlib, textwrap
import shutil
import pytest

def test_backend_docker_build():
    # Build backend Docker image to ensure Dockerfile is valid
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    dockerfile = repo_root / "backend" / "Dockerfile"
    cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        str(repo_root),
        "-t", "backend-test-img"
    ]
    # Skip if docker CLI is not available in container
    if shutil.which("docker") is None:
        pytest.skip("docker executable not available")
    completed = subprocess.run(cmd, capture_output=True, text=True)
    # On failure, print stderr for debugging
    assert completed.returncode == 0, textwrap.shorten(completed.stderr, 800)
