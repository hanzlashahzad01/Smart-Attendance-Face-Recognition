# System Architecture

## Overview
The Smart Attendance System is built primarily around a local Python environment using Streamlit for UI, SQLite for local storage, and DeepFace (via TensorFlow/Keras) for machine learning facial recognition.

## Core Modules

### 1. **Camera & Vision (`src/camera.py`, `admin_panel/app.py`)**
Handles the stream from local hardware. Images are captured, temporarily processed in memory (RAM), and completely discarded after inference. No raw images are written to disk.

### 2. **ML Engine (`src/recognition.py`)**
Integrates with `DeepFace` configured to use `FaceNet` weights.
- **Input:** Single BGR OpenCV Frame.
- **Output:** 128/512-dimensional facial embedding vector.
- **Matching:** Calculates the Cosine Similarity between the incoming live embedding and all database embeddings.

### 3. **Security Layer (`src/encryption.py`)**
- Encrypts embeddings symmetrically using Python `cryptography.fernet.Fernet`.
- Embeddings are json-serialized, UTF-8 encoded, then ciphered before storage (`BLOB`).

### 4. **Database (`src/utils.py`)**
SQLite database with three core tables:
1. `users`: Stores user identity, encrypted biometric data, and retention configurations.
2. `attendance`: Logs events linking check-ins to users based on successful inferences.
3. `audit_logs`: Records transparent, immutable evidence of every sensitive action (enrollment, deletion, login).

### 5. **Admin Interface (`admin_panel/app.py`)**
Provides operations based on Streamlit, allowing easy and quick real-time interaction for authorized personnel. Handles Right-to-Erasure requests and log reporting.
