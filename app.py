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
crowdsourced_votes = {}       # {"station_id": {"light": X, "medium": Y, "heavy": Z, "last_updated": datetime}}
user_vote_timestamps = {}     # {user_id: timestamp}
processed_message_ids = {}    # {message_id: timestamp}

# API Smart Caching: {"coords": {"speed": X, "timestamp": datetime}}
traffic_cache = {}

STATION_PROFILES = {
    # === MRT-3 LINE ===
    "mrt3_north_ave_nb": {"name": "🚆 MRT-3 North Avenue (Northbound End Terminal)", "is_interchange": True, "coords": "14.6531,121.0307"},
    "mrt3_north_ave_sb": {"name": "🚆 MRT-3 North Avenue (Southbound → Taft)", "is_interchange": True, "coords": "14.6531,121.0307"},
    "mrt3_quezon_ave_nb": {"name": "🚆 MRT-3 Quezon Avenue (Northbound → North Ave)", "is_interchange": False, "coords": "14.6425,121.0385"},
    "mrt3_quezon_ave_sb": {"name": "🚆 MRT-3 Quezon Avenue (Southbound → Taft)", "is_interchange": False, "coords": "14.6425,121.0385"},
    "mrt3_kamuning_nb": {"name": "🚆 MRT-3 GMA Kamuning (Northbound → North Ave)", "is_interchange": False, "coords": "14.6352,121.0435"},
    "mrt3_kamuning_sb": {"name": "🚆 MRT-3 GMA Kamuning (Southbound → Taft)", "is_interchange": False, "coords": "14.6352,121.0435"},
    "mrt3_cubao_nb": {"name": "🚆 MRT-3 Cubao (Northbound → North Ave)", "is_interchange": True, "coords": "14.6195,121.0511"},
    "mrt3_cubao_sb": {"name": "🚆 MRT-3 Cubao (Southbound → Taft)", "is_interchange": True, "coords": "14.6195,121.0511"},
    "mrt3_santolan_nb": {"name": "🚆 MRT-3 Santolan-Annapolis (Northbound → North Ave)", "is_interchange": False, "coords": "14.6078,121.0565"},
    "mrt3_santolan_sb": {"name": "🚆 MRT-3 Santolan-Annapolis (Southbound → Taft)", "is_interchange": False, "coords": "14.6078,121.0565"},
    "mrt3_ortigas_nb": {"name": "🚆 MRT-3 Ortigas (Northbound → North Ave)", "is_interchange": False, "coords": "14.5878,121.0567"},
    "mrt3_ortigas_sb": {"name": "🚆 MRT-3 Ortigas (Southbound → Taft)", "is_interchange": False, "coords": "14.5878,121.0567"},
    "mrt3_shaw_nb": {"name": "🚆 MRT-3 Shaw Boulevard (Northbound → North Ave)", "is_interchange": False, "coords": "14.5813,121.0536"},
    "mrt3_shaw_sb": {"name": "🚆 MRT-3 Shaw Boulevard (Southbound → Taft)", "is_interchange": False, "coords": "14.5813,121.0536"},
    "mrt3_boni_nb": {"name": "🚆 MRT-3 Boni (Northbound → North Ave)", "is_interchange": False, "coords": "14.5739,121.0481"},
    "mrt3_boni_sb": {"name": "🚆 MRT-3 Boni (Southbound → Taft)", "is_interchange": False, "coords": "14.5739,121.0481"},
    "mrt3_guadalupe_nb": {"name": "🚆 MRT-3 Guadalupe (Northbound → North Ave)", "is_interchange": False, "coords": "14.5672,121.0456"},
    "mrt3_guadalupe_sb": {"name": "🚆 MRT-3 Guadalupe (Southbound → Taft)", "is_interchange": False, "coords": "14.5672,121.0456"},
    "mrt3_buendia_nb": {"name": "🚆 MRT-3 Buendia (Northbound → North Ave)", "is_interchange": False, "coords": "14.5542,121.0343"},
    "mrt3_buendia_sb": {"name": "🚆 MRT-3 Buendia (Southbound → Taft)", "is_interchange": False, "coords": "14.5542,121.0343"},
    "mrt3_ayala_nb": {"name": "🚆 MRT-3 Ayala (Northbound → North Ave)", "is_interchange": True, "coords": "14.5494,121.0279"},
    "mrt3_ayala_sb": {"name": "🚆 MRT-3 Ayala (Southbound → Taft)", "is_interchange": True, "coords": "14.5494,121.0279"},
    "mrt3_magallanes_nb": {"name": "🚆 MRT-3 Magallanes (Northbound → North Ave)", "is_interchange": True, "coords": "14.5421,121.0195"},
    "mrt3_magallanes_sb": {"name": "🚆 MRT-3 Magallanes (Southbound → Taft)", "is_interchange": True, "coords": "14.5421,121.0195"},
    "mrt3_taft_nb": {"name": "🚆 MRT-3 Taft Avenue (Northbound → North Ave)", "is_interchange": True, "coords": "14.5376,121.0014"},
    "mrt3_taft_sb": {"name": "🚆 MRT-3 Taft Avenue (Southbound End Terminal)", "is_interchange": True, "coords": "14.5376,121.0014"},

    # === LRT-2 LINE ===
    "lrt2_antipolo_eb": {"name": "🚇 LRT-2 Antipolo (Eastbound End Terminal)", "is_interchange": False, "coords": "14.6241,121.1214"},
    "lrt2_antipolo_wb": {"name": "🚇 LRT-2 Antipolo (Westbound → Recto)", "is_interchange": False, "coords": "14.6241,121.1214"},
    "lrt2_marikina_eb": {"name": "🚇 LRT-2 Marikina-Pasig (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6191,121.1002"},
    "lrt2_marikina_wb": {"name": "🚇 LRT-2 Marikina-Pasig (Westbound → Recto)", "is_interchange": False, "coords": "14.6191,121.1002"},
    "lrt2_santolan_eb": {"name": "🚇 LRT-2 Santolan (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6219,121.0858"},
    "lrt2_santolan_wb": {"name": "🚇 LRT-2 Santolan (Westbound → Recto)", "is_interchange": False, "coords": "14.6219,121.0858"},
    "lrt2_katipunan_eb": {"name": "🚇 LRT-2 Katipunan (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6309,121.0726"},
    "lrt2_katipunan_wb": {"name": "🚇 LRT-2 Katipunan (Westbound → Recto)", "is_interchange": False, "coords": "14.6309,121.0726"},
    "lrt2_anonas_eb": {"name": "🚇 LRT-2 Anonas (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6281,121.0642"},
    "lrt2_anonas_wb": {"name": "🚇 LRT-2 Anonas (Westbound → Recto)", "is_interchange": False, "coords": "14.6281,121.0642"},
    "lrt2_cubao_eb": {"name": "🚇 LRT-2 Cubao (Eastbound → Antipolo)", "is_interchange": True, "coords": "14.6226,121.0526"},
    "lrt2_cubao_wb": {"name": "🚇 LRT-2 Cubao (Westbound → Recto)", "is_interchange": True, "coords": "14.6226,121.0526"},
    "lrt2_betty_go_eb": {"name": "🚇 LRT-2 Betty Go-Belmonte (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6186,121.0427"},
    "lrt2_betty_go_wb": {"name": "🚇 LRT-2 Betty Go-Belmonte (Westbound → Recto)", "is_interchange": False, "coords": "14.6186,121.0427"},
    "lrt2_gilmore_eb": {"name": "🚇 LRT-2 Gilmore (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6135,121.0343"},
    "lrt2_gilmore_wb": {"name": "🚇 LRT-2 Gilmore (Westbound → Recto)", "is_interchange": False, "coords": "14.6135,121.0343"},
    "lrt2_j_ruiz_eb": {"name": "🚇 LRT-2 J. Ruiz (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6105,121.0264"},
    "lrt2_j_ruiz_wb": {"name": "🚇 LRT-2 J. Ruiz (Westbound → Recto)", "is_interchange": False, "coords": "14.6105,121.0264"},
    "lrt2_v_mapa_eb": {"name": "🚇 LRT-2 V. Mapa (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6042,121.0121"},
    "lrt2_v_mapa_wb": {"name": "🚇 LRT-2 V. Mapa (Westbound → Recto)", "is_interchange": False, "coords": "14.6042,121.0121"},
    "lrt2_pureza_eb": {"name": "🚇 LRT-2 Pureza (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6014,121.0053"},
    "lrt2_pureza_wb": {"name": "🚇 LRT-2 Pureza (Westbound → Recto)", "is_interchange": False, "coords": "14.6014,121.0053"},
    "lrt2_legarda_eb": {"name": "🚇 LRT-2 Legarda (Eastbound → Antipolo)", "is_interchange": False, "coords": "14.6008,120.9922"},
    "lrt2_legarda_wb": {"name": "🚇 LRT-2 Legarda (Westbound → Recto)", "is_interchange": False, "coords": "14.6008,120.9922"},
    "lrt2_recto_eb": {"name": "🚇 LRT-2 Recto (Eastbound → Antipolo)", "is_interchange": True, "coords": "14.6038,120.9831"},
    "lrt2_recto_wb": {"name": "🚇 LRT-2 Recto (Westbound End Terminal)", "is_interchange": True, "coords": "14.6038,120.9831"},

    # === LRT-1 LINE ===
    "lrt1_fpj_nb": {"name": "🟢 LRT-1 Fernando Poe Jr. (Northbound End Terminal)", "is_interchange": False, "coords": "14.6575,121.0211"},
    "lrt1_fpj_sb": {"name": "🟢 LRT-1 Fernando Poe Jr. (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6575,121.0211"},
    "lrt1_balintawak_nb": {"name": "🟢 LRT-1 Balintawak (Northbound → FPJ)", "is_interchange": False, "coords": "14.6504,121.0011"},
    "lrt1_balintawak_sb": {"name": "🟢 LRT-1 Balintawak (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6504,121.0011"},
    "lrt1_monumento_nb": {"name": "🟢 LRT-1 Monumento (Northbound → FPJ)", "is_interchange": False, "coords": "14.6542,120.9839"},
    "lrt1_monumento_sb": {"name": "🟢 LRT-1 Monumento (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6542,120.9839"},
    "lrt1_5th_ave_nb": {"name": "🟢 LRT-1 5th Avenue (Northbound → FPJ)", "is_interchange": False, "coords": "14.6444,120.9834"},
    "lrt1_5th_ave_sb": {"name": "🟢 LRT-1 5th Avenue (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6444,120.9834"},
    "lrt1_r_papa_nb": {"name": "🟢 LRT-1 R. Papa (Northbound → FPJ)", "is_interchange": False, "coords": "14.6361,120.9831"},
    "lrt1_r_papa_sb": {"name": "🟢 LRT-1 R. Papa (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6361,120.9831"},
    "lrt1_abad_santos_nb": {"name": "🟢 LRT-1 Abad Santos (Northbound → FPJ)", "is_interchange": False, "coords": "14.6305,120.9825"},
    "lrt1_abad_santos_sb": {"name": "🟢 LRT-1 Abad Santos (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6305,120.9825"},
    "lrt1_blumentritt_nb": {"name": "🟢 LRT-1 Blumentritt (Northbound → FPJ)", "is_interchange": True, "coords": "14.6226,120.9828"},
    "lrt1_blumentritt_sb": {"name": "🟢 LRT-1 Blumentritt (Southbound → Dr. Santos)", "is_interchange": True, "coords": "14.6226,120.9828"},
    "lrt1_tayuman_nb": {"name": "🟢 LRT-1 Tayuman (Northbound → FPJ)", "is_interchange": False, "coords": "14.6167,120.9825"},
    "lrt1_tayuman_sb": {"name": "🟢 LRT-1 Tayuman (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6167,120.9825"},
    "lrt1_bambang_nb": {"name": "🟢 LRT-1 Bambang (Northbound → FPJ)", "is_interchange": False, "coords": "14.6111,120.9822"},
    "lrt1_bambang_sb": {"name": "🟢 LRT-1 Bambang (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.6111,120.9822"},
    "lrt1_d_jose_nb": {"name": "🟢 LRT-1 Doroteo Jose (Northbound → FPJ)", "is_interchange": True, "coords": "14.6055,120.9819"},
    "lrt1_d_jose_sb": {"name": "🟢 LRT-1 Doroteo Jose (Southbound → Dr. Santos)", "is_interchange": True, "coords": "14.6055,120.9819"},
    "lrt1_carriedo_nb": {"name": "🟢 LRT-1 Carriedo (Northbound → FPJ)", "is_interchange": False, "coords": "14.5997,120.9814"},
    "lrt1_carriedo_sb": {"name": "🟢 LRT-1 Carriedo (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5997,120.9814"},
    "lrt1_central_nb": {"name": "🟢 LRT-1 Central Terminal (Northbound → FPJ)", "is_interchange": False, "coords": "14.5928,120.9817"},
    "lrt1_central_sb": {"name": "🟢 LRT-1 Central Terminal (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5928,120.9817"},
    "lrt1_un_ave_nb": {"name": "🟢 LRT-1 United Nations Avenue (Northbound → FPJ)", "is_interchange": False, "coords": "14.5826,120.9819"},
    "lrt1_un_ave_sb": {"name": "🟢 LRT-1 United Nations Avenue (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5826,120.9819"},
    "lrt1_pedro_gil_nb": {"name": "🟢 LRT-1 Pedro Gil (Northbound → FPJ)", "is_interchange": False, "coords": "14.5769,120.9881"},
    "lrt1_pedro_gil_sb": {"name": "🟢 LRT-1 Pedro Gil (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5769,120.9881"},
    "lrt1_quirino_nb": {"name": "🟢 LRT-1 Quirino Avenue (Northbound → FPJ)", "is_interchange": False, "coords": "14.5701,120.9914"},
    "lrt1_quirino_sb": {"name": "🟢 LRT-1 Quirino Avenue (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5701,120.9914"},
    "lrt1_vito_cruz_nb": {"name": "🟢 LRT-1 Vito Cruz (Northbound → FPJ)", "is_interchange": False, "coords": "14.5633,120.9947"},
    "lrt1_vito_cruz_sb": {"name": "🟢 LRT-1 Vito Cruz (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5633,120.9947"},
    "lrt1_gil_puyat_nb": {"name": "🟢 LRT-1 Gil Puyat (Northbound → FPJ)", "is_interchange": True, "coords": "14.5544,120.9969"},
    "lrt1_gil_puyat_sb": {"name": "🟢 LRT-1 Gil Puyat (Southbound → Dr. Santos)", "is_interchange": True, "coords": "14.5544,120.9969"},
    "lrt1_libertad_nb": {"name": "🟢 LRT-1 Libertad (Northbound → FPJ)", "is_interchange": False, "coords": "14.5476,120.9986"},
    "lrt1_libertad_sb": {"name": "🟢 LRT-1 Libertad (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5476,120.9986"},
    "lrt1_edsa_nb": {"name": "🟢 LRT-1 EDSA-Taft Avenue (Northbound → FPJ)", "is_interchange": True, "coords": "14.5386,121.0011"},
    "lrt1_edsa_sb": {"name": "🟢 LRT-1 EDSA-Taft Avenue (Southbound → Dr. Santos)", "is_interchange": True, "coords": "14.5386,121.0011"},
    "lrt1_baclaran_nb": {"name": "🟢 LRT-1 Baclaran (Northbound → FPJ)", "is_interchange": False, "coords": "14.5283,120.9981"},
    "lrt1_baclaran_sb": {"name": "🟢 LRT-1 Baclaran (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5283,120.9981"},
    "lrt1_redemptorist_nb": {"name": "🟢 LRT-1 Redemptorist-Aseana (Northbound → FPJ)", "is_interchange": False, "coords": "14.5195,120.9967"},
    "lrt1_redemptorist_sb": {"name": "🟢 LRT-1 Redemptorist-Aseana (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5195,120.9967"},
    "lrt1_mia_road_nb": {"name": "🟢 LRT-1 MIA Road (Northbound → FPJ)", "is_interchange": False, "coords": "14.5097,120.9953"},
    "lrt1_mia_road_sb": {"name": "🟢 LRT-1 MIA Road (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.5097,120.9953"},
    "lrt1_asia_world_nb": {"name": "🟢 LRT-1 Asia World (Northbound → FPJ)", "is_interchange": True, "coords": "14.5019,120.9939"},
    "lrt1_asia_world_sb": {"name": "🟢 LRT-1 Asia World (Southbound → Dr. Santos)", "is_interchange": True, "coords": "14.5019,120.9939"},
    "lrt1_ninoy_aquino_nb": {"name": "🟢 LRT-1 Ninoy Aquino (Northbound → FPJ)", "is_interchange": False, "coords": "14.4933,120.9925"},
    "lrt1_ninoy_aquino_sb": {"name": "🟢 LRT-1 Ninoy Aquino (Southbound → Dr. Santos)", "is_interchange": False, "coords": "14.4933,120.9925"},
    "lrt1_dr_santos_nb": {"name": "🟢 LRT-1 Dr. Santos (Northbound → FPJ)", "is_interchange": False, "coords": "14.4792,120.9958"},
    "lrt1_dr_santos_sb": {"name": "🟢 LRT-1 Dr. Santos (Southbound End Terminal)", "is_interchange": False, "coords": "14.4792,120.9958"},
}

