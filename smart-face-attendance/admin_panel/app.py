import streamlit as st
import cv2
import pandas as pd
import datetime
import os
import sys
import numpy as np
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import get_db_connection, init_db, log_audit, cleanup_expired_data, hash_identifier, speak_offline, send_email_alert
from src.enrollment import enroll_user, delete_user, re_enroll_user, generate_user_qr
from src.recognition import extract_embeddings, load_all_known_users, find_match_in_list, check_liveness
from src.attendance import mark_attendance
from dotenv import load_dotenv
import hashlib
import streamlit.components.v1 as components

load_dotenv()
DEFAULT_MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.65"))
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

st.set_page_config(page_title="GuardianAI Presence", page_icon="🛡️", layout="wide")

# ---- UI CUSTOMIZATION (CLEAN LIGHT MODE) ----
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main .block-container {
        background: white;
        border-radius: 12px;
        padding: 2.5rem;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        border: 1px solid #eee;
    }
    h1, h2, h3 {
        color: #1E3A8A !important;
        font-weight: 700;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1e40af;
        border: none;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ GuardianAI: Intelligence Suite")

# Initialize database and cleanup expired data
init_db()
deleted_count = cleanup_expired_data()
if deleted_count > 0:
    st.sidebar.info(f"🛡️ Auto-Cleanup: Removed {deleted_count} expired records.")

@st.cache_data(ttl=5) # short TTL for dynamic cache
def cached_users():
    return load_all_known_users()



# ---- AUTHENTICATION SYSTEM ----
def check_login(user, pwd):
    conn = get_db_connection()
    c = conn.cursor()
    h = hashlib.sha256(pwd.encode()).hexdigest()
    c.execute("SELECT * FROM admins WHERE username=? AND password_hash=?", (user, h))
    res = c.fetchone()
    conn.close()
    return res

# ---- VOICE FEEDBACK UTILITY ----
def speak(text):
    speak_offline(text)

# ---- NAVIGATION & ACCESS CONTROL ----
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Sidebar logo or Title
st.sidebar.markdown("## 🛡️ GuardianAI")

if not st.session_state['logged_in']:
    # PUBLIC KIOSK MENU
    menu = ["Live Recognition", "Admin Login"]
    choice = st.sidebar.selectbox("Kiosk Menu", menu)
    
    if choice == "Admin Login":
        st.header("🔑 Admin Secure Access")
        l_col1, _ = st.columns([2, 1])
        with l_col1:
            u = st.text_input("Username", placeholder="Enter admin username")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            if st.button("Login to Dashboard"):
                if check_login(u, p):
                    st.session_state['logged_in'] = True
                    st.session_state['admin_user'] = u
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
        st.info("💡 Employees do not need to login. Use 'Live Recognition' for attendance.")
        st.stop() # Stop execution for public if on login page
else:
    # ADMIN PRIVATE MENU
    st.sidebar.success(f"Logged in: {st.session_state['admin_user']}")
    menu = ["Live Recognition", "Enroll User", "Manage Users", "Analytics Dashboard", "Attendance Reports", "Accuracy Evaluation", "Audit Logs", "Settings"]
    choice = st.sidebar.selectbox("Admin Menu", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

# Shared Global Settings (Moveable based on preference, keeping for now)
st.sidebar.divider()
st.sidebar.header("Camera Settings")
current_threshold = st.sidebar.slider("Recognition Threshold", min_value=0.4, max_value=0.9, value=DEFAULT_MATCH_THRESHOLD, step=0.01)
office_start_time = st.sidebar.time_input("Office Start Time", datetime.time(9, 30))

# Session state for challenge-response liveness
if 'challenge' not in st.session_state:
    st.session_state['challenge'] = random.choice(["Blink", "Smile", "Turn Left", "Turn Right"])
    st.session_state['challenge_start'] = datetime.datetime.now()

if choice == "Live Recognition":
    st.header("Live Face Recognition")
    known_users = cached_users()
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.subheader("Interactive Liveness")
        st.info(f"Challenge: **{st.session_state['challenge']}**")
        if st.button("Passed? (Manual Validation)"):
             st.session_state['challenge_passed'] = True
             st.success("Liveness Verified!")
             st.session_state['challenge'] = random.choice(["Blink", "Smile", "Turn Left", "Turn Right"])
        
    with col1:
        run_camera = st.checkbox("Start Camera")
        FRAME_WINDOW = st.image([])
    
    if run_camera:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        frame_counter = 0
        latest_results = [] # stores tuples of (bbox, text, color)
        
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                st.error("Cannot read camera. Check permissions or CAMERA_INDEX.")
                break
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            max_h, max_w, _ = rgb_frame.shape
            
            if frame_counter % 5 == 0:
                latest_results = []
                faces = extract_embeddings(frame)
                
                for emb, bbox in faces:
                    # Capture face ROI for liveness
                    x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
                    face_roi = rgb_frame[max(0, y):min(max_h, y+h), max(0, x):min(max_w, x+w)]
                    
                    # Liveness Check (Movement)
                    is_live = True
                    if 'prev_face' in st.session_state:
                         is_live = check_liveness(face_roi, st.session_state['prev_face'])
                    
                    st.session_state['prev_face'] = face_roi
                    
                    match, score = find_match_in_list(emb, current_threshold, known_users)
                    color = (255, 0, 0)
                    text = "Unknown"
                    
                    if not is_live:
                        text = "SPOOF DETECTED"
                        color = (0, 0, 255)
                    elif match:
                        color = (0, 255, 0)
                        text = f"{match['name']} ({score:.2f})"
                        
                        # Trigger Voice Greeting on EVERY recognition (with a small frame delay)
                        if frame_counter % 50 == 0:
                            speak(f"Present {match['name']}")
                        
                        # Independent Attendance Marking Logic
                        success, msg = mark_attendance(match['id'], score, late_threshold_time=office_start_time)
                        if success:
                            st.toast(f"✅ Attendance Marked: {match['name']}", icon='👤')
                            st.sidebar.success(f"Marked: {match['name']} ({datetime.datetime.now().strftime('%H:%M:%S')})")
                            # Email Alerts are currently under maintenance
                        else:
                            if "Already marked" in msg:
                                # Just show info in sidebar, no toast for duplicate
                                if frame_counter % 50 == 0:
                                     st.sidebar.info(f"Status: {match['name']} is already marked.")
                    else:
                        if score > 0:
                            text = f"Unknown ({score:.2f})"
                            
                    latest_results.append((bbox, text, color))
            
            frame_counter += 1
            
            # Render ALL tracked faces
            for bbox, text, color in latest_results:
                x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
                x, y = max(0, x), max(0, y)
                w, h = min(w, max_w - x), min(h, max_h - y)
                
                cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(rgb_frame, text, (x, max(0, y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
            FRAME_WINDOW.image(rgb_frame)
            
        cap.release()

elif choice == "Enroll User":
    st.header("Enroll New User")
    name = st.text_input("Full Name")
    dept = st.selectbox("Department", ["IT", "HR", "Sales", "Security", "Staff", "Other"])
    retention_days = st.number_input("Data Retention (Days)", min_value=1, value=90)
    
    # Enable multiple images for better accuracy
    st.write("Capture or upload multiple images for robust biometric enrollment.")
    uploaded_files = st.file_uploader("Upload Face Images", type=['jpg','png','jpeg'], accept_multiple_files=True)
    img_file = st.camera_input("Or take a picture directly")
    
    if st.button("Enroll with Consent"):
        if name and (uploaded_files or img_file):
            frames = []
            if img_file:
                bytes_data = img_file.getvalue()
                frames.append(cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR))
            for uf in uploaded_files:
                bytes_data = uf.read()
                frames.append(cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR))
            
            with st.spinner("Processing local embeddings securely..."):
                try:
                    user_id = enroll_user(name, frames, department=dept, retention_days=retention_days)
                    st.success(f"Enrolled {name} successfully! ID: {user_id}")
                    
                    # Generate QR for MFA
                    qr_img = generate_user_qr(user_id)
                    st.image(qr_img, caption="MFA Access QR Code (Save this!)", width=200)
                    
                    cached_users.clear() # invalidate cache
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Provide name and at least one image.")

elif choice == "Manage Users":
    st.header("Manage Users (GDPR Compliance)")
    conn = get_db_connection()
    users_df = pd.read_sql_query('SELECT id, name, department, consent_at, retention_days FROM users', conn)
    conn.close()
    st.dataframe(users_df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Permanently Delete / Right to Erasure")
        del_id = st.selectbox("Select User ID to Delete", [""] + users_df['id'].tolist() if not users_df.empty else [""])
        if st.button("Delete User Data"):
            if del_id and delete_user(del_id):
                st.success("User deleted securely.")
                cached_users.clear()
                st.rerun()
            
    with col2:
        st.subheader("Re-Enroll User")
        ren_id = st.selectbox("Select User ID to update biometrics", [""] + users_df['id'].tolist() if not users_df.empty else [""])
        new_img = st.file_uploader("Upload New Image for User", type=['png','jpg','jpeg'], key="ren")
        if st.button("Update Biometrics"):
            if ren_id and new_img:
                cv2_img = cv2.imdecode(np.frombuffer(new_img.read(), np.uint8), cv2.IMREAD_COLOR)
                try:
                    re_enroll_user(ren_id, [cv2_img])
                    st.success("Updated biometrics successfully!")
                    cached_users.clear()
                except Exception as e:
                    st.error(f"Failed: {str(e)}")

elif choice == "Analytics Dashboard":
    st.header("📊 AI Attendance Analytics")
    conn = get_db_connection()
    df_att = pd.read_sql_query('''
        SELECT a.date, a.time, a.status, u.department, u.name
        FROM attendance a
        JOIN users u ON a.user_id = u.id
    ''', conn)
    conn.close()
    
    if df_att.empty:
        st.warning("No data available for analytics yet.")
    else:
        # 1. Attendance Status Breakdown
        col1, col2 = st.columns(2)
        
        status_counts = df_att['status'].value_counts().reset_index()
        fig1 = px.pie(status_counts, names='status', values='count', title="Overall Status Distribution", hole=0.4)
        col1.plotly_chart(fig1, use_container_width=True)
        
        # 2. Dept wise Attendance
        dept_counts = df_att.groupby(['department', 'status']).size().reset_index(name='count')
        fig2 = px.bar(dept_counts, x='department', y='count', color='status', barmode='group', title="Attendance by Department")
        col2.plotly_chart(fig2, use_container_width=True)
        
        # 3. Time Series Trends
        df_att['datetime'] = pd.to_datetime(df_att['date'] + ' ' + df_att['time'])
        df_att = df_att.sort_values('datetime')
        
        daily_att = df_att.groupby(['date', 'status']).size().reset_index(name='count')
        fig3 = px.line(daily_att, x='date', y='count', color='status', title="Daily Attendance Trends", markers=True)
        st.plotly_chart(fig3, use_container_width=True)
        
        # 4. Late Arrival Heatmap (Hour of Day)
        df_att['hour'] = df_att['datetime'].dt.hour
        hour_counts = df_att.groupby(['hour', 'status']).size().reset_index(name='count')
        fig4 = px.area(hour_counts, x='hour', y='count', color='status', title="Peak Arrival Hours")
        st.plotly_chart(fig4, use_container_width=True)

elif choice == "Attendance Reports":
    st.header("Attendance Logs & Filtering")
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT a.date, a.time, u.name, a.status, a.confidence, u.id as user_uuid
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.date DESC, a.time DESC
    ''', conn)
    conn.close()
    
    # Anonymize identifiers in the view for data minimization
    if not df.empty:
        df['Anonymized_ID'] = df['user_uuid'].apply(hash_identifier)
        # We keep name for display, but show what a hashed log would look like
    
    col1, col2 = st.columns(2)
    s_date = col1.date_input("Filter by Date", value=None)
    s_user = col2.text_input("Filter by User Name")
    
    if s_date:
        df = df[df['date'] == s_date.strftime('%Y-%m-%d')]
    if s_user:
        df = df[df['name'].str.contains(s_user, case=False, na=False)]
        
    st.dataframe(df)
    
    if not df.empty:
        total_logs = len(df)
        present = len(df[df['status'] == 'Present'])
        late = len(df[df['status'] == 'Late'])
        
        st.write("### Quick Stats")
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Total Logs", total_logs)
        mcol2.metric("Total Present (On Time)", present)
        mcol3.metric("Total Late", late)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV Export", data=csv, file_name="attendance.csv", mime="text/csv")
        
elif choice == "Accuracy Evaluation":
    st.header("Accuracy & Matrix Evaluation")
    st.markdown("Test DB embeddings against uploaded images to manually map **False Acceptance Rates (FAR)** and **False Rejection Rates (FRR)**.")
    
    test_files = st.file_uploader("Upload Test Faces (Real World Scenarios)", accept_multiple_files=True, type=['jpg','png','jpeg'])
    
    known_users = cached_users()
    user_options = ["Unknown Imposter"] + [u['name'] for u in known_users]
    
    ec1, ec2 = st.columns(2)
    ground_truth = ec1.selectbox("Select the True Identity mapped to these test images:", user_options)
    lighting_condition = ec2.selectbox("Lighting Condition of Test Set", ["Ideal", "Low Light", "Backlit", "Side Light", "Variable"])
    
    if st.button("Calculate Metrics"):
        if test_files:
            total_faces = 0
            tp = 0
            fp = 0
            fn = 0
            tn = 0
            
            with st.spinner("Analyzing evaluation set..."):
                for tf in test_files:
                    img = cv2.imdecode(np.frombuffer(tf.read(), np.uint8), cv2.IMREAD_COLOR)
                    faces = extract_embeddings(img)
                    for emb, _ in faces:
                        total_faces += 1
                        match, _ = find_match_in_list(emb, current_threshold, known_users)
                        
                        if ground_truth == "Unknown Imposter":
                            if match:
                                fp += 1
                            else:
                                tn += 1
                        else:
                            if match and match['name'] == ground_truth:
                                tp += 1
                            elif match:
                                fp += 1 # matched wrong user
                                fn += 1 # failed to match real user
                            else:
                                fn += 1 # failed to match real user
                                
            st.write(f"Faces Processed: **{total_faces}**")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("True Positives (TP)", tp)
            c2.metric("False Positives (FP)", fp)
            c3.metric("True Negatives (TN)", tn)
            c4.metric("False Negatives (FN)", fn)
            
            st.info(f"Evaluation Context: **{lighting_condition}**")
            
            if total_faces > 0:
                if ground_truth == "Unknown Imposter":
                    far = (fp / total_faces)*100
                    st.warning(f"**False Acceptance Rate (FAR): {far:.2f}%**")
                    st.info("Formula: FP / (FP + TN) -> Indicates Security Risk. If FAR is high, consider increasing the threshold constraint.")
                else:
                    frr = (fn / total_faces)*100
                    st.warning(f"**False Rejection Rate (FRR): {frr:.2f}%**")
                    st.info("Formula: FN / (TP + FN) -> Indicates User Friction. If FRR is high, consider adding more clear/diverse photos for the user during re-enrollment, or slightly lower threshold constraint.")
            else:
                st.error("No faces were visible enough to be detected in the provided images.")
            
elif choice == "Audit Logs":
    st.header("Security & Audit Logs")
    conn = get_db_connection()
    logs_df = pd.read_sql_query('SELECT timestamp, action, actor FROM audit_logs ORDER BY timestamp DESC LIMIT 200', conn)
    conn.close()
    st.dataframe(logs_df)

elif choice == "Settings":
    st.header("System Configurations")
    st.subheader("Global Security")
    new_pwd = st.text_input("Update Admin Password", type="password")
    if st.button("Update Password"):
        h = hashlib.sha256(new_pwd.encode()).hexdigest()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE admins SET password_hash=? WHERE username=?", (h, st.session_state['admin_user']))
        conn.commit()
        conn.close()
        st.success("Password updated successfully!")
    
    st.divider()
    st.subheader("🚀 Upcoming Features")
    st.info("📨 **Automated Notifications (Email/WhatsApp)** are currently under development and will be available in the next update.")
    st.write("We are working on integrating a secure OAuth2 gateway for reliable message delivery.")
