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

def lire_gpx_universel(chemin_fichier):
    """Lit les GPX, qu'ils soient des Traces (réelles) ou des Routes (planifiées)"""
    donnees_vol = []
    
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            points_bruts = []
            
            # Récupère les traces
            for track in gpx.tracks:
                for segment in track.segments:
                    points_bruts.extend(segment.points)
                    
            # Récupère les routes
            for route in gpx.routes:
                points_bruts.extend(route.points)
                
            for point in points_bruts:
                air_alt = point.elevation if point.elevation is not None else 0
                terr_alt = 0  
                spd = 0
                crs = 0
                
                # Cherche les données cachées SDVFR
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
    """Calcule le point moyen pour centrer la caméra"""
    if not flight_data:
        return 0, 0
    avg_lon = sum(pt['lon'] for pt in flight_data) / len(flight_data)
    avg_lat = sum(pt['lat'] for pt in flight_data) / len(flight_data)
    return avg_lon, avg_lat

# ==========================================
# GESTION DES BOUTONS DE CONTRÔLE CAMERA
# ==========================================

def generer_controles_html(centre_lon, centre_lat, init_zoom=10, init_pitch=65):
    """Génère le bloc CSS, HTML et JavaScript pour les boutons (avec animation et souris corrigée)"""
    css = """
    <style>
        #control-panel {
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            gap: 12px;
            font-family: Arial, sans-serif;
            font-size: 14px;
        }
        .control-group {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        #control-panel button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
            min-width: 40px;
        }
        #control-panel button:hover { background-color: #0056b3; }
        #control-panel button:active { background-color: #004085; }
        #control-panel h3 { margin: 0 0 5px 0; font-size: 16px; text-align: center; color: #333; }
    </style>
    """
    
    html = """
    <div id="control-panel">
        <h3>Caméra PyDeck</h3>
        <div class="control-group">
            <button onclick="changeView('zoomIn')">＋</button>
            <button onclick="changeView('zoomOut')">－</button>
            <span>Zoom</span>
        </div>
        <div class="control-group">
            <button onclick="changeView('pitchUp')">⬆</button>
            <button onclick="changeView('pitchDown')">⬇</button>
            <span>Inclinaison</span>
        </div>
        <div class="control-group">
            <button onclick="changeView('center')" style="width:100%;">Recentrer la vue</button>
        </div>
    </div>
    """
    
    js = f"""
    <script>
        const centerPos = {{ longitude: {centre_lon}, latitude: {centre_lat} }};
        const defaultZoom = {init_zoom};
        const defaultPitch = {init_pitch};
        const defaultBearing = 45;

        function changeView(action) {{
            let deckObj = window.deckInstance;
            
            if (!deckObj) {{
                console.error("❌ Erreur : Impossible de localiser l'objet DeckGL.");
                return;
            }}
            
            let currentViewState = deckObj.props.viewState || deckObj.props.initialViewState;
            if (!currentViewState) return;
            
            let newViewState = {{ ...currentViewState }};

            switch (action) {{
                case 'zoomIn': newViewState.zoom += 0.8; break;
                case 'zoomOut': newViewState.zoom -= 0.8; break;
                case 'pitchUp': newViewState.pitch = Math.min(newViewState.pitch + 15, 85); break;
                case 'pitchDown': newViewState.pitch = Math.max(newViewState.pitch - 15, 0); break;
                case 'center':
                    newViewState.longitude = centerPos.longitude;
                    newViewState.latitude = centerPos.latitude;
                    newViewState.zoom = defaultZoom;
                    newViewState.pitch = defaultPitch;
                    newViewState.bearing = defaultBearing;
                    break;
            }}

            // Ajout de l'animation fluide (800ms)
            newViewState.transitionDuration = 800;

            // On met à jour la vue ET on reconnecte les événements de la souris
            deckObj.setProps({{ 
                viewState: newViewState,
                onViewStateChange: ({{viewState}}) => deckObj.setProps({{viewState: viewState}})
            }});
        }}
    </script>
    """
    return css + html + js

def generer_carte_finale_interactive(pdk_deck_object, injection_code):
    """Compile la carte PyDeck, injecte les contrôles HTML et patche la variable d'instance"""
    html_pdk_brut = pdk_deck_object.to_html(as_string=True)
    html_modifie = html_pdk_brut.replace("</body>", injection_code + "\n</body>")
    
    # PATCH DÉFINITIF pour PyDeck 0.9.1
    cible = "const deckInstance = createDeck({"
    remplacement = "const deckInstance = window.deckInstance = createDeck({"
    
    if cible in html_modifie:
        html_final = html_modifie.replace(cible, remplacement)
        print("✅ Patch PyDeck appliqué avec succès (variable deckInstance trouvée) !")
    else:
        print("⚠️ AVERTISSEMENT : La cible n'a pas été trouvée dans le HTML.")
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
    print("❌ Impossible de lire des données valides. Le GPX est peut-être vide.")
    exit()

# Valeurs de base de la caméra
centre_lon, centre_lat = calculer_centre(donnees_vol_completes)
init_zoom = 10
init_pitch = 65

# --- Préparation des données PyDeck ---

# Trace principale (Ligne rouge)
ma_trace_pos = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]
df_trace = pd.DataFrame({
    "trace": [ma_trace_pos],
    "couleur": [[255, 50, 50]]
})

# L'ombre / Piliers (LineLayer)
sources = [[pt['lon'], pt['lat'], pt['terr_alt']] for pt in donnees_vol_completes]
cibles = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]
df_ombre = pd.DataFrame({
    "depart": sources,
    "arrivee": cibles,
    "couleur": [[100, 100, 100, 120]] * len(donnees_vol_completes) 
})

# --- Configuration Relief ---
ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer(
    "TerrainLayer",
    elevation_decoder=ELEVATION_DECODER,
    texture=SATELLITE_URL,
    elevation_data=TERRAIN_URL,
)

# --- Configuration Ombre (Lignes verticales) ---
couche_ombre = pdk.Layer(
    "LineLayer",
    df_ombre,
    get_source_position="depart",
    get_target_position="arrivee",
    get_color="couleur",
    get_width=2,
)

# --- Configuration Trace (Ligne en vol) ---
couche_trace = pdk.Layer(
    "PathLayer",
    df_trace,
    get_path="trace",
    get_color="couleur",
    width_scale=20,
    width_min_pixels=5,
    get_width=5,
    joint_rounded=True,
    cap_rounded=True,
)

# --- Configuration de la caméra ---
vue_initiale = pdk.ViewState(
    longitude=centre_lon,
    latitude=centre_lat,
    zoom=init_zoom,
    pitch=init_pitch,
    bearing=45   
)

# --- Création de l'objet Carte ---
carte_pdk = pdk.Deck(
    layers=[couche_relief, couche_ombre, couche_trace],
    initial_view_state=vue_initiale,
    map_provider=None
)

# --- Génération interactive ---
print("Génération de l'application interactive...")
code_injection = generer_controles_html(centre_lon, centre_lat, init_zoom, init_pitch)
html_application_finale = generer_carte_finale_interactive(carte_pdk, code_injection)

# --- Sauvegarde et Ouverture ---
fichier_sortie = "mon_application_vol_3d.html"
with open(fichier_sortie, "w", encoding="utf-8") as f:
    f.write(html_application_finale)

chemin_absolu = os.path.abspath(fichier_sortie)
print(f"✅ Terminé ! Ouverture de l'application interactive...")
webbrowser.open(f"file://{chemin_absolu}")