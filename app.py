from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from google import genai
import os
import time
import sqlite3
from datetime import datetime
import random

load_dotenv()

app = Flask(__name__)

# =========================================================
# GEMINI AI
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("ERROR: GEMINI_API_KEY nahi mili.")

client = genai.Client(api_key=API_KEY)


# =========================================================
# DATABASE
# =========================================================

DATABASE = "greencare.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_db()

    # -----------------------------------------------------
    # COMPLAINTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_number TEXT UNIQUE,
            name TEXT,
            phone TEXT,
            issue TEXT,
            description TEXT,
            location TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # PICKUP REQUESTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pickup_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_number TEXT UNIQUE,
            name TEXT,
            phone TEXT,
            address TEXT,
            waste_type TEXT,
            pickup_date TEXT,
            notes TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    # -----------------------------------------------------
    # GREEN POINTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS green_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            name TEXT,
            points INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# GREEN POINTS FUNCTION
# =========================================================

def add_green_points(name, phone, points):

    conn = get_db()

    user = conn.execute("""
        SELECT * FROM green_points
        WHERE phone = ?
    """, (phone,)).fetchone()

    if user:

        conn.execute("""
            UPDATE green_points
            SET points = points + ?,
                name = ?
            WHERE phone = ?
        """, (
            points,
            name,
            phone
        ))

    else:

        conn.execute("""
            INSERT INTO green_points
            (phone, name, points)
            VALUES (?, ?, ?)
        """, (
            phone,
            name,
            points
        ))

    conn.commit()

    user = conn.execute("""
        SELECT * FROM green_points
        WHERE phone = ?
    """, (phone,)).fetchone()

    conn.close()

    return dict(user)


# =========================================================
# GREEN LEVEL
# =========================================================

def get_green_level(points):

    if points >= 100:
        return "🏆 Eco Hero"

    elif points >= 50:
        return "🌿 Green Champion"

    elif points >= 25:
        return "♻️ Eco Helper"

    else:
        return "🌱 Green Beginner"


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return send_file("index.html")


# =========================================================
# REPORT WASTE ISSUE
# =========================================================

@app.route("/report", methods=["POST"])
def report():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Data nahi mila."
            }), 400

        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        issue = data.get("issue", "").strip()
        description = data.get("description", "").strip()
        location = data.get("location", "").strip()

        if not name or not phone or not issue or not location:

            return jsonify({
                "success": False,
                "error": "Name, phone, issue aur location required hai."
            }), 400

        # -------------------------------------------------
        # UNIQUE COMPLAINT NUMBER
        # -------------------------------------------------

        complaint_number = (
            "WC-" +
            datetime.now().strftime("%Y%m%d") +
            "-" +
            str(random.randint(1000, 9999))
        )

        created_at = datetime.now().strftime(
            "%d/%m/%Y, %I:%M:%S %p"
        )

        conn = get_db()

        conn.execute("""
            INSERT INTO complaints
            (
                complaint_number,
                name,
                phone,
                issue,
                description,
                location,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_number,
            name,
            phone,
            issue,
            description,
            location,
            "Submitted",
            created_at
        ))

        conn.commit()
        conn.close()

        # -------------------------------------------------
        # GREEN POINTS
        # Report karne par +10
        # -------------------------------------------------

        user_points = add_green_points(
            name,
            phone,
            10
        )

        return jsonify({
            "success": True,
            "complaint_number": complaint_number,
            "message": "Waste issue successfully reported.",
            "status": "Submitted",
            "green_points": user_points["points"],
            "green_level": get_green_level(
                user_points["points"]
            )
        })

    except Exception as e:

        print("REPORT ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Report submit nahi ho paya.",
            "details": str(e)
        }), 500


# =========================================================
# TRACK COMPLAINT
# =========================================================

@app.route("/track", methods=["POST"])
def track():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Complaint data nahi mila."
            }), 400

        complaint_number = data.get(
            "complaint_number",
            ""
        ).strip().upper()

        if not complaint_number:

            return jsonify({
                "success": False,
                "error": "Complaint number enter karo."
            }), 400

        conn = get_db()

        complaint = conn.execute("""
            SELECT *
            FROM complaints
            WHERE complaint_number = ?
        """, (
            complaint_number,
        )).fetchone()

        conn.close()

        if not complaint:

            return jsonify({
                "success": False,
                "error": "Complaint number nahi mila."
            }), 404

        return jsonify({
            "success": True,
            "complaint": dict(complaint)
        })

    except Exception as e:

        print("TRACK ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Tracking error.",
            "details": str(e)
        }), 500


# =========================================================
# WASTE PICKUP REQUEST
# =========================================================

@app.route("/pickup", methods=["POST"])
def pickup():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Data nahi mila."
            }), 400

        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        address = data.get("address", "").strip()
        waste_type = data.get("waste_type", "").strip()
        pickup_date = data.get("pickup_date", "").strip()
        notes = data.get("notes", "").strip()

        if (
            not name
            or not phone
            or not address
            or not waste_type
            or not pickup_date
        ):

            return jsonify({
                "success": False,
                "error": "Please required fields fill karo."
            }), 400

        request_number = (
            "WP-" +
            datetime.now().strftime("%Y%m%d") +
            "-" +
            str(random.randint(1000, 9999))
        )

        created_at = datetime.now().strftime(
            "%d/%m/%Y, %I:%M:%S %p"
        )

        conn = get_db()

        conn.execute("""
            INSERT INTO pickup_requests
            (
                request_number,
                name,
                phone,
                address,
                waste_type,
                pickup_date,
                notes,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_number,
            name,
            phone,
            address,
            waste_type,
            pickup_date,
            notes,
            "Requested",
            created_at
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "request_number": request_number,
            "message": "Waste pickup request submitted successfully."
        })

    except Exception as e:

        print("PICKUP ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Pickup request submit nahi ho payi.",
            "details": str(e)
        }), 500


