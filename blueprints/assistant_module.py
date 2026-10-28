"""
KrishiSense Module -- Voice Assistant & Chatbot (Krishi Mitra / ಕೃಷಿ ಮಿತ್ರ)
----------------------------------------------------------------------------
Provides:
1. Speech-to-Intent parsing and voice-driven tab/module navigation in English & Kannada.
2. Intelligent agricultural chatbot (Q&A on crops, leaf diseases, mandi prices, IoT sensors) in English & Kannada.
3. Live sensor telemetry & prices database integration for real-time status answers.
4. User activity logging & timeline tracking across sessions.
5. Auto-detection of Kannada Unicode script and explicit language toggling.
6. Optional Gemini/LLM external API support when GEMINI_API_KEY is configured.
"""
import os
import json
import sqlite3
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session

assistant_bp = Blueprint("assistant_bp", __name__)

USER_DB_PATH = "users.db"
TELEMETRY_DB = "telemetry.db"
PRICES_DB = "prices.db"

# ------------------------------------------------------------------
# Database: User Activity Logging
# ------------------------------------------------------------------
def init_activity_table():
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                details TEXT,
                page TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[assistant] DB init error: {e}")

init_activity_table()

def log_activity(username, action_type, description, details=None, page=None):
    if not username:
        username = "guest"
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO user_activities (username, action_type, description, details, page)
               VALUES (?, ?, ?, ?, ?)""",
            (username, action_type, description, details, page)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[assistant] Activity logging error: {e}")

def get_activities(username, limit=25):
    if not username:
        return []
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, action_type, description, details, page, created_at
               FROM user_activities
               WHERE username = ?
               ORDER BY id DESC LIMIT ?""",
            (username, limit)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[assistant] Activity fetch error: {e}")
        return []

