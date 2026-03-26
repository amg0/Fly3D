import pydeck as pdk
import pandas as pd
import gpxpy
import os
import webbrowser
import subprocess
import platform
import json

# ==========================================
# FONCTIONS DE SÉLECTION DE FICHIER 
# ==========================================

def choisir_fichier_gpx_mac():
    print("Ouverture de la fenêtre de sélection Mac...")
    script_apple = '''
    set leFichier to choose file with prompt "Sélectionnez votre trace ou route SDVFR (fichier .gpx)"
    POSIX path of leFichier
    '''
    try:
        resultat = subprocess.run(
            ['osascript', '-e', script_apple], 
            capture_output=True, text=True, check=True
        )
        return resultat.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def choisir_fichier_gpx_windows():
    print("Ouverture de la fenêtre de sélection Windows...")
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True) 
    
    fichier = filedialog.askopenfilename(
        title="Sélectionnez votre trace ou route SDVFR (fichier .gpx)",
        filetypes=[("Fichiers GPX", "*.gpx"), ("Tous les fichiers", "*.*")]
    )
    return fichier

def choisir_fichier_gpx():
    systeme = platform.system()
    if systeme == "Darwin":
        return choisir_fichier_gpx_mac()
    else:
        return choisir_fichier_gpx_windows()

# ==========================================
# FONCTIONS DE TRAITEMENT DES DONNÉES
# ==========================================

def charger_aeroports_france():
    url = "https://davidmegginson.github.io/ourairports-data/airports.csv"
    try:
        print("⬇️ Téléchargement en cours de la base de données des aéroports...")
        df = pd.read_csv(url, low_memory=False)
        
        # Nettoyage des données pour éviter les variables vides
        df = df[df['iso_country'] == 'FR']
        df = df[df['type'] != 'closed']
        df = df.dropna(subset=['longitude_deg', 'latitude_deg'])
        
        df['elevation_m'] = (df['elevation_ft'].fillna(0) * 0.3048) + 80
        df['etiquette'] = df.apply(
            lambda row: str(row['local_code']) if pd.notna(row['local_code']) and str(row['local_code']).strip() != '' else str(row['ident']), 
            axis=1
        )
        
        df['tooltip_html'] = "<b>" + df['etiquette'] + "</b> - " + df['name'] + "<br/><i>Type: " + df['type'] + "</i>"
        
        def get_color(airport_type):
            if airport_type == 'large_airport': return [0, 50, 255, 120]
            elif airport_type == 'medium_airport': return [0, 150, 255, 120]
            elif airport_type == 'small_airport': return [100, 200, 255, 120]
            else: return [200, 200, 200, 90]
            
        def get_radius(airport_type):
            if airport_type == 'large_airport': return 1000
            elif airport_type == 'medium_airport': return 600
            elif airport_type == 'small_airport': return 300
            else: return 150

        df['couleur'] = df['type'].apply(get_color)
        df['rayon'] = df['type'].apply(get_radius)
        
        # SOLUTION ANTI-PLANTAGE WINDOWS : On convertit le DataFrame en objets Python purs
        records = df.to_dict(orient='records')
        clean_records = []
        for r in records:
            clean_records.append({
                'longitude_deg': float(r['longitude_deg']),
                'latitude_deg': float(r['latitude_deg']),
                'elevation_m': float(r['elevation_m']),
                'couleur': r['couleur'],
                'rayon': int(r['rayon']),
                'etiquette': str(r['etiquette']),
                'tooltip_html': str(r['tooltip_html'])
            })
            
        print(f"✅ {len(clean_records)} aéroports/aérodromes français chargés avec succès.")
        return clean_records
        
    except Exception as e:
        print(f"⚠️ Impossible de charger les aéroports : {e}")
        return []

def lire_gpx_universel(chemin_fichier):
    donnees_vol = []
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            points_bruts = []
            
            for track in gpx.tracks:
                for segment in track.segments:
                    points_bruts.extend(segment.points)
                    
            for route in gpx.routes:
                points_bruts.extend(route.points)
                
            for point in points_bruts:
                air_alt = point.elevation if point.elevation is not None else 0
                terr_alt = 0  
                spd = 0
                crs = 0
                
                if point.description:
                    try:
                        desc_data = json.loads(point.description)
                        if 'alt' in desc_data and 'ele' in desc_data:
                            air_alt = desc_data['alt']
                            terr_alt = desc_data['ele']
                        spd = desc_data.get('spd', 0)
                        crs = desc_data.get('crs', 0)
                    except json.JSONDecodeError:
                        pass
                
                donnees_vol.append({
                    'lon': point.longitude,
                    'lat': point.latitude,
                    'air_alt': air_alt,
                    'terr_alt': terr_alt,
                    'spd': spd,
                    'crs': crs
                })
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return []
    return donnees_vol

def calculer_centre(flight_data):
    if not flight_data:
        return 0.0, 0.0
    avg_lon = float(sum(pt['lon'] for pt in flight_data) / len(flight_data))
    avg_lat = float(sum(pt['lat'] for pt in flight_data) / len(flight_data))
    return avg_lon, avg_lat

# ==========================================
# GESTION DES BOUTONS DE CONTRÔLE CAMERA
# ==========================================

