import os, re, hashlib
from pathlib import Path

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

print("=== CALCULATING CURRENT HASHES ===")
artifacts = [
    "RoS-Legacy-iOS.ipa",
    "extracted/Payload/client.app/client",
    "ros_phase6B_7_1_checksum_padding_evidence_report.md",
    "ros_phase6B_7_2_pbc_padding_checksum_validation_report.md",
    "ros_phase6B_7_3_independent_audit_report.md",
    "ros_phase6B_8_local_synthetic_gateway_report.md",
    "ros_phase6B_8_1_independent_gateway_audit_report.md",
    "phase6B_8_1_audit/independent_reconstruction.py",
    "phase6B_8_1_audit/verify_engine_comparison.py"
]

current_hashes = {}
for a in artifacts:
    p = Path(a)
    if p.exists():
        h = get_sha256(p)
        current_hashes[a] = h
        print(f"{a}: {h} ({p.stat().st_size} bytes)")
    else:
        print(f"{a}: NOT FOUND")

print("\n=== SEARCHING HISTORICAL HASHES IN PREVIOUS REPORTS ===")
md_files = list(Path(".").glob("*.md"))
for md in md_files:
    content = md.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"([0-9a-fA-F]{64})", content)
    if matches:
        print(f"In {md.name}:")
        for m in matches:
            print(f"  Found 64-hex: {m}")