PH_HOLIDAYS = ["2026-06-12", "2026-08-31", "2026-11-01", "2026-12-25", "2026-12-30"]

# --- DATA FUSION MODIFIERS & API MONITORING ---

def get_weather_data(coords):
    """Fetches real-time weather text description and impact score for specific station coordinates."""
    try:
        lat, lon = coords.split(",")
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=3).json()
        
        condition = res.get("weather", [{}])[0].get("main", "Clear")
        description = res.get("weather", [{}])[0].get("description", "clear sky").capitalize()
        temp = round(res.get("main", {}).get("temp", 30))
        
        impact = 15 if condition in ["Rain", "Thunderstorm", "Drizzle"] else 0
        weather_text = f"{description} ({temp}°C)"
        
        return impact, weather_text
    except Exception:
        return 0, "Data Unavailable"

def get_traffic_impact(coords):
    """Checks cache first. Calls TomTom API only once every 5 minutes per set of coordinates."""
    now = datetime.now()
    if coords in traffic_cache:
        cached_speed, timestamp = traffic_cache[coords]
        if (now - timestamp).total_seconds() < 300:
            return parse_speed_to_score(cached_speed)
            
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_API_KEY}&point={coords}"
        res = requests.get(url, timeout=3).json()
        speed = res.get("flowSegmentData", {}).get("currentSpeed", 30)
        traffic_cache[coords] = (speed, now)
        return parse_speed_to_score(speed)
    except Exception: pass
    return 0