def generer_controles_html(centre_lon, centre_lat, donnees_vol, init_zoom=10, init_pitch=65):
    css = """
    <style>
        #control-panel {
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            gap: 10px;
            font-family: Arial, sans-serif;
            font-size: 13px; 
            width: 220px;
        }
        .control-group { display: flex; gap: 5px; align-items: center; justify-content: space-between; }
        .btn-container { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
        
        #control-panel button {
            background-color: #007bff; color: white; border: none;
            padding: 6px 10px; border-radius: 4px; cursor: pointer;
            font-weight: bold; transition: background 0.2s;
            user-select: none;
        }
        .btn-small {
            padding: 6px 8px !important;
            min-width: 30px !important;
            text-align: center;
        }
        
        #control-panel button:hover { background-color: #0056b3; }
        #control-panel button:active { background-color: #004085; }
        #control-panel h3 { margin: 0 0 5px 0; font-size: 15px; text-align: center; color: #333; }
        
        #btn-play { background-color: #28a745; width: 100%; margin-top: 5px; padding: 8px; }
        #btn-play:hover { background-color: #218838; }
        
        .val-display { font-weight: bold; width: 45px; text-align: center; display: inline-block; font-size: 12px; }
    </style>
    """
    
    html = """
    <div id="control-panel">
        <h3>Caméra PyDeck</h3>
        
        <div class="control-group">
            <span>Zoom</span>
            <div class="btn-container">
                <button class="btn-small" onclick="changeView('zoomOut')">－</button>
                <button class="btn-small" onclick="changeView('zoomIn')">＋</button>
            </div>
        </div>
        
        <div class="control-group">
            <span>Inclinaison</span>
            <div class="btn-container">
                <button class="btn-small" onclick="changeView('pitchDown')">⬇</button>
                <button class="btn-small" onclick="changeView('pitchUp')">⬆</button>
            </div>
        </div>
        
        <div class="control-group">
            <span>Hauteur Cam</span>
            <div class="btn-container">
                <button class="btn-small" onmousedown="startAltChange(-20)" onmouseup="stopAltChange()" onmouseleave="stopAltChange()">－</button>
                <span id="alt-val" class="val-display">10m</span>
                <button class="btn-small" onmousedown="startAltChange(20)" onmouseup="stopAltChange()" onmouseleave="stopAltChange()">＋</button>
            </div>
        </div>
        
        <div class="control-group">
            <span>Vitesse</span>
            <div class="btn-container">
                <button class="btn-small" onmousedown="startSpeedChange(-0.25)" onmouseup="stopSpeedChange()" onmouseleave="stopSpeedChange()">－</button>
                <span id="speed-val" class="val-display">1x</span>
                <button class="btn-small" onmousedown="startSpeedChange(0.25)" onmouseup="stopSpeedChange()" onmouseleave="stopSpeedChange()">＋</button>
            </div>
        </div>
        
        <button onclick="changeView('center')" style="width:100%; padding: 6px;">Recentrer la vue</button>
        <hr style="width:100%; border:0; border-top:1px solid #ccc; margin: 0;">
        <button id="btn-play" onclick="toggleFlight()">▶️ Revivre le vol</button>
    </div>
    """
    
    vol_json = json.dumps(donnees_vol)
    
    js = f"""
    <script>
        const centerPos = {{ longitude: {centre_lon}, latitude: {centre_lat} }};
        const defaultZoom = {init_zoom};
        const defaultPitch = {init_pitch};
        const defaultBearing = 45;

        let altOffset = 10;
        let altInterval = null;
        let speedMultiplier = 1.0;
        let speedInterval = null; 

        function customViewStateChange({{viewState}}) {{
            let deckObj = window.deckInstance;
            let currentZ = 0;
            
            if (deckObj && deckObj.props.viewState && deckObj.props.viewState.position) {{
                currentZ = deckObj.props.viewState.position[2];
            }} else if (deckObj && deckObj.props.initialViewState && deckObj.props.initialViewState.position) {{
                currentZ = deckObj.props.initialViewState.position[2];
            }}
            
            viewState.position = [0, 0, currentZ];
            viewState.maxPitch = 89; 
            
            deckObj.setProps({{viewState: viewState}});
        }}

        function changeAltOffset(delta) {{
            altOffset += delta;
            document.getElementById('alt-val').innerText = altOffset + "m";
            
            let deckObj = window.deckInstance;
            if (deckObj && !isFlying) {{
                let currentViewState = deckObj.props.viewState || deckObj.props.initialViewState;
                let newViewState = {{ ...currentViewState }};
                
                let currentZ = newViewState.position ? newViewState.position[2] : 0;
                newViewState.position = [0, 0, currentZ + delta];
                newViewState.maxPitch = 89; 
                
                newViewState.transitionDuration = 100; 
                deckObj.setProps({{ 
                    viewState: newViewState,
                    onViewStateChange: customViewStateChange
                }});
            }}
        }}

        function startAltChange(delta) {{
            changeAltOffset(delta); 
            altInterval = setInterval(() => {{
                changeAltOffset(delta); 
            }}, 120); 
        }}

        function stopAltChange() {{
            if (altInterval) {{
                clearInterval(altInterval);
                altInterval = null;
            }}
        }}

        function changeSpeed(delta) {{
            speedMultiplier = Math.round((speedMultiplier + delta) * 100) / 100;
            if (speedMultiplier < 0.25) speedMultiplier = 0.25;
            if (speedMultiplier > 5.0) speedMultiplier = 5.0;
            
            let displayValue = Number.isInteger(speedMultiplier) ? speedMultiplier + "x" : speedMultiplier.toFixed(2) + "x";
            document.getElementById('speed-val').innerText = displayValue;
        }}

        function startSpeedChange(delta) {{
            changeSpeed(delta); 
            speedInterval = setInterval(() => {{
                changeSpeed(delta); 
            }}, 150); 
        }}

        function stopSpeedChange() {{
            if (speedInterval) {{
                clearInterval(speedInterval);
                speedInterval = null;
            }}
        }}

        function changeView(action) {{
            let deckObj = window.deckInstance;
            if (!deckObj) return;
            if (isFlying) toggleFlight(); 
            
            let currentViewState = deckObj.props.viewState || deckObj.props.initialViewState;
            if (!currentViewState) return;
            let newViewState = {{ ...currentViewState }};
            newViewState.maxPitch = 89; 

            switch (action) {{
                case 'zoomIn': newViewState.zoom += 0.8; break;
                case 'zoomOut': newViewState.zoom -= 0.8; break;
                case 'pitchUp': newViewState.pitch = Math.min(newViewState.pitch + 15, 89); break; 
                case 'pitchDown': newViewState.pitch = Math.max(newViewState.pitch - 15, 0); break;
                case 'center':
                    newViewState.longitude = centerPos.longitude;
                    newViewState.latitude = centerPos.latitude;
                    newViewState.position = [0, 0, 0]; 
                    newViewState.zoom = defaultZoom;
                    newViewState.pitch = defaultPitch;
                    newViewState.bearing = defaultBearing;
                    break;
            }}

            newViewState.transitionDuration = 800; 
            deckObj.setProps({{ 
                viewState: newViewState,
                onViewStateChange: customViewStateChange 
            }});
        }}

        const flightData = {vol_json};
        let segments = [];
        let totalDist = 0;

        function calcDist(p1, p2) {{
            let R = 6371e3; 
            let lat1 = p1.lat * Math.PI/180;
            let lat2 = p2.lat * Math.PI/180;
            let dLat = (p2.lat-p1.lat) * Math.PI/180;
            let dLon = (p2.lon-p1.lon) * Math.PI/180;
            let a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon/2) * Math.sin(dLon/2);
            let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }}

        function calcBearing(p1, p2) {{
            let lat1 = p1.lat * Math.PI/180;
            let lat2 = p2.lat * Math.PI/180;
            let dLon = (p2.lon - p1.lon) * Math.PI/180;
            let y = Math.sin(dLon) * Math.cos(lat2);
            let x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
            let brng = Math.atan2(y, x) * 180 / Math.PI;
            return (brng + 360) % 360;
        }}
        
        for(let i = 0; i < flightData.length - 1; i++) {{
            let p1 = flightData[i];
            let p2 = flightData[i+1];
            let dist = calcDist(p1, p2);
            let brng = calcBearing(p1, p2); 
            
            segments.push({{p1: p1, p2: p2, dist: dist, brng: brng}});
            totalDist += dist;
        }}

        let isFlying = false;
        let flownDist = 0;
        let lastTime = 0;
        let animFrame;
        let currentBrng = null;
        let currentZoom = 15.5; 
        let currentSegIdx = 0;
        let currentSegAccum = 0;

        function getPointAtDist(targetDist, startIdx, startAccum) {{
            if (targetDist >= totalDist) return {{ pos: segments[segments.length - 1].p2, idx: segments.length - 1, accum: totalDist }};
            let d = startAccum;
            for (let i = startIdx; i < segments.length; i++) {{
                if (d + segments[i].dist >= targetDist) {{
                    let prog = segments[i].dist > 0 ? (targetDist - d) / segments[i].dist : 0;
                    return {{
                        pos: {{
                            lon: segments[i].p1.lon + (segments[i].p2.lon - segments[i].p1.lon) * prog,
                            lat: segments[i].p1.lat + (segments[i].p2.lat - segments[i].p1.lat) * prog,
                            alt: segments[i].p1.air_alt + (segments[i].p2.air_alt - segments[i].p1.air_alt) * prog
                        }},
                        idx: i,
                        accum: d,
                        brng: segments[i].brng
                    }};
                }}
                d += segments[i].dist;
            }}
            return {{ pos: segments[segments.length - 1].p2, idx: segments.length - 1, accum: d, brng: segments[segments.length - 1].brng }};
        }}

        function toggleFlight() {{
            let btn = document.getElementById('btn-play');
            let deckObj = window.deckInstance;
            
            if (isFlying) {{
                isFlying = false;
                cancelAnimationFrame(animFrame);
                btn.innerHTML = "▶️ Revivre le vol";
                btn.style.backgroundColor = "#28a745"; 
                lastTime = 0;
                
                if (deckObj && deckObj.props.viewState) {{
                    let finalState = {{ ...deckObj.props.viewState }};
                    finalState.transitionDuration = 0;
                    finalState.maxPitch = 89; 
                    deckObj.setProps({{
                        viewState: finalState,
                        onViewStateChange: customViewStateChange
                    }});
                }}
            }} else {{
                isFlying = true;
                btn.innerHTML = "⏹️ Arrêter le vol";
                btn.style.backgroundColor = "#dc3545"; 
                if (flownDist >= totalDist) {{
                    flownDist = 0;
                    currentSegIdx = 0;
                    currentSegAccum = 0;
                    currentBrng = null;
                }}
                animFrame = requestAnimationFrame(animateFlight);
            }}
        }}

        function animateFlight(time) {{
            if (!isFlying) return;
            if (!lastTime) lastTime = time;
            let dt = time - lastTime;
            lastTime = time;
            
            let baseSpeed = totalDist / 150000; 
            let currentFlightSpeed = baseSpeed * speedMultiplier;
            flownDist += currentFlightSpeed * dt;
            
            if (flownDist >= totalDist) {{
                toggleFlight();
                return;
            }}
            
            let curState = getPointAtDist(flownDist, currentSegIdx, currentSegAccum);
            currentSegIdx = curState.idx;
            currentSegAccum = curState.accum;
            let curPos = curState.pos;

            let targetBrng = curState.brng;

            if (currentBrng === null) currentBrng = targetBrng;
            let diff = targetBrng - currentBrng;
            while (diff <= -180) diff += 360;
            while (diff > 180) diff -= 360;
            
            let rotationSpeed = 0.006 * Math.max(1.0, Math.sqrt(speedMultiplier));
            currentBrng += diff * Math.min(1.0, dt * rotationSpeed); 
            while (currentBrng < 0) currentBrng += 360;
            while (currentBrng >= 360) currentBrng -= 360;

            let targetZoom = 16 - (curPos.alt / 1500); 
            if (targetZoom < 12) targetZoom = 12; 
            if (targetZoom > 17) targetZoom = 17; 
            currentZoom += (targetZoom - currentZoom) * Math.min(1.0, dt * 0.002);

            window.deckInstance.setProps({{
                viewState: {{
                    longitude: curPos.lon,
                    latitude: curPos.lat,
                    position: [0, 0, curPos.alt + altOffset], 
                    zoom: currentZoom,
                    pitch: 82, 
                    maxPitch: 89, 
                    bearing: currentBrng,
                    transitionDuration: 0 
                }},
                onViewStateChange: customViewStateChange 
            }});
            
            animFrame = requestAnimationFrame(animateFlight);
        }}
    </script>
    """
    return css + html + js

