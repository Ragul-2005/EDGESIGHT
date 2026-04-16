#!/usr/bin/env python3
"""
MICRO Voice Assistant + NEON OCR + FPGA Object Detection + AI DIARY
- Voice chatbot (speech â†’ Gemini â†’ speech)
- OCR scanner with auto capture & auto voice & auto return
- Object detection scanner (OpenCV capture, FPGA YOLO, NO bounding boxes)
- AI Diary module (voice recording â†’ text storage â†’ retrieval with voice playback)
- Saying "OCR" / "scan text" / "object detection" / "diary" in chatbot will navigate.
"""

from flask import Flask, jsonify, Response, send_from_directory, request, render_template
from dotenv import load_dotenv
import os, subprocess, threading, re, requests, speech_recognition as sr
import cv2, pytesseract, time, sqlite3, json
import shutil, sys, glob
from datetime import datetime

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing in .env")

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY missing in .env")

GEN_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

AUDIO_DEVICE = "plughw:0,0"
AUDIO_FILE = "/tmp/speech.wav"
PORT = 5000

# ------------- OCR Paths -------------
OCR_WORK_DIR = "/root/ocr_cam_app"
os.makedirs(OCR_WORK_DIR, exist_ok=True)
OCR_CAP_IMG = f"{OCR_WORK_DIR}/capture.jpg"
OCR_OUT_IMG = f"{OCR_WORK_DIR}/result.jpg"
OCR_TXT = f"{OCR_WORK_DIR}/ocr.txt"

# ------------- Object Detection Paths -------------
DET_WORK_DIR = "/root/senba/web_app"
os.makedirs(DET_WORK_DIR, exist_ok=True)
DET_CAP_IMG = f"{DET_WORK_DIR}/capture.jpg"
DET_OUT_IMG = f"{DET_WORK_DIR}/result.jpg"     # same as CAP (no boxes)
DETS_FILE = f"{DET_WORK_DIR}/detections.txt"

RUN_MODEL = "/root/VectorBlox-SDK-release-v2.0.3/example/soc-c/run-model"
MODEL = "/root/yolov8n_512x288.vnnx"
POST = "ULTRALYTICS"

# ------------- Diary Paths & Database -------------
DIARY_WORK_DIR = "/root/diary_app"
os.makedirs(DIARY_WORK_DIR, exist_ok=True)
DIARY_DB = f"{DIARY_WORK_DIR}/diary.db"
DIARY_AUDIO_FILE = f"{DIARY_WORK_DIR}/diary_entry.wav"