# =========================================================
# GREEN POINTS
# =========================================================

@app.route("/points", methods=["POST"])
def points():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "error": "Data nahi mila."
            }), 400

        phone = data.get(
            "phone",
            ""
        ).strip()

        if not phone:

            return jsonify({
                "success": False,
                "error": "Phone number required."
            }), 400

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM green_points
            WHERE phone = ?
        """, (
            phone,
        )).fetchone()

        conn.close()

        if not user:

            return jsonify({
                "success": True,
                "name": "",
                "points": 0,
                "level": "🌱 Green Beginner"
            })

        user_points = user["points"]

        return jsonify({
            "success": True,
            "name": user["name"],
            "points": user_points,
            "level": get_green_level(user_points)
        })

    except Exception as e:

        print("POINTS ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Points check nahi ho paye.",
            "details": str(e)
        }), 500


# =========================================================
# ADMIN DASHBOARD DATA
# =========================================================

@app.route("/admin/data", methods=["GET"])
def admin_data():

    try:

        conn = get_db()

        total = conn.execute("""
            SELECT COUNT(*) AS count
            FROM complaints
        """).fetchone()["count"]

        submitted = conn.execute("""
            SELECT COUNT(*) AS count
            FROM complaints
            WHERE status = 'Submitted'
        """).fetchone()["count"]

        in_progress = conn.execute("""
            SELECT COUNT(*) AS count
            FROM complaints
            WHERE status = 'In Progress'
        """).fetchone()["count"]

        resolved = conn.execute("""
            SELECT COUNT(*) AS count
            FROM complaints
            WHERE status = 'Resolved'
        """).fetchone()["count"]

        complaints = conn.execute("""
            SELECT *
            FROM complaints
            ORDER BY id DESC
        """).fetchall()

        conn.close()

        return jsonify({
            "success": True,

            "dashboard": {
                "total": total,
                "submitted": submitted,
                "in_progress": in_progress,
                "resolved": resolved
            },

            "complaints": [
                dict(complaint)
                for complaint in complaints
            ]
        })

    except Exception as e:

        print("ADMIN ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Admin dashboard load nahi ho paya.",
            "details": str(e)
        }), 500


# =========================================================
# ADMIN UPDATE COMPLAINT STATUS
# =========================================================

@app.route("/admin/update-status", methods=["POST"])
def update_status():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "error": "Data nahi mila."
            }), 400

        complaint_number = data.get(
            "complaint_number",
            ""
        ).strip().upper()

        status = data.get(
            "status",
            ""
        ).strip()

        allowed_status = [
            "Submitted",
            "In Progress",
            "Resolved"
        ]

        if status not in allowed_status:

            return jsonify({
                "success": False,
                "error": "Invalid status."
            }), 400

        conn = get_db()

        complaint = conn.execute("""
            SELECT *
            FROM complaints
            WHERE complaint_number = ?
        """, (
            complaint_number,
        )).fetchone()

        if not complaint:

            conn.close()

            return jsonify({
                "success": False,
                "error": "Complaint nahi mili."
            }), 404

        old_status = complaint["status"]

        conn.execute("""
            UPDATE complaints
            SET status = ?
            WHERE complaint_number = ?
        """, (
            status,
            complaint_number
        ))

        conn.commit()
        conn.close()

        # -------------------------------------------------
        # RESOLVED BONUS
        # -------------------------------------------------

        bonus_points = 0
        total_points = None

        if (
            status == "Resolved"
            and old_status != "Resolved"
        ):

            user_points = add_green_points(
                complaint["name"],
                complaint["phone"],
                15
            )

            bonus_points = 15
            total_points = user_points["points"]

        return jsonify({
            "success": True,
            "message": "Complaint status updated.",
            "status": status,
            "bonus_points": bonus_points,
            "total_points": total_points
        })

    except Exception as e:

        print("STATUS UPDATE ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": "Status update nahi ho paya.",
            "details": str(e)
        }), 500


# =========================================================
# AI WASTE ASSISTANT
# =========================================================

@app.route("/solve", methods=["POST"])
def solve():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error": "Problem data nahi mila."
            }), 400

        problem = data.get(
            "problem",
            ""
        ).strip()

        if not problem:

            return jsonify({
                "error": "Please problem enter karo."
            }), 400

        prompt = f"""
