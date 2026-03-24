from flask import Flask, request, jsonify
from flask_cors import CORS
import swisseph as swe
from datetime import datetime, timedelta
import calendar

app = Flask(__name__)
CORS(app)
# வார நாட்களுக்கான ராகு, எம, குளிகை நேரங்கள்
TIMINGS = {
    0: {"rk": "07:30-09:00", "ek": "10:30-12:00", "gk": "13:30-15:00"}, # திங்கள்
    1: {"rk": "15:00-16:30", "ek": "09:00-10:30", "gk": "12:00-13:30"}, # செவ்வாய்
    2: {"rk": "12:00-13:30", "ek": "07:30-09:00", "gk": "10:30-12:00"}, # புதன்
    3: {"rk": "13:30-15:00", "ek": "06:00-07:30", "gk": "09:00-10:30"}, # வியாழன்
    4: {"rk": "10:30-12:00", "ek": "15:00-16:30", "gk": "07:30-09:00"}, # வெள்ளி
    5: {"rk": "09:00-10:30", "ek": "13:30-15:00", "gk": "06:00-07:30"}, # சனி
    6: {"rk": "16:30-18:00", "ek": "12:00-13:30", "gk": "15:00-16:30"}  # ஞாயிறு
}
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(round(((deg - d) * 60 - m) * 60))
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d:03d}:{m:02d}:{s:02d}"

