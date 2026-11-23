"""
ROS Sothatt — Stage 38Q-C: Second App Packaging & Clean-Room Hook Preparation Tool.

Prepares the separate ROS Sothatt application package (ROS-Sothatt-iOS.ipa):
- Derived strictly from pristine baseline RoS-Legacy-iOS.ipa (D1F638AD...)
- Target Bundle Identifier: net.roslegacy.sothatt
- Target Display Name: ROS Sothatt
- Target URL Scheme: rossothat://
- Enables UIFileSharingEnabled and LSSupportsOpeningDocumentsInPlace
- Embeds Documents/ros_server.json default configuration
- Preserves original ARM64 client executable bit-for-bit (51E63BFE...)
- Preserves all 18 NeoX NPK archives bit-for-bit
- Installs clean-room configured rosauthhook.dylib in separate App 2 package
- Output path: build/stage38_sothatt/ROS-Sothatt-iOS.ipa
- Enforces strict non-modification of original baseline archives
"""

import hashlib
import json
import os
import plistlib
import shutil
import struct
import sys
import time
import zipfile
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BASELINE_ORIGINAL_IPA_SHA256 = "D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55"
BASELINE_MACHO_CLIENT_SHA256 = "51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6"

SOURCE_IPA = os.path.join(PROJECT_ROOT, "RoS-Legacy-iOS.ipa")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "build", "stage38_sothatt")
OUTPUT_IPA = os.path.join(OUTPUT_DIR, "ROS-Sothatt-iOS.ipa")

NPK_ARCHIVES = [
    "Payload/client.app/assets.npk",
    "Payload/client.app/script.npk",
    "Payload/client.app/res/animators.npk",
    "Payload/client.app/res/common.npk",
    "Payload/client.app/res/cubemap.npk",
    "Payload/client.app/res/decal.npk",
    "Payload/client.app/res/effect_cache.npk",
    "Payload/client.app/res/emote.npk",
    "Payload/client.app/res/entities.npk",
    "Payload/client.app/res/pet.npk",
    "Payload/client.app/res/props.npk",
    "Payload/client.app/res/roads.npk",
    "Payload/client.app/res/scenario.npk",
    "Payload/client.app/res/shader.npk",
    "Payload/client.app/res/textures.npk",
    "Payload/client.app/res/track.npk",
    "Payload/client.app/res/ui.npk",
    "Payload/client.app/res/weather.npk",
]

DEFAULT_SERVER_HOST = os.environ.get("ROS_SERVER_HOST", "192.168.1.6")

DEFAULT_SERVER_CONFIG = {
    "version": 1,
    "server_host": DEFAULT_SERVER_HOST,
    "auth_port": 20080,
    "discovery_port": 50010,
    "discovery_https_port": 50443,
    "baseapp_port": 20014,
    "cellapp_port": 20002,
    "auth_path": "/v2/ros/login_mobile_ios_v2",
    "discovery_path": "/server_list_ios.txt",
    "timeout_seconds": 5.0,
    "tls_enabled": False
}


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def compute_bytes_sha256(data: bytes) -> str:
    """Computes SHA-256 hash of in-memory bytes."""
    return hashlib.sha256(data).hexdigest().upper()


def validate_macho_arm64_dylib(data: bytes) -> bool:
    """Validates that bytes represent a 64-bit ARM64 Mach-O dynamic library."""
    if len(data) < 32:
        return False
    magic, cputype, cpusubtype, filetype = struct.unpack("<IIII", data[:16])
    # MH_MAGIC_64 = 0xfeedfacf, CPU_TYPE_ARM64 = 0x0100000c, MH_DYLIB = 0x6
    return magic == 0xFEEDFACF and cputype == 0x0100000C and filetype == 0x6