You are an AI Waste Management Assistant for GreenCare.

User's waste-related problem:
{problem}

Give a simple and practical solution.

Use this format:

Problem:
Explain the problem.

Main Causes:
Explain the possible causes.

Practical Solution:
Give realistic solutions.

Step-by-Step Action Plan:
Give clear steps.

Waste Management Tips:
Give useful tips about waste segregation,
recycling, plastic reduction and keeping the environment clean.

Keep the answer easy to understand.
"""

        # =================================================
        # AI MODELS - FALLBACK SYSTEM
        # =================================================

        models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash"
        ]

        last_error = ""

        for model in models:

            for attempt in range(2):

                try:

                    print(
                        f"AI attempt: {model} "
                        f"(try {attempt + 1}/2)"
                    )

                    response = client.models.generate_content(
                        model=model,
                        contents=prompt
                    )

                    if response and response.text:

                        print(
                            f"AI SUCCESS: {model}"
                        )

                        return jsonify({
                            "success": True,
                            "solution": response.text,
                            "model": model
                        })

                except Exception as e:

                    last_error = str(e)

                    print(
                        f"AI ERROR: {model} "
                        f"(try {attempt + 1}/2): "
                        f"{last_error}"
                    )

                    error_text = last_error.upper()

                    temporary_error = (
                        "503" in error_text
                        or "UNAVAILABLE" in error_text
                        or "429" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    )

                    if temporary_error:

                        wait_time = 2 ** attempt

                        print(
                            f"Waiting {wait_time} seconds..."
                        )

                        time.sleep(wait_time)

                        continue

                    break

        return jsonify({
            "error": "AI service temporarily unavailable.",
            "details": (
                "All AI models are currently busy. "
                "Please try again after a short time."
            ),
            "technical_error": last_error
        }), 503

    except Exception as e:

        print("SOLVE ERROR:", str(e))

        return jsonify({
            "error": "AI service error",
            "details": str(e)
        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print("===================================")
    print("🌿 GreenCare Waste Management")
    print("Server: http://127.0.0.1:5000")
    print("===================================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )