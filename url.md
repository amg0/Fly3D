ELEVATION_DECODER = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
#SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
#SATELLITE_URL = "https://a.tile.opentopomap.org/{z}/{x}/{y}.png"
SATELLITE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
#SATELLITE_URL = "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
#SATELLITE_URL = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
