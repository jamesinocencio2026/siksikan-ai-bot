import os
import requests
from datetime import datetime, timedelta
from pytz import timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- WEBHOOK & API TOKENS ---
FB_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "BayanihanSiksikanAI2026")
FB_PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_KEY")
TOMTOM_API_KEY = os.environ.get("TOMTOM_KEY")

# --- MEMORY CACHE STORES ---
# Live counts container: {"station_id": {"light": X, "medium": Y, "heavy": Z, "last_updated": datetime}}
crowdsourced_votes = {}

# Anti-Spam Lie Detector: {user_id: timestamp}
user_vote_timestamps = {}

# Idempotency Layer (Fixes Multiple Replies): {message_id: timestamp}
processed_message_ids = {}

STATION_PROFILES = {
    "mrt3_taft_nb": {"name": "🚆 MRT-3 Taft Avenue (Northbound → North Ave)", "is_interchange": True, "coords": "14.5376,121.0014"},
    "mrt3_taft_sb": {"name": "🚆 MRT-3 Taft Avenue (Southbound End Terminal)", "is_interchange": True, "coords": "14.5376,121.0014"},
    "mrt3_cubao_nb": {"name": "🚆 MRT-3 Cubao (Northbound → North Ave)", "is_interchange": True, "coords": "14.6195,121.0511"},
    "mrt3_cubao_sb": {"name": "🚆 MRT-3 Cubao (Southbound → Taft Ave)", "is_interchange": True, "coords": "14.6195,121.0511"},
    "mrt3_guadalupe_nb": {"name": "🚆 MRT-3 Guadalupe (Northbound → North Ave)", "is_interchange": False, "coords": "14.5672,121.0456"},
    "mrt3_guadalupe_sb": {"name": "🚆 MRT-3 Guadalupe (Southbound → Taft Ave)", "is_interchange": False, "coords": "14.5672,121.0456"},
    "lrt2_cubao_wb": {"name": "🚇 LRT-2 Cubao (Westbound ← Recto/U-Belt)", "is_interchange": True, "coords": "14.6226,121.0526"},
    "lrt2_cubao_eb": {"name": "🚇 LRT-2 Cubao (Eastbound → Marikina/Antipolo)", "is_interchange": True, "coords": "14.6226,121.0526"}
}

PH_HOLIDAYS = ["2026-06-12", "2026-08-31", "2026-11-01", "2026-12-25", "2026-12-30"]

# --- DATA FUSION MODIFIERS ---

def get_weather_impact():
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Manila&appid={OPENWEATHER_API_KEY}"
        res = requests.get(url, timeout=4).json()
        if res.get("weather", [{}])[0].get("main", "Clear") in ["Rain", "Thunderstorm", "Drizzle"]:
            return 15
    except Exception: pass
    return 0

def get_traffic_impact(coords):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_API_KEY}&point={coords}"
        res = requests.get(url, timeout=4).json()
        speed = res.get("flowSegmentData", {}).get("currentSpeed", 30)
        if speed <= 8: return 20
        elif speed <= 15: return 10
    except Exception: pass
    return 0

def enforce_cache_decay(station_id):
    """Enforces database cleanliness. If a vote payload is older than 15 mins, flush it."""
    now = datetime.now()
    if station_id in crowdsourced_votes:
        last_updated = crowdsourced_votes[station_id]["last_updated"]
        if (now - last_updated).total_seconds() > 900: # 15 minutes
            del crowdsourced_votes[station_id]

def clean_old_message_ids():
    """Removes processed message IDs older than 5 minutes to prevent memory leaks."""
    now = datetime.now()
    expired_ids = [msg_id for msg_id, timestamp in processed_message_ids.items() 
                   if (now - timestamp).total_seconds() > 300]
    for msg_id in expired_ids:
        del processed_message_ids[msg_id]

def calculate_density(station_id, pht_now):
    enforce_cache_decay(station_id)
    profile = STATION_PROFILES.get(station_id)
    if not profile: return "🟢 LIGHT"
    
    score = 0
    hour = pht_now.hour
    day = pht_now.weekday()
    date_str = pht_now.strftime("%Y-%m-%d")

    # 1. Historical Directional Vectors
    if "mrt3_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_sb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_nb"): score += 30
    elif "lrt2_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_wb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_eb"): score += 30
        
    if profile["is_interchange"]: score += 10

    # 2. Calendar Anomalies Checking
    if (pht_now.day in [14, 15, 30, 31]) and day == 4: score += 25
    elif date_str in PH_HOLIDAYS: score += 20

    # 3. Environmental API Feeds Integration
    score += get_weather_impact()
    score += get_traffic_impact(profile["coords"])

    # 4. Filtered Crowdsourced Vectors Layer
    if station_id in crowdsourced_votes:
        v = crowdsourced_votes[station_id]
        total = v["light"] + v["medium"] + v["heavy"]
        if total > 0:
            score += ((v["medium"] * 15) + (v["heavy"] * 35)) / total

    if score >= 60: return "🔴 HEAVY"
    elif score >= 35: return "🟡 MEDIUM"
    return "🟢 LIGHT"

