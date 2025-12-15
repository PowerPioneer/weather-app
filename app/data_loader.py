"""
Load weather data from GeoTIFF files for specific coordinates.
Calculates averages across all available years for each month.
"""
import rasterio
from pathlib import Path
import json
import numpy as np

# Path to climate data
ERA5_DIR = Path(__file__).parent.parent / "data" / "era5"
CRU_DIR = Path(__file__).parent.parent / "data" / "cru"

def get_value_at_coordinate(lat, lng, variable, month):
    """
    Get the average value from all GeoTIFF files for a specific month/location.
    Averages data across all available years (2020-2024).
    
    Args:
        lat: Latitude
        lng: Longitude
        variable: 'tmin', 'tmax', 'prec', or 'sunhours'
        month: Month number (1-12)
    
    Returns:
        The average value at that coordinate, or None if not found
    """
    # Find the GeoTIFF file for this variable and month
    # sunhours is in CRU directory, others in ERA5
    if variable == 'sunhours':
        var_dir = CRU_DIR / variable
    else:
        var_dir = ERA5_DIR / variable
    
    if not var_dir.exists():
        return None
    
    # Find ALL files matching the month (across all years)
    # Different format for different variables:
    # tmin/tmax/prec: ...YYYY-MM.tif
    # sunhours: ...MM.tif
    tif_files = []
    
    # Try both formats
    tif_files = list(var_dir.glob(f"*-{month:02d}.tif"))  # YYYY-MM format
    if not tif_files:
        tif_files = list(var_dir.glob(f"*_{month:02d}.tif"))  # _MM format
    
    if not tif_files:
        return None
    
    # Sort to get consistent ordering (all years for this month)
    tif_files = sorted(tif_files)
    
    # Read values from all files and calculate average
    values = []
    
    for tif_file in tif_files:
        try:
            with rasterio.open(tif_file) as src:
                # Convert lat/lng to pixel coordinates
                row, col = src.index(lng, lat)
                
                # Read the value at that pixel
                data = src.read(1)
                
                # Check bounds
                if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                    value = data[row, col]
                    
                    # Check for nodata
                    if src.nodata is not None and value == src.nodata:
                        continue
                    
                    values.append(float(value))
        except Exception as e:
            print(f"Error reading {tif_file}: {e}")
            continue
    
    # Return average if we have values
    if values:
        return float(np.mean(values))
    
    return None

def get_grid_data(variable, month, bounds, resolution=50):
    """
    Get grid data for a variable and month within specified bounds.
    
    Args:
        variable: 'tmin', 'tmax', 'prec', or 'sunhours'
        month: Month number (1-12)
        bounds: Dict with 'north', 'south', 'east', 'west' in degrees
        resolution: Number of points per dimension (default 50)
    
    Returns:
        Dictionary with grid data: {
            'lats': [...],
            'lngs': [...],
            'values': [[...], [...], ...]
        }
        Note: For prec, values are converted from mm/month to mm/day
    """
    # sunhours is in CRU directory, others in ERA5
    if variable == 'sunhours':
        var_dir = CRU_DIR / variable
    else:
        var_dir = ERA5_DIR / variable
    
    if not var_dir.exists():
        return None
    
    # Find the GeoTIFF file(s) for this month
    tif_files = list(var_dir.glob(f"*-{month:02d}.tif"))
    if not tif_files:
        tif_files = list(var_dir.glob(f"*_{month:02d}.tif"))
    
    if not tif_files:
        return None
    
    # Use the first file to get the data (or average if multiple)
    tif_file = sorted(tif_files)[0]
    
    try:
        with rasterio.open(tif_file) as src:
            # Debug: Print transform info
            print(f"Raster transform: {src.transform}")
            print(f"Raster bounds: {src.bounds}")
            print(f"Request bounds: north={bounds['north']}, south={bounds['south']}, east={bounds['east']}, west={bounds['west']}")
            
            # Create grid of lat/lng points from north to south, west to east
            # These are the CENTER points of each grid cell
            lats = np.linspace(bounds['north'], bounds['south'], resolution)
            lngs = np.linspace(bounds['west'], bounds['east'], resolution)
            
            print(f"Grid lats: {lats[0]} to {lats[-1]}")
            print(f"Grid lngs: {lngs[0]} to {lngs[-1]}")
            
            # Read the full raster data
            data = src.read(1)
            
            # Sample values at grid points
            values = []
            for lat in lats:
                row_values = []
                for lng in lngs:
                    try:
                        # rasterio.index expects (x, y) = (longitude, latitude)
                        row, col = src.index(lng, lat)
                        if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                            value = data[row, col]
                            # Check for nodata AND NaN values
                            if src.nodata is not None and value == src.nodata:
                                row_values.append(None)
                            elif np.isnan(value):
                                row_values.append(None)
                            else:
                                row_values.append(float(value))
                        else:
                            row_values.append(None)
                    except:
                        row_values.append(None)
                values.append(row_values)
            
            return {
                'lats': lats.tolist(),
                'lngs': lngs.tolist(),
                'values': values
            }
    except Exception as e:
        print(f"Error reading grid data from {tif_file}: {e}")
        return None

def get_weather_for_location(lat, lng, month):
    """
    Get weather data for a specific location and month.
    
    Returns:
        Dictionary with tmin, tmax, prec, and sunhours values
    """
    return {
        'tmin': get_value_at_coordinate(lat, lng, 'tmin', month),
        'tmax': get_value_at_coordinate(lat, lng, 'tmax', month),
        'prec': get_value_at_coordinate(lat, lng, 'prec', month),
        'sunhours': get_value_at_coordinate(lat, lng, 'sunhours', month)
    }
