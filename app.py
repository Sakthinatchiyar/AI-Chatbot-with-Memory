
import os
import time
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --------------------------------
# 1. GEMINI API CONFIGURATION
# --------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "Gemini API key is missing. Check your .env file."
    )

client = genai.Client(api_key=API_KEY)

# Use a supported Gemini model
MODEL = "gemini-3.8-flash"


# --------------------------------
# 2. CONVERSATION STORAGE
# --------------------------------

conversations = {}

# Maximum number of previous messages
MAX_HISTORY = 10


# --------------------------------
# 3. SYSTEM PROMPT
# --------------------------------

SYSTEM_PROMPT = """
You are StudyBuddy, a friendly and intelligent AI assistant.

Your purpose is to help students understand programming,
technology, and academic concepts.

Your rules:

1. Explain concepts in simple language.
2. Give examples whenever useful.
3. Be friendly, patient, and encouraging.
4. Remember details from earlier messages.
5. Help students with Java, Python and other technologies.
6. If you do not know something, say so honestly.
7. Give clear step-by-step explanations when requested.
"""

# --------------------------------
# GEMINI AUTOMATIC FALLBACK
# --------------------------------

PRIMARY_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def get_ai_reply(contents):

    models = [PRIMARY_MODEL, FALLBACK_MODEL]

    last_error = None

    for model_name in models:

        print("Trying model:", model_name)

        # Try each model twice
        for attempt in range(2):

            try:

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=1000
                    )
                )

                if response.text and response.text.strip():

                    print("Success using:", model_name)
                    return response.text

                raise ValueError("AI returned an empty response.")

            except errors.APIError as e:

                last_error = e

                print(
                    f"{model_name} failed: {e}"
                )

                # Retry only when the server is overloaded
                if getattr(e, "code", None) == 503 and attempt == 0:

                    print("Retrying after 2 seconds...")
                    time.sleep(2)
                    continue

                break

    # Both models failed
    if last_error:
        raise last_error

    raise RuntimeError("All AI models failed.")


# --------------------------------
# 4. HOME PAGE
# --------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------
# 5. CHAT API
# --------------------------------

@app.route("/chat", methods=["POST"])
def chat():

    try:

        # Get frontend data
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Invalid request data."
            }), 400

        message = data.get("message", "")

        conversation_id = data.get(
            "conversation_id", ""
        )

        # Validate message
        if not isinstance(message, str):
            return jsonify({
                "error": "Message must be text."
            }), 400

        message = message.strip()

        if not message:
            return jsonify({
                "error": "Please enter a message."
            }), 400

        # Validate conversation ID
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            return jsonify({
                "error": "Conversation ID is missing."
            }), 400

        conversation_id = conversation_id.strip()

        # --------------------------------
        # 6. CREATE CONVERSATION
        # --------------------------------

        if conversation_id not in conversations:

            conversations[conversation_id] = []

        history = conversations[conversation_id]

        # --------------------------------
        # 7. CONTEXT WINDOW MANAGEMENT
        # --------------------------------

        # Select only the latest 10 messages
        recent_history = history[-MAX_HISTORY:]

        # Convert previous messages into Gemini format
        contents = []

        for item in recent_history:

            contents.append(
                types.Content(
                    role=item["role"],
                    parts=[
                        types.Part.from_text(
                            text=item["text"]
                        )
                    ]
                )
            )

        # Add the current user message
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=message
                    )
                ]
            )
        )

        # --------------------------------
        # 8. SEND REQUEST TO GEMINI
        # --------------------------------

        reply = get_ai_reply(contents)

        if not reply or not reply.strip():

            raise ValueError(
                "Gemini returned an empty response."
            )

        # --------------------------------
        # 9. SAVE CONVERSATION HISTORY
        # --------------------------------

        # Save user message
        history.append({
            "role": "user",
            "text": message
        })

        # Save AI response
        history.append({
            "role": "model",
            "text": reply
        })

        # --------------------------------
        # 10. SEND RESPONSE TO FRONTEND
        # --------------------------------

        return jsonify({

            "reply": reply,

            "conversation_id": conversation_id

        }), 200

    # --------------------------------
    # 11. ERROR HANDLING
    # --------------------------------

    except errors.APIError as e:

        app.logger.error(
            "Gemini API Error: %s - %s",
            e.code,
            e.message
        )

        return jsonify({
            "error": "Gemini API Error: " + str(e.message)
        }), 502

    except TimeoutError as e:

        app.logger.error(
            "Request Timeout: %s", e
        )

        return jsonify({
            "error": "Request timed out. Please try again."
        }), 504

    except Exception as e:

        app.logger.exception(
            "Chat request failed: %s", e
        )

        return jsonify({
            "error": "Something went wrong: " + str(e)
        }), 500


# --------------------------------
# 12. RUN FLASK APPLICATION
# --------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