# --- WEBHOOK SYSTEM INTERACTION PROTOCOLS ---

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == FB_VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json()
    if payload.get("object") == "page":
        for entry in payload.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]
                
                # --- EXTRACT UNIQUE ID FOR DEDUPLICATION ---
                msg_id = None
                if event.get("message"):
                    msg_id = event["message"].get("mid")
                elif event.get("postback"):
                    msg_id = f"PB_{event['postback'].get('timestamp')}_{sender_id}"
                
                # --- IDEMPOTENCY FILTER BLOCK ---
                if msg_id:
                    if msg_id in processed_message_ids:
                        return "DUPLICATE_IGNORED", 200 # Instantly stop Meta's retry engine
                    processed_message_ids[msg_id] = datetime.now()

                # Run routine housekeeping
                clean_old_message_ids()

                # Process verified unique payload safely
                if event.get("postback"):
                    handle_postback(sender_id, event["postback"]["payload"])
                elif event.get("message") and event["message"].get("text"):
                    handle_message(sender_id, event["message"]["text"].lower().strip())
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

def handle_message(user_id, text):
    pht = timezone("Asia/Manila")
    now = datetime.now(pht)
    
    # Structural Safety Closure Window
    if now.hour < 5 or (now.hour == 22 and now.minute > 30) or now.hour > 22:
        send_text(user_id, "🌙 *Train lines are currently closed.*\n\nOperating Hours: 5:00 AM - 10:30 PM PHT.")
        return

    # Strict Intent Verification Gates
    if text in ["cubao", "araneta"]:
        send_cubao_menu(user_id)
        return
    if text in ["taft", "pasay", "edsa"]:
        send_taft_menu(user_id)
        return
    if text in ["guada", "guadalupe"]:
        send_guadalupe_menu(user_id)
        return

    # Fallback default text prompt
    send_text(user_id, "👋 Welcome to Siksikan AI! Type a station name to verify conditions (e.g., 'Cubao', 'Taft', or 'Guadalupe').")

def handle_postback(user_id, payload):
    pht = timezone("Asia/Manila")
    now = datetime.now(pht)
    
    if payload.startswith("QUERY_"):
        station_key = payload.replace("QUERY_", "")
        deliver_dashboard(user_id, station_key, now)
        
    elif payload.startswith("VOTE_"):
        # Anti-Spam Lie Detection Enforcement
        if user_id in user_vote_timestamps:
            last_vote = user_vote_timestamps[user_id]
            if (datetime.now() - last_vote).total_seconds() < 900: # 15 mins block
                send_text(user_id, "🔒 Your vote has already been counted recently!")
                return
        
        parts = payload.split("_")
        tier = parts[1].lower() # light, medium, heavy
        station_id = "_".join(parts[2:])
        
        # Write to dynamic state data index
        if station_id not in crowdsourced_votes:
            crowdsourced_votes[station_id] = {"light": 0, "medium": 0, "heavy": 0, "last_updated": datetime.now()}
        
        crowdsourced_votes[station_id][tier] += 1
        crowdsourced_votes[station_id]["last_updated"] = datetime.now()
        user_vote_timestamps[user_id] = datetime.now()
        
        send_text(user_id, "✅ Thank you! Your real-time platform vote has been saved.")

def deliver_dashboard(user_id, station_key, current_time):
    status = calculate_density(station_key, current_time)
    name = STATION_PROFILES[station_key]["name"]
    msg = f"📊 *Siksikan AI Dashboard Update*\n\n📍 Station: {name}\nStatus: {status}\n\nHelp your fellow commuters! If you are standing at the platform right now, please verify below:"
    send_simplified_buttons(user_id, msg, station_key)

def send_text(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}}, timeout=5)

def send_cubao_menu(recipient_id):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": "📍 *Which Cubao Station are you heading to?*\n\nCubao is an interchange for two separate lines. Please tap your exact line and direction below:",
            "quick_replies": [
                {"content_type": "text", "title": "🚆 MRT Northbound", "payload": "QUERY_mrt3_cubao_nb"},
                {"content_type": "text", "title": "🚆 MRT Southbound", "payload": "QUERY_mrt3_cubao_sb"},
                {"content_type": "text", "title": "🚇 LRT Westbound", "payload": "QUERY_lrt2_cubao_wb"},
                {"content_type": "text", "title": "🚇 LRT Eastbound", "payload": "QUERY_lrt2_cubao_eb"}
            ]
        }
    }
    requests.post(url, json=payload, timeout=5)

def send_taft_menu(recipient_id):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": "📍 *Which Taft Avenue Platform direction are you checking?*",
            "quick_replies": [
                {"content_type": "text", "title": "🚆 Northbound (To EDSA)", "payload": "QUERY_mrt3_taft_nb"},
                {"content_type": "text", "title": "🚆 Southbound Terminal", "payload": "QUERY_mrt3_taft_sb"}
            ]
        }
    }
    requests.post(url, json=payload, timeout=5)

def send_guadalupe_menu(recipient_id):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": "📍 *Which Guadalupe Station direction are you checking?*",
            "quick_replies": [
                {"content_type": "text", "title": "🚆 Northbound (To North Ave)", "payload": "QUERY_mrt3_guadalupe_nb"},
                {"content_type": "text", "title": "🚆 Southbound (To Taft)", "payload": "QUERY_mrt3_guadalupe_sb"}
            ]
        }
    }
    requests.post(url, json=payload, timeout=5)

def send_simplified_buttons(recipient_id, text, station_id):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {"type": "postback", "title": "🟢 Light", "payload": f"VOTE_LIGHT_{station_id}"},
                        {"type": "postback", "title": "🟡 Medium", "payload": f"VOTE_MEDIUM_{station_id}"},
                        {"type": "postback", "title": "🔴 Heavy", "payload": f"VOTE_HEAVY_{station_id}"}
                    ]
                }
            }
        }
    }
    requests.post(url, json=payload, timeout=5)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
