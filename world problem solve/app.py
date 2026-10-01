from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from google import genai
import os
import time

load_dotenv()

app = Flask(__name__)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Models automatically try honge
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash"
]


@app.route("/")
def home():
    return send_file("index.html")


@app.route("/solve", methods=["POST"])
def solve():

    data = request.get_json()
    problem = data.get("problem", "").strip()

    if not problem:
        return jsonify({
            "error": "Please enter a problem."
        }), 400

    prompt = f"""
You are the AI brain of World Problem Solver.

User's problem:
{problem}

Analyze this real-world problem and give a practical solution.

Include:

1. Problem Analysis
2. Root Cause
3. Practical Solution
4. Step-by-Step Action Plan
5. Expected Impact
6. Useful Digital Platform Features

Keep the answer clear, realistic and actionable.
"""

    last_error = ""

    for model in MODELS:

        for attempt in range(3):

            try:
                print(f"Trying {model}, attempt {attempt + 1}")

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                ai_answer = response.text

                return jsonify({
                    "problem": problem,
                    "analysis": f"Analyzed using {model}.",
                    "solution": ai_answer,
                    "features": [
                        "Problem reporting",
                        "Status tracking",
                        "User notifications",
                        "AI-powered recommendations"
                    ]
                })

            except Exception as e:

                last_error = str(e)
                print("AI ERROR:", last_error)

                # Temporary 503 ke liye wait
                if "503" in last_error or "UNAVAILABLE" in last_error:
                    time.sleep(2 ** attempt)
                    continue

                break

    return jsonify({
        "error": "Gemini is temporarily unavailable. Please try again in a few seconds.",
        "details": last_error
    }), 503


if __name__ == "__main__":
    app.run(debug=True)