def generer_carte_finale_interactive(pdk_deck_object, injection_code):
    html_pdk_brut = pdk_deck_object.to_html(as_string=True)
    html_modifie = html_pdk_brut.replace("</body>", injection_code + "\n</body>")
    
    cible = "const deckInstance = createDeck({"
    remplacement = "const deckInstance = window.deckInstance = createDeck({"
    if cible in html_modifie:
        html_final = html_modifie.replace(cible, remplacement)
    else:
        html_final = html_modifie
        
    return html_final

# ==========================================
# EXÉCUTION DU PROGRAMME
# ==========================================

chemin_trace = choisir_fichier_gpx()

if not chemin_trace:
    print("❌ Aucun fichier sélectionné ou opération annulée.")
    exit()

print(f"Lecture du fichier : {os.path.basename(chemin_trace)}...")
donnees_vol_completes = lire_gpx_universel(chemin_trace)

if not donnees_vol_completes:
    print("❌ Impossible de lire des données valides.")
    exit()

centre_lon, centre_lat = calculer_centre(donnees_vol_completes)
init_zoom = 10
init_pitch = 65

# --- Préparation des données du vol en Python Pur (Bypass de Pandas pour compatibilité Windows) ---

donnees_points_vol = []
ma_trace_pos = []
donnees_ombre = []

