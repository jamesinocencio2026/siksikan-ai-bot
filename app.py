import os
from datetime import datetime, timedelta
import pytz
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# =====================================================================
# SYSTEM ACCESS KEYS (Updated in Part 4!)
# =====================================================================
PAGE_ACCESS_TOKEN = "PASTE_YOUR_SECRET_META_TOKEN_HERE"
VERIFY_TOKEN = "SiksikanAIBayanihan2026"

# =====================================================================
# MASTER TRANSIT & ADVERTISING ARCHITECTURE
# =====================================================================
TRANSIT_SYSTEM = {
    "mrt3": {
        "name": "MRT-3 (EDSA Line)",
        "stations": {
            "cubao": {
                "status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1,
                "ad": "Don't sweat the rush! The team at Jollibee Farmers Plaza (Level 2) is ready to serve you your favorite Chickenjoy right outside the platform exits. 🐝"
            },
            "guadalupe": {
                "status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1,
                "ad": "Skip the heat! Grab an ice-cold beverage and relax at Macao Imperial Tea right beside the North station stairs. 🧋"
            },
            "taft": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""},
            "shaw": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""}
        }
    },
    "lrt2": {
        "name": "LRT-2 (Antipolo-Recto Line)",
        "stations": {
            "cubao": {
                "status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1,
                "ad": "Beat the crowd! Gateway Mall 2 restaurants are open for dinner right outside the concourse bridge exit. 🍽️"
            },
            "recto": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""},
            "katipunan": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""}
        }
    },
    "lrt1": {
        "name": "LRT-1 (Baclaran-FPJ Line)",
        "stations": {
            "edsa": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""},
            "doroteo jose": {"status": "🟢 LIGHT CROWD", "light_votes": [], "medium_votes": [], "heavy_votes": [], "camera_score": 1, "ad": ""}
        }
    }
}

def is_train_operating():
    """Validates operational hours windows (5:00 AM - 10:30 PM PHT)."""
    manila_tz = pytz.timezone('Asia/Manila')
    now_manila = datetime.now(manila_tz)
    current_time = now_manila.time()
    start_time = datetime.strptime("05:00:00", "%H:%M:%S").time()
    end_time = datetime.strptime("22:30:00", "%H:%M:%S").time()
    return start_time <= current_time <= end_time

def clear_expired_votes(line_id, station_name):
    """Wipes out any passenger votes older than 60 minutes to maintain accuracy."""
    manila_tz = pytz.timezone('Asia/Manila')
    now = datetime.now(manila_tz)
    cutoff_time = now - timedelta(hours=1)
    
    station_cabinet = TRANSIT_SYSTEM[line_id]["stations"][station_name]
    station_cabinet["light_votes"] = [t for t in station_cabinet["light_votes"] if t > cutoff_time]
    station_cabinet["medium_votes"] = [t for t in station_cabinet["medium_votes"] if t > cutoff_time]
    station_cabinet["heavy_votes"] = [t for t in station_cabinet["heavy_votes"] if t > cutoff_time]

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification token mismatch", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data["entry"]:
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if messaging_event.get("message") and "quick_reply" in messaging_event["message"]:
                    vote_payload = messaging_event["message"]["quick_reply"]["payload"]
                    handle_incoming_vote(sender_id, vote_payload)
                    return "EVENT_RECEIVED", 200
                if messaging_event.get("message") and "text" in messaging_event["message"]:
                    user_text = messaging_event["message"]["text"].lower().strip()
                    process_and_reply(sender_id, user_text)
    return "EVENT_RECEIVED", 200

def process_and_reply(sender_id, user_text):
    if not is_train_operating():
        reply_text = (
            "🌙 **Train lines are currently closed.**\n\n"
            "Operating Hours: 5:00 AM - 10:30 PM PHT.\n\n"
            "💡 **Siksikan AI Alternative:** The 24/7 EDSA Carousel Bus line "
            "is operating outside major stations to keep your transit active!"
        )
        send_to_messenger(sender_id, reply_text)
        return

    if "cubao" in user_text:
        if "mrt" in user_text or "mrt3" in user_text: send_station_status(sender_id, "mrt3", "cubao")
        elif "lrt" in user_text or "lrt2" in user_text: send_station_status(sender_id, "lrt2", "cubao")
        else: send_clarification_menu(sender_id, "cubao")
        return

    if "edsa" in user_text or "taft" in user_text:
        if "mrt" in user_text: send_station_status(sender_id, "mrt3", "taft")
        elif "lrt" in user_text or "lrt1" in user_text: send_station_status(sender_id, "lrt1", "edsa")
        else: send_clarification_menu(sender_id, "taft_edsa_interchange")
        return

    for line_id, line_info in TRANSIT_SYSTEM.items():
        for station_name in line_info["stations"].keys():
            if station_name in user_text:
                send_station_status(sender_id, line_id, station_name)
                return

    fallback_prompt = (
        "Welcome to **Siksikan AI** 🚆 Which station would you like to check?\n\n"
        "Please specify both the Line Name and Station Name for instant results.\n\n"
        "💡 Examples: 'MRT Cubao', 'LRT Katipunan', 'MRT Guadalupe'"
    )
    send_to_messenger(sender_id, fallback_prompt)

