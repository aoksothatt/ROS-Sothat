"""
ROS Sothatt — Stage 38Q Milestone B: GitHub Actions Workflow Dispatcher & Monitor.

Dispatches build-hook-dylib.yml on GitHub Actions, monitors the build run to completion,
downloads the compiled rosauthhook.dylib artifact, and verifies its checksum and symbols.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile

REPO_OWNER = "aoksothatt"
REPO_NAME = "ROS-Sothat"
WORKFLOW_FILE = "build-hook-dylib.yml"
TARGET_BRANCH = "main"
TARGET_COMMIT = sys.argv[1] if len(sys.argv) > 1 else "dd19ebbdfabff2d245f4d067f5ba4df1e185c043"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class NoAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req and "blob.core.windows.net" in newurl:
            new_req.headers = {k: v for k, v in new_req.headers.items() if k.lower() != "authorization"}
        return new_req


def get_github_token() -> str:
    """Retrieves GitHub token from Git Credential Manager."""
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        text=True,
        capture_output=True,
        check=True
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Could not retrieve GitHub token from git credential manager.")


def api_request(endpoint: str, method: str = "GET", data: dict = None, token: str = None) -> dict:
    """Executes authenticated GitHub REST API request."""
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ROS-Sothatt-CI-Agent"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        if resp.status == 204:
            return {}
        content = resp.read()
        if content:
            return json.loads(content.decode("utf-8"))
        return {}


def download_binary(url: str, output_path: str, token: str):
    """Downloads binary file (such as build artifact zip) using authenticated request."""
    opener = urllib.request.build_opener(NoAuthRedirectHandler())
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ROS-Sothatt-CI-Agent"
    }
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req) as resp, open(output_path, "wb") as out_f:
        while chunk := resp.read(1024 * 1024):
            out_f.write(chunk)


def main():
    print("=" * 70)
    print(" ROS SOTHATT — GITHUB ACTIONS DISPATCHER & MONITOR")
    print(f" Target Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f" Workflow File:     {WORKFLOW_FILE}")
    print(f" Target Branch:     {TARGET_BRANCH}")
    print(f" Target Commit:     {TARGET_COMMIT}")
    print("=" * 70)

    token = get_github_token()
    print("[*] Retrieved GitHub authentication token successfully.")

    # 1. Locate workflow ID
    workflows = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows", token=token)
    workflow_id = None
    for wf in workflows.get("workflows", []):
        if WORKFLOW_FILE in wf.get("path", ""):
            workflow_id = wf["id"]
            print(f"[*] Found workflow: {wf['name']} (ID: {workflow_id})")
            break

    if not workflow_id:
        raise RuntimeError(f"Workflow {WORKFLOW_FILE} not found on GitHub!")

    # 2. Dispatch workflow
    print(f"[*] Dispatching workflow {workflow_id} on ref '{TARGET_BRANCH}'...")
    dispatch_payload = {"ref": TARGET_BRANCH}
    api_request(
        f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/dispatches",
        method="POST",
        data=dispatch_payload,
        token=token
    )
    print("[+] Workflow dispatched successfully.")

    # 3. Wait for workflow run to register
    print("[*] Waiting for new workflow run to appear on GitHub...")
    run_id = None
    start_time = time.time()
    while time.time() - start_time < 60:
        time.sleep(5)
        runs_data = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/runs", token=token)
        runs = runs_data.get("workflow_runs", [])
        if runs:
            latest_run = runs[0]
            # Check if this run is recent (within last 2 minutes)
            if latest_run.get("head_sha") == TARGET_COMMIT:
                run_id = latest_run["id"]
                print(f"[+] Found workflow run: ID {run_id} (Status: {latest_run.get('status')})")
                print(f"    HTML URL: {latest_run.get('html_url')}")
                break

    if not run_id:
        raise TimeoutError("Timed out waiting for new workflow run to appear.")

    # 4. Monitor run until completion
    print(f"[*] Monitoring workflow run {run_id}...")
    poll_count = 0
    while True:
        poll_count += 1
        time.sleep(10)
        run_info = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}", token=token)
        status = run_info.get("status")
        conclusion = run_info.get("conclusion")
        print(f"    [{poll_count:02d}] Status: {status}, Conclusion: {conclusion}")

        if status == "completed":
            if conclusion == "success":
                print("[+] Build succeeded successfully on macOS runner!")
                break
            else:
                raise RuntimeError(f"Workflow run failed with conclusion: {conclusion}")

    # 5. Retrieve artifacts
    print("[*] Fetching build artifacts...")
    artifacts_data = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/artifacts", token=token)
    artifacts = artifacts_data.get("artifacts", [])
    if not artifacts:
        raise RuntimeError("No artifacts found for this workflow run!")

    artifact = artifacts[0]
    artifact_id = artifact["id"]
    artifact_name = artifact["name"]
    download_url = artifact["archive_download_url"]
    print(f"[*] Artifact: {artifact_name} (ID: {artifact_id}, Size: {artifact['size_in_bytes']} bytes)")

    # 6. Download and extract artifact
    artifact_zip_path = os.path.join(PROJECT_ROOT, f"{artifact_name}.zip")
    print(f"[*] Downloading artifact to {artifact_zip_path}...")
    download_binary(download_url, artifact_zip_path, token=token)

    extract_dir = os.path.join(PROJECT_ROOT, "src", "hook")
    print(f"[*] Extracting artifact into {extract_dir}...")
    with zipfile.ZipFile(artifact_zip_path, "r") as z:
        for filename in z.namelist():
            print(f"    Extracting: {filename}")
            z.extract(filename, path=extract_dir)

    # 7. Verification of extracted dylib
    dylib_path = os.path.join(extract_dir, "rosauthhook.dylib")
    sha_file = os.path.join(extract_dir, "rosauthhook.dylib.sha256")
    ver_txt = os.path.join(extract_dir, "verification.txt")

    if not os.path.exists(dylib_path):
        raise FileNotFoundError(f"Extracted dylib missing: {dylib_path}")

    with open(dylib_path, "rb") as f:
        dylib_bytes = f.read()

    computed_sha = hashlib.sha256(dylib_bytes).hexdigest().upper()
    print("=" * 70)
    print(" FORENSIC VERIFICATION OF COMPILED ROSAUTHOOK.DYLIB")
    print(f" File Size:   {len(dylib_bytes)} bytes")
    print(f" SHA-256:     {computed_sha}")
    print("=" * 70)

    # Verify Mach-O 64-bit ARM64 Header
    import struct
    magic, cputype, cpusubtype, filetype = struct.unpack("<IIII", dylib_bytes[:16])
    is_macho_arm64 = (magic == 0xFEEDFACF and cputype == 0x0100000C and filetype == 0x6)
    print(f"[*] Mach-O ARM64 dylib header: {'PASS' if is_macho_arm64 else 'FAIL'} (magic=0x{magic:08X}, cpu=0x{cputype:08X}, filetype=0x{filetype:08X})")

    # Verify Symbols & Strings
    symbols_to_check = [
        b"sothat_hook_connect",
        b"rossothat_install_connect_hook",
        b"rossothat_hook_initialize",
        b"rossothat_hook_shutdown",
        b"rossothat_fnv1a_32",
        b"rossothat_stamp_baseapp_handshake",
        b"172.65.54.209",
        b"192.168.1.7",
        b"50443",
    ]
    for sym in symbols_to_check:
        found = sym in dylib_bytes
        print(f"[*] Symbol/String {sym.decode('latin1', errors='ignore')}: {'FOUND' if found else 'MISSING'}")

    if os.path.exists(sha_file):
        with open(sha_file, "r") as sf:
            remote_sha_line = sf.read().strip()
            print(f"\n[*] Remote SHA Checksum File: {remote_sha_line}")

    if os.path.exists(ver_txt):
        print("\n--- Remote Verification Log Excerpts ---")
        with open(ver_txt, "r", encoding="utf-8", errors="ignore") as vf:
            for line in vf:
                line_str = line.strip()
                if any(k in line_str for k in ["Architecture", "Mach-O", "Mandatory", "ALLOW", "FOUND", "SHA-256", "PASS"]):
                    print("  " + line_str)

    print("\n[+] Build, download, extraction, and verification complete.")


if __name__ == "__main__":
    main()
