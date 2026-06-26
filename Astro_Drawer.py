import os
import datetime
try:
    import swisseph as swe
except ImportError:
    import pyeph as swe

# ================= 設定區 =================
# 指定 ephe 資料夾路徑 (確保同一個資料夾內有 ephe 資料夾及 .se1 檔案)
EPHE_PATH = os.path.join(os.path.dirname(__file__), 'ephe')
swe.set_ephe_path(EPHE_PATH)

def calculate_chart(utc_datetime, lat, lon, house_system=b'P'):
    """
    根據時間與經緯度計算星盤資料。
    """
    # 1. 轉換時間為小數格式並取得儒略日 (Julian Day)
    year, month, day = utc_datetime.year, utc_datetime.month, utc_datetime.day
    hour_decimal = utc_datetime.hour + (utc_datetime.minute / 60.0) + (utc_datetime.second / 3600.0)
    
    jd = swe.julday(year, month, day, hour_decimal)
    
    # 2. 定義需要計算的星體
    planets_map = {
        '太陽': swe.SUN, '月亮': swe.MOON, '水星': swe.MERCURY,
        '金星': swe.VENUS, '火星': swe.MARS, '木星': swe.JUPITER,
        '土星': swe.SATURN, '天王星': swe.URANUS, '海王星': swe.NEPTUNE,
        '冥王星': swe.PLUTO, '北交點': swe.TRUE_NODE 
    }
    
    positions = {}
    
    # 3. 計算各星體黃道經度
    for name, planet_id in planets_map.items():
        pos, ret = swe.calc_ut(jd, planet_id)
        positions[name] = pos[0] 
        
    # 4. 計算宮位、上升與中天
    cusps, ascmc = swe.houses(jd, lat, lon, house_system)
    
    asc_degree = ascmc[0] # 上升 ASC
    mc_degree = ascmc[1]  # 中天 MC
    
    positions['上升'] = asc_degree
    positions['中天'] = mc_degree
    
    return positions, asc_degree, cusps, mc_degree