# ------------------------------------------------------------------
# Telemetry and Price Helpers
# ------------------------------------------------------------------
def get_live_telemetry():
    if not os.path.exists(TELEMETRY_DB):
        return None
    try:
        conn = sqlite3.connect(TELEMETRY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        print(f"[assistant] Telemetry fetch error: {e}")
    return None

def get_latest_commodity_prices(commodity=None):
    if not os.path.exists(PRICES_DB):
        return []
    try:
        conn = sqlite3.connect(PRICES_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if commodity:
            cursor.execute(
                """SELECT Commodity, Market, Modal_Price, Date
                   FROM prices
                   WHERE LOWER(Commodity) LIKE ?
                   ORDER BY Date DESC LIMIT 5""",
                (f"%{commodity.lower()}%",)
            )
        else:
            cursor.execute(
                """SELECT Commodity, Market, Modal_Price, Date
                   FROM prices
                   GROUP BY Commodity
                   ORDER BY Date DESC LIMIT 6"""
            )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[assistant] Prices fetch error: {e}")
        return []

# ------------------------------------------------------------------
# Navigation Intent Matcher (English & Kannada)
# ------------------------------------------------------------------
NAV_TARGETS = [
    {
        "id": "dashboard",
        "name": "Price DSS Dashboard",
        "name_kn": "ಬೆಲೆ ಸಲಹಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "url": "/dashboard",
        "keywords": [
            "dashboard", "price dss", "price prediction", "price forecast",
            "market prices", "price tab", "home tab", "home page",
            "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "ಬೆಲೆ ಸಲಹೆ", "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ", "ಬೆಲೆ ಮುನ್ಸೂಚನೆ", "ಮುಖಪುಟ", "ಹೋಮ್"
        ]
    },
    {
        "id": "crop",
        "name": "Crop Advisor",
        "name_kn": "ಬೆಳೆ ಸಲಹೆಗಾರ",
        "url": "/crop",
        "keywords": [
            "crop advisor", "recommend crop", "crop recommendation", "crop tab",
            "crop recommender", "crop page", "advisor tab", "crops",
            "ಬೆಳೆ ಸಲಹೆಗಾರ", "ಬೆಳೆ ಶಿಫಾರಸು", "ಬೆಳೆ ಟ್ಯಾಬ್", "ಯಾವ ಬೆಳೆ", "ಬೆಳೆಗಳು"
        ]
    },
    {
        "id": "disease",
        "name": "Leaf Disease Detection",
        "name_kn": "ಎಲೆ ರೋಗ ಪತ್ತೆ",
        "url": "/disease",
        "keywords": [
            "leaf scan", "disease scan", "leaf disease", "scan leaf", "detect disease",
            "disease tab", "leaf tab", "plant disease scan",
            "ಎಲೆ ಸ್ಕ್ಯಾನ್", "ಎಲೆ ರೋಗ", "ರೋಗ ಪತ್ತೆ", "ಗಿಡದ ರೋಗ", "ಎಲೆ ಟ್ಯಾಬ್", "ರೋಗ ಟ್ಯಾಬ್"
        ]
    },
    {
        "id": "telemetry",
        "name": "Sensor Node Telemetry",
        "name_kn": "ಸೆನ್ಸಾರ್ ನೋಡ್ ಮಾನಿಟರಿಂಗ್",
        "url": "/telemetry",
        "keywords": [
            "sensor node", "telemetry", "sensor tab", "telemetry tab", "iot tab",
            "hardware tab", "node tab", "live sensors",
            "ಸೆನ್ಸಾರ್ ನೋಡ್", "ಸೆನ್ಸಾರ್ ಟ್ಯಾಬ್", "ಸೆನ್ಸಾರ್", "ತೇವಾಂಶ ನೋಡ್", "ಐಒಟಿ", "ಹಾರ್ಡ್‌ವೇರ್"
        ]
    },
    {
        "id": "insights",
        "name": "Model Insights",
        "name_kn": "ಮಾದರಿ ಒಳನೋಟಗಳು",
        "url": "/insights",
        "keywords": [
            "model insights", "insights tab", "insights page", "feature importance",
            "shap tab", "ಒಳನೋಟ", "ಒಳನೋಟಗಳು", "ಮಾಡೆಲ್ ಒಳನೋಟ"
        ]
    },
    {
        "id": "comparison",
        "name": "Model Comparison",
        "name_kn": "ಮಾದರಿ ಹೋಲಿಕೆ",
        "url": "/model-comparison",
        "keywords": [
            "model comparison", "compare models", "comparison tab", "comparison page",
            "algorithms tab", "ಮಾದರಿ ಹೋಲಿಕೆ", "ಹೋಲಿಕೆ", "ಮಾದರಿಗಳ ಹೋಲಿಕೆ"
        ]
    },
    {
        "id": "admin",
        "name": "Admin Dashboard",
        "name_kn": "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "url": "/admin",
        "keywords": [
            "admin dashboard", "admin panel", "admin page", "retrain models",
            "ನಿರ್ವಾಹಕ", "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "ಅಡ್ಮಿನ್"
        ]
    },
    {
        "id": "logout",
        "name": "Logout",
        "name_kn": "ಲಾಗ್ ಔಟ್",
        "url": "/logout",
        "keywords": [
            "logout", "log out", "sign out", "sign off", "exit system",
            "ಲಾಗ್ ಔಟ್", "ನಿರ್ಗಮಿಸಿ", "ಹೊರಬನ್ನಿ"
        ]
    }
]

def has_kannada_chars(text):
    return any('\u0C80' <= ch <= '\u0CFF' for ch in text)

def detect_navigation_intent(text):
    clean = text.lower().strip()

    # If it's purely an informational question (e.g. "what is...", "how to...", "ಎಷ್ಟು..."),
    # do NOT navigate unless an explicit navigation action verb is used.
    question_starters = [
        "what is", "what are", "how is", "how are", "how to", "why is", "tell me", "explain", "is the", "are the",
        "ಎಷ್ಟು", "ಹೇಗೆ", "ಯಾವುದು", "ತಿಳಿಸಿ", "ಹೇಳಿ", "ಏನು"
    ]
    is_info_question = (
        any(clean.startswith(q) for q in question_starters) or
        any(q in clean for q in ["ಎಷ್ಟು", "ಹೇಗೆ ಗುಣಪಡಿಸುವುದು", "ಯಾವ ಬೆಳೆ"]) or
        (clean.endswith("?") and not any(v in clean for v in ["go to", "open", "switch", "navigate", "ತೆರೆಯಿರಿ", "ಹೋಗಿ"]))
    )

    nav_verbs = [
        "go to", "open", "switch to", "show", "take me to", "navigate to", "move to", "change to", "visit",
        "ತೆರೆಯಿರಿ", "ಹೋಗಿ", "ಬದಲಾಯಿಸಿ", "ತೋರಿಸಿ", "ಓಪನ್"
    ]
    is_explicit_nav = any(verb in clean for verb in nav_verbs)

    if is_info_question and not is_explicit_nav:
        return None

    best_match = None
    max_len = 0

    for target in NAV_TARGETS:
        # Check explicit ID match (e.g. single word "crop", "disease", "telemetry", "dashboard")
        if clean in [target["id"], target["name"].lower()]:
            return target

        for kw in target["keywords"]:
            if kw in clean:
                if len(kw) > max_len:
                    max_len = len(kw)
                    best_match = target

    return best_match

# ------------------------------------------------------------------
# Knowledge Engine: Agricultural Expert Q&A (English & Kannada)
# ------------------------------------------------------------------
def get_expert_response(text, lang="en"):
    clean = text.lower()
    if has_kannada_chars(text):
        lang = "kn"

    # 1. LIVE SENSOR / TELEMETRY QUERIES
    sensor_terms = ["moisture", "soil moisture", "sensor reading", "pot reading", "temperature", "humidity", "ph level", "how is my plant", "water",
                    "ತೇವಾಂಶ", "ಮಣ್ಣಿನ ತೇವಾಂಶ", "ಸೆನ್ಸಾರ್", "ತಾಪಮಾನ", "ಆರ್ದ್ರತೆ", "ಗಿಡದ ಸ್ಥಿತಿ", "ನೀರು", "ಪಿಎಚ್"]
    if any(k in clean for k in sensor_terms):
        t = get_live_telemetry()
        if t:
            m = float(t.get("moisture_pct") or 0.0)
            temp = float(t.get("air_temp_c") or 26.5)
            hum = float(t.get("humidity_pct") or 65.0)
            ph = float(t.get("ph") or 6.8)
            status_en = "optimal" if 40 <= m <= 70 else ("low (needs watering)" if m < 40 else "excessively wet")
            status_kn = "ಉತ್ತಮವಾಗಿದೆ" if 40 <= m <= 70 else ("ಕಡಿಮೆ ಇದೆ (ನೀರು ಹಾಕಿ)" if m < 40 else "ಅತಿಯಾದ ತೇವಾಂಶವಿದೆ")

            if lang == "kn":
                return (
                    f"**🌱 ಲೈವ್ ಮಣ್ಣು & ಸೆನ್ಸಾರ್ ಮಾಹಿತಿ:**\n"
                    f"• **ಮಣ್ಣಿನ ತೇವಾಂಶ:** {m:.1f}% ({status_kn})\n"
                    f"• **ಗಾಳಿಯ ತಾಪಮಾನ:** {temp:.1f}°C\n"
                    f"• **ಆರ್ದ್ರತೆ:** {hum:.1f}%\n"
                    f"• **ಮಣ್ಣಿನ pH:** {ph:.1f}\n\n"
                    f"ನಿಮ್ಮ ಗಿಡದ ಲೈವ್ ಗ್ರಾಫ್ ಮತ್ತು ವಿವರಗಳನ್ನು ನೋಡಲು **ಸೆನ್ಸಾರ್ ನೋಡ್** ಟ್ಯಾಬ್ ತೆರೆಯಬಹುದು.",
                    f"ಪ್ರಸ್ತುತ ಮಣ್ಣಿನ ತೇವಾಂಶ {m:.1f} ಶೇಕಡಾ ಇದೆ, {status_kn}. ತಾಪಮಾನ {temp:.1f} ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್."
                )
            return (
                f"**🌱 Live Pot Telemetry:**\n"
                f"• **Soil Moisture:** {m:.1f}% ({status_en})\n"
                f"• **Air Temperature:** {temp:.1f}°C\n"
                f"• **Air Humidity:** {hum:.1f}%\n"
                f"• **Soil pH:** {ph:.1f}\n\n"
                f"Would you like me to switch you to the **Sensor Node** tab to view the live timeline?",
                f"Current soil moisture is {m:.1f} percent, which is {status_en}. Air temperature is {temp:.1f} degrees Celsius."
            )
        else:
            if lang == "kn":
                return (
                    "ಸೆನ್ಸಾರ್ ನೋಡ್ ಹಾರ್ಡ್‌ವೇರ್ ಅಥವಾ ಸಿಮ್ಯುಲೇಶನ್ ಡೇಟಾಗೆ ಕಾಯುತ್ತಿದೆ. ದಯವಿಟ್ಟು ಆರ್ಡುಯಿನೋ ಯುನೋ ನೋಡ್ ಸಂಪರ್ಕಿಸಿ ಅಥವಾ **ಸೆನ್ಸಾರ್ ನೋಡ್** ಟ್ಯಾಬ್ ಪರಿಶೀಲಿಸಿ.",
                    "ಲೈವ್ ಸೆನ್ಸಾರ್ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಸೆನ್ಸಾರ್ ನೋಡ್ ಟ್ಯಾಬ್ ನೋಡಿ."
                )
            return (
                "The sensor node is waiting for hardware or simulation data. You can plug in your Arduino Uno node or check the **Sensor Node** tab.",
                "No live sensor telemetry received yet. Please check the Sensor Node tab."
            )

    # 2. MANDI / COMMODITY PRICES
    price_terms = ["price", "mandi", "rate", "cost", "arecanut", "coconut", "black pepper", "cashew", "banana",
                   "ಬೆಲೆ", "ದರ", "ಮಂಡಿ", "ಅಡಿಕೆ", "ತೆಂಗು", "ತೆಂಗಿನಕಾಯಿ", "ಕಾಳುಮೆಣಸು", "ಗೋಡಂಬಿ", "ಬಾಳೆಹಣ್ಣು", "ಮಾರುಕಟ್ಟೆ"]
    if any(k in clean for k in price_terms):
        target_crop = None
        crop_map = {
            "arecanut": "Arecanut", "ಅಡಿಕೆ": "Arecanut",
            "coconut": "Coconut", "ತೆಂಗು": "Coconut", "ತೆಂಗಿನಕಾಯಿ": "Coconut",
            "black pepper": "Black Pepper", "ಕಾಳುಮೆಣಸು": "Black Pepper", "ಮೆಣಸು": "Black Pepper",
            "cashew": "Cashew", "ಗೋಡಂಬಿ": "Cashew",
            "banana": "Banana", "ಬಾಳೆ": "Banana", "ಬಾಳೆಹಣ್ಣು": "Banana"
        }
        for term, crop_val in crop_map.items():
            if term in clean:
                target_crop = crop_val
                break

        prices = get_latest_commodity_prices(target_crop)
        if prices:
            if lang == "kn":
                items_str = "\n".join([f"• **{p['Commodity']}** ({p['Market']}): ₹{float(p['Modal_Price'] or 0):.2f}/ಕ್ವಿಂಟಾಲ್ (ದಿನಾಂಕ: {p['Date']})" for p in prices[:4]])
                return (
                    f"**📊 ಇತ್ತೀಚಿನ ಮಂಡಿ ಮಾರುಕಟ್ಟೆ ದರಗಳು (ದಕ್ಷಿಣ ಕನ್ನಡ):**\n{items_str}\n\n"
                    f"ಮುಂದಿನ 7–14 ದಿನಗಳ ಮಾರುಕಟ್ಟೆ ಮುನ್ಸೂಚನೆ ಮತ್ತು **ಮಾರಾಟ / ಶೇಖರಣೆ** ಸಲಹೆಗಾಗಿ **ಬೆಲೆ ಸಲಹಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್** ಪರಿಶೀಲಿಸಿ.",
                    f"ಇತ್ತೀಚಿನ ಮಂಡಿ ದರಗಳನ್ನು ಪಡೆಯಲಾಗಿದೆ. ಹೆಚ್ಚಿನ ಮುನ್ಸೂಚನೆಗೆ ಬೆಲೆ ಸಲಹಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ನೋಡಿ."
                )
            items_str = "\n".join([f"• **{p['Commodity']}** at {p['Market']}: ₹{float(p['Modal_Price'] or 0):.2f}/quintal ({p['Date']})" for p in prices[:4]])
            return (
                f"**📊 Latest Mandi Price Insights:**\n{items_str}\n\n"
                f"KrishiSense predicts next 7–14 days modal price and gives a **Sell / Hold** call on the **Price DSS** tab.",
                f"Here are the latest recorded market prices for your crops."
            )

    # 3. LEAF DISEASE ADVISORY
    disease_terms = ["blight", "yellow", "spots", "curl", "fungus", "pesticide", "remedy", "cure", "bacterial", "leaf",
                     "ಎಲೆ", "ರೋಗ", "ಚುಕ್ಕೆ", "ಸುಟ್ಟ ರೋಗ", "ಬೇವಿನ ಎಣ್ಣೆ", "ಶಿಲೀಂಧ್ರ", "ಟೊಮೆಟೊ", "ಔಷಧಿ", "ಪರಿಹಾರ", "ರೋಗ ನಿಯಂತ್ರಣ"]
    if any(k in clean for k in disease_terms):
        if lang == "kn":
            return (
                "**🍃 ಎಲೆ ರೋಗ & ಸಸ್ಯ ಸಂರಕ್ಷಣಾ ಸಲಹೆ:**\n"
                "• **ಎಲೆ ಚುಕ್ಕೆ / ಬ್ಲೈಟ್ (ಸುಟ್ಟ ರೋಗ):** ಎಲೆಗಳ ಮೇಲೆ ಕಂದು ಅಥವಾ ಕಪ್ಪು ಬಣ್ಣದ ಚುಕ್ಕೆಗಳು ಕಾಣಿಸಿಕೊಳ್ಳುತ್ತವೆ. ಇದಕ್ಕೆ ಕಾಪರ್ ಆಕ್ಸಿಕ್ಲೋರೈಡ್ (2.5 ಗ್ರಾಂ/ಲೀಟರ್) ಅಥವಾ ಮ್ಯಾಂಕೋಜೆಬ್ ಸಿಂಪಡಿಸಿ.\n"
                "• **ಸಾವಯವ ನಿಯಂತ್ರಣ:** ಆರಂಭಿಕ ಹಂತದಲ್ಲಿ ಬೇವಿನ ಎಣ್ಣೆ (5 ಮಿಲಿ/ಲೀಟರ್) ಅಥವಾ ಟ್ರೈಕೋಡರ್ಮಾ ಸಿಂಪಡಿಸಿ. ಹಾನಿಗೊಳಗಾದ ಎಲೆಗಳನ್ನು ತಕ್ಷಣ ತೆಗೆದುಹಾಕಿ.\n"
                "• **ಸ್ಕ್ಯಾನ್ ಮಾಡಿ:** ನಿಮ್ಮ ಗಿಡದ ಎಲೆಯ ಫೋಟೋವನ್ನು **ಎಲೆ ಸ್ಕ್ಯಾನ್** ಟ್ಯಾಬ್‌ನಲ್ಲಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ, AI ತಕ್ಷಣ ರೋಗವನ್ನು ಪತ್ತೆ ಮಾಡಿ ನಿಖರ ಔಷಧ ತಿಳಿಸುತ್ತದೆ!",
                "ಎಲೆ ಚುಕ್ಕೆ ಅಥವಾ ಸುಟ್ಟ ರೋಗಕ್ಕೆ ಕಾಪರ್ ಆಕ್ಸಿಕ್ಲೋರೈಡ್ ಅಥವಾ ಬೇವಿನ ಎಣ್ಣೆ ಸಿಂಪಡಿಸಿ. ನಿಖರ ತಪಾಸಣೆಗೆ ಎಲೆ ಸ್ಕ್ಯಾನ್ ಟ್ಯಾಬ್ ಬಳಸಿ."
            )
        return (
            "**🍃 Leaf Health & Disease Control Advisory:**\n"
            "• **Early/Late Blight & Leaf Spot:** Causes brown/black concentric spots and yellowing. Apply Copper Oxychloride (2.5g/L) or Mancozeb. Ensure proper air circulation and avoid wetting leaves directly.\n"
            "• **Organic Control:** Spray diluted cold-pressed neem oil (5ml/L) or Trichoderma viride in early stages.\n"
            "• You can take a photo of the affected leaf and upload it in the **Leaf Scan** tab for immediate ONNX-powered diagnosis!",
            "For leaf blight, apply copper oxychloride or spray neem oil. You can upload a photo to the Leaf Scan tab for diagnosis."
        )

    # 4. CROP RECOMMENDATION ADVISORY
    crop_terms = ["crop", "grow", "soil", "sow", "fertilizer", "npk", "which crop",
                  "ಬೆಳೆ", "ಬಿತ್ತನೆ", "ಯಾವ ಬೆಳೆ", "ಗೊಬ್ಬರ", "ಮಣ್ಣು", "ಎನ್‌ಪಿಕೆ", "ಕರಾವಳಿ", "ದಕ್ಷಿಣ ಕನ್ನಡ", "ಶಿಫಾರಸು"]
    if any(k in clean for k in crop_terms):
        if lang == "kn":
            return (
                "**🌾 KrishiSense ಬೆಳೆ ಶಿಫಾರಸು (Module M2):**\n"
                "• ದಕ್ಷಿಣ ಕನ್ನಡ ಮತ್ತು ಕರಾವಳಿ ಕರ್ನಾಟಕದ ಮಣ್ಣಿಗೆ **ಅಡಿಕೆ, ತೆಂಗು, ಗೋಡಂಬಿ, ಕಾಳುಮೆಣಸು** ಮತ್ತು **ಭತ್ತ** ಅತ್ಯಂತ ಲಾಭದಾಯಕ ಬೆಳೆಗಳಾಗಿವೆ.\n"
                "• ಅಡಿಕೆ ಮತ್ತು ತೆಂಗಿಗೆ ಮಣ್ಣಿನ pH 5.5 ರಿಂದ 7.0 (ಸ್ವಲ್ಪ ಆಮ್ಲೀಯದಿಂದ ತಟಸ್ಥ) ಮತ್ತು ಉತ್ತಮ ನೀರು ಬಸಿದುಹೋಗುವ ಮಣ್ಣು ಅಗತ್ಯ.\n"
                "• ನಿಮ್ಮ ಮಣ್ಣಿನ ಪೋಷಕಾಂಶಗಳಾದ ನೈಟ್ರೋಜನ್ (N), ಫಾಸ್ಫರಸ್ (P), ಪೊಟ್ಯಾಸಿಯಮ್ (K) ಮತ್ತು ಹವಾಮಾನಕ್ಕೆ ಅನುಗುಣವಾಗಿ ಟಾಪ್ 3 ಸೂಕ್ತ ಬೆಳೆಗಳನ್ನು ತಿಳಿಯಲು **ಬೆಳೆ ಸಲಹೆಗಾರ** ಟ್ಯಾಬ್ ಬಳಸಿ!",
                "ಕರಾವಳಿ ಕರ್ನಾಟಕದ ಮಣ್ಣಿಗೆ ಅಡಿಕೆ, ತೆಂಗು, ಗೋಡಂಬಿ ಮತ್ತು ಕಾಳುಮೆಣಸು ಉತ್ತಮ ಬೆಳೆಗಳು. ವೈಯಕ್ತಿಕ ಶಿಫಾರಸಿಗೆ ಬೆಳೆ ಸಲಹೆಗಾರ ಟ್ಯಾಬ್ ನೋಡಿ."
            )
        return (
            "**🌾 KrishiSense Crop Recommender (Module M2):**\n"
            "• In Dakshina Kannada / Coastal Karnataka, top high-yield cash crops are **Arecanut, Coconut, Cashew, Black Pepper**, and **Paddy**.\n"
            "• Ideal soil pH for arecanut and coconut is 5.5 to 7.0 (slightly acidic to neutral).\n"
            "• You can run our scientific model (7 features: N, P, K, Temp, Humidity, pH, Rainfall) or the Regional Karnataka Advisor on the **Crop Advisor** tab!",
            "For coastal Karnataka soils, Arecanut, Coconut, Cashew and Black Pepper are prime choices. Visit the Crop Advisor tab to run a personalized prediction."
        )

    # 5. GREETING & GENERAL CAPABILITIES
    greeting_terms = ["hello", "hi", "namaste", "hey", "who are you", "help", "what can you do",
                      "ನಮಸ್ಕಾರ", "ಹಲೋ", "ನೀನು ಯಾರು", "ಏನು ಮಾಡಬಲ್ಲೆ", "ಸಹಾಯ", "ಕೃಷಿ ಮಿತ್ರ"]
    if any(k in clean for k in greeting_terms):
        if lang == "kn":
            return (
                "👋 **ನಮಸ್ಕಾರ! ನಾನು ಕೃಷಿ ಮಿತ್ರ (Krishi Mitra), ನಿಮ್ಮ KrishiSense AI ಧ್ವನಿ ಸಹಾಯಕ.**\n\n"
                "ನಾನು ನಿಮಗೆ ಈ ಕೆಳಗಿನ ವಿಷಯಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:\n"
                "1. **ಧ್ವನಿ ಮೂಲಕ ಟ್ಯಾಬ್ ಬದಲಾವಣೆ:** *'ಬೆಳೆ ಸಲಹೆಗಾರ'*, *'ಎಲೆ ಸ್ಕ್ಯಾನ್'*, *'ಸೆನ್ಸಾರ್ ನೋಡ್'*, ಅಥವಾ *'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್'* ಎಂದು ಹೇಳಿ.\n"
                "2. **ಲೈವ್ ಸೆನ್ಸಾರ್ ಮಾಹಿತಿ:** *'ಮಣ್ಣಿನ ತೇವಾಂಶ ಎಷ್ಟು?'* ಅಥವಾ *'ಗಿಡದ ಸ್ಥಿತಿ ಹೇಗಿದೆ?'* ಎಂದು ಕೇಳಿ.\n"
                "3. **ಮಂಡಿ ಬೆಲೆಗಳು:** *'ಅಡಿಕೆ ಬೆಲೆ ಎಷ್ಟು?'* ಅಥವಾ *'ತೆಂಗಿನಕಾಯಿ ದರ ತಿಳಿಸಿ'* ಎಂದು ಕೇಳಿ.\n"
                "4. **ಬೆಳೆ & ರೋಗ ಪರಿಹಾರ:** *'ಯಾವ ಬೆಳೆ ಬೆಳೆಯಬೇಕು?'* ಅಥವಾ *'ಎಲೆ ಚುಕ್ಕೆ ರೋಗಕ್ಕೆ ಮದ್ದು ಏನು?'* ಎಂದು ಕೇಳಿ.\n"
                "5. **ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್:** ಮೊಬೈಲ್‌ನಲ್ಲಿ ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಲು *'ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್'* ಎಂದು ಹೇಳಿ.\n"
                "6. **ಚಟುವಟಿಕೆ ದಾಖಲೆ:** ನಿಮ್ಮ ಎಲ್ಲಾ ಪ್ರಶ್ನೆಗಳು ಮತ್ತು ಸಂವಾದಗಳು **ಚಟುವಟಿಕೆ ಲಾಗ್** ಟ್ಯಾಬ್‌ನಲ್ಲಿ ದಾಖಲಾಗುತ್ತವೆ.",
                "ನಮಸ್ಕಾರ! ನಾನು ಕೃಷಿ ಮಿತ್ರ. ಕೃಷಿ ಸಲಹೆ, ಮಂಡಿ ಬೆಲೆ, ಎಲೆ ರೋಗ ಅಥವಾ ಧ್ವನಿ ಆಜ್ಞೆಗಳಿಗೆ ನಾನು ಸಿದ್ಧನಿದ್ದೇನೆ. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
            )
        return (
            "👋 **Namaste! I am Krishi Mitra, your KrishiSense Voice & Chat Assistant.**\n\n"
            "I can assist you with:\n"
            "1. **Voice Tab Navigation:** Say *'Go to Crop Advisor'*, *'Open Leaf Scan'*, *'Show Sensor Node'*, or *'Take me to Dashboard'*.\n"
            "2. **Live Pot Telemetry:** Ask *'What is the soil moisture?'* or *'How is my plant?'*.\n"
            "3. **Mandi Price Queries:** Ask *'What is arecanut price?'* or *'Show coconut rates'*\n"
            "4. **Disease & Farming Advice:** Ask about leaf spots, remedies, or which crop to sow.\n"
            "5. **Download as App:** Say *'Install app'* to get KrishiSense on your phone home screen.\n"
            "6. **Activity Capture:** I log all your requests and navigation in your live **Activity Log** tab.",
            "Hello! I am Krishi Mitra. You can ask me questions about your crops or speak commands to navigate between tabs."
        )

    # 6. APP INSTALL / DOWNLOAD AS APP QUERIES
    app_terms = ["install app", "download app", "mobile app", "install", "download as app", "pwa",
                 "ಆ್ಯಪ್", "ಡೌನ್‌ಲೋಡ್", "ಇನ್‌ಸ್ಟಾಲ್", "ಮೊಬೈಲ್ ಆ್ಯಪ್"]
    if any(k in clean for k in app_terms):
        if lang == "kn":
            return (
                "📱 **KrishiSense ಮೊಬೈಲ್ ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್ & ಇನ್‌ಸ್ಟಾಲೇಶನ್:**\n\n"
                "• **Android (Chrome):** ಪರದೆಯ ಮೇಲ್ಭಾಗದಲ್ಲಿ ಕಾಣಿಸುವ **'📲 ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಿ'** ಬಟನ್ ಕ್ಲಿಕ್ ಮಾಡಿ ಅಥವಾ ಬ್ರೌಸರ್ ಮೆನು (⋮) ಒತ್ತಿ **'Install App'** ಆಯ್ಕೆಮಾಡಿ.\n"
                "• **iPhone / iPad (Safari):** ಕೆಳಭಾಗದಲ್ಲಿರುವ **Share (⎋)** ಐಕಾನ್ ಒತ್ತಿ ನಂತರ **'Add to Home Screen (⊞)'** ಆಯ್ಕೆಮಾಡಿ.\n"
                "• ಇದರಿಂದ KrishiSense ನಿಮ್ಮ ಮೊಬೈಲ್‌ನ ಹೋಮ್ ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿ ಸ್ವತಂತ್ರ ಆ್ಯಪ್ ಆಗಿ ಡೌನ್‌ಲೋಡ್ ಆಗುತ್ತದೆ!",
                "KrishiSense ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಲು ಮೇಲಿನ ಇನ್‌ಸ್ಟಾಲ್ ಬಟನ್ ಅಥವಾ ಬ್ರೌಸರ್ ಮೆನುವಿನಲ್ಲಿ ಆ್ಯಡ್ ಟು ಹೋಮ್ ಸ್ಕ್ರೀನ್ ಆಯ್ಕೆಮಾಡಿ."
            )
        return (
            "📱 **How to Download & Install KrishiSense as an App:**\n\n"
            "• **On Android (Chrome/Edge):** Click the floating **'📲 Install App'** pill at the top-right, or tap the browser menu (⋮) $\\rightarrow$ **'Install app'** / **'Add to Home screen'**.\n"
            "• **On iPhone/iPad (Safari):** Tap the **Share icon (⎋)** at the bottom of Safari $\\rightarrow$ select **'Add to Home Screen (⊞)'**.\n"
            "• **Desktop (Chrome/Edge):** Click the install icon in the browser address bar $\\rightarrow$ **'Install KrishiSense'**.\n\n"
            "KrishiSense will install as a standalone mobile application with full offline caching and no browser address bar!",
            "To install KrishiSense on your phone, click the Install App button at the top or choose Add to Home Screen in your browser menu."
        )

    # Default fallback response
    if lang == "kn":
        return (
            "ನಾನು ನಿಮ್ಮ ಕೃಷಿ ನಿರ್ವಹಣೆಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ! ನೀವು ಬೆಳೆ ಆಯ್ಕೆ, ಎಲೆ ರೋಗಗಳು, ಮಂಡಿ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು, ಲೈವ್ ಸೆನ್ಸಾರ್ ತೇವಾಂಶದ ಬಗ್ಗೆ ಕೇಳಬಹುದು ಅಥವಾ *'ಬೆಳೆ ಸಲಹೆಗಾರನಿಗೆ ಹೋಗಿ'*, *'ಎಲೆ ಸ್ಕ್ಯಾನ್ ತೆರೆಯಿರಿ'* ಎಂದು ಹೇಳಿ ಟ್ಯಾಬ್ ಬದಲಾಯಿಸಬಹುದು.",
            "ಕೃಷಿ ಸಲಹೆ, ಮಂಡಿ ಬೆಲೆ, ಎಲೆ ರೋಗ ಅಥವಾ ಟ್ಯಾಬ್ ಬದಲಾವಣೆಗೆ ನಾನು ಸಿದ್ಧನಿದ್ದೇನೆ. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        )
    return (
        "I am here to help you manage your farm with KrishiSense! You can ask about crop suitability, leaf diseases, mandi price trends, live sensor telemetry, or tell me to switch tabs (e.g. *'Open Leaf Scan'* or *'Go to Crop Advisor'*).",
        "I can help with crop advice, leaf disease diagnosis, market prices, and voice navigation. How may I assist you?"
    )

# ------------------------------------------------------------------
# Optional External LLM Integration (Google Gemini)
# ------------------------------------------------------------------
def call_external_llm(user_message, current_page, lang="en"):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return None
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        prompt = (
            f"You are Krishi Mitra, an expert precision agricultural assistant for KrishiSense smart farming system in Karnataka, India. "
            f"User is on page '{current_page}'. User's language preference is '{lang}'. "
            f"If lang is 'kn' or user query is in Kannada, respond fluently in natural Kannada (ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ). "
            f"Answer concisely, helpfully and accurately for a Karnataka farmer in 2-3 short paragraphs. "
            f"User query: {user_message}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                # extract
                for part in candidates[0].get('content', {}).get('parts', []):
                    if 'text' in part and not part.get('thought', False):
                        return part['text'].strip()
                reply = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if reply:
                    return reply.strip()
    except Exception as e:
        print(f"[assistant] Gemini call exception: {e}")
    return None

# ------------------------------------------------------------------
# API Routes
# ------------------------------------------------------------------
@assistant_bp.route("/api/assistant/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    current_page = data.get("current_page", "/dashboard")
    lang = data.get("lang", "en")
    username = session.get("username", "guest")

    if not message:
        return jsonify({"success": False, "error": "Empty message"}), 400

    # Auto-detect Kannada script
    if has_kannada_chars(message):
        lang = "kn"

    # 1. Check for tab navigation intent first
    nav_match = detect_navigation_intent(message)
    if nav_match:
        target_name = nav_match["name_kn"] if lang == "kn" else nav_match["name"]
        if lang == "kn":
            reply_text = f"🚀 **ಟ್ಯಾಬ್ ಬದಲಾವಣೆ:** **{target_name}** ಪುಟಕ್ಕೆ ಕರೆದೊಯ್ಯಲಾಗುತ್ತಿದೆ."
            speech_text = f"{target_name} ಪುಟವನ್ನು ತೆರೆಯಲಾಗುತ್ತಿದೆ."
        else:
            reply_text = f"🚀 **Switching tab:** Navigating to **{target_name}** now."
            speech_text = f"Navigating to {target_name}."

        log_activity(
            username=username,
            action_type="tab_navigation",
            description=f"Switched to {nav_match['name']} tab via voice/chat",
            details=f"Command: '{message}'",
            page=nav_match["url"]
        )

        return jsonify({
            "success": True,
            "reply": reply_text,
            "speech": speech_text,
            "action": "navigate",
            "target_url": nav_match["url"],
            "target_name": target_name,
            "intent": f"nav_{nav_match['id']}",
            "lang": lang
        })

    # 2. Try external LLM (Gemini) if configured, otherwise use built-in expert engine
    reply_text = None
    speech_text = None
    external_reply = call_external_llm(message, current_page, lang)
    if external_reply:
        reply_text = external_reply
        # Strip markdown for speech synthesis
        speech_text = re.sub(r"[\*\_#`]", "", external_reply)[:180] + "..."
    else:
        reply_text, speech_text = get_expert_response(message, lang)

    # 3. Log user activity
    log_activity(
        username=username,
        action_type="chat_query",
        description=f"Asked: \"{message[:60]}...\"" if len(message) > 60 else f"Asked: \"{message}\"",
        details=f"Response provided on page {current_page} (Language: {lang})",
        page=current_page
    )

    return jsonify({
        "success": True,
        "reply": reply_text,
        "speech": speech_text,
        "action": "reply",
        "intent": "general_advisory",
        "lang": lang
    })

@assistant_bp.route("/api/assistant/activity", methods=["POST"])
def api_log_activity():
    data = request.get_json(silent=True) or {}
    username = session.get("username", "guest")
    action_type = data.get("action_type", "user_action")
    description = data.get("description", "User performed an action")
    details = data.get("details", "")
    page = data.get("page", "")

    log_activity(username, action_type, description, details, page)
    return jsonify({"success": True})

@assistant_bp.route("/api/assistant/activities", methods=["GET"])
def api_get_activities():
    username = session.get("username", "guest")
    items = get_activities(username, limit=30)
    return jsonify({"success": True, "activities": items, "username": username})