def prepare_sothatt_dylib(original_dylib_bytes: bytes, target_host: str = DEFAULT_SERVER_HOST) -> bytes:
    """
    Prepares the separate ROS Sothatt dynamic library:
    - Retains ARM64 Mach-O structure, segments, and load commands.
    - Reconfigures hardcoded endpoint strings in __cstring section to target
      the private ROS Sothatt backend over local LAN.
    - Preserves exact memory allocation and byte offsets.
    """
    dylib = bytearray(original_dylib_bytes)

    # 1. Update Authentication URL
    # Original: https://api.roslegacy.net/v2/ros/login_mobile_ios_v2 (52 bytes)
    # Private:  http://{target_host}:20080/v2/ros/login_mobile_ios_v2 (52 bytes for 192.168.1.7)
    # Target endpoint /v2/ros/login_mobile_ios_v2 is standardized for LegacyMobileAuthServer.
    orig_auth = b"https://api.roslegacy.net/v2/ros/login_mobile_ios_v2"
    auth_route = "/v2/ros/login_mobile_ios_v2" if len(f"http://{target_host}:20080/v2/ros/login_mobile_ios_v2") <= len(orig_auth) else "/v2/ros/login_mobile_ios"
    priv_auth = f"http://{target_host}:20080{auth_route}".encode("utf-8")
    if len(priv_auth) > len(orig_auth):
        raise ValueError(
            f"priv_auth '{priv_auth.decode()}' length ({len(priv_auth)} bytes) "
            f"exceeds original buffer capacity ({len(orig_auth)} bytes)!"
        )
    priv_auth_padded = priv_auth + b"\x00" * (len(orig_auth) - len(priv_auth))
    pos_auth = dylib.find(orig_auth)
    if pos_auth == -1:
        raise ValueError("Original authentication endpoint not found in rosauthhook.dylib binary!")
    dylib[pos_auth : pos_auth + len(orig_auth)] = priv_auth_padded

    # 2. Update Discovery CDN URL
    # Original: https://cdn.mobile.roslegacy.net/ios/ (36 bytes)
    # Private:  http://{target_host}:50010/ios/     (30 bytes for 192.168.1.13)
    orig_disc = b"https://cdn.mobile.roslegacy.net/ios/"
    priv_disc = f"http://{target_host}:50010/ios/".encode("utf-8")
    if len(priv_disc) > len(orig_disc):
        raise ValueError(
            f"priv_disc '{priv_disc.decode()}' length ({len(priv_disc)} bytes) "
            f"exceeds original buffer capacity ({len(orig_disc)} bytes)!"
        )
    priv_disc_padded = priv_disc + b"\x00" * (len(orig_disc) - len(priv_disc))
    pos_disc = dylib.find(orig_disc)
    if pos_disc == -1:
        raise ValueError("Original discovery CDN endpoint not found in rosauthhook.dylib binary!")
    dylib[pos_disc : pos_disc + len(orig_disc)] = priv_disc_padded

    # Post-patch verification assertions
    patched_bytes = bytes(dylib)
    assert orig_auth not in patched_bytes, "FATAL: Original auth URL still present in patched dylib!"
    assert priv_auth in patched_bytes, "FATAL: Patched auth URL missing from dylib!"
    assert orig_disc not in patched_bytes, "FATAL: Original discovery CDN URL still present in patched dylib!"
    assert priv_disc in patched_bytes, "FATAL: Patched discovery CDN URL missing from dylib!"
    assert len(patched_bytes) == len(original_dylib_bytes), "FATAL: Patched dylib byte size altered!"

    return patched_bytes


def update_info_plist(plist_bytes: bytes, target_host: str = DEFAULT_SERVER_HOST) -> bytes:
    """
    Updates client Info.plist to decouple App 2 from App 1:
    - CFBundleIdentifier = net.roslegacy.sothatt
    - CFBundleDisplayName = ROS Sothatt
    - CFBundleName = ROS Sothatt
    - Registers rossothat:// URL scheme
    - Enables UIFileSharingEnabled and LSSupportsOpeningDocumentsInPlace
    """
    plist = plistlib.loads(plist_bytes)

    plist["CFBundleIdentifier"] = "net.roslegacy.sothatt"
    plist["CFBundleDisplayName"] = "ROS Sothatt"
    plist["CFBundleName"] = "ROS Sothatt"

    # Update URL Schemes: change rosmobile to rossothat
    url_types = plist.get("CFBundleURLTypes", [])
    for entry in url_types:
        schemes = entry.get("CFBundleURLSchemes", [])
        if "rosmobile" in schemes:
            idx = schemes.index("rosmobile")
            schemes[idx] = "rossothat"
        if entry.get("CFBundleURLName") == "rosmobile":
            entry["CFBundleURLName"] = "rossothat"
    plist["CFBundleURLTypes"] = url_types

    # Enable iTunes and Files app document sharing for ros_server.json access
    plist["UIFileSharingEnabled"] = True
    plist["LSSupportsOpeningDocumentsInPlace"] = True

    # App Transport Security: explicitly permit local RFC1918 networking for iOS 16.7.16.
    # Keep NSAllowsArbitraryLoads = YES and NSAllowsLocalNetworking = YES.
    # Remove numeric IP entries from NSExceptionDomains as iOS 16 ATS fails on raw IPs in exception domains.
    ats = plist.setdefault("NSAppTransportSecurity", {})
    ats["NSAllowsArbitraryLoads"] = True
    ats["NSAllowsLocalNetworking"] = True
    ats.pop("NSExceptionDomains", None)

    return plistlib.dumps(plist, fmt=plistlib.FMT_XML)


