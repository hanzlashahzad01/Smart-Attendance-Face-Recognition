import uuid
import datetime
from src.encryption import encrypt_embedding
from src.utils import get_db_connection, log_audit
from src.recognition import extract_embeddings
import qrcode
import io

def enroll_user(name, frames, department="General", retention_days=90):
    embeddings = []
    for frame in frames:
        faces = extract_embeddings(frame)
        if faces:
            # Assumes the first face found is the enrollee
            embeddings.append(faces[0][0])
    
    if len(embeddings) == 0:
        raise ValueError("No faces detected in the provided images.")

    avg_embedding = [float(sum(col))/len(col) for col in zip(*embeddings)]
    encrypted_emb = encrypt_embedding(avg_embedding)
    
    user_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (id, name, department, encrypted_embedding, consent_at, retention_days)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, name, department, encrypted_emb, now, retention_days))
    conn.commit()
    conn.close()
    
    log_audit(f"User enrolled: {name} ({department}) (ID: {user_id})", actor="Admin")
    return user_id

def generate_user_qr(user_id):
    """Generates a QR code for the user's ID for MFA."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(user_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def re_enroll_user(user_id, frames):
    """Allows updating an existing user's biometric data seamlessly."""
    embeddings = []
    for frame in frames:
        faces = extract_embeddings(frame)
        if faces:
            embeddings.append(faces[0][0])
    
    if len(embeddings) == 0:
        raise ValueError("No faces detected in the provided images.")

    # Re-average
    avg_embedding = [float(sum(col))/len(col) for col in zip(*embeddings)]
    encrypted_emb = encrypt_embedding(avg_embedding)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET encrypted_embedding = ?, consent_at = ? WHERE id = ?', 
              (encrypted_emb, datetime.datetime.now(), user_id))
    conn.commit()
    conn.close()
    
    log_audit(f"User re-enrolled (ID: {user_id})", actor="Admin")
    return True

def delete_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT name FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
        
    name = row['name']
    
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    c.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    log_audit(f"User deleted: {name} (ID: {user_id}) - Right to Erasure requested", actor="Admin")
    return True
