import os
import cv2
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from deepface import DeepFace
import numpy as np
from src.encryption import decrypt_embedding
from src.utils import get_db_connection, log_audit

def extract_embeddings(frame):
    """Extracts all face embeddings from a BGR OpenCV frame using DeepFace (FaceNet)."""
    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        objs = DeepFace.represent(img_path=rgb_frame, model_name="Facenet", enforce_detection=True)
        faces = []
        if objs and len(objs) > 0:
            for obj in objs:
                faces.append((obj["embedding"], obj["facial_area"]))
        return faces
    except Exception as e:
        # No face detected
        pass
    return []

def cosine_similarity(embedding1, embedding2):
    """Calculates cosine similarity between two vectors."""
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def load_all_known_users():
    """Loads and decrypts all user embeddings into memory."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, encrypted_embedding FROM users')
    rows = c.fetchall()
    conn.close()

    users = []
    for row in rows:
        try:
            db_embedding = decrypt_embedding(row['encrypted_embedding'])
            users.append({'id': row['id'], 'name': row['name'], 'embedding': db_embedding})
        except Exception as e:
            log_audit(f"Decryption failure for user {row['id']}: {str(e)}", actor="System")
            continue
    return users

def find_match_in_list(embedding, threshold, known_users):
    """Matches a given embedding against the loaded database of decrypted embeddings."""
    best_match = None
    best_score = -1.0

    for user in known_users:
        similarity = cosine_similarity(embedding, user['embedding'])
        if similarity > best_score:
            best_score = similarity
            best_match = {"id": user['id'], "name": user['name']}

    if best_match and best_score >= threshold:
        return best_match, best_score
    
    return None, best_score

def check_liveness(face_image, prev_face_image):
    """
    Heuristic liveness check via temporal variance (movement).
    Returns True if enough variation is detected between sequential frames.
    """
    if prev_face_image is None:
        return True # First frame, assume valid but wait for next
    
    try:
        # Resize to same dimensions for comparison
        prev_face_image = cv2.resize(prev_face_image, (face_image.shape[1], face_image.shape[0]))
        
        # Calculate Absolute Difference
        diff = cv2.absdiff(face_image, prev_face_image)
        mean_diff = np.mean(diff)
        
        # Heuristic: Static photos have very low variance (~0.1-1.0) 
        # Live humans have micro-movements (3.0+)
        return mean_diff > 1.5 
    except:
        return True
