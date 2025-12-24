"""
Load weather data from optimized GeoTIFF files for specific coordinates.
Uses pre-computed monthly averages (2020-2024) for faster access and smaller file sizes.
"""
import rasterio
from pathlib import Path
import json
import numpy as np

# Path to climate data (optimized monthly averages)
OPTIMIZED_DIR = Path(__file__).parent.parent / "data" / "optimized"

def get_value_at_coordinate(lat, lng, variable, month):
    """
    Get the value from optimized GeoTIFF file for a specific month/location.
    Uses pre-averaged monthly files (2020-2024 average).
    
    Args:
        lat: Latitude
        lng: Longitude
        variable: 'tmin', 'tmax', 'prec', or 'sunhours'
        month: Month number (1-12)
    
    Returns:
        The value at that coordinate, or None if not found
    """
    # Find the optimized GeoTIFF file for this variable and month
    var_dir = OPTIMIZED_DIR / variable
    
    if not var_dir.exists():
        return None
    
    # Look for the monthly averaged file
    tif_file = var_dir / f"{variable}_month_{month:02d}.tif"
    
    if not tif_file.exists():
        return None
    
    # Read value from the optimized file
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
                    return None
                
                return float(value)
    except Exception as e:
        print(f"Error reading {tif_file}: {e}\")\n        return None\n    \n    return None

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
    # Find the optimized GeoTIFF file for this variable and month
    var_dir = OPTIMIZED_DIR / variable
    
    if not var_dir.exists():
        return None
    
    # Look for the monthly averaged file
    tif_file = var_dir / f"{variable}_month_{month:02d}.tif"
    
    if not tif_file.exists():
        return None
    
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
