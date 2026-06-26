import streamlit as st
import datetime
from kerykeion import KrInstance
import matplotlib.pyplot as plt  # 👈 補上這一行！
import numpy as np               # 👈 順便檢查有沒有這一行，因為你後面繪圖有用到 np.deg2rad
import os
import io
import numpy as np
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz


st.set_page_config(page_title="星盤測試", layout="wide")
st.title("🔮 星盤測試")

if st.button("測試計算"):
    try:
        chart = KrInstance("Test", 1993, 9, 27, 12, 0, lat=53.48, lng=-2.24)  # Manchester
        chart.make_chart()
        st.success("✅ kerykeion 安裝成功！")
        st.json(chart.get_all())
    except Exception as e:
        st.error(f"錯誤: {e}")

# ==================== 【重要修改】使用 kerykeion ====================
from kerykeion import KrInstance   # 新增

# ================= 1. 基礎設定與常數 =================
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans'] 
plt.rcParams['axes.unicode_minus'] = False

ZODIAC_SYMBOLS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']
ZODIAC_NAMES = ['牡羊', '金牛', '雙子', '巨蟹', '獅子', '處女', '天秤', '天蠍', '射手', '摩羯', '水瓶', '雙魚']

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

# ================= 2. 核心函數 (完全保留原本嘅計算同畫圖) =================
EPHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ephe')
swe.set_ephe_path(EPHE_PATH)

