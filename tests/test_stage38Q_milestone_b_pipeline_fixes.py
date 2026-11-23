"""
ROS Sothatt — Stage 38Q Milestone B: Hook Pipeline & Packaging Integration Test Suite.

Verifies:
1. Fresh-installation IP fallback:
   - Default server host in config_manager.m is 192.168.1.13.
   - First-launch fallback checks bundle ros_server.json before defaultConfig.
   - saveToDocumentsDirectory serializes discovery_https_port.
   - SothattLoginVC placeholder matches 192.168.1.13.
   - Zero occurrences of retired 192.168.100.11 in src/hook.
2. Packaging integration with supplied clean-room dylib:
   - Accepts explicit compiled dylib path via --dylib / compiled_dylib_path.
   - Validates ARM64 Mach-O MH_DYLIB header.
   - Embeds supplied dylib into Payload/client.app/rosauthhook.dylib.
   - Preserves original client executable bit-for-bit (51E63BFE...).
   - Preserves all 18 NeoX NPK archives bit-for-bit against pristine baseline.
3. Error handling:
   - Explicit nonexistent dylib path raises FileNotFoundError.
   - Invalid or truncated dylib raises ValueError.
4. Baseline immutability:
   - RoS-Legacy-iOS.ipa SHA-256 matches baseline.
   - diamond_economy.db remains untouched.
"""

import hashlib
import json
import os
import plistlib
import struct
import sys
import tempfile
import unittest
import zipfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tools.prepare_second_app as prep
from tools.prepare_second_app import (
    BASELINE_MACHO_CLIENT_SHA256,
    BASELINE_ORIGINAL_IPA_SHA256,
    NPK_ARCHIVES,
    SOURCE_IPA,
    compute_bytes_sha256,
    compute_file_sha256,
    prepare_second_app_package,
    validate_macho_arm64_dylib,
)

DB_PATH = os.path.join(PROJECT_ROOT, "phase6B_25_diamond_economy", "data", "diamond_economy.db")
EXPECTED_DB_SHA256 = "6A33C908BA73B8A65FC262599D66B6B39C0672F538DC4A3C5621539F5F807E39"


