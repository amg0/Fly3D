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
            
            # 1. On rassemble tous les points (qu'ils viennent d'une trace ou d'une route)
            points_bruts = []
            
            # Récupère les traces (vols effectués)
            for track in gpx.tracks:
                for segment in track.segments:
                    points_bruts.extend(segment.points)
                    
            # Récupère les routes (vols planifiés)
            for route in gpx.routes:
                points_bruts.extend(route.points)
                
            # 2. On traite chaque point de manière robuste
            for point in points_bruts:
                # A. Valeurs par défaut standard (pour GPX classique)
                air_alt = point.elevation if point.elevation is not None else 0
                terr_alt = 0  # Si on ne connait pas le sol, on descend le mur jusqu'à 0 (le relief coupera la ligne visuellement)
                spd = 0
                crs = 0
                
                # B. On essaie de surcharger avec les données spécifiques SDVFR si elles existent
                if point.description:
                    try:
                        desc_data = json.loads(point.description)
                        if 'alt' in desc_data and 'ele' in desc_data:
                            air_alt = desc_data['alt']
                            terr_alt = desc_data['ele']
                        spd = desc_data.get('spd', 0)
                        crs = desc_data.get('crs', 0)
                    except json.JSONDecodeError:
                        # Ce n'est pas du JSON ou pas le format SDVFR, on ignore
                        pass
                
                # C. On ajoute à notre liste propre
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
donnees_vol_completes = lire_gpx_universel(chemin_trace)

if not donnees_vol_completes:
    print("❌ Impossible de lire des données valides. Le GPX est peut-être vide.")
    exit()

# 1. Trace principale (Ligne rouge)
ma_trace_pos = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]
df_trace = pd.DataFrame({
    "trace": [ma_trace_pos],
    "couleur": [[255, 50, 50]]
})

# 2. L'ombre / Piliers (LineLayer)
sources = [[pt['lon'], pt['lat'], pt['terr_alt']] for pt in donnees_vol_completes]
cibles = [[pt['lon'], pt['lat'], pt['air_alt']] for pt in donnees_vol_completes]

df_ombre = pd.DataFrame({
    "depart": sources,
    "arrivee": cibles,
    "couleur": [[100, 100, 100, 120]] * len(donnees_vol_completes) 
})

centre_lon, centre_lat = calculer_centre(donnees_vol_completes)

# Configuration Relief
ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer(
    "TerrainLayer",
    elevation_decoder=ELEVATION_DECODER,
    texture=SATELLITE_URL,
    elevation_data=TERRAIN_URL,
)

# Configuration Ombre (Lignes verticales)
couche_ombre = pdk.Layer(
    "LineLayer",
    df_ombre,
    get_source_position="depart",
    get_target_position="arrivee",
    get_color="couleur",
    get_width=2,
)

# Configuration Trace (Ligne en vol)
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
    zoom=10, # J'ai réduit le zoom à 10 car une navigation couvre plus de terrain qu'un vol local
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