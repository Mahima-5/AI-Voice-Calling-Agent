# AI Voice Calling Agent (Python + Twilio + OpenAI)

## 🔧 Setup
1. Clone repo & install dependencies:
   ```bash
   pip install -r requirements.txt
Create .env from .env.example and fill credentials.

Start Flask:

python app.py

Run ngrok (in new terminal):

bash
Copy code
ngrok http 5000
Copy HTTPS URL from ngrok → set BASE_URL in .env.

☎️ Trigger Outbound Call
bash
Copy code
curl -X POST http://localhost:5000/call -H "Content-Type: application/json" -d "{\"to\":\"+91XXXXXXXXXX\"}"
📋 View Summary
After the call:

bash
Copy code
GET http://localhost:5000/summary/<call_sid>
✅ Features
Outbound voice call using Twilio

Speech-to-Text (Twilio STT)

Text-to-Speech (Twilio TTS)

AI-driven conversation (OpenAI)

MongoDB transcript + summary

yaml
Copy code

---

### **8️⃣ logs/calls.txt**
Used to keep a local backup of conversations if needed.

---

## 🚀 Next Steps (Today’s Tasks)

1. Copy this structure into a folder (`ai-calling-agent`).
2. Replace credentials in `.env`.
3. Run `app.py` and `ngrok`.
4. Use Postman or curl to hit `/call` and trigger a test outbound call.
5. Verify conversation in MongoDB and `/summary` endpoint.

---

Would you like me to include **sample test data + example MongoDB document and JSON report output** (so you can show something even before your first live Twilio call)?  
That’ll help you **simulate and record a quick demo** while you’re still wiring up Twili