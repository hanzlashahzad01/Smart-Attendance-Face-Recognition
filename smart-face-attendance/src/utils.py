import os
import sqlite3
import hashlib
import threading
import pyttsx3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'attendance.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            department TEXT,
            encrypted_embedding BLOB,
            consent_at DATETIME,
            retention_days INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT,
            time TEXT,
            status TEXT,
            confidence REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            actor TEXT,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def log_audit(action, actor="SYSTEM"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO audit_logs (action, actor, timestamp) VALUES (?, ?, ?)', (action, actor, datetime.now()))
    conn.commit()
    conn.close()

def cleanup_expired_data():
    """Implements GDPR data retention policy by deleting users after their retention period."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Select users where current date > consent_at + retention_days
    # SQLite doesn't have a direct 'add days' for timestamps easily without logic,
    # so we'll do it by selecting all and checking in Python or using date()
    c.execute('SELECT id, name, consent_at, retention_days FROM users')
    rows = c.fetchall()
    
    deleted_count = 0
    now = datetime.now()
    
    for row in rows:
        consent_at = row['consent_at']
        if isinstance(consent_at, str):
            consent_at = datetime.fromisoformat(consent_at)
            
        retention_days = row['retention_days']
        expiry_date = consent_at.timestamp() + (retention_days * 86400)
        
        if now.timestamp() > expiry_date:
            user_id = row['id']
            c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            c.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
            deleted_count += 1
            log_audit(f"Auto-deleted expired user data: {row['name']} (ID: {user_id})", actor="RETENTION_SYSTEM")

    conn.commit()
    conn.close()
    return deleted_count

def hash_identifier(identifier):
    """Hashes a user identifier (ID or Email) to ensure privacy in logs (Data Minimization)."""
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]

def speak_offline(text):
    """Speaks text using system TTS in a non-blocking thread."""
    def run_tts():
        try:
            engine = pyttsx3.init()
            # Reduce properties for faster response
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            engine.say(text)
            engine.runAndWait()
        except:
            pass
            
    threading.Thread(target=run_tts, daemon=True).start()

def send_email_alert(subject, body):
    """Sends an automated email alert in a background thread."""
    def run_email():
        # Force reload .env to get the latest saved credentials
        load_dotenv(override=True)
        
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        receiver_email = os.getenv("RECEIVER_EMAIL")

        if not all([sender_email, sender_password, receiver_email]):
            print("Email skipped: Missing credentials in .env")
            return

        print(f"Attempting to send email from {sender_email} to {receiver_email}...")
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.set_debuglevel(1) # Enable debug output in console
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            print("Email sent successfully!")
        except Exception as e:
            print(f"CRITICAL: Email failed: {str(e)}")

    threading.Thread(target=run_email, daemon=True).start()