def send_station_status(sender_id, line_id, station_name):
    clear_expired_votes(line_id, station_name)
    line_title = TRANSIT_SYSTEM[line_id]["name"]
    info = TRANSIT_SYSTEM[line_id]["stations"][station_name]
    
    l_count = len(info["light_votes"])
    m_count = len(info["medium_votes"])
    h_count = len(info["heavy_votes"])
    
    response_text = (
        f"📍 **{line_title} - {station_name.upper()} STATION**\n\n"
        f"Crowd Status: {info['status']}\n\n"
        f"🗳️ **Active Live Votes (Last 60 Mins):**\n"
        f"• Light Reports: {l_count}\n"
        f"• Medium Reports: {m_count}\n"
        f"• Heavy Reports: {h_count}\n"
    )
    
    # Injection of clean B2B sponsor advertisement branding text
    ad_text = info.get("ad", "")
    if ad_text:
        response_text += f"\n📢 **Sponsor:** {ad_text}\n"
        
    response_text += f"\nAre you at this station now? Help fellow commuters by voting below:"
    
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": sender_id}, "messaging_type": "RESPONSE",
        "message": {
            "text": response_text,
            "quick_replies": [
                {"content_type": "text", "title": "Report Light 🟢", "payload": f"vote_light_{line_id}_{station_name}"},
                {"content_type": "text", "title": "Report Medium 🟡", "payload": f"vote_medium_{line_id}_{station_name}"},
                {"content_type": "text", "title": "Report Heavy 🔴", "payload": f"vote_heavy_{line_id}_{station_name}"}
            ]
        }
    }
    requests.post(url, json=payload)

def send_clarification_menu(sender_id, duplicate_type):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    if duplicate_type == "cubao":
        payload = {
            "recipient": {"id": sender_id}, "messaging_type": "RESPONSE",
            "message": {
                "text": "Which 'Cubao' Station do you mean?",
                "quick_replies": [
                    {"content_type": "text", "title": "MRT-3 Cubao (EDSA)", "payload": "mrt3_cubao"},
                    {"content_type": "text", "title": "LRT-2 Cubao (Aurora)", "payload": "lrt2_cubao"}
                ]
            }
        }
    else:
        payload = {
            "recipient": {"id": sender_id}, "messaging_type": "RESPONSE",
            "message": {
                "text": "Which line at the Pasay Rotonda interchange do you mean?",
                "quick_replies": [
                    {"content_type": "text", "title": "MRT-3 Taft Station", "payload": "mrt3_taft"},
                    {"content_type": "text", "title": "LRT-1 EDSA Station", "payload": "lrt1_edsa"}
                ]
            }
        }
    requests.post(url, json=payload)

def handle_incoming_vote(sender_id, payload):
    parts = payload.split("_")
    if len(parts) < 4: return
    vote_type, line_id, station_name = parts[1], parts[2], parts[3]
    station_cabinet = TRANSIT_SYSTEM[line_id]["stations"][station_name]
    
    manila_tz = pytz.timezone('Asia/Manila')
    timestamp_now = datetime.now(manila_tz)
    
    if vote_type == "light": station_cabinet["light_votes"].append(timestamp_now)
    elif vote_type == "medium": station_cabinet["medium_votes"].append(timestamp_now)
    elif vote_type == "heavy": station_cabinet["heavy_votes"].append(timestamp_now)

    recalculate_station_status(line_id, station_name)
    send_to_messenger(sender_id, "Thank you for reporting! 🗳️ Your vote has been added. Travel safely!")

@app.route("/update_camera", methods=["POST"])
def update_camera():
    data = request.get_json()
    if data.get("secret_key") != "SiksikanAICameraSecure2026":
        return jsonify({"error": "Unauthorized"}), 403
        
    line_id, station_name, new_score = data.get("line_id"), data.get("station"), int(data.get("score"))
    if line_id in TRANSIT_SYSTEM and station_name in TRANSIT_SYSTEM[line_id]["stations"]:
        station_cabinet = TRANSIT_SYSTEM[line_id]["stations"][station_name]
        
        # Freshness Fix: Wipe stale user arrays if camera notes a crowd shift
        if station_cabinet["camera_score"] != new_score:
            station_cabinet["light_votes"], station_cabinet["medium_votes"], station_cabinet["heavy_votes"] = [], [], []
            
        station_cabinet["camera_score"] = new_score
        recalculate_station_status(line_id, station_name)
        return jsonify({"status": "Success"}), 200
    return jsonify({"error": "Not Found"}), 404

def recalculate_station_status(line_id, station_name):
    clear_expired_votes(line_id, station_name)
    station_cabinet = TRANSIT_SYSTEM[line_id]["stations"][station_name]
    cctv_base_score = station_cabinet["camera_score"]
    l_v, m_v, h_v = len(station_cabinet["light_votes"]), len(station_cabinet["medium_votes"]), len(station_cabinet["heavy_votes"])
    total_human_votes = l_v + m_v + h_v
    
    if total_human_votes == 0:
        if cctv_base_score == 3:   station_cabinet["status"] = "🔴 HEAVY CROWD"
        elif cctv_base_score == 2: station_cabinet["status"] = "🟡 MEDIUM CROWD"
        else:                      station_cabinet["status"] = "🟢 LIGHT CROWD"
        return

    total_points = (cctv_base_score) + (l_v * 1) + (m_v * 2) + (h_v * 3)
    weighted_average = total_points / (1 + total_human_votes)
    
    if weighted_average >= 2.34:   station_cabinet["status"] = "🔴 HEAVY CROWD"
    elif weighted_average >= 1.67: station_cabinet["status"] = "🟡 MEDIUM CROWD"
    else:                          station_cabinet["status"] = "🟢 LIGHT CROWD"

def send_to_messenger(sender_id, text_to_send):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": sender_id}, "message": {"text": text_to_send}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=8080)