for pt in donnees_vol_completes:
    spd_kt = int(pt['spd'] * 1.94384)
    alt_ft = int(pt['air_alt'] * 3.28084)
    crs = int(pt['crs'])
    
    # Casting explicite en Python Standard
    lon = float(pt['lon'])
    lat = float(pt['lat'])
    air_alt = float(pt['air_alt'])
    terr_alt = float(pt['terr_alt'])
    
    tooltip = f"<b>📍 Point de vol</b><br/>Altitude : {alt_ft} ft ({int(air_alt)} m)<br/>Vitesse : {spd_kt} kt<br/>Cap : {crs}°"
    
    donnees_points_vol.append({
        'lon': lon,
        'lat': lat,
        'air_alt': air_alt,
        'tooltip_html': tooltip
    })
    
    ma_trace_pos.append([lon, lat, air_alt])
    
    donnees_ombre.append({
        "depart": [lon, lat, terr_alt],
        "arrivee": [lon, lat, air_alt],
        "couleur": [100, 100, 100, 120]
    })

donnees_trace = [{"trace": ma_trace_pos, "couleur": [255, 50, 50]}]
donnees_aeroports = charger_aeroports_france()

# --- Configuration de la carte 3D ---
ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer("TerrainLayer", elevation_decoder=ELEVATION_DECODER, texture=SATELLITE_URL, elevation_data=TERRAIN_URL)

