# Fly3D

A Python tool to visualize flight paths from GPX files in interactive 3D maps.

## Features

- Parse GPX files containing flight tracks
- Generate 3D visualizations with terrain elevation
- Interactive map with satellite imagery
- Automatic camera centering on flight path

## Dependencies

- `pydeck` - For 3D deck.gl visualizations
- `pandas` - Data manipulation
- `gpxpy` - GPX file parsing

## Installation

Install the required packages:

```bash
pip install pydeck pandas gpxpy
```

## Usage

1. Run the script:
   ```bash
   python vol_3d.py
   ```

2. When prompted, drag and drop your GPX file into the terminal and press Enter.

3. The script will generate `mon_vol_3d.html` and open it in your default browser.

## Output

The generated HTML file contains an interactive 3D map showing:
- Terrain elevation from satellite data
- Your flight path as a red line
- Satellite imagery as the base layer

You can interact with the map by rotating, zooming, and panning.

## Notes

- Supports GPX files with multiple track segments
- Output filename can be changed by editing `vol_3d.py` variable `OUTPUT_HTML`
- Tested on macOS and Linux with Python 3.8+
