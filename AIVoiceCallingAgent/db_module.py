import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["ai_call_logs"]
calls = db["conversations"]

# Ensure local logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def log_message(call_sid, role, text):
    """Logs each message to MongoDB and a local .txt file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Save to MongoDB ---
    calls.update_one(
        {"call_sid": call_sid},
        {"$push": {"transcript": {"role": role, "text": text, "time": timestamp}}},
        upsert=True
    )

    # --- Save to local file ---
    log_path = os.path.join(LOG_DIR, f"{call_sid}.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}: {text}\n")

    print(f"[{timestamp}] {role.upper()}: {text}")


def save_summary(call_sid, summary_text):
    """Stores summary in MongoDB and local log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Save to MongoDB ---
    calls.update_one(
        {"call_sid": call_sid},
        {"$set": {"summary": summary_text, "summary_time": timestamp}},
        upsert=True
    )

    # --- Save to local log ---
    log_path = os.path.join(LOG_DIR, f"{call_sid}.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] SUMMARY: {summary_text}\n")

    print(f"Summary saved for {call_sid}")
