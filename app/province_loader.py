"""
Load province-level aggregated climate data.
This provides pre-computed province averages as an alternative to grid-based data.
"""
import json
from pathlib import Path
import geopandas as gpd

# Path to province data
PROVINCES_DIR = Path(__file__).parent.parent / "data" / "provinces" / "aggregated"

# Cache for loaded province data
_province_cache = {}

def get_province_data(month):
    """
    Load province-level climate data for a specific month.
    
    Args:
        month: Month number (1-12)
    
    Returns:
        GeoJSON dict with province polygons and climate data, or None if not found
    """
    # Check cache first
    cache_key = f"month_{month:02d}"
    if cache_key in _province_cache:
        return _province_cache[cache_key]
    
    # Load from file
    geojson_file = PROVINCES_DIR / f"provinces_month_{month:02d}.geojson"
    
    if not geojson_file.exists():
        print(f"Province data not found for month {month}: {geojson_file}")
        return None
    
    try:
        with open(geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Cache it
        _province_cache[cache_key] = data
        
        return data
    except Exception as e:
        print(f"Error loading province data for month {month}: {e}")
        return None

def filter_by_bounds(geojson_data, north, south, east, west):
    """
    Filter GeoJSON features by bounding box.
    
    Args:
        geojson_data: GeoJSON dict with features
        north, south, east, west: Bounding box coordinates
    
    Returns:
        Filtered GeoJSON dict
    """
    if not geojson_data or 'features' not in geojson_data:
        return geojson_data
    
    filtered_features = []
    
    for feature in geojson_data['features']:
        if 'geometry' not in feature or not feature['geometry']:
            continue
            
        geometry = feature['geometry']
        
        # Check if geometry intersects with bounds
        # For simplicity, check if any coordinate is within bounds
        if geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]  # Outer ring
        elif geometry['type'] == 'MultiPolygon':
            coords = geometry['coordinates'][0][0]  # First polygon, outer ring
        else:
            continue
        
        # Check if any point in the geometry is within bounds
        for coord in coords:
            lon, lat = coord[0], coord[1]
            if south <= lat <= north and west <= lon <= east:
                filtered_features.append(feature)
                break
    
    return {
        'type': 'FeatureCollection',
        'features': filtered_features
    }

def get_province_data_for_variable(month, variable, bounds=None):
    """
    Get province data filtered for a specific variable and optional bounding box.
    
    Args:
        month: Month number (1-12)
        variable: 'temperature', 'rainfall', 'sunshine', or 'overall'
        bounds: Optional dict with 'north', 'south', 'east', 'west' keys
    
    Returns:
        GeoJSON dict with relevant data field
    """
    data = get_province_data(month)
    
    if not data:
        return None
    
    # Map display variable names to data field names
    variable_map = {
        'temperature': 'temp_avg',
        'rainfall': 'prec_mean',
        'sunshine': 'sunhours_mean',
        'overall': 'overall_score'
    }
    
    data_field = variable_map.get(variable)
    
    if not data_field:
        return None
    
    # Apply viewport filtering if bounds provided
    if bounds:
        data = filter_by_bounds(
            data,
            bounds.get('north'),
            bounds.get('south'),
            bounds.get('east'),
            bounds.get('west')
        )
    
    # Return full GeoJSON (frontend will extract the needed field)
    return data

def get_available_months():
    """
    Get list of months for which province data is available.
    
    Returns:
        List of month numbers (1-12)
    """
    if not PROVINCES_DIR.exists():
        return []
    
    available = []
    for month in range(1, 13):
        geojson_file = PROVINCES_DIR / f"provinces_month_{month:02d}.geojson"
        if geojson_file.exists():
            available.append(month)
    
    return available

def clear_cache():
    """Clear the province data cache."""
    global _province_cache
    _province_cache = {}
