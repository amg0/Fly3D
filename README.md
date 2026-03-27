# Fly3D

![Example](Example.png)

A Python tool to visualize flight paths from GPX files in interactive 3D maps with French airports overlay.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [Camera Controls](#camera-controls)
- [Supported GPX Formats](#supported-gpx-formats)
- [Notes](#notes)
- [License](#license)

## Features

- **File Selection Dialog**: Native file picker for macOS and Windows to select GPX files
- **GPX Parsing**: Parse GPX files containing flight tracks with altitude, speed, and course data
- **3D Terrain Visualization**: Interactive 3D maps with real terrain elevation from satellite data
- **Flight Path Display**: Red flight path line with shadow lines connecting ground to flight altitude
- **French Airports Database**: Automatic loading and display of all French airports and airfields
- **Airport Visualization**: Airports displayed as colored circles with size based on airport type (large/medium/small)
- **Interactive Labels**: Airport codes displayed as white text labels above each airport
- **Camera Controls**: Interactive buttons for zoom in/out, pitch adjustment, and view recentering
- **Satellite Imagery**: High-resolution satellite base layer
- **Tooltips**: Hover information showing airport details (name, type, code)
- **Flight Replay**: Replay flight with play/pause button in control panel
- **Enhanced Controls**: Commands to adjust camera height, zoom, pitch, and recentering

## Requirements

- Python 3.8 or higher
- Internet connection (for airport database and terrain tiles)

## Dependencies

- `pydeck` - For 3D deck.gl visualizations
- `pandas` - Data manipulation and airport database processing
- `gpxpy` - GPX file parsing
- `tkinter` - File selection dialog (Windows, included with Python)

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

2. A native file selection dialog will open - select your GPX file containing flight track data.

3. The script will automatically:
   - Download the French airports database
   - Process your flight data
   - Generate an interactive 3D visualization
   - Open the result in your default web browser

## Output

The generated HTML file (`mon_application_vol_3d.html`) contains an interactive 3D map showing:

- **Terrain Layer**: Real elevation data with satellite texture
- **Flight Path**: Red line showing your flight trajectory at actual altitude
- **Shadow Lines**: Gray lines connecting ground elevation to flight altitude
- **Airports**: Colored circles representing French airports:
  - Large airports: Large blue circles
  - Medium airports: Medium blue circles
  - Small airports: Small light blue circles
  - Other facilities: Small gray circles
- **Airport Labels**: White text showing airport codes (ICAO/local codes)
- **Interactive Controls**: Camera control panel in top-left corner

## Camera Controls

Use the control panel to:
- **Zoom buttons** (+/-): Increase/decrease zoom level
- **Pitch buttons** (↑/↓): Adjust viewing angle
- **Recenter button**: Return to default view centered on flight path
- **Play/Pause button** (▶️/⏸️): Replay the flight animation

## Supported GPX Formats

- Standard GPX tracks and routes
- Extended data in point descriptions (JSON format):
  - `alt`: Aircraft altitude
  - `ele`: Ground elevation
  - `spd`: Speed
  - `crs`: Course/heading

## Notes

- Supports GPX files with multiple track segments
- Automatic internet connection required for airport database and terrain tiles
- Output filename: `mon_application_vol_3d.html` (can be changed in the script)
- Tested on macOS and Windows with Python 3.8+
- Airport data sourced from OurAirports database (updated automatically)

## License

This project is open source. Please check the license file for details.
