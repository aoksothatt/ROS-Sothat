"""
Master Test Runner for Phase 6.2B.8 Local Synthetic Mercury Gateway
Phase 6.2B.8 - Research & Prototype Only

Executes and reports each test category separately:
1. Pure Algorithmic Unit Tests (Golden PBC, Padding, Checksum, Framing)
2. Channel State Machine Tests (Initialization, Isolation, Progression, Reset)
3. Security & Isolation Tests (127.0.0.1 Binding, Fuzzing, Zero DB Connections)
4. Local UDP Socket Integration Tests (14 Scenarios on 127.0.0.1)
"""

import unittest
import sys
import time
from pathlib import Path

# Add gateway package to sys.path
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

import test_unit
import test_channel_state
import test_security
import test_offline_integration
import test_independent_verification
import test_udp_integration


def run_suite(name: str, suite: unittest.TestSuite):
    print("\n" + "=" * 70)
    print(f" RUNNING CATEGORY: {name}")
    print("=" * 70)
    runner = unittest.TextTestRunner(verbosity=2)
    start = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start
    return {
        "name": name,
        "runs": result.testsRun,
        "errors": len(result.errors),
        "failures": len(result.failures),
        "elapsed": round(elapsed, 3),
        "success": result.wasSuccessful()
    }


def main():
    loader = unittest.TestLoader()
    
    categories = [
        ("1. Pure Algorithmic Unit Tests", loader.loadTestsFromModule(test_unit)),
        ("2. Channel State Machine Tests", loader.loadTestsFromModule(test_channel_state)),
        ("3. Security & Isolation Tests", loader.loadTestsFromModule(test_security)),
        ("4. Offline In-Memory Integration Tests", loader.loadTestsFromModule(test_offline_integration)),
        ("5. Independent Golden Verification Tests", loader.loadTestsFromModule(test_independent_verification)),
        ("6. Local UDP Loopback Integration Tests", loader.loadTestsFromModule(test_udp_integration)),
    ]

    summaries = []
    total_start = time.time()
    for name, suite in categories:
        res = run_suite(name, suite)
        summaries.append(res)
    total_elapsed = time.time() - total_start

    print("\n" + "#" * 70)
    print(" ROS SOTHAT — PHASE 6.2B.8 TEST SUITE SUMMARY")
    print("#" * 70)
    all_success = True
    total_tests = 0
    total_failures = 0
    total_errors = 0

    for s in summaries:
        status_str = "PASS" if s["success"] else "FAIL"
        if not s["success"]:
            all_success = False
        total_tests += s["runs"]
        total_failures += s["failures"]
        total_errors += s["errors"]
        print(f" {s['name']:<40} | {status_str:<4} | Tests: {s['runs']:<2} | Failures: {s['failures']} | Errors: {s['errors']} | Time: {s['elapsed']}s")

    print("-" * 70)
    overall_status = "ALL TESTS PASSED (100%)" if all_success else "TEST SUITE FAILED"
    print(f" OVERALL VERDICT: {overall_status}")
    print(f" Total Tests Run: {total_tests} | Failures: {total_failures} | Errors: {total_errors} | Total Time: {round(total_elapsed, 3)}s")
    print("#" * 70 + "\n")

    if not all_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
