import streamlit as st
import datetime
from kerykeion import KrInstance
import matplotlib.pyplot as plt
import numpy as np
import os
import io
import swisseph as swe
from geopy.geocoders import ArcGIS
from timezonefinder import TimezoneFinder
import pytz
import requests # 新增：用於 IP 定位

st.set_page_config(page_title="專業星盤系統", layout="wide")

# ================= 0. Session State 狀態管理 =================
now = datetime.datetime.now()
if 'n_year' not in st.session_state:
    st.session_state.update({
        'n_year': 1993, 'n_month': 9, 'n_day': 27, 'n_hour': 12, 'n_minute': 0, 'n_loc': "Manchester", 'name_input': "Vincent",
        'p_year': now.year, 'p_month': now.month, 'p_day': now.day, 'p_hour': now.hour, 'p_minute': now.minute, 'p_loc': "Manchester",
        'target_age': now.year - 1993
    })

def set_current_time():
    n = datetime.datetime.now()
    st.session_state.n_year, st.session_state.n_month, st.session_state.n_day = n.year, n.month, n.day
    st.session_state.n_hour, st.session_state.n_minute = n.hour, n.minute
    st.session_state.name_input = "卜卦"

def set_current_loc():
    try:
        res = requests.get('http://ip-api.com/json/', timeout=3).json()
        st.session_state.n_loc = res.get('city', 'Hong Kong')
    except:
        st.session_state.n_loc = "Hong Kong"

def update_year_from_age():
    st.session_state.p_year = st.session_state.n_year + st.session_state.target_age

def update_age_from_year():
    st.session_state.target_age = st.session_state.p_year - st.session_state.n_year

# ================= 1. 基礎設定與常數 =================
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans'] 
plt.rcParams['axes.unicode_minus'] = False

ZODIAC_SYMBOLS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']
ZODIAC_NAMES = ['牡羊', '金牛', '雙子', '巨蟹', '獅子', '處女', '天秤', '天蠍', '射手', '摩羯', '水瓶', '雙魚']
ZR_PERIODS = [15, 8, 20, 25, 19, 20, 8, 15, 12, 27, 30, 12] # 黃道釋放各星座歲數限制

PLANET_SYMBOLS = {
    '太陽': {'sym': '☉', 'color': '#e67e22'}, '月亮': {'sym': '☽', 'color': '#7f8c8d'},
    '水星': {'sym': '☿', 'color': '#27ae60'}, '金星': {'sym': '♀', 'color': '#2ecc71'},
    '火星': {'sym': '♂', 'color': '#e74c3c'}, '木星': {'sym': '♃', 'color': '#d35400'},
    '土星': {'sym': '♄', 'color': '#2c3e50'}, '天王星': {'sym': '♅', 'color': '#8e44ad'},
    '海王星': {'sym': '♆', 'color': '#2980b9'}, '冥王星': {'sym': '♇', 'color': '#34495e'},
    '北交點': {'sym': '☊', 'color': '#000000'},
    '上升': {'sym': 'ASC', 'color': '#c0392b'}, '中天': {'sym': 'MC', 'color': '#2980b9'}
}

TRADITIONAL_RULERS = {
    '牡羊': '火星', '金牛': '金星', '雙子': '水星', '巨蟹': '月亮',
    '獅子': '太陽', '處女': '水星', '天秤': '金星', '天蠍': '火星',
    '射手': '木星', '摩羯': '土星', '水瓶': '土星', '雙魚': '木星'
}

LILLY_MOITIES = {
    '太陽': 7.5, '月亮': 6.0, '土星': 4.5, '木星': 4.5, '火星': 4.0, '金星': 3.5, '水星': 3.5,
    '天王星': 2.5, '海王星': 2.5, '冥王星': 2.5, '北交點': 2.5, '上升': 0.0, '中天': 0.0
}

DIGNITIES = {
    '太陽': {'廟': [4], '旺': [0], '弱': [10], '陷': [6]},
    '月亮': {'廟': [3], '旺': [1], '弱': [9], '陷': [7]},
    '水星': {'廟': [2, 5], '旺': [5], '弱': [8, 11], '陷': [11]},
    '金星': {'廟': [1, 6], '旺': [11], '弱': [7, 0], '陷': [5]},
    '火星': {'廟': [0, 7], '旺': [9], '弱': [6, 1], '陷': [3]},
    '木星': {'廟': [8, 11], '旺': [3], '弱': [2, 5], '陷': [9]},
    '土星': {'廟': [9, 10], '旺': [6], '弱': [3, 4], '陷': [0]}
}

