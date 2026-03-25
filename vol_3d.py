import pydeck as pdk
import pandas as pd
import gpxpy
import os
import webbrowser

def choisir_fichier_gpx():
    """Demande le fichier via le terminal avec support du glisser-déposer"""
    print("\n" + "="*55)
    print("🚁 GÉNÉRATEUR DE VOL 3D")
    print("="*55)
    print("Glissez-déposez votre fichier trace .gpx ici,")
    print("puis appuyez sur Entrée :")
    
    chemin = input("> ").strip()
    
    # Le terminal Mac rajoute souvent des guillemets lors d'un glisser-déposer,
    # on les retire proprement pour éviter les bugs de lecture.
    if chemin.startswith("'") and chemin.endswith("'"):
        chemin = chemin[1:-1]
    elif chemin.startswith('"') and chemin.endswith('"'):
        chemin = chemin[1:-1]
        
    return chemin.strip()

def lire_gpx(chemin_fichier):
    """Lit le fichier GPX et renvoie une liste [longitude, latitude, altitude]"""
    flight_path = []
    
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        altitude = point.elevation if point.elevation is not None else 0
                        flight_path.append([point.longitude, point.latitude, altitude])
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return []
                    
    return flight_path

def calculer_centre(flight_path):
    """Calcule le point moyen pour centrer la caméra"""
    if not flight_path:
        return 0, 0
    
    avg_lon = sum([pt[0] for pt in flight_path]) / len(flight_path)
    avg_lat = sum([pt[1] for pt in flight_path]) / len(flight_path)
    return avg_lon, avg_lat

# ==========================================
# EXÉCUTION DU PROGRAMME
# ==========================================

chemin_trace = choisir_fichier_gpx()

if not chemin_trace or not os.path.exists(chemin_trace):
    print("❌ Fichier introuvable ou invalide. Annulation.")
    exit()

print(f"Lecture du fichier : {os.path.basename(chemin_trace)}...")
ma_trace = lire_gpx(chemin_trace)

if not ma_trace:
    exit()

df_vol = pd.DataFrame({
    "trace": [ma_trace],
    "couleur": [[255, 50, 50]] 
})

centre_lon, centre_lat = calculer_centre(ma_trace)

ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer(
    "TerrainLayer",
    elevation_decoder=ELEVATION_DECODER,
    texture=SATELLITE_URL,
    elevation_data=TERRAIN_URL,
)

couche_trace = pdk.Layer(
    "PathLayer",
    df_vol,
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
    layers=[couche_relief, couche_trace],
    initial_view_state=vue_initiale,
    map_provider=None 
)

fichier_sortie = "mon_vol_sdvfr_3d.html"
carte.to_html(fichier_sortie)

chemin_absolu = os.path.abspath(fichier_sortie)
print(f"✅ Terminé ! Ouverture de la carte 3D dans votre navigateur...")
webbrowser.open(f"file://{chemin_absolu}")