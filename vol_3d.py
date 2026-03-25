# vol_3d
import pydeck as pdk
import pandas as pd

# 1. Nos données de vol factices (Longitude, Latitude, Altitude en mètres)
# Exemple d'une trace qui monte en altitude au-dessus des montagnes
flight_path = [
    [5.80, 45.18, 1500], # Point de départ
    [5.85, 45.20, 2000], # On monte...
    [5.90, 45.22, 2500],
    [5.95, 45.24, 2800],
    [6.00, 45.26, 3000], # Sommet du vol
    [6.05, 45.28, 2600], # Descente
    [6.10, 45.30, 2000],
]

# On place la trace dans un DataFrame Pandas (format attendu par PyDeck)
df_vol = pd.DataFrame({
    "trace": [flight_path],
    "couleur": [[255, 50, 50]] # Rouge vif pour bien voir le trajet
})

# 2. Configuration du relief (TerrainLayer)
# On utilise des données d'élévation libres (AWS Terrarium) et une image satellite (ArcGIS)
# Cela t'évite d'avoir à créer des clés d'API pour ce test !
ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

couche_relief = pdk.Layer(
    "TerrainLayer",
    elevation_decoder=ELEVATION_DECODER,
    texture=SATELLITE_URL,
    elevation_data=TERRAIN_URL,
)

# 3. Configuration de la trace 3D (PathLayer)
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

# 4. Paramètres de la caméra (ViewState)
# On se place au centre de la trace, on "penche" la caméra (pitch) et on zoome
vue_initiale = pdk.ViewState(
    longitude=5.95,
    latitude=45.24,
    zoom=10.5,
    pitch=65,    # C'est ce qui donne l'effet 3D !
    bearing=45   # Orientation de la boussole
)

# 5. Création de la carte et exportation
carte = pdk.Deck(
    layers=[couche_relief, couche_trace],
    initial_view_state=vue_initiale,
    # On désactive la carte de fond par défaut car on utilise notre propre texture satellite
    map_provider=None 
)

# Génère le fichier HTML
fichier_sortie = "mon_vol_3d.html"
carte.to_html(fichier_sortie)
print(f"✅ Fichier {fichier_sortie} généré avec succès ! Ouvre-le dans ton navigateur.")