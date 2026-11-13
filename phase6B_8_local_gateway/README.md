# ROS Sothat — Phase 6.2B.8: Local Synthetic Mercury UDP Gateway Prototype

This directory contains the local synthetic Mercury UDP gateway prototype developed for **ROS Sothat**.
This prototype demonstrates stateful communication, Blowfish Plaintext Block Chaining (PBC) encryption, single-byte trailer padding, and post-decryption 32-bit XOR checksum validation over local UDP sockets bound strictly to `127.0.0.1`.

---

## 1. Security & Isolation Controls

- **Strict Localhost Binding:** The gateway binds exclusively to `127.0.0.1`. A hard startup assertion halts execution immediately if any non-localhost interface (e.g. `0.0.0.0`, LAN, or WAN) is configured.
- **Zero External Network Traffic:** No sockets connect to remote hosts, routers, or external networks.
- **Zero Database Access:** No imports or connections to PostgreSQL, Redis, or Alembic migrations.
- **Pure Synthetic Identifiers:** Uses synthetic Blowfish keys, synthetic account tokens, and synthetic channel identifiers.
- **Crash Immunity:** Handles truncated, unaligned, bit-flipped, or oversized datagram floods without crashing.

---

## 2. Architecture & File Layout

| Module | Description |
|---|---|
| `config.py` | Configuration settings, default port (30042), master synthetic keys, and `127.0.0.1` startup assertion. |
| `logging_utils.py` | Safe, redaction-enforced structured telemetry logger and terminal status reporter. |
| `packet_parser.py` | Low-level Mercury framing: header flags word (offset 0) and reverse-order footers unpacking from tail. |
| `protocol_engine.py` | Integrates Blowfish PBC, single-byte trailer padding (wastage count), and 32-bit XOR checksum. |
| `channel_manager.py` | Stateful channel tracker (Channel ID, session state, sequence progression, duplicate rejection, ACK queues). |
| `gateway.py` | Local UDP server running on `127.0.0.1` with multi-client channel dispatch and robust exception handling. |
| `synthetic_client.py` | Local UDP test client constructing encrypted Mercury packets and validating returned responses and ACKs. |
| `tests/test_unit.py` | Unit tests for golden vectors, padding boundaries, checksum alignment, and bad flags. |
| `tests/test_channel_state.py` | Tests for channel lifecycle, sequence tracking, duplicate detection, and channel isolation. |
| `tests/test_security.py` | Tests for 127.0.0.1 enforcement, forbidden 0.0.0.0 binding, fuzzing resilience, and zero DB access. |
| `tests/test_udp_integration.py` | End-to-end integration tests over local UDP sockets covering all 14 required scenarios. |
| `tests/run_all_tests.py` | Master test runner executing and reporting each category separately. |

---

## 3. Running the Automated Tests

To execute the entire 28-test suite:

```powershell
python phase6B_8_local_gateway\tests\run_all_tests.py
```

To run individual test categories:

```powershell
# 1. Pure unit tests
python phase6B_8_local_gateway\tests\test_unit.py -v

# 2. Channel state machine tests
python phase6B_8_local_gateway\tests\test_channel_state.py -v

# 3. Security and boundary tests
python phase6B_8_local_gateway\tests\test_security.py -v

# 4. Local UDP integration tests (14 scenarios)
python phase6B_8_local_gateway\tests\test_udp_integration.py -v
```