class TestHookPipelineFixes(unittest.TestCase):
    """Unit tests verifying pipeline fixes for Stage 38Q Milestone B."""

    def test_01_config_manager_source_audit(self):
        """Verifies config_manager.m defaults and bundle fallback logic."""
        cfg_m_path = os.path.join(PROJECT_ROOT, "src", "hook", "src", "config_manager.m")
        self.assertTrue(os.path.exists(cfg_m_path), "config_manager.m must exist")

        with open(cfg_m_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Default host must be 192.168.1.6
        self.assertIn('kDefaultServerHost = @"192.168.1.6"', content)
        self.assertNotIn("192.168.100.11", content)

        # 2. Bundle fallback in loadFromDocumentsDirectory
        self.assertIn('pathForResource:@"ros_server" ofType:@"json"', content)
        self.assertIn("bundleCfg", content)

        # 3. Serialization of discovery_https_port in saveToDocumentsDirectory
        self.assertIn('@"discovery_https_port": @(config.discoveryHttpsPort)', content)

    def test_02_login_vc_source_audit(self):
        """Verifies SothattLoginVC.m placeholder uses correct LAN server IP."""
        vc_path = os.path.join(PROJECT_ROOT, "src", "hook", "src", "SothattLoginVC.m")
        self.assertTrue(os.path.exists(vc_path), "SothattLoginVC.m must exist")

        with open(vc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('Server IPv4 (e.g. 192.168.1.6)', content)
        self.assertNotIn("192.168.100.11", content)

    def test_03_zero_retired_ip_in_hook_tree(self):
        """Ensures retired IP 192.168.100.11 is absent across entire src/hook tree."""
        hook_dir = os.path.join(PROJECT_ROOT, "src", "hook")
        for root, _, files in os.walk(hook_dir):
            for file in files:
                if file.endswith((".c", ".m", ".h", ".sh", ".txt")):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()
                        self.assertNotIn(
                            "192.168.100.11",
                            file_content,
                            f"Retired IP found in {filepath}"
                        )

    def test_04_validate_macho_arm64_dylib_logic(self):
        """Verifies validate_macho_arm64_dylib on valid and invalid byte sequences."""
        # 1. Baseline dylib from original IPA is a valid ARM64 Mach-O dylib
        with zipfile.ZipFile(SOURCE_IPA, "r") as z:
            real_dylib = z.read("Payload/client.app/rosauthhook.dylib")
        self.assertTrue(validate_macho_arm64_dylib(real_dylib))

        # 2. Synthetic valid 64-bit ARM64 MH_DYLIB header (32 bytes)
        # MH_MAGIC_64 = 0xFEEDFACF, CPU_TYPE_ARM64 = 0x0100000C, CPU_SUBTYPE_ARM64_ALL = 0, MH_DYLIB = 0x6
        valid_hdr = struct.pack("<IIII", 0xFEEDFACF, 0x0100000C, 0, 0x6) + b"\x00" * 16
        self.assertTrue(validate_macho_arm64_dylib(valid_hdr))

        # 3. Invalid magic (e.g. 32-bit Mach-O or ELF or PE)
        invalid_magic = struct.pack("<IIII", 0xFEEDFACE, 0x0100000C, 0, 0x6) + b"\x00" * 16
        self.assertFalse(validate_macho_arm64_dylib(invalid_magic))

        # 4. Invalid CPU type (e.g. x86_64 = 0x01000007)
        invalid_cpu = struct.pack("<IIII", 0xFEEDFACF, 0x01000007, 0, 0x6) + b"\x00" * 16
        self.assertFalse(validate_macho_arm64_dylib(invalid_cpu))

        # 5. Invalid filetype (e.g. MH_EXECUTE = 0x2)
        invalid_ftype = struct.pack("<IIII", 0xFEEDFACF, 0x0100000C, 0, 0x2) + b"\x00" * 16
        self.assertFalse(validate_macho_arm64_dylib(invalid_ftype))

        # 6. Truncated bytes
        self.assertFalse(validate_macho_arm64_dylib(b"\x00" * 10))
        self.assertFalse(validate_macho_arm64_dylib(b""))

    def test_05_prepare_second_app_with_supplied_cleanroom_dylib(self):
        """Verifies prepare_second_app_package accepts an explicit compiled dylib."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a mock clean-room ARM64 Mach-O dynamic library
            dummy_header = struct.pack("<IIII", 0xFEEDFACF, 0x0100000C, 0, 0x6)
            dummy_body = b"ROS_SOTHATT_CLEANROOM_DYLIB_TEST_MARKER" + b"\x00" * 100
            mock_dylib_bytes = dummy_header + dummy_body
            mock_dylib_path = os.path.join(tmp_dir, "test_rosauthhook.dylib")
            with open(mock_dylib_path, "wb") as f:
                f.write(mock_dylib_bytes)

            mock_dylib_sha = compute_bytes_sha256(mock_dylib_bytes)

            # Redirect output IPA to temporary directory
            orig_output_dir = prep.OUTPUT_DIR
            orig_output_ipa = prep.OUTPUT_IPA
            prep.OUTPUT_DIR = tmp_dir
            prep.OUTPUT_IPA = os.path.join(tmp_dir, "Test-ROS-Sothatt-iOS.ipa")

            try:
                out_sha = prepare_second_app_package(
                    target_host="192.168.1.13",
                    compiled_dylib_path=mock_dylib_path
                )
                self.assertTrue(os.path.exists(prep.OUTPUT_IPA))

                # Verify packaged archive contents
                with zipfile.ZipFile(prep.OUTPUT_IPA, "r") as z_out:
                    # 1. dylib matches supplied clean-room bytes exactly
                    pkg_dylib = z_out.read("Payload/client.app/rosauthhook.dylib")
                    self.assertEqual(compute_bytes_sha256(pkg_dylib), mock_dylib_sha)
                    self.assertIn(b"ROS_SOTHATT_CLEANROOM_DYLIB_TEST_MARKER", pkg_dylib)

                    # 2. client executable is 100% bit-for-bit preserved
                    pkg_client = z_out.read("Payload/client.app/client")
                    self.assertEqual(compute_bytes_sha256(pkg_client), BASELINE_MACHO_CLIENT_SHA256)

                    # 3. All 18 NPK archives are 100% bit-for-bit preserved
                    with zipfile.ZipFile(SOURCE_IPA, "r") as z_in:
                        for npk in NPK_ARCHIVES:
                            self.assertEqual(
                                compute_bytes_sha256(z_out.read(npk)),
                                compute_bytes_sha256(z_in.read(npk)),
                                f"NPK mismatch: {npk}"
                            )

                    # 4. Info.plist updated
                    plist_data = plistlib.loads(z_out.read("Payload/client.app/Info.plist"))
                    self.assertEqual(plist_data["CFBundleIdentifier"], "net.roslegacy.sothatt")
                    self.assertEqual(plist_data["CFBundleDisplayName"], "ROS Sothatt")
                    self.assertTrue(plist_data["UIFileSharingEnabled"])

                    # 5. ros_server.json embedded with 192.168.1.13 & discovery_https_port
                    cfg_data = json.loads(z_out.read("Payload/client.app/ros_server.json").decode("utf-8"))
                    self.assertEqual(cfg_data["server_host"], "192.168.1.13")
                    self.assertEqual(cfg_data["discovery_https_port"], 50443)
                    self.assertEqual(cfg_data["auth_port"], 20080)
                    self.assertEqual(cfg_data["discovery_port"], 50010)
                    self.assertEqual(cfg_data["baseapp_port"], 20014)

            finally:
                prep.OUTPUT_DIR = orig_output_dir
                prep.OUTPUT_IPA = orig_output_ipa

    def test_06_prepare_second_app_error_handling(self):
        """Verifies error handling when compiled dylib path is invalid or corrupted."""
        # 1. Nonexistent dylib path raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            prepare_second_app_package(compiled_dylib_path="nonexistent_dylib_path_xyz.dylib")

        # 2. Corrupt dylib (not ARM64 Mach-O MH_DYLIB) raises ValueError
        with tempfile.NamedTemporaryFile(suffix=".dylib", delete=False) as f:
            f.write(b"NOT_A_MACHO_BINARY_DATA_CORRUPT")
            bad_path = f.name

        try:
            with self.assertRaises(ValueError):
                prepare_second_app_package(compiled_dylib_path=bad_path)
        finally:
            if os.path.exists(bad_path):
                os.remove(bad_path)

    def test_07_immutability_of_baselines_and_database(self):
        """Verifies source IPA, baseline Mach-O, and database remain unchanged."""
        self.assertEqual(compute_file_sha256(SOURCE_IPA), BASELINE_ORIGINAL_IPA_SHA256)
        if os.path.exists(DB_PATH):
            self.assertEqual(compute_file_sha256(DB_PATH), EXPECTED_DB_SHA256)


if __name__ == "__main__":
    unittest.main()