# ================= 2. 核心函數 =================
EPHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ephe')
swe.set_ephe_path(EPHE_PATH)

def format_degree(lon):
    idx = int(lon // 30) % 12
    deg = int(lon % 30)
    mins = int(round((lon % 1) * 60))
    if mins == 60:
        mins = 0; deg += 1
        if deg == 30: deg = 0; idx = (idx + 1) % 12
    return f"{ZODIAC_NAMES[idx]}({deg:02d}°{mins:02d})"

def get_house_number(lon, cusps, house_system):
    c_list = list(cusps)[1:] if len(cusps) == 13 else list(cusps)
    if house_system == b'W':
        asc_sign = int(c_list[0] // 30)
        p_sign = int(lon // 30)
        return (p_sign - asc_sign) % 12 + 1
    for h in range(12):
        c1 = c_list[h]
        c2 = c_list[(h + 1) % 12]
        if c1 <= c2:
            if c1 <= lon < c2: return h + 1
        else:
            if lon >= c1 or lon < c2: return h + 1
    return 12

def calc_midpoint(p1_lon, p2_lon):
    diff = abs(p1_lon - p2_lon)
    return ((p1_lon + p2_lon + 360) / 2.0 if diff > 180 else (p1_lon + p2_lon) / 2.0) % 360

def calculate_chart_engine(jd, lat, lon, house_system):
    planets_map = {
        '太陽': swe.SUN, '月亮': swe.MOON, '水星': swe.MERCURY, '金星': swe.VENUS, '火星': swe.MARS, 
        '木星': swe.JUPITER, '土星': swe.SATURN, '天王星': swe.URANUS, '海王星': swe.NEPTUNE, 
        '冥王星': swe.PLUTO, '北交點': swe.TRUE_NODE
    }
    positions = {}
    speeds = {}
    for name, planet_id in planets_map.items():
        pos, _ = swe.calc_ut(jd, planet_id)
        positions[name] = pos[0] 
        speeds[name] = pos[3] 
    cusps, ascmc = swe.houses(jd, lat, lon, house_system)
    positions['上升'] = ascmc[0]
    positions['中天'] = ascmc[1]
    return positions, ascmc[0], cusps, ascmc[1], speeds

def get_aspect_modifier_engine(p1, p2, target_angle, current_diff, jd, lat, lon, house_sys):
    positions_future, _, _, _, _ = calculate_chart_engine(jd + 0.005, lat, lon, house_sys)
    if p1 in positions_future and p2 in positions_future:
        f_diff = abs(positions_future[p1] - positions_future[p2])
        if f_diff > 180: f_diff = 360 - f_diff
        return "+" if abs(f_diff - target_angle) < abs(current_diff - target_angle) else "-"
    return ""

def calc_zodiacal_releasing(lot_lon, birth_jd, target_jd):
    """黃道釋放 (Zodiacal Releasing) 核心算法"""
    start_sign = int(lot_lon // 30)
    total_days = target_jd - birth_jd
    if total_days < 0: return None, None, False
    
    # 計算 L1 (主限)
    l1_sign = start_sign
    rem_days = total_days
    while True:
        period_days = ZR_PERIODS[l1_sign] * 360
        if rem_days >= period_days:
            rem_days -= period_days
            l1_sign = (l1_sign + 1) % 12
        else:
            break
            
    # 計算 L2 (次限) 與 LB 判斷
    l2_sign = l1_sign
    months = 0
    is_lb = False
    while True:
        sub_period_days = ZR_PERIODS[l2_sign] * 30
        if rem_days >= sub_period_days:
            rem_days -= sub_period_days
            months += 1
            if months == 12: # 滿12個月產生「解縛 LB」跳至對宮
                l2_sign = (l2_sign + 6) % 12
                is_lb = True
            else:
                l2_sign = (l2_sign + 1) % 12
        else:
            break
    return l1_sign, l2_sign, is_lb

def draw_astrology_chart(positions, asc_degree, cusps, specs, aspect_system):
    aspects = []
    p_names = [p for p in positions.keys() if p in PLANET_SYMBOLS]
    for i in range(len(p_names)):
        for j in range(i+1, len(p_names)):
            p1, p2 = p_names[i], p_names[j]
            diff = abs(positions[p1] - positions[p2])
            if diff > 180: diff = 360 - diff
            for angle, name, color, orb in specs:
                if orb == 0: continue
                allowed_orb = LILLY_MOITIES.get(p1, 2.5) + LILLY_MOITIES.get(p2, 2.5) if aspect_system == "古典 (威廉・里利)" else orb
                if abs(diff - angle) <= allowed_orb:
                    aspects.append((p1, p2, color))
                    break

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'})
    ax.set_theta_zero_location("W"); ax.set_theta_direction(-1)      
    def get_canvas_angle(zodiac_degree): return np.deg2rad(asc_degree - zodiac_degree)
    ax.axis('off')
    ax.add_artist(plt.Circle((0, 0), 1.0, transform=ax.transData._b, fill=False, color='#333', lw=1.2))
    ax.add_artist(plt.Circle((0, 0), 0.82, transform=ax.transData._b, fill=False, color='#333', lw=1.2))
    ax.add_artist(plt.Circle((0, 0), 0.45, transform=ax.transData._b, fill=False, color='#ccc', lw=0.8))

    for i in range(12):
        angle = get_canvas_angle(i * 30)
        ax.plot([angle, angle], [0.82, 1.0], color='#888', lw=0.8)
        ax.text(get_canvas_angle(i * 30 + 15), 0.91, ZODIAC_SYMBOLS[i], fontsize=16, ha='center', va='center')

    c_list = list(cusps)[1:] if len(cusps) == 13 else list(cusps)
    for i, deg in enumerate(c_list):
        ax.plot([get_canvas_angle(deg)]*2, [0.45, 0.82], color='red' if i == 0 else ('blue' if i == 9 else '#666'), lw=1.5 if i in [0,9] else 0.7)

    for p1, p2, color in aspects:
        ax.plot([get_canvas_angle(positions[p1]), get_canvas_angle(positions[p2])], [0.45, 0.45], color=color, lw=1.2, alpha=0.3)

    sorted_planets = sorted([(p, deg) for p, deg in positions.items() if p in PLANET_SYMBOLS], key=lambda x: x[1])
    allocated_radii = {}
    for i, (p, deg) in enumerate(sorted_planets):
        r_level = 0.70
        for j in range(max(0, i-4), i):
            if abs((deg - sorted_planets[j][1] + 180) % 360 - 180) < 6.5 and allocated_radii.get(sorted_planets[j][0], 0.70) == r_level:
                r_level -= 0.06
        allocated_radii[p] = r_level

    for planet, deg in positions.items():
        if planet not in PLANET_SYMBOLS: continue
        angle = get_canvas_angle(deg); sym = PLANET_SYMBOLS[planet]; r = allocated_radii[planet]
        ax.text(angle, r, sym['sym'], fontsize=11 if planet in ['上升', '中天'] else 18, ha='center', va='center', color=sym['color'], fontweight='bold' if planet in ['上升', '中天'] else 'normal')
        ax.text(angle, r - 0.09, f"{int(deg % 30)}°", fontsize=8, ha='center', va='center', color='#555')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=145)
    buf.seek(0); plt.close()
    return buf

def resolve_location_and_time(loc_name, y, m, d, h, minute):
    if not loc_name: 
        raise ValueError("城市名稱不能為空！")
    location = ArcGIS(timeout=10).geocode(loc_name)
    if not location: 
        raise ValueError(f"無法定位城市: '{loc_name}'")
    
    lat, lon = location.latitude, location.longitude
    tz_str = TimezoneFinder().timezone_at(lng=lon, lat=lat) or "UTC"
    local_dt = pytz.timezone(tz_str).localize(datetime.datetime(y, m, d, h, minute))
    utc_dt = local_dt.astimezone(pytz.utc)
    
    hour_decimal = utc_dt.hour + (utc_dt.minute / 60.0)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal)
    info = f"城市: {location.address}\n時區: {tz_str}\n時間: {local_dt.strftime('%Y-%m-%d %H:%M')}\n"
    return jd, lat, lon, info, utc_dt

# ================= 3. Streamlit UI 介面 =================
st.title("🔮 進階專業星盤推運系統")

# --- 側邊欄：本命盤設定 ---
st.sidebar.header("本命盤基本資訊")
name = st.sidebar.text_input("姓名", key="name_input")
gender = st.sidebar.selectbox("性別", ["男", "女"])

col1, col2, col3 = st.sidebar.columns(3)
col1.number_input("年", key="n_year", step=1)
col2.number_input("月", key="n_month", min_value=1, max_value=12)
col3.number_input("日", key="n_day", min_value=1, max_value=31)

col4, col5 = st.sidebar.columns(2)
col4.number_input("時", key="n_hour", min_value=0, max_value=23)
col5.number_input("分", key="n_minute", min_value=0, max_value=59)
st.sidebar.text_input("出生城市", key="n_loc")

btn_col1, btn_col2 = st.sidebar.columns(2)
btn_col1.button("🕒 當下時間", on_click=set_current_time, use_container_width=True)
btn_col2.button("📍 當下地點", on_click=set_current_loc, use_container_width=True)

st.sidebar.divider()

# --- 側邊欄：推運設定 (收納) ---
with st.sidebar.expander("推運 / 行運 / 日返設定", expanded=False):
    st.number_input("推運 年", key="p_year", step=1, on_change=update_age_from_year)
    col6, col7 = st.columns(2)
    col6.number_input("推運 月", key="p_month", min_value=1, max_value=12)
    col7.number_input("推運 日", key="p_day", min_value=1, max_value=31)
    
    col8, col9 = st.columns(2)
    col8.number_input("推運 時", key="p_hour", min_value=0, max_value=23)
    col9.number_input("推運 分", key="p_minute", min_value=0, max_value=59)
    st.text_input("目標城市", key="p_loc")
    
    st.divider()
    st.number_input("👉 快速設定推運歲數", key="target_age", min_value=0, max_value=120, on_change=update_year_from_age)

h_sys_name = st.sidebar.selectbox("宮位系統", ["普拉西度 (Placidus)", "整宮制 (Whole Sign)", "Regiomontanus"])

# --- 側邊欄：自訂相位 ---
a_sys_name = st.sidebar.selectbox("相位系統", ["現代", "古典 (威廉・里利)", "自訂"])
custom_orbs = {}
if a_sys_name == "自訂":
    with st.sidebar.expander("⚙️ 自訂相位容許度", expanded=True):
        c1, c2, c3 = st.columns(3)
        custom_orbs[0] = c1.number_input("0°", value=8, min_value=0, max_value=15)
        custom_orbs[30] = c2.number_input("30°", value=0, min_value=0, max_value=15)
        custom_orbs[45] = c3.number_input("45°", value=1, min_value=0, max_value=15)
        custom_orbs[60] = c1.number_input("60°", value=6, min_value=0, max_value=15)
        custom_orbs[90] = c2.number_input("90°", value=7, min_value=0, max_value=15)
        custom_orbs[120] = c3.number_input("120°", value=7, min_value=0, max_value=15)
        custom_orbs[135] = c1.number_input("135°", value=1, min_value=0, max_value=15)
        custom_orbs[150] = c2.number_input("150°", value=0, min_value=0, max_value=15)
        custom_orbs[180] = c3.number_input("180°", value=8, min_value=0, max_value=15)
else:
    custom_orbs = {0: 8.0, 30: 0, 45: 0, 60: 6.0, 90: 7.0, 120: 7.0, 135: 0, 150: 0, 180: 8.0}

st.sidebar.subheader("進階功能選項")
chk_greek = st.sidebar.checkbox("七大希臘點")
chk_midpoint = st.sidebar.checkbox("顯示中點")
chk_whole_rule = st.sidebar.checkbox("宮主星整宮制")
chk_solar_arc = st.sidebar.checkbox("真實日弧相位")
chk_sa_midpoint = st.sidebar.checkbox("日弧中點")    # 新增功能
chk_profection = st.sidebar.checkbox("顯示小限歲數")
chk_zr = st.sidebar.checkbox("黃道釋放")             # 新增功能
chk_solar_return = st.sidebar.checkbox("計算日返星盤")
chk_transit = st.sidebar.checkbox("計算過運行運")

# --- 產生相位於繪圖格式 ---
aspect_specs_full = [
    (0, "合相", '#95a5a6', custom_orbs.get(0, 0)),
    (30, "十二分", '#f39c12', custom_orbs.get(30, 0)),
    (45, "半四分", '#d35400', custom_orbs.get(45, 0)),
    (60, "六分", '#2ecc71', custom_orbs.get(60, 0)),
    (90, "四分", '#e74c3c', custom_orbs.get(90, 0)),
    (120, "三分", '#27ae60', custom_orbs.get(120, 0)),
    (135, "補八分", '#c0392b', custom_orbs.get(135, 0)),
    (150, "補十二", '#8e44ad', custom_orbs.get(150, 0)),
    (180, "對相", '#2980b9', custom_orbs.get(180, 0))
]

# --- 主計算按鈕 ---
if st.sidebar.button("🔮 執行占星整合計算", use_container_width=True, type="primary"):
    try:
        with st.spinner('天文運算與分析報告生成中...'):
            h_code = b'W' if "整宮" in h_sys_name else (b'R' if "Regiomontanus" in h_sys_name else b'P')
            
            jd_n, lat_n, lon_n, meta_n, dt_n_utc = resolve_location_and_time(
                st.session_state.n_loc, st.session_state.n_year, st.session_state.n_month, 
                st.session_state.n_day, st.session_state.n_hour, st.session_state.n_minute)
            jd_p, lat_p, lon_p, meta_p, dt_p_utc = resolve_location_and_time(
                st.session_state.p_loc, st.session_state.p_year, st.session_state.p_month, 
                st.session_state.p_day, st.session_state.p_hour, st.session_state.p_minute)
            
            pos_n, asc_n, cusps_n, mc_n, speed_n = calculate_chart_engine(jd_n, lat_n, lon_n, h_code)
            img_n = draw_astrology_chart(pos_n, asc_n, cusps_n, aspect_specs_full, a_sys_name)
            
            is_day = 7 <= get_house_number(pos_n['太陽'], cusps_n, h_code) <= 12
            
            report = f"== 命盤基本觀測 ==\n持有人：{st.session_state.name_input} ({gender})\n{meta_n}\n"
            report += "【星體位置】\n"
            for k in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '北交點', '上升', '中天']:
                h_num = get_house_number(pos_n[k], cusps_n, h_code)
                base_str = f"{k: <3}：{format_degree(pos_n[k])} {h_num: >2}宮"
                status_parts = []
                if k in DIGNITIES:
                    sign_idx = int(pos_n[k] // 30) % 12
                    dig_str = ""
                    if sign_idx in DIGNITIES[k]['廟']: dig_str += "廟"
                    if sign_idx in DIGNITIES[k]['旺']: dig_str += "旺"
                    if sign_idx in DIGNITIES[k]['弱']: dig_str += "弱"
                    if sign_idx in DIGNITIES[k]['陷']: dig_str += "陷"
                    if dig_str: status_parts.append(dig_str)
                if is_day and k in ['太陽', '木星', '土星']: status_parts.append("得時")
                elif not is_day and k in ['月亮', '金星', '火星']: status_parts.append("得時")
                if k in ['水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
                    if speed_n.get(k, 0) < 0: status_parts.append("逆行")
                
                report += f"{base_str}    {'   '.join(status_parts)}\n" if status_parts else f"{base_str}\n"

            # 計算希臘點
            sun, moon, mars, jup, sat = pos_n['太陽'], pos_n['月亮'], pos_n['火星'], pos_n['木星'], pos_n['土星']
            fortune = (asc_n + moon - sun) if is_day else (asc_n + sun - moon)
            spirit = (asc_n + sun - moon) if is_day else (asc_n + moon - sun)

            if chk_greek:
                greek = {
                    '幸運點': fortune % 360, '精神點': spirit % 360,
                    '愛欲點': ((asc_n + spirit - fortune) if is_day else (asc_n + fortune - spirit)) % 360,
                    '必然點': ((asc_n + fortune - spirit) if is_day else (asc_n + spirit - fortune)) % 360,
                    '勇氣點': ((asc_n + mars - fortune) if is_day else (asc_n + fortune - mars)) % 360,
                    '勝利點': ((asc_n + jup - spirit) if is_day else (asc_n + spirit - jup)) % 360,
                    '復仇點': ((asc_n + fortune - sat) if is_day else (asc_n + sat - fortune)) % 360
                }
                report += "\n【七大希臘點位置】\n"
                for k, v in greek.items():
                    report += f"{k}：{format_degree(v)} {get_house_number(v, cusps_n, h_code)}宮\n"

            # 【新增功能】黃道釋放
            if chk_zr:
                report += "\n【黃道釋放 Zodiacal Releasing】\n"
                # 幸運點釋放
                f_l1, f_l2, f_lb = calc_zodiacal_releasing(fortune % 360, jd_n, jd_p)
                if f_l1 is not None:
                    lb_txt = " (解縛 LB)" if f_lb else ""
                    report += f"幸運點釋放：L1 {ZODIAC_NAMES[f_l1]} -> L2 {ZODIAC_NAMES[f_l2]}{lb_txt}\n"
                # 精神點釋放
                s_l1, s_l2, s_lb = calc_zodiacal_releasing(spirit % 360, jd_n, jd_p)
                if s_l1 is not None:
                    lb_txt = " (解縛 LB)" if s_lb else ""
                    report += f"精神點釋放：L1 {ZODIAC_NAMES[s_l1]} -> L2 {ZODIAC_NAMES[s_l2]}{lb_txt}\n"

            report += "\n【宮頭】\n"
            c_list_n = list(cusps_n)[1:] if len(cusps_n) == 13 else list(cusps_n)
            if chk_whole_rule:
                asc_sign_idx = int(asc_n // 30)
                for i in range(12):
                    report += f"{i+1}宮：{ZODIAC_NAMES[(asc_sign_idx + i) % 12]}\n"
            else:
                for i, deg in enumerate(c_list_n):
                    label = " (ASC)" if i == 0 else (" (MC)" if i == 9 else "")
                    report += f"{i+1}宮{label}：{format_degree(deg)}\n"

            report += "\n【相位列表】\n"
            p_names = [p for p in pos_n.keys() if p in PLANET_SYMBOLS]
            aspect_lines = []
            for i in range(len(p_names)):
                for j in range(i+1, len(p_names)):
                    p1, p2 = p_names[i], p_names[j]
                    diff = abs(pos_n[p1] - pos_n[p2])
                    if diff > 180: diff = 360 - diff
                    for angle, a_name, _, orb in aspect_specs_full:
                        if orb == 0: continue
                        allowed_orb = LILLY_MOITIES.get(p1, 2.5) + LILLY_MOITIES.get(p2, 2.5) if a_sys_name == "古典 (威廉・里利)" else orb
                        if abs(diff - angle) <= allowed_orb:
                            sign = get_aspect_modifier_engine(p1, p2, angle, diff, jd_n, lat_n, lon_n, h_code)
                            aspect_lines.append(f"{p1}-{p2} {a_name} {sign}{abs(diff - angle):.1f} °")
                            break
            report += "\n".join(aspect_lines) if aspect_lines else "無符合規格相位"

            if chk_midpoint:
                report += "\n\n【行星中點】\n"
                mid_lines = []
                base_planets = ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '北交點', '上升']
                for i in range(len(base_planets)):
                    for j in range(i+1, len(base_planets)):
                        bp1, bp2 = base_planets[i], base_planets[j]
                        m_lon = calc_midpoint(pos_n[bp1], pos_n[bp2])
                        for p in base_planets:
                            diff = (pos_n[p] - m_lon) % 360
                            for angle in [0, 90, 180, 270]:
                                dev = diff - angle
                                if dev > 180: dev -= 360
                                if dev < -180: dev += 360
                                if abs(dev) <= 1.0:
                                    mid_lines.append(f"{p} ＝ {bp1}/{bp2} {'+' if dev>=0 else '-'}{abs(dev):.1f}°")
                                    break
                report += "\n".join(mid_lines) if mid_lines else "無符合容許度的中點相位"

            if chk_profection:
                report += "\n\n【小限宮位管轄歲數 (0-75)】\n"
                asc_sign_idx = int(asc_n // 30)
                for h in range(12):
                    if chk_whole_rule: sign_name = ZODIAC_NAMES[(asc_sign_idx + h) % 12]
                    else: sign_name = ZODIAC_NAMES[int(c_list_n[h] // 30) % 12]
                    ruler = TRADITIONAL_RULERS[sign_name]
                    ages = [str(age) for age in range(76) if age % 12 == h]
                    report += f"{h+1}宮-{ruler}：{ '、'.join(ages) }\n"

            # 日弧與中點預先計算
            age_in_years = (dt_p_utc - dt_n_utc).days / 365.242199
            jd_progressed = jd_n + age_in_years
            pos_prog, _ = swe.calc_ut(jd_progressed, swe.SUN)
            solar_arc = (pos_prog[0] - pos_n['太陽']) % 360

            if chk_solar_arc:
                report += "\n\n【日弧相位】\n"
                sa_lines = []
                sa_specs = [(0, "合相"), (45, "半四分"), (90, "四分"), (135, "補八分"), (180, "對相")]
                for p1 in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
                    sa_lon = (pos_n[p1] + solar_arc) % 360
                    for p2 in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '上升', '中天']:
                        diff = abs(sa_lon - pos_n[p2])
                        if diff > 180: diff = 360 - diff
                        for angle, a_name in sa_specs:
                            if abs(diff - angle) <= 1.0: 
                                sa_lon_future = (sa_lon + 0.005) % 360
                                diff_future = abs(sa_lon_future - pos_n[p2])
                                if diff_future > 180: diff_future = 360 - diff_future
                                sa_sign = "+" if abs(diff_future - angle) < abs(diff - angle) else "-"
                                sa_lines.append(f"［弧］{p1} - ［命］{p2} {a_name} {sa_sign}{abs(diff - angle):.1f}°")
                                break
                report += "\n".join(sa_lines) if sa_lines else "無符合規格之日弧相位"

            # 【新增功能】日弧中點
            if chk_sa_midpoint:
                report += "\n\n【日弧中點】\n"
                sam_lines = []
                base_planets = ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '上升', '中天']
                sa_targets = ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']
                
                for p1 in sa_targets:
                    sa_lon = (pos_n[p1] + solar_arc) % 360
                    for i in range(len(base_planets)):
                        for j in range(i+1, len(base_planets)):
                            bp1, bp2 = base_planets[i], base_planets[j]
                            m_lon = calc_midpoint(pos_n[bp1], pos_n[bp2])
                            
                            diff = (sa_lon - m_lon) % 360
                            for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                                dev = diff - angle
                                if dev > 180: dev -= 360
                                if dev < -180: dev += 360
                                if abs(dev) <= 1.0:
                                    sa_lon_future = (sa_lon + 0.005) % 360
                                    diff_f = (sa_lon_future - m_lon) % 360
                                    dev_f = diff_f - angle
                                    if dev_f > 180: dev_f -= 360
                                    if dev_f < -180: dev_f += 360
                                    sa_sign = "+" if abs(dev_f) < abs(dev) else "-"
                                    sam_lines.append(f"［弧］{p1} ＝ ［本］{bp1} / {bp2}  {sa_sign}{abs(dev):.1f}°")
                                    break
                report += "\n".join(sam_lines) if sam_lines else "無符合規格之日弧中點"

            if chk_transit:
                pos_t, _, _, _, _ = calculate_chart_engine(jd_p, lat_p, lon_p, h_code)
                pos_t_future, _, _, _, _ = calculate_chart_engine(jd_p + 0.005, lat_p, lon_p, h_code)
                
                report += f"\n\n【行運觀測資訊】\n目標城市：{st.session_state.p_loc}\n"
                for k in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
                    h_num = get_house_number(pos_t[k], cusps_n, h_code)
                    report += f"[運]{k} ：{format_degree(pos_t[k])} [命] {h_num}宮\n"
                
                report += "\n【行運星與本命星相位】\n"
                t_lines = []
                for p1 in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
                    for p2 in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '上升', '中天']:
                        diff = abs(pos_t[p1] - pos_n[p2])
                        if diff > 180: diff = 360 - diff
                        for angle, a_name, _, orb in aspect_specs_full:
                            if orb == 0: continue
                            allowed_orb = LILLY_MOITIES.get(p1, 2.5) + LILLY_MOITIES.get(p2, 2.5) if a_sys_name == "古典 (威廉・里利)" else orb
                            if abs(diff - angle) <= allowed_orb:
                                f_diff = abs(pos_t_future[p1] - pos_n[p2])
                                if f_diff > 180: f_diff = 360 - f_diff
                                t_sign = "+" if abs(f_diff - angle) < abs(diff - angle) else "-"
                                t_lines.append(f"[運]{p1} {a_name} [命]{p2} {t_sign} {abs(diff - angle):.1f}°")
                report += "\n".join(t_lines) if t_lines else "無符合交叉行運相位"

            img_sr = None
            if chk_solar_return:
                jd_approx = swe.julday(st.session_state.p_year, dt_n_utc.month, dt_n_utc.day, 12.0)
                def sun_diff(j_val): return ((swe.calc_ut(j_val, swe.SUN)[0][0] - pos_n['太陽'] + 180) % 360 - 180)
                j1, j2 = jd_approx - 2, jd_approx + 2
                f1, f2 = sun_diff(j1), sun_diff(j2)
                for _ in range(15):
                    if abs(f2 - f1) < 1e-11: break
                    j_next = j2 - f2 * (j2 - j1) / (f2 - f1)
                    j1, j2, f1 = j2, j_next, f2
                    f2 = sun_diff(j2)
                
                jd_sr = j2
                pos_sr, asc_sr, cusps_sr, mc_sr, _ = calculate_chart_engine(jd_sr, lat_p, lon_p, h_code)
                img_sr = draw_astrology_chart(pos_sr, asc_sr, cusps_sr, aspect_specs_full, a_sys_name)
                
                tf = TimezoneFinder()
                tz_str = tf.timezone_at(lng=lon_p, lat=lat_p) or "UTC"
                sr_utc_dt = datetime.datetime(2000, 1, 1, 12, 0, tzinfo=pytz.utc) + datetime.timedelta(days=jd_sr - 2451545.0)
                sr_local_dt = sr_utc_dt.astimezone(pytz.timezone(tz_str))
                
                report += f"\n\n【日返報告】\n返照精確時間：{sr_local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_str})\n"
                for k in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '上升', '中天']:
                    report += f"日返{k}：{format_degree(pos_sr[k])} {get_house_number(pos_sr[k], cusps_sr, h_code)}宮\n"
                
                report += "\n【日返相位列表】\n"
                sr_aspect_lines = []
                p_names_sr = [p for p in pos_sr.keys() if p in PLANET_SYMBOLS]
                for i in range(len(p_names_sr)):
                    for j in range(i+1, len(p_names_sr)):
                        p1, p2 = p_names_sr[i], p_names_sr[j]
                        diff = abs(pos_sr[p1] - pos_sr[p2])
                        if diff > 180: diff = 360 - diff
                        for angle, a_name, _, orb in aspect_specs_full:
                            if orb == 0: continue
                            allowed_orb = LILLY_MOITIES.get(p1, 2.5) + LILLY_MOITIES.get(p2, 2.5) if a_sys_name == "古典 (威廉・里利)" else orb
                            if abs(diff - angle) <= allowed_orb:
                                sign = get_aspect_modifier_engine(p1, p2, angle, diff, jd_sr, lat_p, lon_p, h_code)
                                sr_aspect_lines.append(f"{p1}-{p2} {a_name} {sign}{abs(diff - angle):.1f}°")
                                break
                report += "\n".join(sr_aspect_lines) if sr_aspect_lines else "無符合規格之日返相位"

            # ================= UI 佈局顯示 =================
            col_main1, col_main2 = st.columns([1, 1])
            
            with col_main1:
                st.subheader("圖表視覺化")
                tab1, tab2 = st.tabs(["本命星盤", "日返星盤"])
                with tab1:
                    st.image(img_n, use_container_width=True)
                with tab2:
                    if img_sr: st.image(img_sr, use_container_width=True)
                    else: st.info("請於左側勾選「計算日返星盤」以生成。")
                    
            with col_main2:
                st.subheader("綜合觀測報告")
                st.code(report, language="text") 

    except Exception as e:
        st.error(f"系統執行時發生問題：\n{str(e)}")
