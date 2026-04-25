# Privacy & Ethics

## GDPR & Privacy-First Design
Biometric data represents a high-risk category of personal information under the General Data Protection Regulation (GDPR). This system implements strict controls and safeguards.

### 1. Data Minimization
We never store raw facial images. Once an analog identity is mathematically represented as a vector (embedding) during enrollment, the raw capture is instantly purged from memory. 

### 2. Consent Model
Enrollment allows setting a `consent_at` timestamp and a customizable `retention_days` limit representing explicit participant approval.

### 3. Right to Erasure
Within the Admin Panel, administrators have access to an instant "Delete User Data" mechanism. This drops all trace of an individual—destroying their encrypted embeddings and removing their check-in history.

### 4. Encryption at Rest
Biometric vectors aren't stored in plaintext arrays. We implement Fernet symmetric encryption. If the SQLite file is stolen, attackers only see encrypted binary blobs—useless without the `.env` encryption key decoupled from the database.

### 5. Automated Data Retention
The system automatically purges User records and identifying Attendance logs once the `retention_days` period has elapsed from the `consent_at` date, ensuring we do not hold data longer than legally or ethically justified.

### 6. Anonymized Diagnostic Monitoring
Internal audit logs and diagnostic views utilize SHA-256 hashed identifiers for users where full name display isn't strictly necessary for the immediate task, following the principle of Privacy-by-Default.

## Ethical Considerations
- **Bias:** DeepFace underlying models might inherit training data biases (lighting variances, varying facial features). The default threshold (`0.65`) is a tunable parameter and should be evaluated on the target population to ensure Fair Acceptance Rates (FAR).
- **Human Override Policy:** A human supervisor must confirm attendance disputes as the model may throw False Rejections (FRR).
- **Proportionality:** Face recognition may be disproportionately invasive for standard workflows. Use cases should transparently justify biometric verification.
