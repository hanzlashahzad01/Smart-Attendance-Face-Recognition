import datetime
from src.utils import get_db_connection, log_audit

def mark_attendance(user_id, confidence, late_threshold_time=None):
    """Marks attendance for a user if not already marked today."""
    conn = get_db_connection()
    c = conn.cursor()
    
    now = datetime.datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')
    
    # Check if already marked today
    c.execute('SELECT id FROM attendance WHERE user_id = ? AND date = ?', (user_id, current_date))
    if c.fetchone() is not None:
        conn.close()
        return False, "Already marked for today"
    
    # Logic for determining 'Late' status
    entry_time = now.time()
    if late_threshold_time is None:
        late_threshold_time = datetime.time(9, 30)
    
    status = "Late" if entry_time > late_threshold_time else "Present"
    
    c.execute('''
        INSERT INTO attendance (user_id, date, time, status, confidence)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, current_date, current_time, status, confidence))
    
    conn.commit()
    conn.close()
    
    log_audit(f"Attendance marked for user {user_id} - Status: {status}", actor="System")
    return True, status