def to_short_deg(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    return f"{d}.{m:02d}"

def get_sign_lord(degree):
    lords = ["செவ்", "சுக்", "புத", "சந்", "சூரி", "புத", "சுக்", "செவ்", "குரு", "சனி", "சனி", "குரு"]
    return lords[int((degree % 360) / 30)]

def get_navamsa_sign(deg):
    rasi = int((deg % 360) / 30)
    part = int(((deg % 360) % 30) / (30 / 9.0))
    starts = [0, 9, 6, 3] 
    return (starts[rasi % 4] + part) % 12

def get_rasi_star_pada(degree):
    rasis = ["மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்"]
    stars = ["அஸ்வினி", "பரணி", "கிருத்திகை", "ரோகிணி", "மிருகசீரிடம்", "திருவாதிரை", "புனர்பூசம்", "பூசம்", "ஆயில்யம்",
             "மகம்", "பூரம்", "உத்திரம்", "அஸ்தம்", "சித்திரை", "சுவாதி", "விசாகம்", "அனுஷம்", "கேட்டை",
             "மூலம்", "பூராடம்", "உத்திராடம்", "திருவோணம்", "அவிட்டம்", "சதயம்", "பூரட்டாதி", "உத்திரட்டாதி", "ரேவதி"]
    deg = degree % 360
    se = 40.0 / 3.0
    return rasis[int(deg / 30)], stars[int(deg / se)], int((deg % se) / (se / 4.0)) + 1

def get_all_lords(degree):
    dasa_lords = [("கேது", 7), ("சுக்", 20), ("சூரி", 6), ("சந்", 10), ("செவ்", 7), ("ராகு", 18), ("குரு", 16), ("சனி", 19), ("புத", 17)]
    deg_sec = (degree % 360) * 3600.0
    star_idx = int(deg_sec / 48000.0) % 9
    L1 = dasa_lords[star_idx][0]
    passed_sec = deg_sec % 48000.0
    
    cur_sec = 0.0
    L2, idx2 = "", 0
    for i in range(9):
        idx = (star_idx + i) % 9
        ext_sec = dasa_lords[idx][1] * 400.0
        if passed_sec < cur_sec + ext_sec:
            L2, idx2 = dasa_lords[idx][0], idx
            break
        cur_sec += ext_sec
    if not L2: idx2 = (star_idx + 8) % 9; L2 = dasa_lords[idx2][0]; cur_sec -= dasa_lords[idx2][1] * 400.0
        
    passed_sub_sec = passed_sec - cur_sec
    cur_sub_sec = 0.0
    L3, idx3 = "", 0
    ss_base = (dasa_lords[idx2][1] * 400.0) / 120.0
    for i in range(9):
        idx = (idx2 + i) % 9
        ext_sec = dasa_lords[idx][1] * ss_base
        if passed_sub_sec < cur_sub_sec + ext_sec:
            L3, idx3 = dasa_lords[idx][0], idx
            break
        cur_sub_sec += ext_sec
    if not L3: idx3 = (idx2 + 8) % 9; L3 = dasa_lords[idx3][0]; cur_sub_sec -= dasa_lords[idx3][1] * ss_base
        
    passed_sssl_sec = passed_sub_sec - cur_sub_sec
    cur_sssl_sec = 0.0
    L4 = ""
    sss_base = (dasa_lords[idx3][1] * ss_base) / 120.0
    for i in range(9):
        idx = (idx3 + i) % 9
        ext_sec = dasa_lords[idx][1] * sss_base
        if passed_sssl_sec < cur_sssl_sec + ext_sec:
            L4 = dasa_lords[idx][0]
            break
        cur_sssl_sec += ext_sec
    if not L4: L4 = dasa_lords[(idx3 + 8) % 9][0]
        
    return L1, L2, L3, L4

def get_house_occupied(deg, cusps):
    deg = deg % 360
    for i in range(12):
        s, e = cusps[i], cusps[(i+1)%12]
        if s < e:
            if s <= deg < e: return i+1
        else:
            if deg >= s or deg < e: return i+1
    return 1

def get_kp_horary_lagna(kp_num):
    dasa_lords = [("கேது", 7), ("சுக்", 20), ("சூரி", 6), ("சந்", 10), ("செவ்", 7), ("ராகு", 18), ("குரு", 16), ("சனி", 19), ("புத", 17)]
    current_deg = 0.0
    count = 1
    for star_idx in range(27):
        lord_idx = star_idx % 9
        for sub_i in range(9):
            sub_idx = (lord_idx + sub_i) % 9
            span = (dasa_lords[sub_idx][1] / 120.0) * (40.0 / 3.0)
            next_deg = current_deg + span
            sign_boundary = int(current_deg / 30) * 30 + 30
            
            if round(next_deg, 6) > round(sign_boundary, 6):
                if count == kp_num: return current_deg
                count += 1
                current_deg = sign_boundary
                if count == kp_num: return current_deg
                count += 1
                current_deg = next_deg
            else:
                if count == kp_num: return current_deg
                count += 1
                current_deg = next_deg
    return 0.0

@app.route('/calculate', methods=['POST'])
def calculate_astrology():
    try:
        data = request.json
        dob_str, tob_str = data.get('dob'), data.get('tob')
        lat, lon = float(data.get('lat', 11.12)), float(data.get('lon', 78.00))
        ayanamsa_type = data.get('ayanamsa', 'kp')
        
        is_kp = data.get('is_kp', False)
        raw_kp = data.get('kp_num')
        kp_num = int(raw_kp) if raw_kp else 0

        if len(tob_str.split(':')) == 2: tob_str += ":00"
        dt_ist = datetime.strptime(f"{dob_str} {tob_str}", "%Y-%m-%d %H:%M:%S")
        dt_utc = dt_ist - timedelta(hours=5, minutes=30)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

        if ayanamsa_type == 'lahiri':
            swe.set_sid_mode(swe.SIDM_LAHIRI)
        else:
            swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        horary_jd = jd
        if is_kp and 1 <= kp_num <= 249:
            target_lagna = get_kp_horary_lagna(kp_num) + 0.0001
            for _ in range(15):
                cusps_temp, _ = swe.houses_ex(horary_jd, lat, lon, b'P', flags)
                diff = (target_lagna - cusps_temp[0]) % 360
                if diff > 180: diff -= 360
                if abs(diff) < 0.0001: break
                horary_jd += diff / 360.9856

        cusps_all, _ = swe.houses_ex(horary_jd, lat, lon, b'P', flags)
        cusps = cusps_all[1:13] if len(cusps_all) == 13 else cusps_all[0:12]
        
        p_ids = [swe.SUN, swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.TRUE_NODE]
        p_names = ["சூரி", "சந்", "செவ்", "புத", "குரு", "சுக்", "சனி", "ராகு"]
        planet_positions = {}
        r_deg = 0
        for i, pid in enumerate(p_ids):
            pos, _ = swe.calc_ut(jd, pid, flags)
            deg = pos[0] % 360
            if p_names[i] == "ராகு": r_deg = deg
            L1, L2, L3, L4 = get_all_lords(deg)
            planet_positions[p_names[i]] = {"deg": deg, "stl": L1, "sbl": L2, "ssl": L3, "sssl": L4}
            
        k_deg = (r_deg + 180.0) % 360
        kL1, kL2, kL3, kL4 = get_all_lords(k_deg)
        planet_positions["கேது"] = {"deg": k_deg, "stl": kL1, "sbl": kL2, "ssl": kL3, "sssl": kL4}

        cusp_sbls = {}
        bhavas_data = []
        for i in range(12):
            deg = cusps[i] % 360
            rN, sN, pD = get_rasi_star_pada(deg)
            L1, L2, L3, L4 = get_all_lords(deg)
            cusp_sbls[i+1] = L2
            bhavas_data.append({"cs": str(i+1), "deg": deg, "dms": to_dms(deg), "short_deg": to_short_deg(deg), "rasi": rN, "star": sN, "pada": pD, "stl": L1, "bhu": L2, "and": L3, "sssl": L4, "rasi_no": int(deg / 30), "nav_rasi_no": get_navamsa_sign(deg)})

        sig_map = {}
        sbl_map = {p: [] for p in list(planet_positions.keys())}
        for c, lord in cusp_sbls.items():
            if lord in sbl_map: sbl_map[lord].append(int(c))
            
        for p, data_p in planet_positions.items():
            if len(sbl_map[p]) > 0:
                sorted_cusps = sorted(sbl_map[p])
                sig_map[p] = ", ".join([str(x) for x in sorted_cusps])
            else:
                occ = get_house_occupied(data_p["deg"], cusps)
                sig_map[p] = f"{occ}$"

        planets_data = []
        planet_sig_data = []
        for p, data_p in planet_positions.items():
            deg = data_p["deg"]
            rN, sN, pD = get_rasi_star_pada(deg)
            planets_data.append({"pln": p, "deg": deg, "dms": to_dms(deg), "short_deg": to_short_deg(deg), "rasi": rN, "star": sN, "pada": pD, "stl": data_p["stl"], "sbl": data_p["sbl"], "ssl": data_p["ssl"], "sssl": data_p["sssl"], "rasi_no": int(deg / 30), "nav_rasi_no": get_navamsa_sign(deg)})
            planet_sig_data.append({
                "pln": p, "p_sig": sig_map.get(p, ""), "stl": data_p["stl"], "stl_sig": sig_map.get(data_p["stl"], ""), 
                "sbl": data_p["sbl"], "sbl_sig": sig_map.get(data_p["sbl"], ""), "ssl": data_p["ssl"], "ssl_sig": sig_map.get(data_p["ssl"], "")
            })

        cusp_sig_data = []
        for i in range(12):
            c_sbl = cusp_sbls[i+1]
            stl_of_sbl = planet_positions[c_sbl]["stl"] if c_sbl in planet_positions else ""
            sbl_of_sbl = planet_positions[c_sbl]["sbl"] if c_sbl in planet_positions else ""
            ssl_of_sbl = planet_positions[c_sbl]["ssl"] if c_sbl in planet_positions else ""
            cusp_sig_data.append({
                "cs": str(i+1), "sbl": c_sbl, "sbl_sig": sig_map.get(c_sbl, ""), "stl": stl_of_sbl, "stl_sig": sig_map.get(stl_of_sbl, ""), 
                "sub": sbl_of_sbl, "sub_sig": sig_map.get(sbl_of_sbl, ""), "ssl": ssl_of_sbl, "ssl_sig": sig_map.get(ssl_of_sbl, "")
            })

        dasa_lords = [("கேது", 7), ("சுக்", 20), ("சூரி", 6), ("சந்", 10), ("செவ்", 7), ("ராகு", 18), ("குரு", 16), ("சனி", 19), ("புத", 17)]
        se = 40.0 / 3.0
        
        moon_deg = planet_positions["சந்"]["deg"]
        m_idx = int((moon_deg % 360) / se) % 9
        m_bal_years = ((se - ((moon_deg % 360) % se)) / se) * dasa_lords[m_idx][1]
        m_past_years = dasa_lords[m_idx][1] - m_bal_years
        m_theory_start_dt = dt_ist - timedelta(days=m_past_years * 365.2425)

        lagna_deg = cusps[0] % 360
        l_idx = int((lagna_deg % 360) / se) % 9
        l_bal_years = ((se - ((lagna_deg % 360) % se)) / se) * dasa_lords[l_idx][1]
        l_past_years = dasa_lords[l_idx][1] - l_bal_years
        l_theory_start_dt = dt_ist - timedelta(days=l_past_years * 365.2425)

        basic_info = {
            "lagna": bhavas_data[0]['rasi'], "lagna_star": bhavas_data[0]['star'], 
            "moon_rasi": next(p['rasi'] for p in planets_data if p['pln'] == 'சந்'), 
            "moon_star": next(p['star'] for p in planets_data if p['pln'] == 'சந்'),
            "birth_dt": dt_ist.strftime("%Y-%m-%dT%H:%M:%S"),
            "theory_start_dt": m_theory_start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "dasa_start_idx": m_idx,
            "l_theory_start_dt": l_theory_start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "l_dasa_start_idx": l_idx,
            "day_of_week": dt_ist.weekday()
        }

        return jsonify({"status": "success", "bhavas": bhavas_data, "planets": planets_data, "basic_info": basic_info, "planet_sigs": planet_sig_data, "cusp_sigs": cusp_sig_data})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/transit', methods=['POST'])
def calculate_transit_only():
    try:
        data = request.json
        dt_str = data.get('datetime')
        lat = float(data.get('lat', 11.12))
        lon = float(data.get('lon', 78.00))
        ayanamsa_type = data.get('ayanamsa', 'kp')

        dt_ist = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        dt_utc = dt_ist - timedelta(hours=5, minutes=30)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

        if ayanamsa_type == 'lahiri':
            swe.set_sid_mode(swe.SIDM_LAHIRI)
        else:
            swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        t_planets_list = []
        t_p_ids = [swe.SUN, swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.TRUE_NODE]
        t_p_names = ["சூரி", "சந்", "செவ்", "புத", "குரு", "சுக்", "சனி", "ராகு"]
        t_r_deg = 0

        for i, pid in enumerate(t_p_ids):
            pos, _ = swe.calc_ut(jd, pid, flags)
            deg = pos[0] % 360
            if t_p_names[i] == "ராகு": t_r_deg = deg
            L1, L2, L3, L4 = get_all_lords(deg)
            rN, sN, pD = get_rasi_star_pada(deg)
            t_planets_list.append({"pln": t_p_names[i], "rasi_no": int(deg / 30), "star": sN, "pada": pD, "stl": L1, "sbl": L2, "ssl": L3, "sssl": L4})
            
        t_k_deg = (t_r_deg + 180.0) % 360
        kL1, kL2, kL3, kL4 = get_all_lords(t_k_deg)
        krN, ksN, kpD = get_rasi_star_pada(t_k_deg)
        t_planets_list.append({"pln": "கேது", "rasi_no": int(t_k_deg / 30), "star": ksN, "pada": kpD, "stl": kL1, "sbl": kL2, "ssl": kL3, "sssl": kL4})
        
        t_cusps_all, _ = swe.houses_ex(jd, lat, lon, b'P', flags)
        t_cusps = t_cusps_all[1:13] if len(t_cusps_all) == 13 else t_cusps_all[0:12]
        tl_deg = t_cusps[0] % 360
        tl_L1, tl_L2, tl_L3, tl_L4 = get_all_lords(tl_deg)
        tl_rN, tl_sN, tl_pD = get_rasi_star_pada(tl_deg)
        t_planets_list.append({"pln": "லக்", "rasi_no": int(tl_deg / 30), "star": tl_sN, "pada": tl_pD, "stl": tl_L1, "sbl": tl_L2, "ssl": tl_L3, "sssl": tl_L4})

        return jsonify({"status": "success", "t_planets": t_planets_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# --- புதிய மாதாந்திர பஞ்சாங்க கணித வழி (Monthly Panchangam Route) ---
@app.route('/monthly_panchangam', methods=['POST'])
def monthly_panchangam():
    try:
        data = request.json
        year = int(data.get('year'))
        month = int(data.get('month'))
        ayanamsa_type = data.get('ayanamsa', 'kp')
        
        if ayanamsa_type == 'lahiri':
            swe.set_sid_mode(swe.SIDM_LAHIRI)
        else:
            swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        num_days = calendar.monthrange(year, month)[1]
        days_data = []

        tithi_names = ["பிரதமை", "துவிதியை", "திருதியை", "சதுர்த்தி", "பஞ்சமி", "சஷ்டி", "சப்தமி", "அஷ்டமி", "நவமி", "தசமி", "ஏகாதசி", "துவாதசி", "திரயோதசி", "சதுர்த்தசி", "பௌர்ணமி", "பிரதமை", "துவிதியை", "திருதியை", "சதுர்த்தி", "பஞ்சமி", "சஷ்டி", "சப்தமி", "அஷ்டமி", "நவமி", "தசமி", "ஏகாதசி", "துவாதசி", "திரயோதசி", "சதுர்த்தசி", "அமாவாசை"]
        star_names = ["அஸ்வினி", "பரணி", "கிருத்திகை", "ரோகிணி", "மிருகசீரிடம்", "திருவாதிரை", "புனர்பூசம்", "பூசம்", "ஆயில்யம்", "மகம்", "பூரம்", "உத்திரம்", "அஸ்தம்", "சித்திரை", "சுவாதி", "விசாகம்", "அனுஷம்", "கேட்டை", "மூலம்", "பூராடம்", "உத்திராடம்", "திருவோணம்", "அவிட்டம்", "சதயம்", "பூரட்டாதி", "உத்திரட்டாதி", "ரேவதி"]

        for d in range(1, num_days + 1):
            # அதிகாலை 6 மணி நிலவரப்படி கணிதம்
            dt = datetime(year, month, d, 6, 0, 0)
            dt_utc = dt - timedelta(hours=5, minutes=30)
            jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

            sun_pos, _ = swe.calc_ut(jd, swe.SUN, flags)
            moon_pos, _ = swe.calc_ut(jd, swe.MOON, flags)
            rahu_pos, _ = swe.calc_ut(jd, swe.TRUE_NODE, flags)

            sun_deg = sun_pos[0] % 360
            moon_deg = moon_pos[0] % 360
            rahu_deg = rahu_pos[0] % 360
            ketu_deg = (rahu_deg + 180) % 360

            diff = (moon_deg - sun_deg) % 360
            tithi_idx = int(diff / 12)
            star_idx = int(moon_deg / (360/27.0))

            events = []
            
            # திதி விசேஷங்கள்
            if tithi_idx == 14: events.append({"name": "பௌர்ணமி 🌕", "type": "full"})
            elif tithi_idx == 29: events.append({"name": "அமாவாசை 🌑", "type": "new"})
            elif tithi_idx == 10 or tithi_idx == 25: events.append({"name": "ஏகாதசி", "type": "vrat"})
            elif tithi_idx == 12 or tithi_idx == 27: events.append({"name": "பிரதோஷம்", "type": "vrat"})
            elif tithi_idx == 5 or tithi_idx == 20: events.append({"name": "சஷ்டி", "type": "vrat"})
            elif tithi_idx == 3: events.append({"name": "சதுர்த்தி", "type": "vrat"})
            elif tithi_idx == 18: events.append({"name": "சங்கடஹர சதுர்த்தி", "type": "vrat"})
            
            # சுப முகூர்த்தம் (வளர்பிறை + சுப திதி)
            is_valarpirai = diff < 180
            good_tithis = [1, 2, 4, 6, 9, 10, 12] 
            if is_valarpirai and tithi_idx in good_tithis:
                events.append({"name": "சுப முகூர்த்தம் 🌸", "type": "muhurtham"})

            # கிரகணங்கள் (ராகு/கேதுவுடன் சந்திரன் நெருக்கம்)
            dist_rahu = min(abs(moon_deg - rahu_deg), 360 - abs(moon_deg - rahu_deg))
            dist_ketu = min(abs(moon_deg - ketu_deg), 360 - abs(moon_deg - ketu_deg))
            dist_node = min(dist_rahu, dist_ketu)
            
            if tithi_idx == 14 and dist_node < 15: events.append({"name": "சந்திர கிரகணம் 🌘", "type": "eclipse"})
            if tithi_idx == 29 and dist_node < 15: events.append({"name": "சூரிய கிரகணம் 🌞", "type": "eclipse"})

            # வாஸ்து நாட்கள் (பொதுவான தோராய தேதிகள்)
            vastu_dates = [(1,26), (2,22), (4,23), (5,8), (6,4), (7,27), (8,22), (10,28), (11,22)]
            if (month, d) in vastu_dates: events.append({"name": "வாஸ்து நாள் 🏠", "type": "vastu"})

            # கிழமை
            weekday = dt.weekday() # 0 = Monday, 6 = Sunday

            days_data.append({
                "date": d,
                "weekday": weekday,
                "tithi": tithi_names[tithi_idx],
                "star": star_names[star_idx],
                "events": events
            })

        return jsonify({"status": "success", "month": month, "year": year, "data": days_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # ஆன்லைனில் பதிவேற்றும்போது '0.0.0.0' என்பது அவசியம்
    app.run(host='0.0.0.0', port=5000)