def parse_speed_to_score(speed):
    if speed <= 8: return 20
    elif speed <= 15: return 10
    return 0

def enforce_cache_decay(station_id):
    now = datetime.now()
    if station_id in crowdsourced_votes:
        last_updated = crowdsourced_votes[station_id]["last_updated"]
        if (now - last_updated).total_seconds() > 900:
            del crowdsourced_votes[station_id]

def clean_old_message_ids():
    now = datetime.now()
    expired_ids = [msg_id for msg_id, t in processed_message_ids.items() if (now - t).total_seconds() > 300]
    for msg_id in expired_ids: del processed_message_ids[msg_id]

def calculate_density(station_id, pht_now, weather_impact):
    enforce_cache_decay(station_id)
    profile = STATION_PROFILES.get(station_id)
    if not profile: return "🟢 LIGHT PLATFORM"
    
    score = 0
    hour = pht_now.hour
    day = pht_now.weekday()
    date_str = pht_now.strftime("%Y-%m-%d")

    # 1. Historical Directional Vectors
    if "mrt3_" in station_id or "lrt1_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_sb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_nb"): score += 30
    elif "lrt2_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_wb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_eb"): score += 30
        
    if profile["is_interchange"]: score += 10

    # 2. Calendar Anomalies
    if (pht_now.day in [14, 15, 30, 31]) and day == 4: score += 25
    elif date_str in PH_HOLIDAYS: score += 20

    # 3. Environmental APIs Integration
    score += weather_impact
    score += get_traffic_impact(profile["coords"])

    # 4. Crowdsourced Vectors
    if station_id in crowdsourced_votes:
        v = crowdsourced_votes[station_id]
        total = v["light"] + v["medium"] + v["heavy"]
        if total > 0:
            score += ((v["medium"] * 15) + (v["heavy"] * 35)) / total

    if score >= 60: return "🔴 HEAVY CONGESTION"
    elif score >= 35: return "🟡 MEDIUM CONGESTION"
    return "🟢 LIGHT PLATFORM"