def prepare_second_app_package(
    target_host: Optional[str] = None,
    compiled_dylib_path: Optional[str] = None,
    output_ipa_path: Optional[str] = None
) -> str:
    """Main packaging routine assembling ROS-Sothatt-iOS.ipa."""
    if target_host is None:
        target_host = DEFAULT_SERVER_HOST

    effective_output_ipa = os.path.abspath(output_ipa_path) if output_ipa_path else OUTPUT_IPA

    print("=" * 72)
    print(" [ROS SOTHATT] STAGE 38Q-C: SEPARATE APP PACKAGE PREPARATION")
    print(f" Target Host: {target_host}")
    print(f" Package: {os.path.basename(effective_output_ipa)} (net.roslegacy.sothatt)")
    print("=" * 72)

    # Step 1: Verify Pristine Baselines
    print("[*] Step 1: Verifying pristine original IPA baseline...")
    if not os.path.exists(SOURCE_IPA):
        raise FileNotFoundError(f"Missing source IPA: {SOURCE_IPA}")

    orig_sha = compute_file_sha256(SOURCE_IPA)
    print(f"    Source IPA SHA-256: {orig_sha}")
    if orig_sha != BASELINE_ORIGINAL_IPA_SHA256:
        raise ValueError(f"Source IPA hash mismatch! Expected {BASELINE_ORIGINAL_IPA_SHA256}, got {orig_sha}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 2: Read baseline archive entries
    print("[*] Step 2: Inspecting and preparing archive contents...")
    with zipfile.ZipFile(SOURCE_IPA, "r") as z_in:
        # Verify Mach-O client hash
        client_data = z_in.read("Payload/client.app/client")
        client_sha = compute_bytes_sha256(client_data)
        print(f"    Original client Mach-O SHA-256: {client_sha}")
        if client_sha != BASELINE_MACHO_CLIENT_SHA256:
            raise ValueError(f"Mach-O client hash mismatch! Got {client_sha}")

        # Compute baseline NPK hashes for bit-for-bit assertion
        baseline_npk_hashes = {}
        for npk in NPK_ARCHIVES:
            baseline_npk_hashes[npk] = compute_bytes_sha256(z_in.read(npk))

        # Prepare modified Info.plist
        raw_plist = z_in.read("Payload/client.app/Info.plist")
        updated_plist = update_info_plist(raw_plist, target_host=target_host)

        # Prepare clean-room rosauthhook.dylib
        is_cleanroom_dylib = False
        resolved_dylib_path = None
        if compiled_dylib_path:
            if not os.path.exists(compiled_dylib_path):
                raise FileNotFoundError(f"Specified compiled dylib not found: {compiled_dylib_path}")
            resolved_dylib_path = os.path.abspath(compiled_dylib_path)
        elif os.path.exists(os.path.join(PROJECT_ROOT, "src", "hook", "rosauthhook.dylib")):
            resolved_dylib_path = os.path.join(PROJECT_ROOT, "src", "hook", "rosauthhook.dylib")

        if resolved_dylib_path:
            print(f"[*] Step 2a: Using compiled clean-room dylib from {resolved_dylib_path}...")
            with open(resolved_dylib_path, "rb") as df:
                sothatt_dylib = df.read()
            if not validate_macho_arm64_dylib(sothatt_dylib):
                raise ValueError(f"Supplied dylib {resolved_dylib_path} is not a valid ARM64 Mach-O MH_DYLIB!")
            is_cleanroom_dylib = True
            print(f"    [PASS] Clean-room dylib validated ({len(sothatt_dylib)} bytes, SHA-256: {compute_bytes_sha256(sothatt_dylib)})")
        else:
            print("[*] Step 2a: No compiled clean-room dylib found; using baseline dylib with string patching...")
            raw_dylib = z_in.read("Payload/client.app/rosauthhook.dylib")
            sothatt_dylib = prepare_sothatt_dylib(raw_dylib, target_host=target_host)

        # Configuration file
        active_config = dict(DEFAULT_SERVER_CONFIG)
        active_config["server_host"] = target_host
        config_json = json.dumps(active_config, indent=2).encode("utf-8")
        server_list_name_txt = b"server_list_ios.txt\n"

        # Step 3: Write new separate IPA
        print(f"[*] Step 3: Writing separate package to {effective_output_ipa}...")
        with zipfile.ZipFile(effective_output_ipa, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                if item.filename == "Payload/client.app/Info.plist":
                    z_out.writestr(item, updated_plist)
                elif item.filename == "Payload/client.app/rosauthhook.dylib":
                    z_out.writestr(item, sothatt_dylib)
                elif item.filename.startswith("Payload/client.app/_CodeSignature/"):
                    # Omit old NetEase code signature so signing tool applies new profile cleanly
                    continue
                else:
                    data = z_in.read(item.filename)
                    z_out.writestr(item, data)

            # Inject default ros_server.json into bundle for initial run
            z_out.writestr("Payload/client.app/ros_server.json", config_json)
            z_out.writestr("Payload/client.app/server_list_file_name.txt", server_list_name_txt)

    # Step 4: Verification of generated package
    print(f"[*] Step 4: Verifying assembled {os.path.basename(effective_output_ipa)}...")
    output_sha = compute_file_sha256(effective_output_ipa)
    print(f"    Output IPA SHA-256: {output_sha}")

    with zipfile.ZipFile(effective_output_ipa, "r") as z_ver:
        # Verify client Mach-O preserved bit-for-bit
        ver_client = z_ver.read("Payload/client.app/client")
        ver_client_sha = compute_bytes_sha256(ver_client)
        if ver_client_sha != BASELINE_MACHO_CLIENT_SHA256:
            raise ValueError(f"Packaged client Mach-O corrupted! Hash: {ver_client_sha}")
        print(f"    [PASS] client Mach-O bit-for-bit match: {ver_client_sha}")

        # Verify Info.plist
        ver_plist = plistlib.loads(z_ver.read("Payload/client.app/Info.plist"))
        assert ver_plist["CFBundleIdentifier"] == "net.roslegacy.sothatt"
        assert ver_plist["CFBundleDisplayName"] == "ROS Sothatt"
        assert ver_plist["UIFileSharingEnabled"] is True
        print("    [PASS] Bundle Identifier: net.roslegacy.sothatt")
        print("    [PASS] Display Name: ROS Sothatt")
        print("    [PASS] UIFileSharingEnabled: True")

        # Verify NPK packages preserved bit-for-bit
        for npk in NPK_ARCHIVES:
            assert npk in z_ver.namelist(), f"Missing {npk}"
            ver_npk_sha = compute_bytes_sha256(z_ver.read(npk))
            if ver_npk_sha != baseline_npk_hashes[npk]:
                raise ValueError(f"Packaged NPK corrupted! {npk}: {ver_npk_sha} != {baseline_npk_hashes[npk]}")
        print(f"    [PASS] All {len(NPK_ARCHIVES)} NPK archives verified bit-for-bit unchanged.")

        # Verify dylib in output package
        ver_dylib = z_ver.read("Payload/client.app/rosauthhook.dylib")
        assert len(ver_dylib) == len(sothatt_dylib), "Packaged dylib size mismatch!"
        assert compute_bytes_sha256(ver_dylib) == compute_bytes_sha256(sothatt_dylib), "Packaged dylib SHA-256 mismatch!"
        if is_cleanroom_dylib:
            print(f"    [PASS] Clean-room compiled dylib verified in package ({len(ver_dylib)} bytes, SHA-256: {compute_bytes_sha256(ver_dylib)})")
        else:
            expected_auth = priv_auth
            expected_disc = f"http://{target_host}:50010/ios/".encode("utf-8")
            assert expected_auth in ver_dylib, f"Expected auth URL {expected_auth} not in dylib!"
            assert expected_disc in ver_dylib, f"Expected discovery URL {expected_disc} not in dylib!"
            assert b"https://api.roslegacy.net/v2/ros/login_mobile_ios_v2" not in ver_dylib, "Old auth URL still in dylib!"
            assert b"https://cdn.mobile.roslegacy.net/ios/" not in ver_dylib, "Old discovery CDN URL still in dylib!"
            print(f"    [PASS] Authentication URL verified: {expected_auth.decode('utf-8')}")
            print(f"    [PASS] Discovery CDN URL verified: {expected_disc.decode('utf-8')}")

    print("=" * 72)
    print(" [ROS SOTHATT] STAGE 38Q-C: PACKAGING COMPLETE AND VERIFIED")
    print("=" * 72)
    return output_sha


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare separate ROS Sothatt testing package")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST, help="Target LAN host IP (default: 192.168.1.6)")
    parser.add_argument("--dylib", default=None, help="Path to clean-room compiled rosauthhook.dylib")
    parser.add_argument("--output", default=None, help="Custom output path for generated IPA")
    args = parser.parse_args()
    prepare_second_app_package(target_host=args.host, compiled_dylib_path=args.dylib, output_ipa_path=args.output)
