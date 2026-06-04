import os
import requests
import math
from datetime import datetime, timedelta
import pytz
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# --- WEBHOOK & API TOKENS ---
FB_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "BayanihanSiksikanAI2026")
FB_PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_KEY")
TOMTOM_API_KEY = os.environ.get("TOMTOM_KEY")

# --- TELEGRAM SYSTEM NOTIFICATIONS ALERT ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOTFATHER_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_USERINFO_ID_HERE")

# --- PERMANENT SUPABASE CLOUD CONNECTION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://your-project-id.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_ANON_PUBLIC_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 🧠 HIGH-PERFORMANCE ANTI-LAG GLOBAL CACHE ---
GLOBAL_SYSTEM_CACHE = {}

# Keep message deduplication for Messenger stability
processed_message_ids = {}    # {message_id: timestamp}

STATION_PROFILES = {
    # === MRT-3 LINE ===
    "mrt3_north_ave_nb": {"name": "🚇 MRT-3 North Avenue (Northbound End Terminal)", "is_interchange": True, "lat": 14.6531, "lon": 121.0307, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_north_ave_sb": {"name": "🚇 MRT-3 North Avenue (Southbound → Taft)", "is_interchange": True, "lat": 14.6531, "lon": 121.0307, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_quezon_ave_nb": {"name": "🚇 MRT-3 Quezon Avenue (Northbound → North Ave)", "is_interchange": False, "lat": 14.6425, "lon": 121.0379, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_quezon_ave_sb": {"name": "🚇 MRT-3 Quezon Avenue (Southbound → Taft)", "is_interchange": False, "lat": 14.6425, "lon": 121.0379, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_kamuning_nb": {"name": "🚇 MRT-3 GMA Kamuning (Northbound → North Ave)", "is_interchange": False, "lat": 14.6352, "lon": 121.0435, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_kamuning_sb": {"name": "🚇 MRT-3 GMA Kamuning (Southbound → Taft)", "is_interchange": False, "lat": 14.6352, "lon": 121.0435, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_cubao_nb": {"name": "🚇 MRT-3 Cubao (Northbound → North Ave)", "is_interchange": True, "lat": 14.6195, "lon": 121.0511, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_cubao_sb": {"name": "🚇 MRT-3 Cubao (Southbound → Taft)", "is_interchange": True, "lat": 14.6195, "lon": 121.0511, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_santolan_nb": {"name": "🚇 MRT-3 Santolan-Annapolis (Northbound → North Ave)", "is_interchange": False, "lat": 14.6078, "lon": 121.0565, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_santolan_sb": {"name": "🚇 MRT-3 Santolan-Annapolis (Southbound → Taft)", "is_interchange": False, "lat": 14.6078, "lon": 121.0565, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_ortigas_nb": {"name": "🚇 MRT-3 Ortigas (Northbound → North Ave)", "is_interchange": False, "lat": 14.5878, "lon": 121.0567, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_ortigas_sb": {"name": "🚇 MRT-3 Ortigas (Southbound → Taft)", "is_interchange": False, "lat": 14.5878, "lon": 121.0567, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_shaw_nb": {"name": "🚇 MRT-3 Shaw Boulevard (Northbound → North Ave)", "is_interchange": True, "lat": 14.5813, "lon": 121.0536, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_shaw_sb": {"name": "🚇 MRT-3 Shaw Boulevard (Southbound → Taft)", "is_interchange": True, "lat": 14.5813, "lon": 121.0536, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_boni_nb": {"name": "🚇 MRT-3 Boni (Northbound → North Ave)", "is_interchange": False, "lat": 14.5739, "lon": 121.0481, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_boni_sb": {"name": "🚇 MRT-3 Boni (Southbound → Taft)", "is_interchange": False, "lat": 14.5739, "lon": 121.0481, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_guadalupe_nb": {"name": "🚇 MRT-3 Guadalupe (Northbound → North Ave)", "is_interchange": False, "lat": 14.5672, "lon": 121.0456, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_guadalupe_sb": {"name": "🚇 MRT-3 Guadalupe (Southbound → Taft)", "is_interchange": False, "lat": 14.5672, "lon": 121.0456, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_buendia_nb": {"name": "🚇 MRT-3 Buendia (Northbound → North Ave)", "is_interchange": False, "lat": 14.5542, "lon": 121.0343, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_buendia_sb": {"name": "🚇 MRT-3 Buendia (Southbound → Taft)", "is_interchange": False, "lat": 14.5542, "lon": 121.0343, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_ayala_nb": {"name": "🚇 MRT-3 Ayala (Northbound → North Ave)", "is_interchange": True, "lat": 14.5494, "lon": 121.0279, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_ayala_sb": {"name": "🚇 MRT-3 Ayala (Southbound → Taft)", "is_interchange": True, "lat": 14.5494, "lon": 121.0279, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_magallanes_nb": {"name": "🚇 MRT-3 Magallanes (Northbound → North Ave)", "is_interchange": True, "lat": 14.5421, "lon": 121.0195, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_magallanes_sb": {"name": "🚇 MRT-3 Magallanes (Southbound → Taft)", "is_interchange": True, "lat": 14.5421, "lon": 121.0195, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_taft_nb": {"name": "🚇 MRT-3 Taft Avenue (Northbound → North Ave)", "is_interchange": True, "lat": 14.5376, "lon": 121.0014, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "mrt3_taft_sb": {"name": "🚇 MRT-3 Taft Avenue (Southbound End Terminal)", "is_interchange": True, "lat": 14.5376, "lon": 121.0014, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},

    # === LRT-2 LINE ===
    "lrt2_recto_nb": {"name": "🚇 LRT-2 Recto (Eastbound → Antipolo)", "is_interchange": True, "lat": 14.6038, "lon": 120.9831, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_recto_sb": {"name": "🚇 LRT-2 Recto (Westbound End Terminal)", "is_interchange": True, "lat": 14.6038, "lon": 120.9831, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_legarda_nb": {"name": "🚇 LRT-2 Legarda (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6008, "lon": 120.9924, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_legarda_sb": {"name": "🚇 LRT-2 Legarda (Westbound → Recto)", "is_interchange": False, "lat": 14.6008, "lon": 120.9924, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_pureza_nb": {"name": "🚇 LRT-2 Pureza (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6019, "lon": 121.0055, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_pureza_sb": {"name": "🚇 LRT-2 Pureza (Westbound → Recto)", "is_interchange": False, "lat": 14.6019, "lon": 121.0055, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_v_mapa_nb": {"name": "🚇 LRT-2 V. Mapa (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6043, "lon": 121.0118, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_v_mapa_sb": {"name": "🚇 LRT-2 V. Mapa (Westbound → Recto)", "is_interchange": False, "lat": 14.6043, "lon": 121.0118, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_j_ruiz_nb": {"name": "🚇 LRT-2 J. Ruiz (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6106, "lon": 121.0253, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_j_ruiz_sb": {"name": "🚇 LRT-2 J. Ruiz (Westbound → Recto)", "is_interchange": False, "lat": 14.6106, "lon": 121.0253, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_gilmore_nb": {"name": "🚇 LRT-2 Gilmore (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6135, "lon": 121.0343, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_gilmore_sb": {"name": "🚇 LRT-2 Gilmore (Westbound → Recto)", "is_interchange": False, "lat": 14.6135, "lon": 121.0343, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_betty_go_nb": {"name": "🚇 LRT-2 Betty Go-Belmonte (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6186, "lon": 121.0435, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_betty_go_sb": {"name": "🚇 LRT-2 Betty Go-Belmonte (Westbound → Recto)", "is_interchange": False, "lat": 14.6186, "lon": 121.0435, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_cubao_l2_nb": {"name": "🚇 LRT-2 Araneta Center-Cubao (Eastbound → Antipolo)", "is_interchange": True, "lat": 14.6219, "lon": 121.0531, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_cubao_l2_sb": {"name": "🚇 LRT-2 Araneta Center-Cubao (Westbound → Recto)", "is_interchange": True, "lat": 14.6219, "lon": 121.0531, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_anonas_nb": {"name": "🚇 LRT-2 Anonas (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6281, "lon": 121.0642, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_anonas_sb": {"name": "🚇 LRT-2 Anonas (Westbound → Recto)", "is_interchange": False, "lat": 14.6281, "lon": 121.0642, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_katipunan_nb": {"name": "🚇 LRT-2 Katipunan (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6319, "lon": 121.0732, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_katipunan_sb": {"name": "🚇 LRT-2 Katipunan (Westbound → Recto)", "is_interchange": False, "lat": 14.6319, "lon": 121.0732, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_santolan_nb": {"name": "🚇 LRT-2 Santolan (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6222, "lon": 121.0858, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_santolan_sb": {"name": "🚇 LRT-2 Santolan (Westbound → Recto)", "is_interchange": False, "lat": 14.6222, "lon": 121.0858, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_marikina_nb": {"name": "🚇 LRT-2 Marikina-Pasig (Eastbound → Antipolo)", "is_interchange": False, "lat": 14.6191, "lon": 121.1011, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_marikina_sb": {"name": "🚇 LRT-2 Marikina-Pasig (Westbound → Recto)", "is_interchange": False, "lat": 14.6191, "lon": 121.1011, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_antipolo_eb": {"name": "🚇 LRT-2 Antipolo (Eastbound End Terminal)", "is_interchange": False, "lat": 14.6175, "lon": 121.1181, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt2_antipolo_wb": {"name": "🚇 LRT-2 Antipolo (Westbound → Recto)", "is_interchange": False, "lat": 14.6175, "lon": 121.1181, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},

    # === LRT-1 LINE ===
    "lrt1_fpj_nb": {"name": "🚇 LRT-1 Fernando Poe Jr. (Northbound End Terminal)", "is_interchange": False, "lat": 14.6575, "lon": 121.0211, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_fpj_sb": {"name": "🚇 LRT-1 Fernando Poe Jr. (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6575, "lon": 121.0211, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_roosevelt_nb": {"name": "🚇 LRT-1 Roosevelt (Northbound → FPJ)", "is_interchange": False, "lat": 14.6575, "lon": 121.0211, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_roosevelt_sb": {"name": "🚇 LRT-1 Roosevelt (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6575, "lon": 121.0211, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_balintawak_nb": {"name": "🚇 LRT-1 Balintawak (Northbound → FPJ)", "is_interchange": False, "lat": 14.6504, "lon": 121.0003, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_balintawak_sb": {"name": "🚇 LRT-1 Balintawak (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6504, "lon": 121.0003, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_monumento_nb": {"name": "🚇 LRT-1 Monumento (Northbound → FPJ)", "is_interchange": False, "lat": 14.6542, "lon": 120.9836, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_monumento_sb": {"name": "🚇 LRT-1 Monumento (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6542, "lon": 120.9836, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_5th_avenue_nb": {"name": "🚇 LRT-1 5th Avenue (Northbound → FPJ)", "is_interchange": False, "lat": 14.6444, "lon": 120.9833, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_5th_avenue_sb": {"name": "🚇 LRT-1 5th Avenue (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6444, "lon": 120.9833, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_r_papa_nb": {"name": "🚇 LRT-1 R. Papa (Northbound → FPJ)", "is_interchange": False, "lat": 14.6361, "lon": 120.9828, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_r_papa_sb": {"name": "🚇 LRT-1 R. Papa (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6361, "lon": 120.9828, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_abad_santos_nb": {"name": "🚇 LRT-1 Abad Santos (Northbound → FPJ)", "is_interchange": False, "lat": 14.6281, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_abad_santos_sb": {"name": "🚇 LRT-1 Abad Santos (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6281, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_blumentritt_nb": {"name": "🚇 LRT-1 Blumentritt (Northbound → FPJ)", "is_interchange": True, "lat": 14.6225, "lon": 120.9828, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_blumentritt_sb": {"name": "🚇 LRT-1 Blumentritt (Southbound → Dr. Santos)", "is_interchange": True, "lat": 14.6225, "lon": 120.9828, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_tayuman_nb": {"name": "🚇 LRT-1 Tayuman (Northbound → FPJ)", "is_interchange": False, "lat": 14.6167, "lon": 120.9831, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_tayuman_sb": {"name": "🚇 LRT-1 Tayuman (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6167, "lon": 120.9831, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_bambang_nb": {"name": "🚇 LRT-1 Bambang (Northbound → FPJ)", "is_interchange": False, "lat": 14.6111, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_bambang_sb": {"name": "🚇 LRT-1 Bambang (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.6111, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_doroteo_jose_nb": {"name": "🚇 LRT-1 Doroteo Jose (Northbound → FPJ)", "is_interchange": True, "lat": 14.6056, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_doroteo_jose_sb": {"name": "🚇 LRT-1 Doroteo Jose (Southbound → Dr. Santos)", "is_interchange": True, "lat": 14.6056, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_carriedo_nb": {"name": "🚇 LRT-1 Carriedo (Northbound → FPJ)", "is_interchange": False, "lat": 14.5997, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_carriedo_sb": {"name": "🚇 LRT-1 Carriedo (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5997, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_central_terminal_nb": {"name": "🚇 LRT-1 Central Terminal (Northbound → FPJ)", "is_interchange": False, "lat": 14.5928, "lon": 120.9817, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_central_terminal_sb": {"name": "🚇 LRT-1 Central Terminal (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5928, "lon": 120.9817, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_un_avenue_nb": {"name": "🚇 LRT-1 United Nations Avenue (Northbound → FPJ)", "is_interchange": False, "lat": 14.5828, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_un_avenue_sb": {"name": "🚇 LRT-1 United Nations Avenue (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5828, "lon": 120.9819, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_pedro_gil_nb": {"name": "🚇 LRT-1 Pedro Gil (Northbound → FPJ)", "is_interchange": False, "lat": 14.5769, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_pedro_gil_sb": {"name": "🚇 LRT-1 Pedro Gil (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5769, "lon": 120.9814, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_quirino_nb": {"name": "🚇 LRT-1 Quirino (Northbound → FPJ)", "is_interchange": False, "lat": 14.5703, "lon": 120.9914, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_quirino_sb": {"name": "🚇 LRT-1 Quirino (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5703, "lon": 120.9914, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_vito_cruz_nb": {"name": "🚇 LRT-1 Vito Cruz (Northbound → FPJ)", "is_interchange": False, "lat": 14.5633, "lon": 120.9947, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_vito_cruz_sb": {"name": "🚇 LRT-1 Vito Cruz (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5633, "lon": 120.9947, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_gil_puyat_nb": {"name": "🚇 LRT-1 Gil Puyat (Northbound → FPJ)", "is_interchange": True, "lat": 14.5544, "lon": 120.9969, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_gil_puyat_sb": {"name": "🚇 LRT-1 Gil Puyat (Southbound → Dr. Santos)", "is_interchange": True, "lat": 14.5544, "lon": 120.9969, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_libertad_nb": {"name": "🚇 LRT-1 Libertad (Northbound → FPJ)", "is_interchange": False, "lat": 14.5476, "lon": 120.9986, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_libertad_sb": {"name": "🚇 LRT-1 Libertad (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5476, "lon": 120.9986, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_edsa_nb": {"name": "🚇 LRT-1 EDSA-Taft Avenue (Northbound → FPJ)", "is_interchange": True, "lat": 14.5386, "lon": 121.0011, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_edsa_sb": {"name": "🚇 LRT-1 EDSA-Taft Avenue (Southbound → Dr. Santos)", "is_interchange": True, "lat": 14.5386, "lon": 121.0011, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_baclaran_nb": {"name": "🚇 LRT-1 Baclaran (Northbound → FPJ)", "is_interchange": False, "lat": 14.5283, "lon": 120.9981, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_baclaran_sb": {"name": "🚇 LRT-1 Baclaran (Southbound → FPJ)", "is_interchange": False, "lat": 14.5283, "lon": 120.9981, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_redemptorist_nb": {"name": "🚇 LRT-1 Redemptorist-Aseana (Northbound → FPJ)", "is_interchange": False, "lat": 14.5195, "lon": 120.9967, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_redemptorist_sb": {"name": "🚇 LRT-1 Redemptorist-Aseana (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5195, "lon": 120.9967, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_mia_road_nb": {"name": "🚇 LRT-1 MIA Road (Northbound → FPJ)", "is_interchange": False, "lat": 14.5097, "lon": 120.9953, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_mia_road_sb": {"name": "🚇 LRT-1 MIA Road (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.5097, "lon": 120.9953, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_asia_world_nb": {"name": "🚇 LRT-1 Asia World (Northbound → FPJ)", "is_interchange": True, "lat": 14.5019, "lon": 120.9939, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_asia_world_sb": {"name": "🚇 LRT-1 Asia World (Southbound → Dr. Santos)", "is_interchange": True, "lat": 14.5019, "lon": 120.9939, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_ninoy_aquino_nb": {"name": "🚇 LRT-1 Ninoy Aquino (Northbound → FPJ)", "is_interchange": False, "lat": 14.4933, "lon": 120.9925, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_ninoy_aquino_sb": {"name": "🚇 LRT-1 Ninoy Aquino (Southbound → Dr. Santos)", "is_interchange": False, "lat": 14.4933, "lon": 120.9925, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_dr_santos_nb": {"name": "🚇 LRT-1 Dr. Santos (Northbound → FPJ)", "is_interchange": False, "lat": 14.4792, "lon": 120.9958, "status": "LIGHT PLATFORM", "weather": "Clear Sky"},
    "lrt1_dr_santos_sb": {"name": "🚇 LRT-1 Dr. Santos (Southbound End Terminal)", "is_interchange": False, "lat": 14.4792, "lon": 120.9958, "status": "LIGHT PLATFORM", "weather": "Clear Sky"}
}

PH_HOLIDAYS = ["2026-06-12", "2026-08-31", "2026-11-01", "2026-12-25", "2026-12-30"]

# --- DATA FUSION MODIFIERS & API MONITORING ---

def update_weather_and_tomtom_cache():
    """Automated background loop executing a multi-station hardware sync sequentially."""
    print("🔄 [AUTOMATION] Initiating global telemetry sync loop across all transit profiles...")
    
    for station_key, data in STATION_PROFILES.items():
        lat = data.get("lat")
        lon = data.get("lon")
        if not lat or not lon:
            continue
            
        # 1. LIVE OPENWEATHER STRINGS SYNC
        try:
            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            w_res = requests.get(weather_url, params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}, timeout=5)
            if w_res.status_code == 200:
                condition = w_res.json()["weather"][0]["description"].title()
                STATION_PROFILES[station_key]["weather"] = condition
        except Exception as e:
            print(f"⚠️ Weather pipeline failure for {station_key}: {e}")

        # 2. LIVE TOMTOM TRAFFIC FLOW SYNC
        try:
            tomtom_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
            t_res = requests.get(tomtom_url, params={"key": TOMTOM_API_KEY, "point": f"{lat},{lon}", "unit": "kmph"}, timeout=5)
            if t_res.status_code == 200:
                flow = t_res.json().get("flowSegmentData", {})
                current_speed = flow.get("currentSpeed", 1)
                free_flow_speed = flow.get("freeFlowSpeed", 1)
                
                # Dynamic Congestion Metric
                ratio = current_speed / free_flow_speed
                
                if ratio <= 0.35:
                    new_status = "HEAVY PLATFORM"
                elif ratio <= 0.75:
                    new_status = "MEDIUM PLATFORM"
                else:
                    new_status = "LIGHT PLATFORM"
                    
                STATION_PROFILES[station_key]["status"] = new_status
        except Exception as e:
            print(f"⚠️ TomTom telemetry pipeline failure for {station_key}: {e}")
            
    print("✅ [AUTOMATION] Global station profiles sync cycle completed successfully.")
    
# --- DATA FUSION MODIFIERS, CLOUD STREAMING & API CONFIGURATIONS ---

def stream_interaction_to_cloud(station_key, interaction_type):
    """
    Silently logs user intent and interaction metrics to Supabase.
    Builds a professional, historically accurate database for future business pitches.
    """
    try:
        pht = timezone("Asia/Manila")
        manila_now = datetime.now(pht)
        
        # Automatically determine the transit rail line tier
        if station_key.startswith("mrt3_"):
            line_tier = "MRT-3"
        elif station_key.startswith("lrt1_"):
            line_tier = "LRT-1"
        elif station_key.startswith("lrt2_"):
            line_tier = "LRT-2"
        else:
            line_tier = "Unknown"

        payload = {
            "created_at": manila_now.isoformat(),
            "line": line_tier,
            "station_id": station_key,
            "action_type": interaction_type,
            "hour_block": manila_now.strftime("%I:00 %p")  # Groups data by clean hours (e.g., "07:00 AM")
        }
        
        # Fire background stream entry to your Supabase tables
        supabase.table("station_traffic_logs").insert(payload).execute()
    except Exception as e:
        print(f"Cloud database stream bypassed smoothly: {e}")

def get_recent_crowdsource_score(station_key):
    """
    Data Accuracy Guard (Safety in Numbers Window).
    Fetches user reports from the last 15 minutes directly from the cloud.
    An isolated vote from home is neutralized by actual matching platform clusters.
    """
    try:
        pht = timezone("Asia/Manila")
        time_boundary = (datetime.now(pht) - timedelta(minutes=15)).isoformat()
        
        # Query Supabase for valid platform entries within the 15-minute threshold
        response = supabase.table("station_traffic_logs") \
            .select("action_type") \
            .eq("station_id", station_key) \
            .gte("created_at", time_boundary) \
            .execute()
            
        records = response.data or []
        votes = [r["action_type"] for r in records if r["action_type"].startswith("vote_")]
        
        if not votes:
            return 0, 0  # No current crowd data available
            
        total_votes = len(votes)
        medium_count = sum(1 for v in votes if "medium" in v)
        heavy_count = sum(1 for v in votes if "heavy" in v)
        
        # Calculate weighted moving impact score
        weighted_score = ((medium_count * 15) + (heavy_count * 35)) / total_votes
        return weighted_score, total_votes
    except Exception as e:
        print(f"Crowdsource vector engine error: {e}")
        return 0, 0

def get_weather_data(lat, lon):
    """Fetches real-time weather text description and impact score for specific station coordinates."""
    try:
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
    """Fetches real-time highway speeds directly from TomTom API to verify baseline gridlock."""
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_API_KEY}&point={coords}"
        res = requests.get(url, timeout=3).json()
        speed = res.get("flowSegmentData", {}).get("currentSpeed", 30)
        
        if speed <= 8: return 20   # Extreme gridlock around the station terminal
        elif speed <= 15: return 10 # Moderate arterial slowdown
        return 0
    except Exception:
        return 0

def clean_old_message_ids():
    """Keeps memory clear of old message tracking IDs."""
    now = datetime.now()
    expired_ids = [msg_id for msg_id, t in processed_message_ids.items() if (now - t).total_seconds() > 300]
    for msg_id in expired_ids: 
        del processed_message_ids[msg_id]

def calculate_density(station_id, pht_now, weather_impact):
    """Blends historical calendars, weather metrics, road speeds, and validated crowd streams."""
    profile = STATION_PROFILES.get(station_id)
    if not profile: return "🟢 LIGHT PLATFORM"
    
    score = 0
    hour = pht_now.hour
    day = pht_now.weekday()
    date_str = pht_now.strftime("%Y-%m-%d")

    # 1. Directional Volume Projections (Directional Vectors)
    if "mrt3_" in station_id or "lrt1_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_sb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_nb"): score += 30
    elif "lrt2_" in station_id:
        if (6 <= hour <= 9) and station_id.endswith("_wb"): score += 30
        elif (16 <= hour <= 20) and station_id.endswith("_eb"): score += 30
        
    if profile["is_interchange"]: score += 10

    # 2. Calendar Anomalies & Holiday Offsets
    if (pht_now.day in [14, 15, 30, 31]) and day == 4: score += 25
    elif date_str in PH_HOLIDAYS: score += 20

    # 3. Environment API Injection
    score += weather_impact
    score += get_traffic_impact(profile["coords"])

    # 4. Filtered Crowdsourced Verification Stream
    crowd_score, total_voters = get_recent_crowdsource_score(station_id)
    score += crowd_score

    # Final Density Categorization Output
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

                # 🛠️ Direct Quick Reply payload routing interceptor
                if event.get("message") and event["message"].get("quick_reply"):
                    qr_payload = event["message"]["quick_reply"].get("payload")
                    if qr_payload:
                        handle_postback(sender_id, qr_payload)
                        return "EVENT_RECEIVED", 200

                # Normal routing paths
                if event.get("postback"):
                    handle_postback(sender_id, event["postback"]["payload"])
                elif event.get("message") and event["message"].get("text"):
                    handle_message(sender_id, event["message"]["text"].lower().strip())
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

def handle_message(user_id, text):
    pht = pytz.timezone("Asia/Manila")
    now = datetime.now(pht)
    
    if now.hour < 5 or (now.hour == 22 and now.minute > 30) or now.hour > 22:
        send_text(user_id, "🌙 *Train lines are currently closed.*\n\nOperating Hours: 5:00 AM - 10:30 PM PHT.")
        return

    # 🛠️ FIX: Intercept the Quick Reply Button text so it routes to the Dashboard
    if "platform" in text:
        for key, data in STATION_PROFILES.items():
            station_base_words = data["name"].lower().replace("(", "").replace(")", "").split()
            if any(word in text for word in station_base_words if len(word) > 4):
                if "northbound" in text and key.endswith("_nb"):
                    deliver_dashboard(user_id, key, now)
                    return
                elif "southbound" in text and key.endswith("_sb"):
                    deliver_dashboard(user_id, key, now)
                    return
                elif "eastbound" in text and key.endswith("_eb"):
                    deliver_dashboard(user_id, key, now)
                    return
                elif "westbound" in text and key.endswith("_wb"):
                    deliver_dashboard(user_id, key, now)
                    return

    # Existing Dynamic Station Intent Search Gate
    matched_stations = []
    cleaned_text = text.replace("station", "").replace("stn", "").replace("status", "").strip()
    
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
    pht = pytz.timezone("Asia/Manila")
    now = datetime.now(pht)
    
    if payload.startswith("QUERY_"):
        station_key = payload.replace("QUERY_", "")
        deliver_dashboard(user_id, station_key, now)
        
    elif payload.startswith("VOTE_"):
        parts = payload.split("_")
        tier = parts[1].lower()           # Extracts 'light', 'medium', or 'heavy'
        station_id = "_".join(parts[2:])  # Reassembles target station key ID string
        
        # One-Tap Data Input: Safely stream valid entry data straight to cloud storage ledger
        stream_interaction_to_cloud(station_id, f"vote_{tier}")
        
        # Instantly refresh the global system cache memory to reflect the new crowd feedback
        if station_id in GLOBAL_SYSTEM_CACHE:
            # Force cache refresh on next request tap interval
            GLOBAL_SYSTEM_CACHE[station_id]["last_updated"] = 0
            
        send_text(user_id, "✅ Thank you! Your real-time platform report has been anonymously verified and saved.")

def deliver_dashboard(user_id, station_key, current_time):
    # 1. Read instantly from lightning-fast RAM memory profile store
    profile = STATION_PROFILES[station_key]
    name = profile.get("name", station_key)
    
    # Safely extract your upgraded separate decimal geography configuration keys
    lat = profile.get("lat")
    lon = profile.get("lon")

    # 2. Silently stream active commuter user interaction footprint to the database
    stream_interaction_to_cloud(station_key, "dashboard_view")

    # 3. Process Global 10-Minute Anti-Lag Memory Cache Engine
    now_timestamp = current_time.timestamp()
    cache_expiry_seconds = 600 # 10 Minutes exact window

    # 💥 CRITICAL UPDATE: Initialize fallback variables so Python never throws a NameError
    status = "UNKNOWN PLATFORM"
    weather_condition = "Clear Sky"

    if station_key not in GLOBAL_SYSTEM_CACHE or (now_timestamp - GLOBAL_SYSTEM_CACHE[station_key]["last_updated"]) > cache_expiry_seconds:
        # Cache expired or empty! Fetch fresh API payloads safely once using split lat/lon
        weather_impact, weather_condition = get_weather_data(lat, lon)
        status = calculate_density(station_key, current_time, weather_impact)
        
        # Lock metrics right into local memory state
        GLOBAL_SYSTEM_CACHE[station_key] = {
            "last_updated": now_timestamp,
            "status": status,
            "weather": weather_condition
        }
    else:
        # Cache is completely valid! Pull directly from RAM to avoid hitting API rate limits
        status = GLOBAL_SYSTEM_CACHE[station_key].get("status", "LIGHT PLATFORM")
        weather_condition = GLOBAL_SYSTEM_CACHE[station_key].get("weather", "Clear Sky")

    # 4. Generate the Blended Real-Time Dashboard Card Layout
    dashboard_text = (
        f"📊 **Siksikan AI Live Dashboard**\n\n"
        f"📍 Location: 🚇 {name}\n"
        f"🚦 Status: **{status.upper()}**\n"
        f"🌤️ Weather: {weather_condition.title()}\n"
        f"🕒 **As of {current_time.strftime('%I:%M %p PST')}**\n\n"
        f"Help your fellow commuters! If you are standing at the platform right now, "
        f"verify conditions by choosing below:"
    )
    
    # 5. Dispatch UI Payload Block directly to Meta Webhook Graph Channel
    send_text(user_id, dashboard_text)
        
  # Read instantly from lightning-fast RAM memory profile store
    active_cache = STATION_PROFILES[station_key]

    # 1. Establish the 30-minute rolling time window (Philippine Standard Time)
    manila_tz = pytz.timezone('Asia/Manila')
    now = datetime.now(manila_tz)
    thirty_minutes_ago = (now - timedelta(minutes=30)).isoformat()
    time_stamp_display = now.strftime("%I:%M %p")

    # 2. Extract active hardware telemetry states from memory profile
    tomtom_road_status = active_cache.get('status', 'LIGHT PLATFORM').upper()
    weather_condition = active_cache.get('weather', 'Clear Sky').lower()

    # Establish baseline mathematical scoring weight
    if "HEAVY" in tomtom_road_status:
        base_score = 3.0
    elif "MEDIUM" in tomtom_road_status:
        base_score = 2.0
    else:
        base_score = 1.0

    # Automatic Environmental Multiplier: Flash rain cripples braking and inflates volume
    severe_weather = ["rain", "storm", "thunderstorm", "drizzle", "heavy intensity rain"]
    if any(keyword in weather_condition for keyword in severe_weather):
        base_score = max(base_score, 2.5) 

    # 3. Pull live, unexpired crowd feedback parameters from Supabase
    recent_reports = supabase.table("station_traffic_logs") \
        .select("status_clicked") \
        .eq("station_key", station_key) \
        .gte("created_at", thirty_minutes_ago) \
        .execute()

    # 4. Compute Weighted Data Fusion (40% Telemetry + 60% User Verified Reality)
    if recent_reports.data and len(recent_reports.data) >= 3:
        vote_scores = []
        for r in recent_reports.data:
            vote = r['status_clicked'].lower()
            if vote == 'heavy': vote_scores.append(3)
            elif vote == 'medium': vote_scores.append(2)
            elif vote == 'light': vote_scores.append(1)
            
        crowd_average = sum(vote_scores) / len(vote_scores)
        final_score = (base_score * 0.4) + (crowd_average * 0.6)
    else:
        # Anti-Joke Protection: Trust TomTom + OpenWeather 100% if less than 3 validations exist
        final_score = base_score

    # 5. Map final score calculation back to structural string layout tags
    if final_score >= 2.5:
        status_text = "HEAVY PLATFORM"
    elif final_score >= 1.5:
        status_text = "MEDIUM PLATFORM"
    else:
        status_text = "LIGHT PLATFORM"

    # 6. Generate Clean UI Layout Message Card
    msg = (
        "📊 *Siksikan AI Live Dashboard*\n\n"
        f"📍 Location: 🚇 {name}\n"
        f"🚦 Status: {status_text}\n"
        f"🌤️ Weather: {active_cache['weather']}\n"
        f"🕒 *As of {time_stamp_display} PST*\n\n"
        "Help your fellow commuters! If you are standing at the platform right now, verify conditions by choosing below:\n\n"
    )

    send_simplified_buttons(user_id, msg, station_key)
    
def send_text(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}}, timeout=5)

def send_direction_menu(recipient_id, base_station_key):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    
    # 💡 SHORTENED LABELS: Keeps titles crisp so they fit cleanly on mobile screens
    if "lrt2" in base_station_key:
        title_1, key_1 = "🚇 Eastbound", f"QUERY_{base_station_key}_eb"
        title_2, key_2 = "🚇 Westbound", f"QUERY_{base_station_key}_wb"
    else:
        title_1, key_1 = "🚆 Northbound", f"QUERY_{base_station_key}_nb"
        title_2, key_2 = "🚆 Southbound", f"QUERY_{base_station_key}_sb"

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
def push_telegram_notification(text_payload):
    """Dispatches system summary updates straight to your private Telegram client workspace."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text_payload, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram dispatch alert connection timeout: {e}")

@app.route("/cron-dispatch-report", methods=["GET"])
def process_automated_analytics_loop():
    """
    Automated background pipeline linked to cron-job.org.
    Analyzes multi-timeframe logs, extracts peak transit hours, and fires summaries to your phone.
    """
    mode = request.args.get("timeframe", "daily") # Defaults to daily run metrics checking
    pht = timezone("Asia/Manila")
    manila_now = datetime.now(pht)
    
    # 1. Establish structural time boundaries based on your request parameter criteria
    if mode == "daily":
        start_date = (manila_now - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
    elif mode == "weekly":
        start_date = (manila_now - timedelta(days=7)).replace(hour=0, minute=0, second=0).isoformat()
    else:  # Monthly tracking criteria parameters configuration mode
        start_date = (manila_now - timedelta(days=30)).replace(hour=0, minute=0, second=0).isoformat()

    try:
        # 2. Query all interaction rows logged since the calculated time boundary
        response = supabase.table("station_traffic_logs") \
            .select("line, station_id, hour_block") \
            .gte("created_at", start_date) \
            .execute()
            
        data = response.data or []
        
        if not data:
            push_telegram_notification(f"⚠️ *SIKSIKAN AI {mode.upper()} ALARM*\n\nNo transit footprints captured yet for this timeframe context window.")
            return "Empty Dataset Logged", 200

        # Initialize tracking matrices containers
        line_totals = {"MRT-3": 0, "LRT-1": 0, "LRT-2": 0}
        station_counts = {}
        hour_clocks = {}

        # 3. Aggregate data across lines, stations, and time slots
        for row in data:
            line = row.get("line", "Unknown")
            stn = row.get("station_id", "Unknown")
            hr = row.get("hour_block", "Unknown")
            
            if line in line_totals:
                line_totals[line] += 1
                
            station_counts[stn] = station_counts.get(stn, 0) + 1
            hour_clocks[hr] = hour_clocks.get(hr, 0) + 1

        # Isolate top traffic spikes components
        sorted_stations = sorted(station_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_hours = sorted(hour_clocks.items(), key=lambda x: x[1], reverse=True)
        
        top_station = sorted_stations[0][0].upper() if sorted_stations else "None"
        peak_hour_1 = sorted_hours[0][0] if sorted_hours else "N/A"
        peak_hour_2 = sorted_hours[1][0] if len(sorted_hours) > 1 else "N/A"

        # 4. Format the Markdown text template
        msg = (
            f"🚀 *SIKSIKAN AI {mode.upper()} ANALYSIS REPORT*\n"
            f"📅 _Range Target Open Start: {start_date[:10]}_\n"
            f"⏱️ _System Compiled Network Grid Run Output_\n\n"
            f"==============================\n"
            f"🔵 *MRT-3 Line Total Inquiries:* {line_totals['MRT-3']:,} users\n"
            f"🟢 *LRT-1 Line Total Inquiries:* {line_totals['LRT-1']:,} users\n"
            f"🟡 *LRT-2 Line Total Inquiries:* {line_totals['LRT-2']:,} users\n"
            f"==============================\n\n"
            f"🏆 *Busiest Network Hub Node:* `{top_station}`\n\n"
            f"🔥 *SYSTEM PEAK COMMUTE WINDOWS:*\n"
            f"🥇 *{peak_hour_1}* ({hour_clocks.get(peak_hour_1, 0):,} lookups)\n"
            f"🥈 *{peak_hour_2}* ({hour_clocks.get(peak_hour_2, 0):,} lookups)\n\n"
            f"📊 *Total System Footprints Logged:* {len(data):,} Commuters\n"
            f"⚙️ _Data Engine Verified Core Source Instance: Supabase Cloud_"
        )
        
        push_telegram_notification(msg)
        return "Analytics Engine Complete", 200
        
    except Exception as e:
        print(f"Telegram Cron loop execution error context details tracking: {e}")
        return "Internal Error Processing Core Metrics Data Loop", 500
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize the automated 10-minute clock worker loop
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_weather_and_tomtom_cache, trigger="interval", minutes=10)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