def init_diary_db():
    """Initialize diary database with entries table."""
    try:
        conn = sqlite3.connect(DIARY_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                entry_text TEXT,
                user_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Diary DB init failed: {e}")

init_diary_db()

# ------------- Medical Assistance Paths & Database -------------
MEDICAL_WORK_DIR = "/root/medical_app"
os.makedirs(MEDICAL_WORK_DIR, exist_ok=True)
MEDICAL_DB = f"{MEDICAL_WORK_DIR}/medical.db"
MEDICAL_AUDIO_FILE = f"{MEDICAL_WORK_DIR}/medical_note.wav"

def init_medical_db():
    """Initialize medical database with notes table."""
    try:
        conn = sqlite3.connect(MEDICAL_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS medical_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                health_note TEXT,
                ai_tips TEXT,
                user_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Medical DB init failed: {e}")

init_medical_db()


def sanitize_medical_tips_db():
    """Remove leftover markdown asterisks from stored AI tips."""
    try:
        conn = sqlite3.connect(MEDICAL_DB)
        c = conn.cursor()
        # remove literal double asterisks and stray single asterisks
        c.execute("UPDATE medical_notes SET ai_tips = REPLACE(ai_tips, '**', '') WHERE ai_tips LIKE '%**%';")
        c.execute("UPDATE medical_notes SET ai_tips = REPLACE(ai_tips, '*', '') WHERE ai_tips LIKE '%*%';")
        conn.commit()
        conn.close()
        print("[INFO] Sanitized existing medical AI tips in DB.")
    except Exception as e:
        print(f"[ERROR] Sanitizing medical AI tips failed: {e}")

# clean up any legacy markdown markers in DB
sanitize_medical_tips_db()

# ------------- Mental Health Checkup Paths & Database -------------
MENTAL_WORK_DIR = "/root/mental_app"
os.makedirs(MENTAL_WORK_DIR, exist_ok=True)
MENTAL_DB = f"{MENTAL_WORK_DIR}/mental.db"
MENTAL_AUDIO_FILE = f"{MENTAL_WORK_DIR}/mental_checkup.wav"

def init_mental_db():
    """Initialize mental health database with checkup records table."""
    try:
        conn = sqlite3.connect(MENTAL_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS mental_checkups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                transcript TEXT,
                emotion TEXT,
                confidence REAL,
                wellness_tips TEXT,
                user_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Mental Health DB init failed: {e}")

init_mental_db()

# ------------- Analytics & Parental Mode Database -------------
ANALYTICS_WORK_DIR = "/root/analytics_app"
os.makedirs(ANALYTICS_WORK_DIR, exist_ok=True)
ANALYTICS_DB = f"{ANALYTICS_WORK_DIR}/analytics.db"

def init_analytics_db():
    """Initialize analytics database with activity tracking table."""
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                module_name TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_seconds INTEGER,
                user_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Analytics DB init failed: {e}")

init_analytics_db()

# ------------- Location Tracking -------------
LOCATION_WORK_DIR = "/root/location_app"
os.makedirs(LOCATION_WORK_DIR, exist_ok=True)

# Cache for location data
location_cache = {
    "latitude": 0.0,
    "longitude": 0.0,
    "accuracy": 0.0,
    "altitude": 0.0,
    "speed": 0.0,
    "timestamp": None
}
location_lock = threading.Lock()

# ---------------------------------------------------------
# STATE
# ---------------------------------------------------------
app = Flask(__name__)
recognizer = sr.Recognizer()

state_lock = threading.Lock()
is_recording = False
last_transcript = ""
last_reply = ""
reply_seq = 0
recorder_process = None

ocr_lock = threading.Lock()
detect_lock = threading.Lock()
diary_lock = threading.Lock()
medical_lock = threading.Lock()

diary_is_recording = False
diary_recorder_process = None
last_diary_entry = ""
diary_seq = 0

medical_is_recording = False
medical_recorder_process = None
last_medical_note = ""
medical_seq = 0

mental_lock = threading.Lock()
mental_is_recording = False
mental_recorder_process = None
last_mental_emotion = ""
last_mental_tips = ""
mental_seq = 0

# Analytics & Parental Mode State
analytics_lock = threading.Lock()
current_module = None
module_start_time = None
analytics_seq = 0

# ---------------------------------------------------------
# HELPERS â€” COMMON
# ---------------------------------------------------------
def clean_text(t):
    return re.sub(r"[*_`#>-]+", "", t).strip()


def ask_gemini_text(text):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
    }

    try:
        res = requests.post(
            GEN_API_URL + "?key=" + GEMINI_API_KEY,
            headers=headers,
            json=payload,
            timeout=25,
        )
        if res.status_code != 200:
            return f"Gemini Error: {res.text}"

        data = res.json()
        cand = data.get("candidates", [])
        if cand:
            parts = cand[0].get("content", {}).get("parts", [])
            msg = "".join(p.get("text", "") for p in parts)
            return clean_text(msg)

        return "No reply from Gemini."
    except Exception as e:
        return f"Exception: {e}"


def safe_remove(p):
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


# ---------------------------------------------------------
# CAMERA SETTINGS (same values for OCR + DETECT)
# ---------------------------------------------------------
def apply_camera_settings():
    cmds = [
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=auto_exposure=1"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=exposure_time_absolute=250"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=gain=0"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=brightness=0"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=contrast=32"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=gamma=150"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=backlight_compensation=0"],
        ["v4l2-ctl", "-d", "/dev/video0", "--set-ctrl=white_balance_automatic=1"],
    ]
    for c in cmds:
        subprocess.run(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------
# OCR HELPERS (GStreamer capture)
# ---------------------------------------------------------
def ocr_capture_frame():
    """Capture single frame for OCR.

    Strategy:
      1. Try GStreamer (gst-launch) as before and capture stdout/stderr for diagnostics
      2. Fall back to multiple OpenCV backends (V4L2, DSHOW/MSMF on Windows)
      3. Return (success: bool, message: str) where message contains useful diagnostics
    """
    apply_camera_settings()

    diagnostics = []

    # ----- Try GStreamer first (Linux targets where gst-launch is available) -----
    gst_cmd = (
        "gst-launch-1.0 -e "
        "v4l2src device=/dev/video0 num-buffers=1 ! "
        "image/jpeg,width=640,height=480 ! "
        "jpegdec ! jpegenc ! "
        f"filesink location={OCR_CAP_IMG}"
    )

    try:
        res = subprocess.run(gst_cmd, shell=True, capture_output=True, timeout=15)
        diagnostics.append(f"gst returncode={res.returncode}")
        try:
            diagnostics.append("gst stdout=" + res.stdout.decode(errors='ignore'))
            diagnostics.append("gst stderr=" + res.stderr.decode(errors='ignore'))
        except Exception:
            pass

        if res.returncode == 0 and os.path.exists(OCR_CAP_IMG):
            try:
                shutil.copy(OCR_CAP_IMG, OCR_OUT_IMG)
            except Exception:
                pass
            return True, "gst: success"
        else:
            diagnostics.append("gst capture did not produce image")
    except Exception as e:
        diagnostics.append(f"gst exception: {e}")

    # ----- Try OpenCV with a few common backends and sources -----
    candidates = []
    plt = sys.platform
    if plt.startswith('linux'):
        candidates = [('/dev/video0', None), (0, cv2.CAP_V4L2), (0, cv2.CAP_ANY)]
    elif plt.startswith('win'):
        candidates = [(0, cv2.CAP_DSHOW), (0, cv2.CAP_MSMF), (0, cv2.CAP_ANY)]
    else:
        candidates = [(0, cv2.CAP_ANY)]

    for src, backend in candidates:
        try:
            diagnostics.append(f"attempt opencv src={src} backend={backend}")
            if backend is not None:
                cap = cv2.VideoCapture(src, backend)
            else:
                cap = cv2.VideoCapture(src)

            if not cap.isOpened():
                diagnostics.append(f"opencv could not open src={src} backend={backend}")
                try:
                    cap.release()
                except Exception:
                    pass
                continue

            ret, frame = cap.read()
            try:
                cap.release()
            except Exception:
                pass

            if not ret or frame is None:
                diagnostics.append(f"opencv read failed for src={src} backend={backend}")
                continue

            try:
                cv2.imwrite(OCR_CAP_IMG, frame)
                try:
                    shutil.copy(OCR_CAP_IMG, OCR_OUT_IMG)
                except Exception:
                    pass
                return True, f"opencv: success src={src} backend={backend}"
            except Exception as e:
                diagnostics.append(f"write failed: {e}")
        except Exception as e:
            diagnostics.append(f"opencv exception for src={src} backend={backend}: {e}")

    # ----- Extra diagnostics on Linux: list /dev/video* and v4l2-ctl output -----
    if plt.startswith('linux'):
        try:
            devs = glob.glob('/dev/video*')
            diagnostics.append(f"devs:{devs}")
        except Exception as e:
            diagnostics.append(f"glob /dev/video* failed: {e}")

        try:
            res = subprocess.run(["v4l2-ctl", "--list-devices"], capture_output=True, timeout=5)
            diagnostics.append("v4l2-ctl:" + res.stdout.decode(errors='ignore'))
        except Exception as e:
            diagnostics.append(f"v4l2-ctl not available or failed: {e}")

    # Final failure
    msg = "; ".join([str(m) for m in diagnostics if m])[:2000]
    print("[ERROR] OCR capture failed (diagnostics):", msg)
    return False, msg


def preprocess_for_ocr():
    img = cv2.imread(OCR_CAP_IMG)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    _, th = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return th


def run_ocr(img_bin):
    text = pytesseract.image_to_string(
        img_bin,
        lang="eng",
        config="--oem 3 --psm 6"
    )
    open(OCR_TXT, "w").write(text)
    return text


# ---------------------------------------------------------
# OBJECT DETECTION HELPERS (OpenCV + FPGA YOLO â€” your code)
# ---------------------------------------------------------
DET_RE = re.compile(
    r"([A-Za-z0-9_]+)"
    r"(?:\s+(\d*\.\d+|\d+))?"
    r".*?(\d+)[,\s]+(\d+)[,\s]+(\d+)[,\s]+(\d+)",
    re.MULTILINE
)


def parse_detections(output):
    dets = []
    for cls, conf, x, y, w, h in DET_RE.findall(output):
        conf = float(conf) if conf else 1.0
        dets.append((cls, conf, int(x), int(y), int(w), int(h)))
    return dets


def detect_capture_frame():
    """Capture single frame for object detection using your OpenCV code."""
    apply_camera_settings()

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    time.sleep(0.08)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("[ERROR] Detect: camera capture failed")
        return False

    cv2.imwrite(DET_CAP_IMG, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    cv2.imwrite(DET_OUT_IMG, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return True


def run_fpga_inference(img):
    try:
        out = subprocess.check_output(
            [RUN_MODEL, MODEL, img, POST],
            stderr=subprocess.STDOUT,
            timeout=20
        ).decode()
        return out
    except Exception as e:
        print("[ERROR] FPGA inference failed:", e)
        return ""


# ---------------------------------------------------------
# AUDIO PROCESSING (CHATBOT)
# ---------------------------------------------------------
def process_audio():
    global last_transcript, last_reply, reply_seq

    if not os.path.exists(AUDIO_FILE):
        with state_lock:
            last_transcript = ""
            last_reply = "No audio recorded."
            reply_seq += 1
        return

    # Speech â†’ Text
    try:
        with sr.AudioFile(AUDIO_FILE) as src:
            audio = recognizer.record(src)
            text = recognizer.recognize_google(audio)
    except Exception as e:
        with state_lock:
            last_transcript = ""
            last_reply = f"STT Error: {e}"
            reply_seq += 1
        safe_remove(AUDIO_FILE)
        return

    with state_lock:
        last_transcript = text

    # Text â†’ Gemini
    reply = ask_gemini_text(text)

    with state_lock:
        last_reply = reply
        reply_seq += 1

    safe_remove(AUDIO_FILE)


# ---------------------------------------------------------
# DIARY HELPERS
# ---------------------------------------------------------
def save_diary_entry(entry_text, user_id="default"):
    """Save diary entry to database with date and time."""
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        conn = sqlite3.connect(DIARY_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO diary_entries (date, time, entry_text, user_id)
            VALUES (?, ?, ?, ?)
        """, (date_str, time_str, entry_text, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Save diary failed: {e}")
        return False


def get_today_diary(user_id="default"):
    """Retrieve today's diary entries."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DIARY_DB)
        c = conn.cursor()
        c.execute("""
            SELECT date, time, entry_text FROM diary_entries
            WHERE date = ? AND user_id = ?
            ORDER BY time DESC
        """, (today, user_id))
        entries = c.fetchall()
        conn.close()
        return entries
    except Exception as e:
        print(f"[ERROR] Get today diary failed: {e}")
        return []


def get_last_diary(user_id="default"):
    """Retrieve last diary entry."""
    try:
        conn = sqlite3.connect(DIARY_DB)
        c = conn.cursor()
        c.execute("""
            SELECT date, time, entry_text FROM diary_entries
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        entry = c.fetchone()
        conn.close()
        return entry
    except Exception as e:
        print(f"[ERROR] Get last diary failed: {e}")
        return None


def process_diary_audio():
    """Convert diary audio file to text and save."""
    global last_diary_entry, diary_seq

    if not os.path.exists(DIARY_AUDIO_FILE):
        return "No audio recorded"

    try:
        with sr.AudioFile(DIARY_AUDIO_FILE) as src:
            audio = recognizer.record(src)
            text = recognizer.recognize_google(audio)
    except Exception as e:
        return f"STT Error: {e}"

    # Save to database
    if save_diary_entry(text):
        with diary_lock:
            last_diary_entry = text
            diary_seq += 1
        safe_remove(DIARY_AUDIO_FILE)
        return text
    else:
        return "Failed to save entry"


# ---------------------------------------------------------
# MEDICAL ASSISTANCE HELPERS
# ---------------------------------------------------------

# Comprehensive Medical Knowledge Database (100+ conditions)
MEDICAL_KNOWLEDGE_DB = {
    # Respiratory Conditions
    "common cold": {
        "medicine": "Paracetamol 500mg, Cetirizine 10mg",
        "duration": "5-7 days",
        "instructions": "Take Paracetamol twice daily after meals. Take Cetirizine once at bedtime. Rest adequately, drink warm fluids, and maintain hydration.",
        "doctor_visit": "If symptoms persist beyond 7 days, fever exceeds 102Â°F, or breathing difficulty develops, please consult a doctor immediately."
    },
    "cough": {
        "medicine": "Dextromethorphan 15mg syrup, Ambroxol 30mg",
        "duration": "5-7 days",
        "instructions": "Take cough syrup 10ml three times daily. Ambroxol tablet twice daily after meals. Avoid cold drinks and maintain throat hydration.",
        "doctor_visit": "If cough persists beyond 2 weeks, produces blood, or is accompanied by chest pain, seek medical attention promptly."
    },
    "flu": {
        "medicine": "Paracetamol 650mg, Vitamin C 500mg, Zinc supplements",
        "duration": "7-10 days",
        "instructions": "Take Paracetamol thrice daily for fever and body ache. Vitamin C once daily. Complete bed rest, warm salt water gargling, and stay hydrated.",
        "doctor_visit": "If high fever persists beyond 3 days, severe headache, or difficulty breathing occurs, consult a physician immediately."
    },
    "sore throat": {
        "medicine": "Amoxicillin 500mg, Betadine gargle solution",
        "duration": "5-7 days",
        "instructions": "Amoxicillin tablet thrice daily after meals. Gargle with warm salt water or Betadine solution 3-4 times daily. Avoid spicy foods.",
        "doctor_visit": "If throat pain is severe, swallowing becomes difficult, or white patches appear, please visit a doctor."
    },
    "fever": {
        "medicine": "Paracetamol 500mg, Ibuprofen 400mg (if needed)",
        "duration": "3-5 days",
        "instructions": "Take Paracetamol every 6 hours if fever exceeds 100Â°F. Use cold compress on forehead. Maintain fluid intake and rest.",
        "doctor_visit": "If fever exceeds 103Â°F, lasts beyond 3 days, or accompanied by seizures or confusion, seek emergency medical care."
    },
    
    # Digestive Issues
    "acidity": {
        "medicine": "Omeprazole 20mg, Rantac 150mg, Gelusil syrup",
        "duration": "7-14 days",
        "instructions": "Omeprazole once daily before breakfast. Rantac at bedtime. Gelusil syrup when acidity occurs. Avoid spicy, oily foods and late-night meals.",
        "doctor_visit": "If symptoms persist despite medication, severe chest pain, or blood in vomit occurs, consult a gastroenterologist."
    },
    "constipation": {
        "medicine": "Isabgol husk, Lactulose syrup 15ml, Bisacodyl 5mg",
        "duration": "3-5 days",
        "instructions": "Take Isabgol with warm water before bed. Lactulose syrup once daily. Increase fiber intake, fruits, vegetables, and water consumption.",
        "doctor_visit": "If constipation lasts beyond 1 week, severe abdominal pain, or bleeding occurs, please seek medical evaluation."
    },
    "diarrhea": {
        "medicine": "Loperamide 2mg, ORS packets, Zinc supplements",
        "duration": "2-3 days",
        "instructions": "Loperamide after each loose motion (max 4 per day). ORS solution frequently. Avoid dairy and greasy foods. Maintain electrolyte balance.",
        "doctor_visit": "If diarrhea persists beyond 3 days, severe dehydration, blood in stool, or high fever develops, consult a doctor urgently."
    },
    "gastritis": {
        "medicine": "Pantoprazole 40mg, Sucralfate suspension",
        "duration": "14-21 days",
        "instructions": "Pantoprazole once daily before breakfast. Sucralfate suspension twice daily on empty stomach. Eat small frequent meals. Avoid alcohol and NSAIDs.",
        "doctor_visit": "If severe abdominal pain, vomiting blood, black stools, or no improvement after 2 weeks, please consult a gastroenterologist."
    },
    "nausea": {
        "medicine": "Ondansetron 4mg, Domperidone 10mg",
        "duration": "2-3 days",
        "instructions": "Ondansetron as needed for nausea. Domperidone before meals. Eat bland foods like crackers and toast. Stay hydrated with small sips.",
        "doctor_visit": "If vomiting is persistent, contains blood, or accompanied by severe headache or dizziness, seek immediate medical attention."
    },
    
    # Pain & Inflammation
    "headache": {
        "medicine": "Aspirin 325mg, Paracetamol 500mg, Ibuprofen 400mg",
        "duration": "As needed, typically 1-2 days",
        "instructions": "Take one of the above medications every 6-8 hours as needed. Rest in a dark, quiet room. Apply cold compress to forehead.",
        "doctor_visit": "If headaches are severe, frequent, accompanied by vision changes, or sudden onset, please consult a neurologist."
    },
    "migraine": {
        "medicine": "Sumatriptan 50mg, Propranolol 40mg (preventive)",
        "duration": "As needed for attacks; preventive therapy ongoing",
        "instructions": "Sumatriptan at onset of migraine. Propranolol daily for prevention. Rest in dark room, avoid triggers like bright lights and certain foods.",
        "doctor_visit": "If migraines increase in frequency, are debilitating, or don't respond to medication, neurological consultation is essential."
    },
    "back pain": {
        "medicine": "Diclofenac 50mg, Thiocolchicoside 4mg, Voltaren gel",
        "duration": "5-7 days",
        "instructions": "Diclofenac tablet twice daily after meals. Apply Voltaren gel to affected area twice daily. Use hot/cold compress. Gentle stretching exercises.",
        "doctor_visit": "If pain radiates to legs, numbness occurs, or pain persists beyond 2 weeks, please see an orthopedic specialist."
    },
    "muscle pain": {
        "medicine": "Ibuprofen 400mg, Methocarbamol 750mg, Pain relief spray",
        "duration": "3-5 days",
        "instructions": "Ibuprofen thrice daily after meals. Methocarbamol for muscle relaxation. Apply pain relief spray topically. Rest affected muscles.",
        "doctor_visit": "If muscle pain is severe, accompanied by swelling, or doesn't improve with rest, consult a doctor."
    },
    "joint pain": {
        "medicine": "Glucosamine 1500mg, Chondroitin 1200mg, Diclofenac gel",
        "duration": "Ongoing supplementation, gel as needed",
        "instructions": "Glucosamine and Chondroitin once daily. Apply Diclofenac gel to joints twice daily. Light exercises and physiotherapy recommended.",
        "doctor_visit": "If joints are swollen, red, extremely painful, or mobility is severely restricted, rheumatology consultation is advised."
    },
    
    # Skin Conditions
    "skin allergy": {
        "medicine": "Cetirizine 10mg, Calamine lotion, Hydrocortisone cream 1%",
        "duration": "5-7 days",
        "instructions": "Cetirizine once daily at bedtime. Apply calamine lotion to affected areas. Hydrocortisone cream twice daily for itching. Avoid allergens.",
        "doctor_visit": "If rash spreads rapidly, severe swelling, breathing difficulty, or no improvement, seek immediate medical care."
    },
    "eczema": {
        "medicine": "Betamethasone cream, Moisturizing lotion, Cetirizine 10mg",
        "duration": "14-21 days",
        "instructions": "Apply Betamethasone cream twice daily to affected areas. Use fragrance-free moisturizer frequently. Cetirizine for itching control.",
        "doctor_visit": "If eczema worsens, becomes infected (yellow crusting), or doesn't respond to treatment, dermatology consultation needed."
    },
    "acne": {
        "medicine": "Benzoyl peroxide 2.5% gel, Adapalene 0.1% gel, Clindamycin gel",
        "duration": "8-12 weeks",
        "instructions": "Apply Benzoyl peroxide in morning. Adapalene at night. Clindamycin gel twice daily. Use oil-free products. Don't squeeze pimples.",
        "doctor_visit": "If acne is severe, cystic, scarring, or not responding to over-the-counter treatments, see a dermatologist."
    },
    "fungal infection": {
        "medicine": "Clotrimazole cream 1%, Fluconazole 150mg tablet",
        "duration": "14-21 days",
        "instructions": "Apply Clotrimazole cream twice daily to affected area and surrounding skin. Fluconazole tablet once weekly. Keep area dry and clean.",
        "doctor_visit": "If infection spreads, becomes very painful, or doesn't improve after 3 weeks, consult a dermatologist."
    },
    "dry skin": {
        "medicine": "Cetaphil moisturizing cream, Vitamin E capsules",
        "duration": "Ongoing as needed",
        "instructions": "Apply moisturizer immediately after bathing. Take Vitamin E capsules daily. Use mild soaps. Avoid hot water baths.",
        "doctor_visit": "If skin becomes extremely dry, cracked, bleeding, or infected, dermatological evaluation is recommended."
    },
    
    # Allergies
    "hay fever": {
        "medicine": "Loratadine 10mg, Fluticasone nasal spray",
        "duration": "During allergy season",
        "instructions": "Loratadine once daily. Fluticasone nasal spray twice daily. Avoid outdoor activities during high pollen count. Use air purifiers.",
        "doctor_visit": "If symptoms are severe, interfere with daily life, or medication isn't effective, allergist consultation recommended."
    },
    "dust allergy": {
        "medicine": "Fexofenadine 120mg, Montelukast 10mg",
        "duration": "Ongoing as needed",
        "instructions": "Fexofenadine once daily. Montelukast at bedtime. Use dust mite covers. Regular cleaning. HEPA filters recommended.",
        "doctor_visit": "If allergic reactions are severe, causing breathing difficulty, or significantly affecting quality of life, see an allergist."
    },
    "food allergy": {
        "medicine": "Antihistamines (Diphenhydramine 25mg), Emergency epinephrine if prescribed",
        "duration": "As needed",
        "instructions": "For mild reactions, take antihistamine immediately. Avoid trigger foods completely. Read food labels carefully. Carry emergency medication.",
        "doctor_visit": "For severe reactions with swelling, breathing difficulty, or anaphylaxis, seek emergency medical care immediately."
    },
    
    # Sleep & Mental Health
    "insomnia": {
        "medicine": "Melatonin 3mg, Diphenhydramine 25mg (short-term)",
        "duration": "2-4 weeks",
        "instructions": "Melatonin 30 minutes before bedtime. Maintain sleep hygiene. Avoid screens 1 hour before bed. Regular sleep schedule essential.",
        "doctor_visit": "If insomnia persists beyond 4 weeks, causes severe daytime impairment, or is accompanied by depression, consult a sleep specialist."
    },
    "anxiety": {
        "medicine": "Mild cases: L-Theanine 200mg, Ashwagandha extract",
        "duration": "Ongoing with medical supervision",
        "instructions": "Natural supplements may help mild anxiety. Practice relaxation techniques, deep breathing, meditation. Regular exercise beneficial.",
        "doctor_visit": "For moderate to severe anxiety, panic attacks, or if it affects daily functioning, psychiatric or psychological consultation is essential."
    },
    "stress": {
        "medicine": "Vitamin B-complex, Magnesium supplements, Adaptogens",
        "duration": "Ongoing",
        "instructions": "B-complex once daily. Magnesium at bedtime. Practice stress management techniques. Regular exercise, adequate sleep, balanced diet.",
        "doctor_visit": "If stress leads to physical symptoms, depression, or severe anxiety, professional mental health consultation is strongly advised."
    },
    
    # Vitamins & Supplements
    "vitamin d deficiency": {
        "medicine": "Vitamin D3 60,000 IU weekly, then maintenance 2000 IU daily",
        "duration": "8-12 weeks loading, then ongoing",
        "instructions": "Take high-dose supplement weekly for 8 weeks, then daily maintenance. Get 15 minutes daily sun exposure. Include fortified foods.",
        "doctor_visit": "If symptoms like bone pain, muscle weakness persist, or levels don't improve, endocrinology consultation needed."
    },
    "vitamin b12 deficiency": {
        "medicine": "Methylcobalamin 1500mcg daily or injections as prescribed",
        "duration": "3-6 months, then reassess",
        "instructions": "Take B12 supplement daily. Include B12-rich foods like eggs, dairy, fish. Injections may be needed for severe deficiency.",
        "doctor_visit": "If neurological symptoms like numbness, tingling, or cognitive issues occur, immediate medical evaluation essential."
    },
    "iron deficiency": {
        "medicine": "Ferrous sulfate 325mg, Vitamin C 500mg (enhances absorption)",
        "duration": "3-6 months",
        "instructions": "Take iron supplement on empty stomach with Vitamin C. Avoid tea/coffee near supplement time. Include iron-rich foods in diet.",
        "doctor_visit": "If anemia symptoms worsen, severe fatigue, or no improvement after 3 months, hematology consultation recommended."
    },
    
    # Women's Health
    "menstrual cramps": {
        "medicine": "Mefenamic acid 500mg, Ibuprofen 400mg, Hyoscine 10mg",
        "duration": "During menstruation",
        "instructions": "Take pain reliever at onset of cramps, thrice daily with meals. Apply heat pad to lower abdomen. Light exercise may help.",
        "doctor_visit": "If cramps are severe, debilitating, or accompanied by heavy bleeding or fever, gynecological evaluation necessary."
    },
    "pms": {
        "medicine": "Evening primrose oil, Vitamin B6, Calcium supplements",
        "duration": "Ongoing, especially week before period",
        "instructions": "Take supplements daily. Reduce caffeine and salt intake. Regular exercise. Stress management techniques beneficial.",
        "doctor_visit": "If PMS severely affects daily life, causes depression, or symptoms are unmanageable, consult a gynecologist."
    },
    "yeast infection": {
        "medicine": "Fluconazole 150mg oral, Clotrimazole vaginal cream",
        "duration": "1-7 days depending on severity",
        "instructions": "Single dose Fluconazole or 7-day cream treatment. Wear cotton underwear. Avoid douching. Probiotics may help prevention.",
        "doctor_visit": "If infections are recurrent (>3 per year), severe, or don't respond to treatment, gynecological consultation needed."
    },
    
    # Urinary Issues
    "uti": {
        "medicine": "Nitrofurantoin 100mg, Cranberry extract, Plenty of water",
        "duration": "5-7 days",
        "instructions": "Take antibiotic twice daily after meals. Drink 8-10 glasses of water daily. Cranberry supplements may help. Don't hold urine.",
        "doctor_visit": "If symptoms worsen, fever develops, blood in urine, or kidney pain occurs, immediate medical attention required."
    },
    "kidney stones": {
        "medicine": "Tamsulosin 0.4mg, Pain relievers as needed, Potassium citrate",
        "duration": "Until stone passes, typically 1-3 weeks",
        "instructions": "Tamsulosin daily to relax urinary muscles. Drink 3-4 liters water daily. Strain urine to catch stone. Limit sodium and protein.",
        "doctor_visit": "For severe pain, inability to pass urine, fever, or stones larger than 5mm, urological intervention may be necessary."
    },
    
    # Eye Conditions
    "dry eyes": {
        "medicine": "Artificial tears (preservative-free), Omega-3 supplements",
        "duration": "Ongoing as needed",
        "instructions": "Use artificial tears 4-6 times daily. Omega-3 daily. Blink frequently when using screens. Use humidifier. 20-20-20 rule for screens.",
        "doctor_visit": "If dryness is severe, vision affected, or eyes become red and painful, ophthalmological evaluation needed."
    },
    "eye strain": {
        "medicine": "Lubricating eye drops, Blue light filtering glasses",
        "duration": "Ongoing with lifestyle modifications",
        "instructions": "Use lubricating drops as needed. Follow 20-20-20 rule: every 20 minutes, look 20 feet away for 20 seconds. Adequate lighting important.",
        "doctor_visit": "If eye strain causes persistent headaches, vision changes, or eye pain, consult an ophthalmologist."
    },
    "conjunctivitis": {
        "medicine": "Antibiotic eye drops (Moxifloxacin), Artificial tears",
        "duration": "5-7 days",
        "instructions": "Apply antibiotic drops 3-4 times daily. Clean eyes with warm compress. Avoid touching eyes. Don't share towels. Highly contagious.",
        "doctor_visit": "If vision is affected, severe pain, or no improvement in 2 days, ophthalmology consultation essential."
    },
    
    # Dental
    "toothache": {
        "medicine": "Ibuprofen 400mg, Clove oil, Saltwater rinse",
        "duration": "Until dental appointment",
        "instructions": "Ibuprofen every 6 hours for pain. Apply clove oil to affected tooth. Rinse with warm salt water. Avoid very hot or cold foods.",
        "doctor_visit": "Toothache requires dental evaluation. If accompanied by fever, swelling, or severe pain, see dentist immediately."
    },
    "gum inflammation": {
        "medicine": "Chlorhexidine mouthwash, Vitamin C supplements",
        "duration": "7-10 days",
        "instructions": "Rinse with Chlorhexidine twice daily after brushing. Vitamin C daily. Gentle brushing, proper flossing. Avoid tobacco.",
        "doctor_visit": "If gums bleed excessively, severe pain, or swelling persists, dental consultation necessary."
    },
    
    # Diabetes Management
    "high blood sugar": {
        "medicine": "Prescribed diabetes medication (Metformin, Insulin, etc.)",
        "duration": "Ongoing lifelong management",
        "instructions": "Take medications exactly as prescribed. Monitor blood sugar regularly. Low-carb diet. Regular exercise. Maintain healthy weight.",
        "doctor_visit": "Regular endocrinologist visits essential. Emergency care if blood sugar >300 mg/dL, confusion, or severe symptoms occur."
    },
    "low blood sugar": {
        "medicine": "Quick glucose source (glucose tablets, juice), then complex carbs",
        "duration": "Immediate treatment",
        "instructions": "Consume 15-20g fast-acting carbs immediately. Recheck in 15 minutes. Follow with snack containing protein. Avoid overtreatment.",
        "doctor_visit": "If hypoglycemia is frequent, severe, or causes loss of consciousness, immediate medical evaluation and medication adjustment needed."
    },
    
    # Blood Pressure
    "high blood pressure": {
        "medicine": "Prescribed antihypertensives (Amlodipine, Losartan, etc.)",
        "duration": "Ongoing lifelong management",
        "instructions": "Take medication at same time daily. Low-salt diet. Regular exercise. Weight management. Reduce stress. Monitor BP regularly.",
        "doctor_visit": "Regular cardiology follow-ups essential. Emergency care if BP >180/120, severe headache, chest pain, or vision changes occur."
    },
    "low blood pressure": {
        "medicine": "Increased salt intake, Fludrocortisone if prescribed",
        "duration": "As needed",
        "instructions": "Increase fluid and salt intake. Wear compression stockings. Rise slowly from sitting/lying. Small frequent meals. Avoid prolonged standing.",
        "doctor_visit": "If causing dizziness, fainting, or symptoms affecting daily life, cardiological evaluation recommended."
    },
    
    # Thyroid
    "hypothyroidism": {
        "medicine": "Levothyroxine (dose prescribed by doctor)",
        "duration": "Lifelong therapy",
        "instructions": "Take Levothyroxine on empty stomach, 30-60 minutes before breakfast. Don't take with calcium or iron supplements. Consistent timing crucial.",
        "doctor_visit": "Regular endocrinology follow-ups for TSH monitoring essential. Dosage adjustments based on lab results."
    },
    "hyperthyroidism": {
        "medicine": "Methimazole or Propylthiouracil as prescribed",
        "duration": "Long-term management",
        "instructions": "Take anti-thyroid medication as prescribed. Regular blood tests essential. Avoid iodine-rich foods. Beta-blockers may control symptoms.",
        "doctor_visit": "Regular endocrinologist visits mandatory. Emergency care if severe palpitations, fever, or thyroid storm symptoms develop."
    },
    
    # Heart Health
    "cholesterol": {
        "medicine": "Atorvastatin 10-40mg, Omega-3 fish oil",
        "duration": "Long-term management",
        "instructions": "Statin once daily at bedtime. Low-fat, high-fiber diet. Regular aerobic exercise. Avoid trans fats. Regular lipid panel monitoring.",
        "doctor_visit": "Regular cardiology follow-ups for lipid monitoring. If muscle pain or weakness develops on statins, immediate consultation needed."
    },
    "heart palpitations": {
        "medicine": "Beta-blockers if prescribed, Magnesium supplements",
        "duration": "As directed by cardiologist",
        "instructions": "Take prescribed medication regularly. Reduce caffeine and alcohol. Stress management. Adequate sleep. Stay hydrated.",
        "doctor_visit": "If palpitations are frequent, accompanied by chest pain, shortness of breath, or fainting, immediate cardiac evaluation essential."
    },
    
    # Respiratory Long-term
    "asthma": {
        "medicine": "Salbutamol inhaler (rescue), Beclomethasone inhaler (controller)",
        "duration": "Long-term management",
        "instructions": "Use controller inhaler daily as prescribed. Rescue inhaler when needed. Avoid triggers. Peak flow monitoring. Have action plan.",
        "doctor_visit": "Regular pulmonology follow-ups essential. Emergency care if severe breathing difficulty, rescue inhaler not helping, or blue lips occur."
    },
    "bronchitis": {
        "medicine": "Amoxicillin 500mg if bacterial, Bronchodilator inhaler, Mucolytic",
        "duration": "7-10 days for acute",
        "instructions": "Complete antibiotic course if prescribed. Use bronchodilator as needed. Mucolytic to loosen mucus. Steam inhalation. Stay hydrated.",
        "doctor_visit": "If breathlessness worsens, high fever persists, or coughing up blood, immediate medical attention required."
    },
    
    # Additional Common Conditions (50-100)
    "ear infection": {
        "medicine": "Amoxicillin 500mg, Ear drops (if prescribed), Pain relievers",
        "duration": "7-10 days",
        "instructions": "Complete full antibiotic course. Pain reliever as needed. Apply warm compress to ear. Keep ear dry. Don't insert objects in ear.",
        "doctor_visit": "If severe pain, drainage from ear, hearing loss, or symptoms worsen, ENT consultation necessary."
    },
    "sinusitis": {
        "medicine": "Amoxicillin-Clavulanate 625mg, Nasal decongestant spray, Steam inhalation",
        "duration": "10-14 days",
        "instructions": "Antibiotic thrice daily with meals. Nasal spray for 3-5 days only. Steam inhalation twice daily. Drink plenty of fluids.",
        "doctor_visit": "If symptoms persist beyond 2 weeks, severe facial pain, or vision changes occur, ENT evaluation needed."
    },
    "vertigo": {
        "medicine": "Betahistine 16mg, Cinnarizine 25mg",
        "duration": "Variable, typically 2-6 weeks",
        "instructions": "Take medication as prescribed. Avoid sudden head movements. Epley maneuver may help. Stay hydrated. Adequate sleep.",
        "doctor_visit": "If vertigo is severe, recurrent, or accompanied by hearing loss or neurological symptoms, neurological evaluation essential."
    },
    "hemorrhoids": {
        "medicine": "Topical hemorrhoid cream, Fiber supplements, Stool softeners",
        "duration": "2-4 weeks",
        "instructions": "Apply cream after each bowel movement. High-fiber diet. Sitz baths twice daily. Avoid straining. Drink plenty of water.",
        "doctor_visit": "If bleeding is excessive, severe pain, or prolapse occurs, colorectal surgical consultation may be needed."
    },
    "gout": {
        "medicine": "Colchicine 0.5mg, Allopurinol 300mg (long-term), NSAIDs for acute",
        "duration": "Acute: 5-7 days; Preventive: ongoing",
        "instructions": "Colchicine at attack onset. Allopurinol daily for prevention. Low-purine diet. Avoid alcohol. Hydrate well. Elevate affected joint.",
        "doctor_visit": "For severe attacks, recurrent gout, or if medication causes side effects, rheumatology consultation recommended."
    },
    "osteoarthritis": {
        "medicine": "Glucosamine-Chondroitin, Paracetamol, Topical NSAIDs",
        "duration": "Ongoing long-term management",
        "instructions": "Joint supplements daily. Pain relievers as needed. Gentle exercises and physiotherapy. Weight management crucial. Avoid joint overuse.",
        "doctor_visit": "Regular orthopedic or rheumatology follow-ups. If pain is severe or mobility severely limited, surgical options may be discussed."
    },
    "tendonitis": {
        "medicine": "Ibuprofen 400mg, Ice therapy, Rest",
        "duration": "2-4 weeks",
        "instructions": "Ibuprofen thrice daily after meals. Ice affected area 15 minutes 3-4 times daily. Rest tendon. Gentle stretching after acute phase.",
        "doctor_visit": "If pain persists beyond 4 weeks, severe swelling, or complete loss of movement, orthopedic evaluation needed."
    },
    "carpal tunnel": {
        "medicine": "NSAIDs, Wrist splint (especially at night), Vitamin B6",
        "duration": "4-8 weeks conservative treatment",
        "instructions": "Wear splint during activities and sleep. NSAIDs for pain. Ergonomic modifications. Nerve gliding exercises. Avoid repetitive wrist movements.",
        "doctor_visit": "If numbness is constant, muscle wasting, or conservative treatment fails, orthopedic or neurosurgical consultation for possible surgery."
    },
    "sciatica": {
        "medicine": "Pregabalin 75mg, Muscle relaxants, NSAIDs",
        "duration": "4-8 weeks",
        "instructions": "Take nerve pain medication as prescribed. Gentle stretching exercises. Alternate heat and ice. Avoid prolonged sitting. Physiotherapy beneficial.",
        "doctor_visit": "If pain radiates down both legs, bowel/bladder dysfunction, or progressive weakness occurs, immediate spinal specialist consultation."
    },
    "plantar fasciitis": {
        "medicine": "NSAIDs, Supportive footwear, Night splints",
        "duration": "6-12 weeks",
        "instructions": "NSAIDs for pain. Wear supportive shoes with good arch support. Stretch calf and foot. Ice bottle rolling. Avoid barefoot walking.",
        "doctor_visit": "If pain is severe, limits mobility, or persists beyond 3 months, podiatry or orthopedic consultation recommended."
    },
    "varicose veins": {
        "medicine": "Diosmin-Hesperidin 450mg/50mg, Compression stockings",
        "duration": "Ongoing management",
        "instructions": "Take vein supplement twice daily. Wear compression stockings during day. Elevate legs when resting. Regular walking. Avoid prolonged standing.",
        "doctor_visit": "If veins become painful, swollen, skin changes occur, or bleeding happens, vascular surgery consultation needed."
    },
    "anemia": {
        "medicine": "Iron supplement (Ferrous sulfate 325mg), Folic acid, Vitamin B12",
        "duration": "3-6 months",
        "instructions": "Iron supplement daily on empty stomach. Vitamin C enhances absorption. Include iron-rich foods. Avoid tea/coffee near supplement time.",
        "doctor_visit": "If symptoms persist, severe fatigue, or hemoglobin doesn't improve, hematology evaluation for underlying causes essential."
    },
    "fatigue": {
        "medicine": "Multivitamin, Iron if deficient, Vitamin D, B-complex",
        "duration": "Ongoing until cause identified",
        "instructions": "Adequate sleep (7-9 hours). Balanced diet. Regular exercise. Stress management. Rule out underlying conditions through blood tests.",
        "doctor_visit": "If fatigue is chronic, severe, affecting daily function, or accompanied by other symptoms, comprehensive medical evaluation necessary."
    },
    "dehydration": {
        "medicine": "ORS (Oral Rehydration Solution), Electrolyte drinks",
        "duration": "1-2 days",
        "instructions": "Drink ORS frequently in small amounts. Clear broths, coconut water beneficial. Avoid caffeinated and alcoholic beverages.",
        "doctor_visit": "If unable to keep fluids down, severe dizziness, decreased urination, or confusion occurs, IV hydration may be needed."
    },
    "motion sickness": {
        "medicine": "Dimenhydrinate 50mg, Meclizine 25mg, Ginger capsules",
        "duration": "30-60 minutes before travel",
        "instructions": "Take medication before travel. Sit in front seats or middle of boat. Focus on horizon. Fresh air. Ginger or peppermint may help.",
        "doctor_visit": "If motion sickness is severe, frequent, or doesn't respond to medication, ENT or neurology consultation may help identify underlying causes."
    },
    "rosacea": {
        "medicine": "Metronidazole gel 0.75%, Azelaic acid cream, Oral antibiotics if severe",
        "duration": "Ongoing management",
        "instructions": "Apply topical treatment as directed. Gentle skincare, fragrance-free products. Avoid triggers (spicy food, alcohol, extreme temps). Sunscreen essential.",
        "doctor_visit": "Regular dermatology follow-ups. If eye involvement, severe flushing, or thickening of skin occurs, prompt evaluation needed."
    },
    "psoriasis": {
        "medicine": "Topical corticosteroids, Vitamin D analogs, Moisturizers",
        "duration": "Ongoing chronic management",
        "instructions": "Apply prescribed topicals as directed. Regular moisturizing crucial. Sunlight exposure beneficial (with precautions). Avoid skin trauma.",
        "doctor_visit": "Regular dermatology visits essential. If widespread, joint pain develops, or severe, systemic therapy or biologics may be needed."
    },
    "dandruff": {
        "medicine": "Ketoconazole shampoo 2%, Selenium sulfide shampoo, Zinc pyrithione shampoo",
        "duration": "Ongoing as needed",
        "instructions": "Use medicated shampoo 2-3 times weekly. Leave on scalp 5 minutes before rinsing. Regular hair washing. Manage stress.",
        "doctor_visit": "If dandruff is severe, causes hair loss, or spreads to face/body, dermatological evaluation recommended."
    },
    "hair loss": {
        "medicine": "Minoxidil 5% solution, Finasteride 1mg (men), Biotin supplements",
        "duration": "6-12 months to see results; ongoing",
        "instructions": "Apply Minoxidil twice daily to scalp. Finasteride daily (men only, prescription needed). Biotin daily. Balanced diet, reduce stress.",
        "doctor_visit": "If hair loss is sudden, patchy, or accompanied by other symptoms, dermatology or endocrinology consultation to rule out underlying conditions."
    },
    "bad breath": {
        "medicine": "Chlorhexidine mouthwash, Tongue scraper, Probiotics",
        "duration": "Ongoing oral hygiene",
        "instructions": "Brush twice daily, floss daily, clean tongue. Use mouthwash. Stay hydrated. Avoid tobacco. Regular dental checkups.",
        "doctor_visit": "If bad breath persists despite good oral hygiene, dental or medical evaluation needed to rule out dental/medical causes."
    },
    "cold sores": {
        "medicine": "Acyclovir cream 5%, Valacyclovir 500mg oral",
        "duration": "5-7 days",
        "instructions": "Apply antiviral cream at first sign. Oral medication if prescribed. Avoid kissing and sharing utensils. Keep area clean and dry.",
        "doctor_visit": "If outbreaks are frequent (>6 per year), severe, or affect eyes, antiviral suppression therapy may be needed - consult doctor."
    },
    "warts": {
        "medicine": "Salicylic acid solution 17%, Cryotherapy (at clinic)",
        "duration": "Several weeks to months",
        "instructions": "Apply salicylic acid daily after soaking area. File down wart gently. Cover with bandage. Avoid spreading to other areas.",
        "doctor_visit": "If warts multiply, are painful, on face/genitals, or don't respond to treatment, dermatology consultation for alternative treatments."
    },
    "ringworm": {
        "medicine": "Clotrimazole cream 1%, Terbinafine cream 1%",
        "duration": "2-4 weeks",
        "instructions": "Apply antifungal cream twice daily, extending beyond rash border. Keep area clean and dry. Wash bedding and clothes in hot water.",
        "doctor_visit": "If infection spreads, affects scalp/nails, or doesn't respond to topical treatment, oral antifungals may be needed."
    },
    "athlete's foot": {
        "medicine": "Clotrimazole cream, Terbinafine cream, Antifungal powder",
        "duration": "2-4 weeks",
        "instructions": "Apply cream twice daily. Use antifungal powder in shoes. Keep feet dry, change socks daily. Avoid walking barefoot in public areas.",
        "doctor_visit": "If infection is severe, spreads, or recurrent despite treatment, dermatology evaluation for oral antifungals."
    },
    "jock itch": {
        "medicine": "Clotrimazole cream 1%, Miconazole cream 2%",
        "duration": "2-3 weeks",
        "instructions": "Apply antifungal cream twice daily. Keep area clean and dry. Wear loose cotton underwear. Avoid tight clothing.",
        "doctor_visit": "If rash doesn't improve in 2 weeks or worsens, dermatological evaluation needed to rule out other conditions."
    },
    "ingrown toenail": {
        "medicine": "Epsom salt soaks, Antibiotic ointment, Pain relievers",
        "duration": "1-2 weeks",
        "instructions": "Soak foot in warm Epsom salt water 3 times daily. Apply antibiotic ointment. Wear open-toed shoes. Don't cut nail too short.",
        "doctor_visit": "If severe pain, pus formation, or infection develops, podiatry or surgical consultation for partial nail removal may be needed."
    },
    "bunion": {
        "medicine": "NSAIDs for pain, Bunion pads, Proper footwear",
        "duration": "Ongoing management",
        "instructions": "Wear wide, comfortable shoes with good support. Use bunion pads to reduce pressure. Ice for pain. Avoid high heels.",
        "doctor_visit": "If bunion is painful, limits mobility, or progressively worsening, orthopedic or podiatry consultation for surgical correction options."
    },
    "calluses": {
        "medicine": "Salicylic acid patches, Moisturizing cream, Pumice stone",
        "duration": "2-4 weeks",
        "instructions": "Soak affected area, gently file with pumice stone. Apply moisturizer daily. Wear properly fitted shoes. Avoid excessive pressure.",
        "doctor_visit": "If calluses are painful, bleeding, or you have diabetes, podiatry evaluation essential before self-treatment."
    },
    "blisters": {
        "medicine": "Sterile bandages, Antibiotic ointment if open",
        "duration": "5-7 days to heal",
        "instructions": "Don't pop blister if possible. If broken, clean with soap and water, apply antibiotic ointment, cover with bandage. Change daily.",
        "doctor_visit": "If blister shows signs of infection (increased pain, redness, pus, fever), medical evaluation needed."
    },
    "sunburn": {
        "medicine": "Aloe vera gel, Ibuprofen 400mg, Hydrocortisone cream 1%",
        "duration": "3-7 days",
        "instructions": "Apply aloe vera frequently. Ibuprofen for pain and inflammation. Cool compresses. Stay hydrated. Moisturize as skin peels.",
        "doctor_visit": "If severe blistering, fever, chills, or signs of infection develop, medical attention required."
    },
    "heat rash": {
        "medicine": "Calamine lotion, Hydrocortisone cream 1%, Antihistamine if itchy",
        "duration": "2-3 days",
        "instructions": "Keep affected area cool and dry. Wear loose, breathable clothing. Avoid heavy creams. Take cool showers.",
        "doctor_visit": "If rash persists beyond 3 days, becomes infected, or is accompanied by fever, medical evaluation recommended."
    },
    "bee sting": {
        "medicine": "Antihistamine (Diphenhydramine 25mg), Ice pack, Pain reliever",
        "duration": "1-3 days",
        "instructions": "Remove stinger by scraping (don't squeeze). Ice area. Antihistamine for swelling/itching. Elevate if on limb.",
        "doctor_visit": "If difficulty breathing, severe swelling, or signs of allergic reaction (anaphylaxis) occur, seek emergency care immediately."
    },
    "mosquito bites": {
        "medicine": "Antihistamine cream, Calamine lotion, Oral antihistamine if needed",
        "duration": "2-5 days",
        "instructions": "Apply anti-itch cream. Don't scratch. Ice pack reduces swelling. Antihistamine for severe itching.",
        "doctor_visit": "If bites become infected, very swollen, or accompanied by fever (possible mosquito-borne illness), seek medical care."
    },
    "minor burns": {
        "medicine": "Silver sulfadiazine cream, Aloe vera gel, Pain relievers",
        "duration": "1-2 weeks",
        "instructions": "Cool burn with running water (not ice). Apply burn cream. Cover with sterile bandage. Change daily. Keep clean.",
        "doctor_visit": "For burns larger than 3 inches, deep (white/charred), on face/hands/joints, or showing infection signs, immediate medical care needed."
    },
    "minor cuts": {
        "medicine": "Antibiotic ointment (Neosporin), Sterile bandages",
        "duration": "5-10 days to heal",
        "instructions": "Clean wound with soap and water. Apply antibiotic ointment. Cover with bandage. Change daily and keep clean.",
        "doctor_visit": "If cut is deep, won't stop bleeding, shows infection signs, or tetanus vaccine not current, medical evaluation needed."
    },
    "bruises": {
        "medicine": "Ice pack (first 24 hours), Arnica gel, Pain relievers",
        "duration": "1-2 weeks",
        "instructions": "Ice immediately for 15 minutes every hour. After 24 hours, warm compress. Elevate if possible. Arnica gel may help.",
        "doctor_visit": "If bruising is excessive, occurs easily/frequently, or very painful, medical evaluation to rule out bleeding disorders."
    },
    "sprains": {
        "medicine": "NSAIDs (Ibuprofen 400mg), Ice, Compression bandage",
        "duration": "1-6 weeks depending on severity",
        "instructions": "RICE protocol: Rest, Ice (15 min every 2-3 hours), Compression bandage, Elevate above heart. NSAIDs for pain/swelling.",
        "doctor_visit": "If unable to bear weight, severe pain, significant swelling, or no improvement in 2 weeks, orthopedic evaluation for possible fracture."
    },
    "nosebleed": {
        "medicine": "Nasal decongestant spray (if recurrent), Ice pack",
        "duration": "Immediate first aid",
        "instructions": "Sit upright, lean slightly forward. Pinch soft part of nose for 10 minutes. Ice pack on bridge of nose. Don't lie down or tilt head back.",
        "doctor_visit": "If bleeding doesn't stop after 20 minutes, recurrent nosebleeds, or after head injury, ENT or emergency evaluation needed."
    },
    "hiccups": {
        "medicine": "Usually none needed; Chlorpromazine for severe persistent cases",
        "duration": "Minutes to hours; persistent >48 hours needs evaluation",
        "instructions": "Hold breath, drink cold water slowly, breathe into paper bag, swallow sugar. Usually self-limiting.",
        "doctor_visit": "If hiccups persist beyond 48 hours or are frequent and bothersome, medical evaluation to rule out underlying causes."
    },
    "leg cramps": {
        "medicine": "Magnesium supplements, Calcium, Vitamin D",
        "duration": "Preventive supplementation ongoing",
        "instructions": "Stretch affected muscle immediately. Massage area. Stay hydrated. Adequate mineral intake. Warm bath before bed may prevent.",
        "doctor_visit": "If cramps are severe, frequent, or accompanied by swelling or skin changes, vascular or neurological evaluation needed."
    },
    "restless legs": {
        "medicine": "Iron supplements if deficient, Magnesium, Dopamine agonists if severe",
        "duration": "Variable; may need ongoing management",
        "instructions": "Regular exercise (but not before bed). Leg massage. Warm/cold compress. Avoid caffeine. Address iron deficiency if present.",
        "doctor_visit": "If significantly affecting sleep and quality of life, neurology consultation for proper diagnosis and treatment."
    },
    "snoring": {
        "medicine": "Nasal strips, Saline nasal spray, Weight loss if overweight",
        "duration": "Ongoing lifestyle management",
        "instructions": "Sleep on side. Elevate head of bed. Avoid alcohol before bed. Maintain healthy weight. Treat nasal congestion.",
        "doctor_visit": "If snoring is loud, causes daytime sleepiness, or witnessed breathing pauses, sleep study for sleep apnea evaluation essential."
    },
    "jet lag": {
        "medicine": "Melatonin 3-5mg, Stay hydrated",
        "duration": "Few days to adjust",
        "instructions": "Melatonin at new bedtime. Get sunlight exposure in new timezone. Stay hydrated during flight. Adjust meal times to new schedule.",
        "doctor_visit": "Usually self-limiting. If severe symptoms or underlying sleep disorder suspected, sleep medicine consultation may help."
    },
    "hangover": {
        "medicine": "Electrolyte drinks, Pain relievers (avoid acetaminophen), B-vitamins",
        "duration": "12-24 hours",
        "instructions": "Rehydrate with water and electrolyte solutions. Light, bland foods. Rest. B-vitamins may help. Best prevention: moderate alcohol intake.",
        "doctor_visit": "If severe vomiting, unable to keep fluids down, or confused, medical evaluation for potential alcohol poisoning or dehydration."
    },
    "food poisoning": {
        "medicine": "ORS, Anti-nausea (Ondansetron), Probiotics",
        "duration": "1-3 days typically",
        "instructions": "Rest stomach, then bland diet (BRAT: Bananas, Rice, Applesauce, Toast). Stay hydrated with ORS. Avoid dairy, greasy foods initially.",
        "doctor_visit": "If severe vomiting/diarrhea, blood in stool, high fever, signs of dehydration, or symptoms persist >3 days, medical care needed."
    },
    "bad posture": {
        "medicine": "Physical therapy, Ergonomic supports, Pain relievers if needed",
        "duration": "Ongoing correction",
        "instructions": "Ergonomic workspace setup. Regular stretching and strengthening exercises. Posture awareness. Physical therapy may help.",
        "doctor_visit": "If causing chronic pain, neurological symptoms, or structural changes, orthopedic or physical medicine consultation recommended."
    }
}


def save_medical_note(health_note, ai_tips, user_id="default"):
    """Save medical note to database with date and time."""
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        conn = sqlite3.connect(MEDICAL_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO medical_notes (date, time, health_note, ai_tips, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (date_str, time_str, health_note, ai_tips, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Save medical note failed: {e}")
        return False


def get_last_medical_note(user_id="default"):
    """Retrieve last medical note."""
    try:
        conn = sqlite3.connect(MEDICAL_DB)
        c = conn.cursor()
        c.execute("""
            SELECT date, time, health_note, ai_tips FROM medical_notes
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        note = c.fetchone()
        conn.close()
        return note
    except Exception as e:
        print(f"[ERROR] Get last medical note failed: {e}")
        return None


def generate_medical_tips(health_note):
    """Generate wellness tips based on health description using static database and Gemini fallback."""
    health_note_lower = health_note.lower()
    
    # Search for matching condition in database
    matched_condition = None
    best_match_score = 0
    
    for condition_key, condition_data in MEDICAL_KNOWLEDGE_DB.items():
        # Count how many keywords from the condition appear in the health note
        keywords = condition_key.split()
        match_score = sum(1 for keyword in keywords if keyword in health_note_lower)
        
        if match_score > best_match_score:
            best_match_score = match_score
            matched_condition = (condition_key, condition_data)
    
    # If we found a good match (at least one keyword matched)
    if matched_condition and best_match_score > 0:
        condition_name, data = matched_condition
        
        response = f"""**Condition Identified:** {condition_name.title()}

**Recommended Medication:** {data['medicine']}

**Treatment Duration:** {data['duration']}

**Instructions:** {data['instructions']}

**Important:** {data['doctor_visit']}

âš ï¸ **MEDICAL DISCLAIMER:** This information is for general guidance only and is NOT a substitute for professional medical diagnosis or treatment. Always consult a qualified healthcare provider for proper medical evaluation and personalized treatment recommendations."""
        
        return response
    
    # Fallback to Gemini if no match found in database
    prompt = f"""The user described their health concern as: "{health_note}"

Please provide:
1. General wellness tips and suggestions (2-3 tips)
2. Common over-the-counter information (if applicable)
3. Always include: "This is not a medical diagnosis. Please consult a qualified doctor for proper evaluation."

Keep it brief, helpful, and professional."""
    
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 350},
        }
        
        res = requests.post(
            GEN_API_URL + "?key=" + GEMINI_API_KEY,
            headers=headers,
            json=payload,
            timeout=25,
        )
        
        if res.status_code != 200:
            return "I couldn't find specific information for your concern. Please consult a qualified doctor for proper medical evaluation and personalized treatment."
        
        data = res.json()
        cand = data.get("candidates", [])
        if cand:
            parts = cand[0].get("content", {}).get("parts", [])
            msg = "".join(p.get("text", "") for p in parts)
            return clean_text(msg) + "\n\nâš ï¸ DISCLAIMER: This is NOT a medical diagnosis. Please consult a qualified doctor."
        
        return "I couldn't find specific information for your concern. Please consult a qualified doctor for proper medical evaluation and personalized treatment."
    except Exception as e:
        return f"I couldn't process your request at this time. Please consult a qualified doctor for proper medical evaluation and personalized treatment. Error: {str(e)}"


def process_medical_audio():
    """Convert medical audio file to text and generate tips."""
    global last_medical_note, medical_seq

    if not os.path.exists(MEDICAL_AUDIO_FILE):
        return {"error": "No audio recorded"}

    try:
        with sr.AudioFile(MEDICAL_AUDIO_FILE) as src:
            audio = recognizer.record(src)
            text = recognizer.recognize_google(audio)
    except Exception as e:
        return {"error": f"STT Error: {e}"}

    # Generate tips using Gemini
    tips = generate_medical_tips(text)
    
    # Save to database
    if save_medical_note(text, tips):
        with medical_lock:
            last_medical_note = text
            medical_seq += 1
        safe_remove(MEDICAL_AUDIO_FILE)
        return {"health_note": text, "ai_tips": tips}
    else:
        return {"error": "Failed to save note"}


# ---------------------------------------------------------
# MENTAL HEALTH HELPERS
# ---------------------------------------------------------
def save_mental_checkup(transcript, emotion, confidence, tips, user_id="default"):
    """Save mental health checkup to database with date and time."""
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        conn = sqlite3.connect(MENTAL_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO mental_checkups (date, time, transcript, emotion, confidence, wellness_tips, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date_str, time_str, transcript, emotion, confidence, tips, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Save mental checkup failed: {e}")
        return False


def get_last_mental_checkup(user_id="default"):
    """Retrieve last mental health checkup."""
    try:
        conn = sqlite3.connect(MENTAL_DB)
        c = conn.cursor()
        c.execute("""
            SELECT date, time, emotion, transcript, wellness_tips FROM mental_checkups
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        checkup = c.fetchone()
        conn.close()
        return checkup
    except Exception as e:
        print(f"[ERROR] Get last mental checkup failed: {e}")
        return None


def analyze_emotion_from_text(transcript):
    """Analyze emotional state from transcript using improved keyword detection + Gemini."""
    
    transcript_lower = transcript.lower()
    
    # IMPROVED: More specific and comprehensive emotion keywords
    emotion_keywords = {
        "sad": [
            "sad", "sadness", "unhappy", "down", "blue", "depressed", "cry", "crying", "tears", "tearful",
            "heartbroken", "broken", "lost", "loss", "fail", "failure", "defeat", "miserable", "sorrow",
            "low", "gloomy", "melancholy"
        ],
        "happy": [
            "happy", "happiness", "glad", "joy", "joyful", "pleased", "delighted", "wonderful", "great",
            "good", "beautiful", "love", "loved", "amazing", "awesome", "fantastic", "excellent",
            "perfect", "success", "succeeded", "win", "won", "victory", "celebrate", "celebration"
        ],
        "excited": [
            "excited", "excitement", "thrilled", "eager", "enthusiastic", "pumped", "stoked",
            "exhilarated", "amazing", "incredible", "fantastic", "awesome", "won", "victory", "winning",
            "looking forward", "anticipate"
        ],
        "anxious": [
            "anxious", "anxiety", "worried", "worry", "nervous", "stress", "stressed", "panic",
            "fear", "afraid", "scared", "frightened", "concern", "concerned", "troubled", "uneasy",
            "uncertain", "doubt", "doubtful"
        ],
        "angry": [
            "angry", "anger", "furious", "fury", "mad", "rage", "enraged", "irritated", "annoyed",
            "upset", "fed up", "frustrated", "frustration", "hate", "hated", "despise"
        ],
        "calm": [
            "calm", "calmness", "peaceful", "peace", "relaxed", "relaxation", "serene", "serenity",
            "tranquil", "tranquility", "quiet", "still", "gentle", "zen", "meditate", "meditation", "soothed"
        ],
        "peaceful": [
            "peaceful", "peace", "serene", "serenity", "tranquil", "tranquility", "zen", "meditate",
            "meditation", "mindful", "harmony", "balanced", "content", "contentment", "satisfied"
        ],
        "focused": [
            "focused", "focus", "concentration", "concentrate", "determined", "determination", "dedicated",
            "committed", "commitment", "goal", "goals", "target", "work", "working", "productive"
        ],
        "stressed": [
            "stressed", "stress", "overwhelmed", "overwhelm", "pressure", "tension", "tense", "busy",
            "hectic", "rush", "rushing", "chaos", "chaotic", "overloaded", "burden", "burdened"
        ],
        "neutral": [
            "okay", "ok", "fine", "normal", "regular", "usual", "standard", "average", "alright"
        ]
    }
    
    # Score emotions based on keyword matches with word boundaries
    import re
    emotion_scores = {}
    for emotion, keywords in emotion_keywords.items():
        score = 0
        for keyword in keywords:
            # Use word boundary matching to find whole word matches only
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, transcript_lower):
                # Weight by keyword length (longer, more specific keywords score higher)
                score += len(keyword) / 10.0
        emotion_scores[emotion] = score
    
    # Find dominant emotion from keywords
    dominant_emotion = max(emotion_scores, key=emotion_scores.get) if emotion_scores else "neutral"
    keyword_confidence = 0.0
    
    if emotion_scores[dominant_emotion] > 0:
        # Calculate confidence based on keyword matches
        total_words = len(transcript.split())
        keyword_matches = emotion_scores[dominant_emotion]
        keyword_confidence = min(0.95, keyword_matches / max(1, total_words / 3))
    
    # Use Gemini for enhanced analysis and tips generation
    prompt = f"""Analyze the following text and determine the person's emotional state. Focus on scenarios like:
- When they mention winning/won â†’ excited
- When they mention being scolded/scold â†’ sad
- Look for emotional context clues

Text: "{transcript}"

Please respond EXACTLY in this format:
EMOTION: [choose one: happy, sad, excited, calm, anxious, angry, neutral, focused, peaceful, stressed]
CONFIDENCE: [0.0-1.0]
TIPS: [3-4 short wellness tips separated by newlines, each starting with a number like "1. "]

Be specific and concise based on the scenario in the text."""
    
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 250},
        }
        
        res = requests.post(
            GEN_API_URL + "?key=" + GEMINI_API_KEY,
            headers=headers,
            json=payload,
            timeout=25,
        )
        
        if res.status_code != 200:
            # Use keyword-based detection as fallback
            return {
                "emotion": dominant_emotion,
                "confidence": min(0.9, keyword_confidence + 0.5),
                "tips": "Take a deep breath and reflect on your feelings. Practice mindfulness and self-care."
            }
        
        data = res.json()
        cand = data.get("candidates", [])
        if cand:
            parts = cand[0].get("content", {}).get("parts", [])
            msg = "".join(p.get("text", "") for p in parts)
            
            # Parse response
            emotion = dominant_emotion  # Default to keyword detection
            confidence = keyword_confidence
            tips = "Take time for self-care and reflection."
            
            lines = msg.split('\n')
            for line in lines:
                if "EMOTION:" in line:
                    gemini_emotion = line.replace("EMOTION:", "").strip().lower()
                    # Validate emotion is in our list
                    if gemini_emotion in emotion_keywords:
                        emotion = gemini_emotion
                elif "CONFIDENCE:" in line:
                    try:
                        conf_str = line.replace("CONFIDENCE:", "").strip()
                        gemini_conf = float(conf_str)
                        # Use average of keyword and Gemini confidence
                        confidence = (keyword_confidence + gemini_conf) / 2
                    except:
                        confidence = keyword_confidence
                elif "TIPS:" in line:
                    tips = '\n'.join([l.strip() for l in lines[lines.index(line)+1:] if l.strip()])
                    if not tips:
                        tips = "Reflect on your feelings and practice self-awareness."
                    break
            
            return {"emotion": emotion, "confidence": min(0.99, confidence), "tips": tips}
        
        # Fallback to keyword-based detection
        return {
            "emotion": dominant_emotion,
            "confidence": min(0.85, keyword_confidence + 0.3),
            "tips": "Take a moment to reflect on your emotional state and practice self-care."
        }
    except Exception as e:
        print(f"[ERROR] Emotion analysis failed: {e}")
        # Fallback to keyword-based detection
        return {
            "emotion": dominant_emotion,
            "confidence": min(0.8, keyword_confidence + 0.2),
            "tips": "Remember to take care of yourself. Practice mindfulness and breathing exercises."
        }


def get_today_mental_stats(user_id="default"):
    """Get today's mental health checkup statistics."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(MENTAL_DB)
        c = conn.cursor()
        
        # Get all today's checkups
        c.execute("""
            SELECT emotion FROM mental_checkups
            WHERE date = ? AND user_id = ?
            ORDER BY created_at DESC
        """, (today, user_id))
        
        emotions = [row[0] for row in c.fetchall()]
        conn.close()
        
        # Count emotions
        from collections import Counter
        emotion_counts = dict(Counter(emotions))
        
        # Find primary emotion
        primary_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "None"
        
        return {
            "today_count": len(emotions),
            "primary_emotion": primary_emotion,
            "emotion_breakdown": emotion_counts
        }
    except Exception as e:
        print(f"[ERROR] Get mental stats failed: {e}")
        return {"today_count": 0, "primary_emotion": "None", "emotion_breakdown": {}}


def process_mental_audio():
    """Convert mental health audio file to text and analyze emotion."""
    global last_mental_emotion, last_mental_tips, mental_seq

    if not os.path.exists(MENTAL_AUDIO_FILE):
        return {"error": "No audio recorded"}

    try:
        with sr.AudioFile(MENTAL_AUDIO_FILE) as src:
            audio = recognizer.record(src)
            transcript = recognizer.recognize_google(audio)
    except Exception as e:
        return {"error": f"STT Error: {e}"}

    # Analyze emotion using Gemini
    analysis = analyze_emotion_from_text(transcript)
    emotion = analysis["emotion"]
    confidence = analysis["confidence"]
    tips = analysis["tips"]
    
    # Save to database
    if save_mental_checkup(transcript, emotion, confidence, tips):
        with mental_lock:
            last_mental_emotion = emotion
            last_mental_tips = tips
            mental_seq += 1
        safe_remove(MENTAL_AUDIO_FILE)
        return {"emotion": emotion, "confidence": confidence, "tips": tips, "transcript": transcript}
    else:
        return {"error": "Failed to save checkup"}


# ---------------------------------------------------------
# LOCATION TRACKING HELPERS
# ---------------------------------------------------------
def get_gps_location():
    """
    Get GPS location from device.
    Attempts multiple methods:
    1. gpsd (GPS daemon) - for devices with GPS hardware
    2. nmea parsing from serial GPS
    3. IP-based geolocation as fallback
    """
    global location_cache
    
    # Method 1: Try gpsd (most common for embedded Linux with GPS)
    try:
        import gps
        session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        for i in range(10):  # Try for up to 10 iterations
            report = session.next()
            if report['class'] == 'TPV':
                if hasattr(report, 'lat') and hasattr(report, 'lon'):
                    with location_lock:
                        location_cache['latitude'] = report.lat
                        location_cache['longitude'] = report.lon
                        location_cache['altitude'] = getattr(report, 'alt', 0.0)
                        location_cache['speed'] = getattr(report, 'speed', 0.0) * 3.6  # m/s to km/h
                        location_cache['accuracy'] = getattr(report, 'epy', 10.0)  # error in meters
                        location_cache['timestamp'] = datetime.now()
                    return True
        return False
    except (ImportError, Exception) as e:
        print(f"[INFO] gpsd not available: {e}")
    
    # Method 2: Try reading from GPS serial device (common NMEA format)
    try:
        import serial
        import pynmea2
        
        # Common GPS serial ports
        gps_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0', '/dev/serial0']
        
        for port in gps_ports:
            if not os.path.exists(port):
                continue
                
            try:
                ser = serial.Serial(port, baudrate=9600, timeout=1)
                
                for i in range(20):  # Read up to 20 lines
                    line = ser.readline().decode('ascii', errors='ignore')
                    
                    if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                        try:
                            msg = pynmea2.parse(line)
                            
                            if hasattr(msg, 'latitude') and msg.latitude:
                                with location_lock:
                                    location_cache['latitude'] = msg.latitude
                                    location_cache['longitude'] = msg.longitude
                                    location_cache['altitude'] = getattr(msg, 'altitude', 0.0)
                                    location_cache['speed'] = getattr(msg, 'spd_over_grnd', 0.0) * 1.852  # knots to km/h
                                    location_cache['accuracy'] = 10.0  # default accuracy
                                    location_cache['timestamp'] = datetime.now()
                                ser.close()
                                return True
                        except pynmea2.ParseError:
                            continue
                
                ser.close()
            except Exception as e:
                print(f"[INFO] Serial GPS error on {port}: {e}")
                continue
    except ImportError:
        print("[INFO] pynmea2/serial not available for GPS parsing")
    except Exception as e:
        print(f"[INFO] Serial GPS read failed: {e}")
    
    # Method 3: IP-based geolocation fallback
    try:
        # Try multiple geolocation services
        services = [
            'http://ip-api.com/json/',
            'https://ipapi.co/json/',
            'https://geolocation-db.com/json/'
        ]
        
        for service_url in services:
            try:
                response = requests.get(service_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Different services use different field names
                    lat = data.get('lat') or data.get('latitude')
                    lon = data.get('lon') or data.get('longitude')
                    
                    if lat and lon:
                        with location_lock:
                            location_cache['latitude'] = float(lat)
                            location_cache['longitude'] = float(lon)
                            location_cache['altitude'] = 0.0
                            location_cache['speed'] = 0.0
                            location_cache['accuracy'] = 5000.0  # IP geolocation is less accurate
                            location_cache['timestamp'] = datetime.now()
                        print(f"[INFO] Using IP-based location: {lat}, {lon}")
                        return True
            except Exception as e:
                print(f"[INFO] Geolocation service {service_url} failed: {e}")
                continue
    except Exception as e:
        print(f"[INFO] IP geolocation failed: {e}")
    
    # If all methods fail, return cached location or default
    return False


def get_cached_location():
    """Get cached location data."""
    with location_lock:
        # If we have a recent location (within last 30 seconds), return it
        if location_cache['timestamp']:
            age = (datetime.now() - location_cache['timestamp']).total_seconds()
            if age < 30:
                return location_cache.copy()
        
        # Try to get fresh location
        get_gps_location()
        return location_cache.copy()


# ---------------------------------------------------------
# ANALYTICS & PARENTAL MODE HELPERS
# ---------------------------------------------------------
def log_activity(module_name, start_time, end_time, user_id="default"):
    """Log a module activity to the analytics database."""
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # Calculate duration in seconds
        start_dt = datetime.strptime(start_time, "%H:%M:%S.%f") if "." in start_time else datetime.strptime(start_time, "%H:%M:%S")
        end_dt = datetime.strptime(end_time, "%H:%M:%S.%f") if "." in end_time else datetime.strptime(end_time, "%H:%M:%S")
        duration = int((end_dt - start_dt).total_seconds())
        
        # Enforce minimum 1 minute (60 seconds) per session
        duration = max(60, duration)
        
        conn = sqlite3.connect(ANALYTICS_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO activity_logs (date, module_name, start_time, end_time, duration_seconds, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date_str, module_name, start_time, end_time, duration, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Log activity failed: {e}")
        return False


def get_daily_summary(user_id="default"):
    """Get today's usage summary."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(ANALYTICS_DB)
        c = conn.cursor()
        
        # Get total time today
        c.execute("""
            SELECT SUM(duration_seconds) FROM activity_logs
            WHERE date = ? AND user_id = ?
        """, (today, user_id))
        total_seconds = c.fetchone()[0] or 0
        
        # Get module breakdown
        c.execute("""
            SELECT module_name, SUM(duration_seconds) FROM activity_logs
            WHERE date = ? AND user_id = ?
            GROUP BY module_name
            ORDER BY SUM(duration_seconds) DESC
        """, (today, user_id))
        module_data = c.fetchall()
        conn.close()
        
        return {
            "total_seconds": total_seconds,
            "total_minutes": total_seconds // 60,
            "module_breakdown": [{"module": m[0], "seconds": m[1], "minutes": m[1] // 60} for m in module_data]
        }
    except Exception as e:
        print(f"[ERROR] Get daily summary failed: {e}")
        return {"total_seconds": 0, "total_minutes": 0, "module_breakdown": []}


def get_module_usage_details(user_id="default"):
    """Get detailed module usage for today."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(ANALYTICS_DB)
        c = conn.cursor()
        c.execute("""
            SELECT module_name, start_time, end_time, duration_seconds FROM activity_logs
            WHERE date = ? AND user_id = ?
            ORDER BY start_time DESC
        """, (today, user_id))
        
        records = c.fetchall()
        conn.close()
        
        result = []
        for record in records:
            result.append({
                "module": record[0],
                "start_time": record[1],
                "end_time": record[2],
                "duration_seconds": record[3],
                "duration_minutes": record[3] // 60
            })
        
        return result
    except Exception as e:
        print(f"[ERROR] Get module details failed: {e}")
        return []


def get_most_used_module(user_id="default"):
    """Get most used module today."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(ANALYTICS_DB)
        c = conn.cursor()
        c.execute("""
            SELECT module_name, SUM(duration_seconds) FROM activity_logs
            WHERE date = ? AND user_id = ?
            GROUP BY module_name
            ORDER BY SUM(duration_seconds) DESC LIMIT 1
        """, (today, user_id))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            return {"module": result[0], "total_seconds": result[1]}
        return None
    except Exception as e:
        print(f"[ERROR] Get most used module failed: {e}")
        return None


# ROUTES â€” AUDIO CONTROL
# ---------------------------------------------------------
@app.route("/start")
def start_record():
    global is_recording, recorder_process

    with state_lock:
        if is_recording:
            return jsonify({"status": "already_recording"})
        is_recording = True
        safe_remove(AUDIO_FILE)

        recorder_process = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", AUDIO_FILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return jsonify({"status": "recording_started"})


@app.route("/stop")
def stop_record():
    global is_recording, recorder_process

    with state_lock:
        if not is_recording:
            return jsonify({"status": "not_recording"})
        is_recording = False
        proc = recorder_process
        recorder_process = None

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    process_audio()
    return jsonify({"status": "recording_stopped"})


@app.route("/get_latest")
def get_latest():
    with state_lock:
        return jsonify({
            "seq": reply_seq,
            "transcript": last_transcript,
            "reply": last_reply
        })


@app.route("/status")
def status():
    with state_lock:
        return jsonify({"is_recording": is_recording, "seq": reply_seq})


# ---------------------------------------------------------
# ROUTES â€” MAIN / OCR / DETECT (serve external HTML files)
# ---------------------------------------------------------
@app.route("/")
def home():
    # Serve ui.html from current directory
    return send_from_directory(".", "ui.html")


@app.route("/ocr")
def ocr_page():
    with ocr_lock:
        safe_remove(OCR_CAP_IMG)
        safe_remove(OCR_OUT_IMG)
        safe_remove(OCR_TXT)
    return send_from_directory(".", "ocr.html")


@app.route("/diary")
def diary_page():
    with diary_lock:
        safe_remove(DIARY_AUDIO_FILE)
    return send_from_directory(".", "diary.html")

@app.route("/medical")
def medical_page():
    with medical_lock:
        safe_remove(MEDICAL_AUDIO_FILE)
    return send_from_directory(".", "medical.html")

@app.route("/parental")
def parental_page():
    return send_from_directory(".", "parental.html")

@app.route("/detect")
def detect_page():
    with detect_lock:
        safe_remove(DET_CAP_IMG)
        safe_remove(DET_OUT_IMG)
        safe_remove(DETS_FILE)
    return send_from_directory(".", "detect.html")


# ----- OCR ROUTES -----
@app.route("/ocr_capture")
def ocr_capture():
    with ocr_lock:
        success, msg = ocr_capture_frame()
        if not success:
            exists = os.path.exists(OCR_CAP_IMG)
            try:
                sz = os.path.getsize(OCR_CAP_IMG) if exists else 0
            except Exception:
                sz = 0
            print(f"[ERROR] ocr_capture: capture failed, exists={exists}, size={sz}, msg={msg}")
            return f"Capture failed (exists={exists}, size={sz}, msg={msg})", 500

        img_bin = preprocess_for_ocr()
        if img_bin is None:
            print("[ERROR] preprocess_for_ocr returned None")
            return "Preprocess failed", 500

        txt = run_ocr(img_bin)
        print("[INFO] OCR text generated, length=", len(txt or ""))
        return "OK"


@app.route("/ocr_result.jpg")
def ocr_result_img():
    if os.path.exists(OCR_OUT_IMG):
        return Response(open(OCR_OUT_IMG, "rb").read(), mimetype="image/jpeg")
    return "No image", 404


@app.route("/ocr_text")
def ocr_text_route():
    if os.path.exists(OCR_TXT):
        return open(OCR_TXT).read()
    return ""


# ----- OBJECT DETECTION ROUTES -----
@app.route("/detect_capture")
def detect_capture():
    with detect_lock:
        if not detect_capture_frame():
            return "Capture failed", 500

        # Run FPGA YOLO inference
        output = run_fpga_inference(DET_CAP_IMG)

        # Parse detections: list of tuples (class, conf, x, y, w, h)
        dets = parse_detections(output)

        # -------------------------------
        # NEW: COUNT EACH DETECTED CLASS
        # -------------------------------
        if dets:
            from collections import Counter

            cls_list = [d[0] for d in dets]      # extract class names
            counts = Counter(cls_list)           # count occurrences

            # Format like: "3 person, 2 chair"
            det_text = ", ".join([f"{counts[c]} {c}" for c in counts])
        else:
            det_text = "No object detected"

        # Save result text
        with open(DETS_FILE, "w") as f:
            f.write(det_text)

        return "OK"


@app.route("/detect_result.jpg")
def detect_result_img():
    if os.path.exists(DET_OUT_IMG):
        return Response(open(DET_OUT_IMG, "rb").read(), mimetype="image/jpeg")
    return "No image", 404


@app.route("/det_text")
def det_text_route():
    if os.path.exists(DETS_FILE):
        return open(DETS_FILE).read()
    return ""


# ----- DIARY ROUTES -----
@app.route("/diary_start")
def diary_start():
    global diary_is_recording, diary_recorder_process

    with diary_lock:
        if diary_is_recording:
            return jsonify({"status": "already_recording"})
        diary_is_recording = True
        safe_remove(DIARY_AUDIO_FILE)

        diary_recorder_process = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", DIARY_AUDIO_FILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return jsonify({"status": "diary_recording_started"})


@app.route("/diary_stop")
def diary_stop():
    global diary_is_recording, diary_recorder_process

    with diary_lock:
        if not diary_is_recording:
            return jsonify({"status": "not_recording"})
        diary_is_recording = False
        proc = diary_recorder_process
        diary_recorder_process = None

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    entry_text = process_diary_audio()
    return jsonify({"status": "diary_recording_stopped", "entry": entry_text})


@app.route("/diary_get_latest")
def diary_get_latest():
    with diary_lock:
        return jsonify({
            "seq": diary_seq,
            "entry": last_diary_entry
        })


@app.route("/diary_read_today")
def diary_read_today():
    entries = get_today_diary()
    if entries:
        combined = " ".join([e[2] for e in entries])
        return combined
    return "No diary entries for today."


@app.route("/diary_read_last")
def diary_read_last():
    entry = get_last_diary()
    if entry:
        return f"On {entry[0]} at {entry[1]}: {entry[2]}"
    return "No diary entries found."


@app.route("/diary_list")
def diary_list():
    """Get all diary entries as JSON."""
    try:
        conn = sqlite3.connect(DIARY_DB)
        c = conn.cursor()
        c.execute("""
            SELECT id, date, time, entry_text FROM diary_entries
            ORDER BY created_at DESC LIMIT 20
        """)
        entries = c.fetchall()
        conn.close()
        
        result = [{"id": e[0], "date": e[1], "time": e[2], "text": e[3]} for e in entries]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# ----- MEDICAL ASSISTANCE ROUTES -----
@app.route("/medical_start")
def medical_start():
    global medical_is_recording, medical_recorder_process

    with medical_lock:
        if medical_is_recording:
            return jsonify({"status": "already_recording"})
        medical_is_recording = True
        safe_remove(MEDICAL_AUDIO_FILE)

        medical_recorder_process = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", MEDICAL_AUDIO_FILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return jsonify({"status": "medical_recording_started"})


@app.route("/medical_stop")
def medical_stop():
    global medical_is_recording, medical_recorder_process

    with medical_lock:
        if not medical_is_recording:
            return jsonify({"status": "not_recording"})
        medical_is_recording = False
        proc = medical_recorder_process
        medical_recorder_process = None

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    result = process_medical_audio()
    return jsonify(result)


@app.route("/medical_list")
def medical_list():
    """Get all medical notes as JSON."""
    try:
        conn = sqlite3.connect(MEDICAL_DB)
        c = conn.cursor()
        c.execute("""
            SELECT id, date, time, health_note, ai_tips FROM medical_notes
            ORDER BY created_at DESC LIMIT 20
        """)
        notes = c.fetchall()
        conn.close()
        
        result = [{"id": e[0], "date": e[1], "time": e[2], "health": e[3], "tips": e[4]} for e in notes]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/medical_read_last")
def medical_read_last():
    note = get_last_medical_note()
    if note:
        return f"On {note[0]} at {note[1]}: Your health concern was: {note[2]}. AI suggestions: {note[3]}"
    return "No medical notes found."


# ----- MENTAL HEALTH ROUTES -----
@app.route("/mental")
def mental_page():
    with mental_lock:
        safe_remove(MENTAL_AUDIO_FILE)
    return send_from_directory(".", "mental.html")


@app.route("/mental_start")
def mental_start():
    global mental_is_recording, mental_recorder_process

    with mental_lock:
        if mental_is_recording:
            return jsonify({"status": "already_recording"})
        mental_is_recording = True
        safe_remove(MENTAL_AUDIO_FILE)

        mental_recorder_process = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", MENTAL_AUDIO_FILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return jsonify({"status": "mental_recording_started"})


@app.route("/mental_stop")
def mental_stop():
    global mental_is_recording, mental_recorder_process

    with mental_lock:
        if not mental_is_recording:
            return jsonify({"status": "not_recording"})
        mental_is_recording = False
        proc = mental_recorder_process
        mental_recorder_process = None

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    result = process_mental_audio()
    return jsonify(result)


@app.route("/mental_read_last")
def mental_read_last():
    checkup = get_last_mental_checkup()
    if checkup:
        return f"On {checkup[0]} at {checkup[1]}: You were feeling {checkup[2]}. You said: {checkup[3]}. Tips: {checkup[4]}"
    return "No mental health checkups found."


@app.route("/mental_stats")
def mental_stats():
    """Get mental health statistics."""
    stats = get_today_mental_stats()
    return jsonify(stats)


@app.route("/mental_list")
def mental_list():
    """Get all mental health checkups as JSON."""
    try:
        conn = sqlite3.connect(MENTAL_DB)
        c = conn.cursor()
        c.execute("""
            SELECT id, date, time, emotion, confidence, wellness_tips FROM mental_checkups
            ORDER BY created_at DESC LIMIT 20
        """)
        checkups = c.fetchall()
        conn.close()
        
        result = [{"id": e[0], "date": e[1], "time": e[2], "emotion": e[3], "confidence": e[4], "tips": e[5]} for e in checkups]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# ----- PARENTAL MODE / ANALYTICS ROUTES -----
@app.route("/log_activity", methods=["POST"])
def log_activity_route():
    """Log a module activity to analytics."""
    try:
        import json
        data = json.loads(request.data) if request.data else {}
        
        module_name = data.get("module", "unknown")
        start_time = data.get("start_time", "")
        end_time = data.get("end_time", "")
        
        if not start_time or not end_time:
            # If no times provided, use current time
            now = datetime.now()
            if not start_time:
                start_time = now.strftime("%H:%M:%S")
            if not end_time:
                end_time = now.strftime("%H:%M:%S")
        
        success = log_activity(module_name, start_time, end_time)
        if success:
            return jsonify({"status": "logged", "module": module_name})
        else:
            return jsonify({"status": "failed"})
    except Exception as e:
        print(f"[ERROR] Log activity route failed: {e}")
        return jsonify({"status": "error", "error": str(e)})


@app.route("/analytics/daily_summary")
def analytics_daily_summary():
    """Get daily usage summary."""
    summary = get_daily_summary()
    return jsonify(summary)


@app.route("/analytics/module_details")
def analytics_module_details():
    """Get detailed module usage for today."""
    details = get_module_usage_details()
    return jsonify(details)


@app.route("/analytics/most_used")
def analytics_most_used():
    """Get most used module today."""
    most_used = get_most_used_module()
    if most_used:
        return jsonify(most_used)
    return jsonify({"module": "None", "total_seconds": 0})


# ----- LOCATION TRACKING ROUTES -----
@app.route("/location")
def location_page():
    """Serve location tracking page."""
    return render_template("location.html", GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY)


@app.route("/location_data")
def location_data():
    """Get current GPS location data."""
    try:
        # Try to get fresh location
        success = get_gps_location()
        
        # Return cached or fresh location
        loc = get_cached_location()
        
        # Ensure we have valid data
        if loc['latitude'] == 0.0 and loc['longitude'] == 0.0:
            # Return a default location with error indicator
            return jsonify({
                "error": "GPS not available. Using default location.",
                "latitude": 20.5937,  # Center of India as default
                "longitude": 78.9629,
                "accuracy": 10000.0,
                "altitude": 0.0,
                "speed": 0.0,
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify({
            "latitude": loc['latitude'],
            "longitude": loc['longitude'],
            "accuracy": loc.get('accuracy', 10.0),
            "altitude": loc.get('altitude', 0.0),
            "speed": loc.get('speed', 0.0),
            "timestamp": loc['timestamp'].isoformat() if loc['timestamp'] else None
        })
    except Exception as e:
        print(f"[ERROR] Location data error: {e}")
        return jsonify({
            "error": str(e),
            "latitude": 20.5937,
            "longitude": 78.9629,
            "accuracy": 10000.0,
            "altitude": 0.0,
            "speed": 0.0
        })


@app.route("/voice_navigation", methods=["POST"])
def voice_navigation():
    """Voice navigation endpoint - converts speech to text, gets directions, returns voice guidance."""
    try:
        audio_file = request.files.get('audio')
        lat = float(request.form.get('lat', 18.5326))
        lng = float(request.form.get('lng', 73.8296))
        
        if not audio_file:
            return jsonify({"success": False, "error": "No audio file provided"})
        
        # Save audio file temporarily
        nav_audio_path = f"{LOCATION_WORK_DIR}/nav_command.wav"
        audio_file.save(nav_audio_path)
        
        # Convert speech to text
        destination = ""
        try:
            with sr.AudioFile(nav_audio_path) as source:
                audio_data = recognizer.record(source)
                destination = recognizer.recognize_google(audio_data)
            print(f"[INFO] Voice destination: {destination}")
        except Exception as e:
            print(f"[ERROR] Speech recognition failed: {e}")
            safe_remove(nav_audio_path)
            return jsonify({"success": False, "error": "Could not understand speech"})
        
        # Get directions using Google Maps Directions API
        route_result = get_navigation_route(lat, lng, destination)
        
        if not route_result:
            safe_remove(nav_audio_path)
            return jsonify({"success": False, "error": "Could not find route"})
        
        # Route text and polyline
        if isinstance(route_result, dict):
            route_text = route_result.get('instructions')
            route_polyline = route_result.get('polyline')
        else:
            route_text = route_result
            route_polyline = None
        
        # Convert route instructions to speech
        audio_url = text_to_speech_navigation(route_text)
        
        # Clean up
        safe_remove(nav_audio_path)
        
        return jsonify({
            "success": True,
            "transcript": destination,
            "route": route_text,
            "polyline": route_polyline,
            "audio_url": audio_url
        })
        
    except Exception as e:
        print(f"[ERROR] Voice navigation failed: {e}")
        return jsonify({"success": False, "error": str(e)})


# ----- NAVIGATION RECORDING ENDPOINTS (Server-side mic recording) -----
nav_recorder_process = None
nav_is_recording = False
nav_lock = threading.Lock()

@app.route("/start_nav_recording")
def start_nav_recording():
    """Start recording from board microphone for navigation."""
    global nav_is_recording, nav_recorder_process

    with nav_lock:
        if nav_is_recording:
            return jsonify({"status": "already_recording"})
        nav_is_recording = True
        
        nav_audio_file = f"{LOCATION_WORK_DIR}/nav_command.wav"
        safe_remove(nav_audio_file)

        nav_recorder_process = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", nav_audio_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return jsonify({"status": "recording_started"})


@app.route("/stop_nav_recording", methods=["POST"])
def stop_nav_recording():
    """Stop navigation recording and process navigation request."""
    global nav_is_recording, nav_recorder_process

    with nav_lock:
        if not nav_is_recording:
            return jsonify({"success": False, "error": "not_recording"})
        nav_is_recording = False
        proc = nav_recorder_process
        nav_recorder_process = None

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    # Get coordinates from request
    try:
        data = request.get_json()
        lat = float(data.get('lat', 18.5326))
        lng = float(data.get('lng', 73.8296))
    except:
        lat = 18.5326
        lng = 73.8296

    # Process the recorded audio
    nav_audio_file = f"{LOCATION_WORK_DIR}/nav_command.wav"
    
    if not os.path.exists(nav_audio_file):
        return jsonify({"success": False, "error": "No audio file recorded"})
    
    # Convert speech to text
    query_text = ""
    try:
        with sr.AudioFile(nav_audio_file) as source:
            audio_data = recognizer.record(source)
            query_text = recognizer.recognize_google(audio_data)
        print(f"[INFO] Voice query: {query_text}")
    except Exception as e:
        print(f"[ERROR] Speech recognition failed: {e}")
        return jsonify({"success": False, "error": "Could not understand speech"})
    
    # Check if this is a places search query (hotel, restaurant, etc.)
    query_lower = query_text.lower()
    place_keywords = ['hotel', 'restaurant', 'cafe', 'coffee', 'gas station', 'atm', 'bank', 
                      'hospital', 'pharmacy', 'store', 'shop', 'mall', 'park', 'gym',
                      'tourist', 'attraction', 'monument', 'temple', 'church', 'museum',
                      'near', 'nearby', 'around', 'close']
    
    is_place_query = any(keyword in query_lower for keyword in place_keywords)
    
    if is_place_query:
        # This is a places search query
        places_result = search_nearby_places(lat, lng, query_text)
        return jsonify(places_result)
    
    # Otherwise, treat as navigation destination
    destination = query_text
    
    # Get directions using Google Maps Directions API
    route_result = get_navigation_route(lat, lng, destination)
    
    if not route_result:
        return jsonify({"success": False, "error": "Could not find route"})
    
    # Route text and polyline
    if isinstance(route_result, dict):
        route_text = route_result.get('instructions')
        route_polyline = route_result.get('polyline')
        distance = route_result.get('distance', '--')
        duration = route_result.get('duration', '--')
        steps = route_result.get('steps', [])
    else:
        route_text = route_result
        route_polyline = None
        distance = '--'
        duration = '--'
        steps = []
    
    # Convert route instructions to speech
    audio_url = text_to_speech_navigation(route_text)
    
    return jsonify({
        "success": True,
        "transcript": destination,
        "route": route_text,
        "polyline": route_polyline,
        "distance": distance,
        "duration": duration,
        "steps": steps,
        "audio_url": audio_url
    })


def search_nearby_places(lat, lng, query):
    """Search for nearby places using Google Places API Text Search."""
    try:
        import requests
        
        # Use Text Search API (more likely to be enabled)
        api_key = GOOGLE_MAPS_API_KEY
        
        # Build search query
        search_query = query
        if 'near' not in query.lower():
            search_query = f"{query} near me"
        
        # Use Text Search endpoint
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': search_query,
            'location': f"{lat},{lng}",
            'radius': 5000,  # 5km
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'REQUEST_DENIED':
            print(f"[ERROR] Places API error: {data.get('error_message', 'Unknown error')}")
            return {
                "success": False,
                "is_places_query": True,
                "error": "Places API not enabled. Please enable 'Places API' in Google Cloud Console."
            }
        
        if data.get('status') != 'OK' or not data.get('results'):
            return {
                "success": False,
                "is_places_query": True,
                "error": f"No places found nearby. Status: {data.get('status')}"
            }
        
        # Extract place information
        places = []
        for place in data['results'][:20]:  # Limit to 20 results
            places.append({
                "name": place.get('name', 'Unknown'),
                "address": place.get('formatted_address', place.get('vicinity', '')),
                "lat": place['geometry']['location']['lat'],
                "lng": place['geometry']['location']['lng'],
                "rating": place.get('rating', 'N/A'),
                "types": place.get('types', []),
                "open_now": place.get('opening_hours', {}).get('open_now', None)
            })
        
        return {
            "success": True,
            "is_places_query": True,
            "query": query,
            "places": places,
            "count": len(places)
        }
        
    except Exception as e:
        print(f"[ERROR] Places search failed: {e}")
        return {
            "success": False,
            "is_places_query": True,
            "error": str(e)
        }


def get_navigation_route(origin_lat, origin_lng, destination):
    """Get navigation route from Google Maps Directions API."""
    try:
        import googlemaps
        
        # Initialize Google Maps client (using the same API key from the HTML)
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        
        # Get directions
        directions_result = gmaps.directions(
            f"{origin_lat},{origin_lng}",
            destination,
            mode="driving",
            language="en"
        )
        
        if not directions_result:
            return None
        
        # Extract route instructions
        route = directions_result[0]
        legs = route['legs'][0]
        
        # Extract distance and duration
        distance = legs['distance']['text']
        duration = legs['duration']['text']
        
        instructions = f"Route to {destination}:\n"
        instructions += f"Total distance: {distance}\n"
        instructions += f"Total duration: {duration}\n\n"
        instructions += "Step by step directions:\n"
        
        # Extract steps with coordinates for distance labels
        steps_data = []
        for i, step in enumerate(legs['steps'], 1):
            # Remove HTML tags from instructions
            text = re.sub(r'<.*?>', '', step['html_instructions'])
            instructions += f"{i}. {text} ({step['distance']['text']})\n"
            
            # Store step data for map markers
            steps_data.append({
                'end_location': {
                    'lat': step['end_location']['lat'],
                    'lng': step['end_location']['lng']
                },
                'distance': {
                    'text': step['distance']['text'],
                    'value': step['distance']['value']
                }
            })
        
        # Capture encoded overview polyline (if present)
        overview_polyline = None
        if 'overview_polyline' in route and route['overview_polyline'].get('points'):
            overview_polyline = route['overview_polyline']['points']
        
        return {
            "instructions": instructions, 
            "polyline": overview_polyline,
            "distance": distance,
            "duration": duration,
            "steps": steps_data
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get navigation route: {e}")
        # Fallback to simple directions using Gemini
        try:
            prompt = f"Give turn-by-turn driving directions from coordinates {origin_lat}, {origin_lng} to {destination}. Be concise and clear."
            fallback = ask_gemini_text(prompt)
            return {"instructions": fallback, "polyline": None}
        except:
            return None


def text_to_speech_navigation(text):
    """Convert navigation text to speech and return audio file URL."""
    try:
        nav_speech_file = f"{LOCATION_WORK_DIR}/nav_speech.wav"
        
        # Use espeak for text-to-speech
        subprocess.run(
            ["espeak", "-w", nav_speech_file, text],
            check=True,
            timeout=30
        )
        
        # Return relative URL for the audio file
        return "/nav_audio"
        
    except Exception as e:
        print(f"[ERROR] Text-to-speech failed: {e}")
        return None


@app.route("/nav_audio")
def serve_nav_audio():
    """Serve navigation audio file."""
    try:
        nav_speech_file = f"{LOCATION_WORK_DIR}/nav_speech.wav"
        if os.path.exists(nav_speech_file):
            return send_from_directory(LOCATION_WORK_DIR, "nav_speech.wav")
        else:
            return "Audio not found", 404
    except Exception as e:
        print(f"[ERROR] Serving nav audio failed: {e}")
        return str(e), 500


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"\nMICRO + OCR + Object Detection + AI DIARY + MEDICAL + PARENTAL MODE + LOCATION TRACKER running at http://0.0.0.0:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
