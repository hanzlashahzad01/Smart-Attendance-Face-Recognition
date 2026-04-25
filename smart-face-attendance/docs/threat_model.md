# Threat Model

## High-Level Threats

| Threat Vector | Risk Level | Description | Current Mitigation | Future Work |
|---------------|------------|-------------|--------------------|-------------|
| **Database Theft** | High | Attacker copies `attendance.db` | Embeddings are Fernet encrypted. Only ID and name are plaintext. | Move to Hashicorp Vault for key management. |
| **Key Compromise** | Medium | Attacker gains access to `.env` | File permissions limit reading `.env`. Key + DB implies full compromise. | Rotate keys frequently; use HSMs. |
| **Spoofing (Print/Screen)** | High | Attacker presents a photo to the camera to trick the system | Tuned confidence threshold | **Liveness Detection** (Blink/Smile constraints) |
| **Injection Attacks** | Low | SQL Injection via Streamlit UI | SQLite parameterized queries are used consistently (`?`). | Continuous vulnerability scanning. |
| **Insider Threat** | Medium | Rogue Admin deleting logs | `audit_logs` tracked. SQLite lacks immutability. | Send Audit Logs to Append-Only cloud logging. |

## Future Security Roadmap
1. **Liveness Detection**: Introduce 3D depth checks or blink-detection logic to prevent spoofing with 2D images.
2. **Federated Learning**: Train models on edge devices without aggregating individual data.
3. **Differential Privacy**: Applying noise to data queries ensuring user anonymity during statistical reviews.
