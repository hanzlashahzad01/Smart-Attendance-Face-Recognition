# 🛡️ Smart Attendance System with Face Recognition (Privacy-Aware)

A privacy-aware face recognition attendance system that securely verifies users in real time and stores encrypted biometric embeddings with robust admin controls and unalterable audit logs.

## 🌟 1. Problem Statement
Manual attendance processes, card swipes, and proxy setups cause significant fraud, time delays, and inefficiency across corporations and educational systems. While biometric attendance solves the proxy problem, it traditionally mandates the highly-invasive act of storing raw face imagery in vulnerable, centralized databases. 

## ⚖️ 2. Why It Matters
Biometrics indisputably save time and ensure absolute accountability. However, the rise of stringent data privacy laws (GDPR, CCPA) dictates a paramount focus on risk minimization. The industry needs a solution that achieves biometric verification **without** compromising the raw identity traits of individuals in an insecure format.

## 🚀 3. Approach
This project operates entirely on the concept of **Ephemeral Processing & Encryption-at-Rest**:
- **FaceNet/DeepFace** models intercept video frames.
- Only mathematical facial boundaries and feature vectors (embeddings) are extracted.
- A **Fernet Symmetric Encryption Layer** immediately sanitizes embeddings into an unintelligible binary payload.
- **Immediate Purging**: Raw image frames never touch disk storage. 
- During check-in, real-time embeddings are compared against decrypted records purely via **Cosine Similarity Thresholding** (>=0.65).

## 📊 4. Results
- **Accuracy**: Dependent directly on lighting quality and camera focus. Tuning `MATCH_THRESHOLD` allows balancing between precise rejection and accepting variability.
- **FAR/FRR**: High threshold (0.8+) inherently drops the False Acceptance Rate (FAR) to near zero but introduces a higher False Rejection Rate (FRR) on occlusions (glasses/masks).
- **Latency**: Near real-time using localized deep learning weights via TensorFlow inference, bypassing cloud transit.

> *Demo features an intuitive Streamlit UI handling both secure enrollments and granular attendance reporting.*

## 🚧 5. Limitations
- **Lighting Sensitivity**: Sharp shadows or aggressive backlighting can hinder contour/landmark detection.
- **Bias**: Open-source models (like FaceNet derivatives) can exhibit performance variances based on skin tone or distinct demographic indicators.
- **Spoofing Risk**: Without True Depth/3D mapping, high-definition digital photographs on smartphones may theoretically bypass the 2D bounding mechanisms.

## 🔐 6. Ethics & Privacy
Compliance out-of-the-box for **GDPR**:
- **Consent Modeling**: Explicit enrollment tracking with automatic retention expiration mapping (e.g. 90-day defaults).
- **Right to Erasure/Be Forgotten**: A "Delete User" interface physically strips cryptographic profiles, cascading deletion to all mapped attendance histories.
- **Data Minimization**: The database is mathematically irreversible without the disconnected encryption key (`.env`).

## 🔮 7. Future Work
1. **On-Device Inference**: Porting `tflite` weights natively to mobile nodes.
2. **Federated Learning**: Synchronizing inference learning weights collectively without transferring raw embeddings over the network.
3. **Differential Privacy**: Applying randomized noise distributions securely to inference querying.
4. **Multi-Modal Biometrics**: Incorporating Voice or Gait analysis parallel to facial thresholds for enhanced liveness.
5. **Automated Cloud Notifications**: Integrating secure Email and WhatsApp alerts via OAuth2/Twilio gateways for real-time stakeholder reporting (In-Progress).

---
### Installation & Run Instructions

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your encryption key to .env (use src/encryption.py or python crypt utilities to generate a key)
# ENCRYPTION_KEY="..."

# 3. Start the application
streamlit run admin_panel/app.py
```
How to run:
        py -3.10 -m streamlit run smart-face-attendance/admin_panel/app.py
