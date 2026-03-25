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
    set leFichier to choose file with prompt "Sélectionnez votre trace SDVFR (fichier .gpx)"
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
        title="Sélectionnez votre trace SDVFR (fichier .gpx)",
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

def lire_gpx_sdvfr_complet(chemin_fichier):
    donnees_vol = []
    
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        desc_texte = point.description
                        if desc_texte:
                            try:
                                desc_data = json.loads(desc_texte)
                                if 'alt' in desc_data and 'ele' in desc_data:
                                    donnees_vol.append({
                                        'lon': point.longitude,
                                        'lat': point.latitude,
                                        'air_alt': desc_data['alt'],
                                        'terr_alt': desc_data['ele'],
                                        'spd': desc_data.get('spd', 0),
                                        'crs': desc_data.get('crs', 0)
                                    })
                            except json.JSONDecodeError:
                                pass
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return []
                    
    return donnees_vol

def calculer_centre(flight_data):
    if not flight_data:
        return 0, 0
    avg_lon = sum(pt['lon'] for pt in flight_data) / len(flight_data)
    avg_lat = sum(pt['lat'] for pt in flight_data) / len(flight_data)
    return avg_lon, avg_lat

# ==========================================
# EXÉCUTION DU PROGRAMME
# ==========================================

chemin_trace = choisir_fichier_gpx()

if not chemin_trace:
    print("❌ Aucun fichier sélectionné ou opération annulée.")
    exit()

print(f"Lecture du fichier : {os.path.basename(chemin_trace)}...")
donnees_vol_completes = lire_gpx_sdvfr_complet(chemin_trace)

if not donnees_vol_completes:
    print("❌ Impossible de lire des données valides pour la 3D avancée.")
    exit()

# 1. Trace principale (Ligne rouge)
ma_trace_pos = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]
df_trace = pd.DataFrame({
    "trace": [ma_trace_pos],
    "couleur": [[255, 50, 50]]
})

# 2. L'ombre verticale (CORRECTION ICI !)
# Pour un LineLayer, on doit séparer le point de départ et d'arrivée
sources = [[pt['lon'], pt['lat'], pt['terr_alt']] for pt in donnees_vol_completes]
cibles = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]

df_ombre = pd.DataFrame({
    "depart": sources,
    "arrivee": cibles,
    "couleur": [[100, 100, 100, 120]] * len(donnees_vol_completes) 
})

centre_lon, centre_lat = calculer_centre(donnees_vol_completes)

ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer(
    "TerrainLayer",
    elevation_decoder=ELEVATION_DECODER,
    texture=SATELLITE_URL,
    elevation_data=TERRAIN_URL,
)

# NOUVEAU : On utilise LineLayer au lieu de PathLayer pour l'ombre
couche_ombre = pdk.Layer(
    "LineLayer",
    df_ombre,
    get_source_position="depart",
    get_target_position="arrivee",
    get_color="couleur",
    get_width=2, # Épaisseur de la ligne en pixels
)

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

vue_initiale = pdk.ViewState(
    longitude=centre_lon,
    latitude=centre_lat,
    zoom=11,     
    pitch=65,    
    bearing=45   
)

carte = pdk.Deck(
    layers=[couche_relief, couche_ombre, couche_trace],
    initial_view_state=vue_initiale,
    map_provider=None 
)

fichier_sortie = "mon_vol_sdvfr_3d.html"
carte.to_html(fichier_sortie)

chemin_absolu = os.path.abspath(fichier_sortie)
print(f"✅ Terminé ! Ouverture de la carte 3D dans votre navigateur...")
webbrowser.open(f"file://{chemin_absolu}")