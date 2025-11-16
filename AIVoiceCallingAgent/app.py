from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from ai_module import get_ai_response
from db_module import log_message, save_summary
import google.generativeai as genai
import os
from dotenv import load_dotenv
from html import escape

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Twilio configuration
TW_SID = os.getenv("TWILIO_ACCOUNT_SID")
TW_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TW_NUMBER = os.getenv("TWILIO_NUMBER")
BASE_URL = os.getenv("BASE_URL")

# Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Gemini model
gemini_model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

# Twilio client
client = Client(TW_SID, TW_TOKEN)


# -------------------------------
# ROUTE 1: Trigger outbound call
# -------------------------------
@app.route("/call", methods=["POST"])
def make_call():
    """Initiates an outbound call to the target number."""
    try:
        data = request.get_json()
        to_number = data.get("to")
        if not to_number:
            return jsonify({"error": "Missing 'to' number"}), 400

        call = client.calls.create(
            to=to_number,
            from_=TW_NUMBER,
            url=f"{BASE_URL}/voice"
        )

        return jsonify({"status": "Call initiated", "call_sid": call.sid})

    except Exception as e:
        print("Error initiating call:", e)
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# ROUTE 2: Start of the call
# ----------------------------------------
@app.route("/voice", methods=["POST"])
def voice():
    """Handles initial greeting and starts conversation."""
    call_sid = request.form.get("CallSid")
    print(f"Call started: {call_sid}")

    resp = VoiceResponse()
    gather = Gather(input="speech", action="/gather", method="POST", timeout=5)
    greet = "Hello, this is an AI HR assistant calling to discuss a job opportunity. Are you available to talk now?"
    gather.say(greet, voice="Polly.Aditi")
    resp.append(gather)
    resp.say("I did not receive a response. Goodbye.", voice="Polly.Aditi")
    resp.hangup()

    log_message(call_sid, "agent", greet)
    return str(resp)


# ----------------------------------------
# ROUTE 3: Handle HR speech and AI response
# ----------------------------------------
@app.route("/gather", methods=["POST"])
def gather():
    """Receives HR's speech, processes with AI, and continues conversation."""
    call_sid = request.form.get("CallSid")
    user_text = request.form.get("SpeechResult", "").strip()

    # Debug logging
    print(f"🔍 GATHER DEBUG - CallSid: {call_sid}")
    print(f"🔍 GATHER DEBUG - SpeechResult: '{user_text}'")

    # Improved silence/incomplete speech detection
    if not user_text or user_text.lower() in ["", "no speech detected", "i", "i just"]:
        print("⚠️ Silence or incomplete speech detected, re-engaging...")
        resp = VoiceResponse()
        
        # Get the last AI message to provide context
        from db_module import calls
        doc = calls.find_one({"call_sid": call_sid})
        if doc and doc.get("transcript"):
            last_ai_msg = None
            for msg in reversed(doc.get("transcript", [])):
                if msg.get("role") == "agent":
                    last_ai_msg = msg.get("text")
                    break
            
            if last_ai_msg and "name" in last_ai_msg.lower():
                gather = Gather(input="speech", action="/gather", method="POST", timeout=10)
                gather.say("I didn't quite catch that. Could you please tell me your full name?", voice="Polly.Aditi")
                resp.append(gather)
            else:
                gather = Gather(input="speech", action="/gather", method="POST", timeout=10)
                gather.say("I didn't hear a response. Could you please repeat that?", voice="Polly.Aditi")
                resp.append(gather)
        else:
            gather = Gather(input="speech", action="/gather", method="POST", timeout=10)
            gather.say("I didn't catch that. Could you please repeat?", voice="Polly.Aditi")
            resp.append(gather)
        
        return str(resp)

    print(f"HR said: {user_text}")
    log_message(call_sid, "hr", user_text)

    # Get AI-generated reply
    ai_reply = get_ai_response(call_sid, user_text)
    print(f"AI replied: {ai_reply}")
    log_message(call_sid, "agent", ai_reply)

    resp = VoiceResponse()

    # ✅ FIXED: More specific conversation ending detection
    # Only end if the AI is explicitly ending the conversation, not just using polite language
    ai_reply_lower = ai_reply.lower()
    
    # Check if this is a genuine conversation end (not just polite language)
    is_ending = (
        "that concludes our conversation" in ai_reply_lower or
        "i have all the information i need" in ai_reply_lower or
        "end of conversation" in ai_reply_lower or
        ("goodbye" in ai_reply_lower and "thank you" in ai_reply_lower) or
        "we're done here" in ai_reply_lower or
        "that's all i needed" in ai_reply_lower
    )
    
    if is_ending:
        print("🎯 Conversation ending detected - wrapping up call")
        resp.say(ai_reply, voice="Polly.Aditi")
        resp.say("Thank you for your time. Goodbye.", voice="Polly.Aditi")
        resp.hangup()
        save_summary(call_sid, "Conversation ended gracefully.")
        return str(resp)

    # ✅ Continue conversation loop with longer timeout
    gather = Gather(input="speech", action="/gather", method="POST", timeout=10, speechTimeout="auto")
    gather.say(ai_reply, voice="Polly.Aditi")
    resp.append(gather)

    return str(resp)


# ----------------------------------------
# ROUTE 4: Generate Call Summary (Gemini)
# ----------------------------------------
@app.route("/summary/<call_sid>", methods=["GET"])
def summary(call_sid):
    """Generates AI summary of the HR call from MongoDB transcript."""
    from db_module import calls
    doc = calls.find_one({"call_sid": call_sid})

    if not doc:
        return jsonify({"error": "No transcript found for this CallSid"}), 404

    transcript_text = "\n".join(
        [f"{m['role']}: {m['text']}" for m in doc.get("transcript", [])]
    )

    summary_prompt = (
        f"Summarize this HR phone call, identifying the candidate's name, years of experience, "
        f"current company, notice period, and expected salary if mentioned:\n\n{transcript_text}"
    )

    try:
        summary_response = gemini_model.generate_content(summary_prompt)
        summary_text = summary_response.text.strip()
        save_summary(call_sid, summary_text)

        return jsonify({
            "call_sid": call_sid,
            "summary": summary_text,
            "transcript": doc.get("transcript", [])
        })

    except Exception as e:
        print("Error generating summary:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------------
# RUN THE FLASK APP
# -------------------------------
if __name__ == "__main__":
    print("🚀 AI Voice Agent Server Running on http://127.0.0.1:5000")
    app.run(port=5000)