couche_ombre = pdk.Layer(
    "LineLayer", 
    donnees_ombre, 
    get_source_position="depart", 
    get_target_position="arrivee", 
    get_color="couleur", 
    get_width=2
)

couche_trace = pdk.Layer(
    "PathLayer", 
    donnees_trace, 
    get_path="trace", 
    get_color="couleur", 
    width_scale=20, 
    width_min_pixels=5, 
    get_width=5, 
    joint_rounded=True, 
    cap_rounded=True
)

couche_trace_interactive = pdk.Layer(
    "ScatterplotLayer",
    donnees_points_vol,
    get_position=['lon', 'lat', 'air_alt'],
    get_radius=40,
    get_fill_color=[255, 255, 255, 1], 
    pickable=True, 
)

liste_couches = [couche_relief, couche_ombre, couche_trace, couche_trace_interactive]

if donnees_aeroports:
    couche_aeroports_cercles = pdk.Layer(
        "ScatterplotLayer",
        donnees_aeroports,
        get_position=['longitude_deg', 'latitude_deg', 'elevation_m'],
        get_fill_color='couleur',
        get_radius='rayon',
        pickable=True, 
        stroked=True,
        get_line_color=[255, 255, 255, 100], 
        line_width_min_pixels=1,
    )
    
    couche_aeroports_textes = pdk.Layer(
        "TextLayer",
        donnees_aeroports,
        get_position=['longitude_deg', 'latitude_deg', 'elevation_m'],
        get_text="etiquette", 
        get_size=12, 
        get_color=[255, 255, 255, 255], 
        get_alignment_baseline="'bottom'", 
        get_pixel_offset=[0, -15], 
        pickable=False
    )
    
    liste_couches.extend([couche_aeroports_cercles, couche_aeroports_textes])

vue_initiale = pdk.ViewState(longitude=centre_lon, latitude=centre_lat, zoom=init_zoom, pitch=init_pitch, max_pitch=89, bearing=45)

carte_pdk = pdk.Deck(
    layers=liste_couches,
    initial_view_state=vue_initiale,
    map_provider=None,
    tooltip={"html": "{tooltip_html}"} 
)

print("Génération de l'application interactive...")
code_injection = generer_controles_html(centre_lon, centre_lat, donnees_vol_completes, init_zoom, init_pitch)
html_application_finale = generer_carte_finale_interactive(carte_pdk, code_injection)

fichier_sortie = "mon_application_vol_3d.html"
with open(fichier_sortie, "w", encoding="utf-8") as f:
    f.write(html_application_finale)

chemin_absolu = os.path.abspath(fichier_sortie)
print(f"✅ Terminé ! Ouverture de l'application interactive...")
webbrowser.open(f"file://{chemin_absolu}")