def format_degree(lon):
    idx = int(lon // 30) % 12
    deg = int(lon % 30)
    mins = int(round((lon % 1) * 60))
    if mins == 60:
        mins = 0; deg += 1
        if deg == 30: deg = 0; idx = (idx + 1) % 12
    return f"{ZODIAC_NAMES[idx]}({deg}°{mins:02d})"

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
    for name, planet_id in planets_map.items():
        pos, _ = swe.calc_ut(jd, planet_id)
        positions[name] = pos[0] 
    cusps, ascmc = swe.houses(jd, lat, lon, house_system)
    positions['上升'] = ascmc[0]
    positions['中天'] = ascmc[1]
    return positions, ascmc[0], cusps, ascmc[1]

def draw_astrology_chart(positions, asc_degree, cusps, orb_map, aspect_system):
    aspects = []
    specs = [(0, "合相", '#95a5a6'), (180, "對相", '#2980b9'), (120, "三分", '#27ae60'), (90, "四分", '#e74c3c'), (60, "六分", '#2ecc71')]
    p_names = [p for p in positions.keys() if p in PLANET_SYMBOLS]
    for i in range(len(p_names)):
        for j in range(i+1, len(p_names)):
            p1, p2 = p_names[i], p_names[j]
            diff = abs(positions[p1] - positions[p2])
            if diff > 180: diff = 360 - diff
            for angle, name, color in specs:
                allowed_orb = LILLY_MOITIES.get(p1, 2.5) + LILLY_MOITIES.get(p2, 2.5) if aspect_system == "古典 (威廉・里利)" else orb_map.get(name, 8.0)
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
    location = Nominatim(user_agent="astro_st_app").geocode(loc_name)
    if not location: 
        raise ValueError(f"無法定位城市: '{loc_name}'")
    
    lat, lon = location.latitude, location.longitude
    tz_str = TimezoneFinder().timezone_at(lng=lon, lat=lat) or "UTC"
    local_dt = pytz.timezone(tz_str).localize(datetime.datetime(y, m, d, h, minute))
    utc_dt = local_dt.astimezone(pytz.utc)
    
    info = f"城市: {location.address}\n座標: {lat:.4f}°N, {lon:.4f}°E\n時區: {tz_str}\n時間: {local_dt.strftime('%Y-%m-%d %H:%M')}\n"
    return utc_dt, lat, lon, info

def calculate_chart_kerykeion(utc_dt, lat, lon, name="Native"):
    """使用 kerykeion 計算星盤"""
    chart = KrInstance(name, utc_dt.year, utc_dt.month, utc_dt.day, 
                      utc_dt.hour, utc_dt.minute, lat, lon)
    chart.make_chart()
    return chart
# ================= 3. Streamlit UI 介面 =================
st.set_page_config(page_title="專業星盤系統", layout="wide")
st.title("🔮 進階專業星盤推運系統")
custom_orbs = {"合相": 8.0, "對相": 8.0, "三分": 7.0, "四分": 7.0, "六分": 6.0}

# --- 側邊欄設定 ---
st.sidebar.header("本命盤基本資訊")
name = st.sidebar.text_input("姓名", "Vincent")
gender = st.sidebar.selectbox("性別", ["男", "女"])

col1, col2, col3 = st.sidebar.columns(3)
n_year = col1.number_input("年", value=1993, step=1)
n_month = col2.number_input("月", value=9, min_value=1, max_value=12)
n_day = col3.number_input("日", value=27, min_value=1, max_value=31)

col4, col5 = st.sidebar.columns(2)
n_hour = col4.number_input("時", value=12, min_value=0, max_value=23)
n_minute = col5.number_input("分", value=0, min_value=0, max_value=59)
n_loc = st.sidebar.text_input("出生城市", "Manchester")

st.sidebar.divider()
st.sidebar.header("推運 / 行運 / 日返設定")
col6, col7, col8 = st.sidebar.columns(3)
p_year = col6.number_input("推運 年", value=2026, step=1)
p_month = col7.number_input("推運 月", value=6, min_value=1, max_value=12)
p_day = col8.number_input("推運 日", value=26, min_value=1, max_value=31)

col9, col10 = st.sidebar.columns(2)
p_hour = col9.number_input("推運 時", value=12, min_value=0, max_value=23)
p_minute = col10.number_input("推運 分", value=0, min_value=0, max_value=59)
p_loc = st.sidebar.text_input("目標城市", "Manchester")

h_sys_name = st.sidebar.selectbox("宮位系統", ["普拉西度 (Placidus)", "整宮制 (Whole Sign)", "Regiomontanus"])
a_sys_name = st.sidebar.selectbox("相位系統", ["現代", "古典 (威廉・里利)"])

st.sidebar.subheader("進階功能選項")
chk_greek = st.sidebar.checkbox("七大希臘點")
chk_midpoint = st.sidebar.checkbox("顯示中點")
chk_whole_rule = st.sidebar.checkbox("宮主星整宮制")
chk_solar_arc = st.sidebar.checkbox("真實日弧相位")
chk_profection = st.sidebar.checkbox("顯示小限歲數")
chk_solar_return = st.sidebar.checkbox("計算日返星盤")
chk_transit = st.sidebar.checkbox("計算過運行運")

# --- 主計算按鈕 ---
if st.sidebar.button("🔮 執行占星整合計算", use_container_width=True, type="primary"):
    try:
        with st.spinner('天文運算中...'):
            h_code = b'W' if "整宮" in h_sys_name else (b'R' if "Regiomontanus" in h_sys_name else b'P')
            
            # 解析時間與地點
            jd_n, lat_n, lon_n, meta_n, dt_n_utc = resolve_location_and_time(n_loc, n_year, n_month, n_day, n_hour, n_minute)
            jd_p, lat_p, lon_p, meta_p, dt_p_utc = resolve_location_and_time(p_loc, p_year, p_month, p_day, p_hour, p_minute)
            
            # 本命盤計算與繪圖
            pos_n, asc_n, cusps_n, mc_n = calculate_chart_engine(jd_n, lat_n, lon_n, h_code)
            img_n = draw_astrology_chart(pos_n, asc_n, cusps_n, custom_orbs, a_sys_name)
            
            # 組織報告文字
            report = f"== 命盤基本觀測 ==\n持有人：{name} ({gender})\n{meta_n}\n"
            report += "【星體與交點位置】\n"
            for k in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星', '北交點', '上升', '中天']:
                report += f"{k}：{format_degree(pos_n[k])} {get_house_number(pos_n[k], cusps_n, h_code)}宮\n"

            # 簡化版報告生成 (此處省略部分 if 邏輯以保持精簡，可將原本 Tkinter 的 report 組合邏輯完整貼上)
            if chk_transit:
                pos_t, _, _, _ = calculate_chart_engine(jd_p, lat_p, lon_p, h_code)
                report += f"\n\n【行運觀測資訊】\n目標城市：{p_loc}\n"
                for k in ['太陽', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
                    report += f"[運]{k} ：{format_degree(pos_t[k])} [命] {get_house_number(pos_t[k], cusps_n, h_code)}宮\n"

            # 日返盤計算與繪圖
            img_sr = None
            if chk_solar_return:
                jd_approx = swe.julday(p_year, dt_n_utc.month, dt_n_utc.day, 12.0)
                def sun_diff(j_val): return ((swe.calc_ut(j_val, swe.SUN)[0][0] - pos_n['太陽'] + 180) % 360 - 180)
                j1, j2 = jd_approx - 2, jd_approx + 2
                f1, f2 = sun_diff(j1), sun_diff(j2)
                for _ in range(15):
                    if abs(f2 - f1) < 1e-11: break
                    j_next = j2 - f2 * (j2 - j1) / (f2 - f1)
                    j1, j2, f1 = j2, j_next, f2
                    f2 = sun_diff(j2)
                
                pos_sr, asc_sr, cusps_sr, mc_sr = calculate_chart_engine(j2, lat_p, lon_p, h_code)
                img_sr = draw_astrology_chart(pos_sr, asc_sr, cusps_sr, custom_orbs, a_sys_name)
                report += f"\n\n【精確日返返照報告已生成】\n"

            # UI 佈局顯示
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
                st.code(report, language="text") # 用 st.code 會自帶右上角「一鍵複製」按鈕！

    except Exception as e:
        st.error(f"系統執行時發生問題：\n{str(e)}")
