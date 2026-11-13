# ROS Sothat — Phase P02.1: OTP Security Review & HMAC Remediation
**Document ID:** `01_otp_security_review.md`  
**System:** ROS Sothat Private Server Platform (`ros-private-server`)  
**Phase:** P02.1 (Security Review & Integration Verification)  
**Date:** November 2026  
**Status:** COMPLETED & VERIFIED  

---

## 1. Executive Security Evaluation: Salted SHA-256 vs. HMAC-SHA256

In Phase P02, the initial OTP generation mechanism stored codes as salted SHA-256 digests:
$$\text{Digest} = \text{SHA256}(\text{salt} \parallel \text{code})$$

### 1.1 The Vulnerability of 6-Digit Codes Under Pure Hashing
A 6-digit numeric verification code provides an entropy space of exactly $10^6$ combinations ($000000$ to $999999$). 
- In the event of an unauthorized database dump or storage backup leak, an adversary gains access to both the `salt` and `otp_hash` columns.
- Because SHA-256 is an unkeyed cryptographic hash function, an attacker can precompute or brute-force all $10^6$ candidates within **10 to 50 milliseconds** on a commodity CPU or GPU.
- If an attacker obtains read access during the 5-minute active window of an OTP, pure salted SHA-256 offers virtually zero resistance to offline code inversion.

### 1.2 The HMAC-SHA256 Remediation
To resolve this structural risk, Phase P02.1 upgrades OTP hashing to a server-side keyed Hash-based Message Authentication Code (HMAC-SHA256):
$$\text{Digest} = \text{HMAC-SHA256}(K_{\text{server}}, \text{salt} \parallel \text{code})$$

Where $K_{\text{server}}$ is a high-entropy secret stored exclusively in server environment variables (`OTP_SECRET_KEY` or `SECRET_KEY`).

#### Security Properties of the Upgraded Implementation:
1. **Zero Database Secret Exposure:** $K_{\text{server}}$ is never stored in the database, SQL backups, or transmitted to clients.
2. **Offline Inversion Resistance:** An attacker who acquires a database dump cannot compute or verify candidate OTPs without the server-side key $K_{\text{server}}$.
3. **Constant-Time Verification:** Digits are validated via `hmac.compare_digest` against side-channel timing attacks.
4. **Stateless Restart Resilience:** Because the HMAC algorithm is deterministic with respect to $(K_{\text{server}}, \text{salt}, \text{code})$, active challenges remain valid across worker or application restarts as long as $K_{\text{server}}$ remains identical.

---

## 2. Key Management & Defensive Guardrails

### 2.1 Configuration Hierarchy
The server resolves the HMAC secret key through a fallback hierarchy:
```python
secret = (settings.OTP_SECRET_KEY or "").strip()
if not secret:
    secret = (settings.SECRET_KEY or "").strip()
```
1. **Dedicated Key (`OTP_SECRET_KEY`):** Recommended for production isolation.
2. **Fallback Key (`SECRET_KEY`):** Ensures backward compatibility for environments with standard FastAPI secret configuration.

### 2.2 Validation Rules
`AccountService.get_otp_hmac_secret()` enforces strict validation prior to any cryptographic operation:
- **Missing Secret:** Raises `ValueError("Missing OTP secret key: neither OTP_SECRET_KEY nor SECRET_KEY is configured.")` if both are empty or whitespace.
- **Insufficient Entropy:** Raises `ValueError("Invalid OTP secret key: must be at least 16 bytes for cryptographic security.")` if the resolved secret has fewer than 16 bytes.
- **Log Sanitation:** The raw secret bytes are never printed, formatted, or emitted to structured log files.

---

## 3. Outstanding Challenge Migration & Invalidation

When upgrading from salted SHA-256 to HMAC-SHA256 on a live or restarting server, outstanding challenges issued prior to the upgrade must not fail silently with generic "wrong password" decrements.

### Safe Invalidation Mechanism:
In `AccountService.verify_otp`:
1. The code is first verified against the current HMAC-SHA256 signature.
2. If verification fails, the service checks whether the code matches the legacy un-keyed SHA-256 formula:
   ```python
   legacy_hash = hashlib.sha256(f"{otp.salt}:{req.code}".encode("utf-8")).hexdigest()
   if hmac.compare_digest(legacy_hash, otp.otp_hash):
       await self.repository.mark_otp_used(otp.id)
       raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Verification code format has been upgraded for security. Please request a new verification code."
       )
   ```
3. **Outcome:**
   - The incompatible legacy OTP row is immediately neutralized (`is_used = True`).
   - The user is notified with an explicit security message instructing them to request a new code.
   - The user is not penalized with failed attempt decrements or confused by bad-password errors.
   - Normal failed attempts (incorrect guesses) decrement `attempts_left` as designed.
