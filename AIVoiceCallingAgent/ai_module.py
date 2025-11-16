import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use a persistent in-memory store so Gemini remembers context
conversation_memory = {}

# Load the Gemini model
gemini_model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")


def get_ai_response(call_sid, user_input):
    """
    Generate a context-aware AI response using Gemini.
    Maintains ongoing conversation memory for each call.
    """
    try:
        # Initialize call memory if not present
        if call_sid not in conversation_memory:
            conversation_memory[call_sid] = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI HR calling assistant conducting a phone screening. "
                        "You speak naturally and politely. "
                        "You must ask questions one by one to gather: "
                        "1. Candidate's full name, "
                        "2. Years of experience, " 
                        "3. Current company, "
                        "4. Notice period, and "
                        "5. Expected CTC. "
                        "Keep your responses concise and under 2 sentences. "
                        "Only end the conversation after collecting all five pieces of information. "
                        "When you have all information, explicitly say: 'That concludes our conversation. Thank you for the information.' "
                        "If the response is unclear, politely ask for clarification."
                        "Do not use phrases like 'thank you' casually during the conversation to avoid triggering end detection."
                    )
                }
            ]

        # Add the HR's response to the conversation
        conversation_memory[call_sid].append({"role": "user", "content": user_input})

        # Construct the full conversation context
        full_context = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_memory[call_sid]])

        # Generate Gemini reply
        response = gemini_model.generate_content(full_context)

        # Extract AI message text
        ai_text = response.text.strip() if hasattr(response, "text") else "Could you please repeat that?"
        
        # Ensure we have a valid response
        if not ai_text or len(ai_text) < 5:
            ai_text = "I didn't quite understand that. Could you please repeat?"

        # Add AI reply to memory
        conversation_memory[call_sid].append({"role": "assistant", "content": ai_text})

        return ai_text

    except Exception as e:
        print("Error in AI response:", e)
        return "I'm sorry, there seems to be a technical issue. Could you please repeat that?"