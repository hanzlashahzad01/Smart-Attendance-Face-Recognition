import sqlite3
import os
import hashlib

db_path = os.path.join('database', 'attendance.db')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        # Create admins table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY,
                password_hash TEXT
            )
        ''')
        
        # Add default admin if not present
        c.execute("SELECT * FROM admins WHERE username = 'admin'")
        if not c.fetchone():
            print("Creating default admin account...")
            c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                      ('admin', hash_password('admin123')))
            conn.commit()
            print("Admin created: user=admin, pass=admin123")
        else:
            print("Admin account already exists.")
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()
else:
    print("Database not found.")