# --- SYSTEM ROUTERS ---

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
                
                msg_id = None
                if event.get("message"):
                    msg_id = event["message"].get("mid")
                elif event.get("postback"):
                    msg_id = f"PB_{event['postback'].get('timestamp')}_{sender_id}"
                
                if msg_id:
                    if msg_id in processed_message_ids:
                        return "DUPLICATE_IGNORED", 200
                    processed_message_ids[msg_id] = datetime.now()

                clean_old_message_ids()

                if event.get("postback"):
                    handle_postback(sender_id, event["postback"]["payload"])
                elif event.get("message") and event["message"].get("text"):
                    handle_message(sender_id, event["message"]["text"].lower().strip())
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

def handle_message(user_id, text):
    pht = timezone("Asia/Manila")
    now = datetime.now(pht)
    
    if now.hour < 5 or (now.hour == 22 and now.minute > 30) or now.hour > 22:
        send_text(user_id, "🌙 *Train lines are currently closed.*\n\nOperating Hours: 5:00 AM - 10:30 PM PHT.")
        return

    matched_stations = []
    cleaned_text = text.replace("station", "").replace("stn", "").strip()
    
    for key, data in STATION_PROFILES.items():
        clean_station_name = data["name"].lower()
        if cleaned_text in clean_station_name and len(cleaned_text) >= 3:
            base_key = "_".join(key.split("_")[:-1])
            if base_key not in matched_stations:
                matched_stations.append(base_key)

    if matched_stations:
        send_direction_menu(user_id, matched_stations[0])
        return

    send_text(user_id, "👋 Welcome to Siksikan AI!\n\nType any active station name from LRT-1, LRT-2, or MRT-3 to verify platform congestion conditions and live local weather details (e.g., 'Guadalupe', 'Gil Puyat', 'Recto').")

def handle_postback(user_id, payload):
    pht = timezone("Asia/Manila")
    now = datetime.now(pht)
    
    if payload.startswith("QUERY_"):
        station_key = payload.replace("QUERY_", "")
        deliver_dashboard(user_id, station_key, now)
        
    elif payload.startswith("VOTE_"):
        if user_id in user_vote_timestamps:
            if (datetime.now() - user_vote_timestamps[user_id]).total_seconds() < 900:
                send_text(user_id, "🔒 Your crowdsourced platform vote has already been submitted recently!")
                return
        
        parts = payload.split("_")
        tier = parts[1].lower()
        station_id = "_".join(parts[2:])
        
        if station_id not in crowdsourced_votes:
            crowdsourced_votes[station_id] = {"light": 0, "medium": 0, "heavy": 0, "last_updated": datetime.now()}
        
        crowdsourced_votes[station_id][tier] += 1
        crowdsourced_votes[station_id]["last_updated"] = datetime.now()
        user_vote_timestamps[user_id] = datetime.now()
        
        send_text(user_id, "✅ Thank you! Your real-time platform vote has been saved.")

def deliver_dashboard(user_id, station_key, current_time):
    profile = STATION_PROFILES[station_key]
    name = profile["name"]
    
    # 1. Fetch station-specific hyper-local weather
    weather_impact, weather_condition = get_weather_data(profile["coords"])
    
    # 2. Feed the calculation engine
    status = calculate_density(station_key, current_time, weather_impact)
    
    msg = (
        f"📊 *Siksikan AI Live Dashboard*\n\n"
        f"📍 Location: {name}\n"
        f"🚦 Status: {status}\n"
        f"🌤️ Weather: {weather_condition}\n\n"
        f"Help your fellow commuters! If you are standing at the platform right now, verify conditions by choosing below:"
    )
    send_simplified_buttons(user_id, msg, station_key)

def send_text(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}}, timeout=5)

def send_direction_menu(recipient_id, base_station_key):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    
    if "lrt2" in base_station_key:
        title_1, key_1 = "🚇 Eastbound Platform", f"QUERY_{base_station_key}_eb"
        title_2, key_2 = "🚇 Westbound Platform", f"QUERY_{base_station_key}_wb"
    else:
        title_1, key_1 = "🚆 Northbound Platform", f"QUERY_{base_station_key}_nb"
        title_2, key_2 = "🚆 Southbound Platform", f"QUERY_{base_station_key}_sb"

    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": "📍 *Select Your Platform Direction:*",
            "quick_replies": [
                {"content_type": "text", "title": title_1, "payload": key_1},
                {"content_type": "text", "title": title_2, "payload": key_2}
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
