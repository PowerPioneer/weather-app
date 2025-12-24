"""
Load country-level aggregated climate data.
This provides pre-computed country averages for zoomed-out map views.
"""
import json
from pathlib import Path

# Path to country data (optimized for web serving)
COUNTRIES_DIR = Path(__file__).parent.parent / "data" / "countries" / "optimized"

# Cache for loaded country data
_country_cache = {}

def get_country_data(month):
    """
    Load country-level climate data for a specific month.
    
    Args:
        month: Month number (1-12)
    
    Returns:
        GeoJSON dict with country polygons and climate data, or None if not found
    """
    # Check cache first
    cache_key = f"month_{month:02d}"
    if cache_key in _country_cache:
        return _country_cache[cache_key]
    
    # Load from file
    geojson_file = COUNTRIES_DIR / f"countries_month_{month:02d}.geojson"
    
    if not geojson_file.exists():
        print(f"Country data not found for month {month}: {geojson_file}")
        return None
    
    try:
        with open(geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Cache it
        _country_cache[cache_key] = data
        
        return data
    except Exception as e:
        print(f"Error loading country data for month {month}: {e}")
        return None

def filter_by_bounds(geojson_data, north, south, east, west):
    """
    Filter GeoJSON features by bounding box.
    Handles longitude wrapping across the international date line.
    
    Args:
        geojson_data: GeoJSON dict with features
        north, south, east, west: Bounding box coordinates
    
    Returns:
        Filtered GeoJSON dict
    """
    if not geojson_data or 'features' not in geojson_data:
        return geojson_data
    
    filtered_features = []
    
    # Check if viewport crosses the international date line (antimeridian)
    crosses_antimeridian = west > east
    
    for feature in geojson_data['features']:
        if 'geometry' not in feature or not feature['geometry']:
            continue
            
        geometry = feature['geometry']
        found_in_bounds = False
        
        # Check if geometry intersects with bounds
        # For simplicity, check if any coordinate is within bounds
        if geometry['type'] == 'Polygon':
            coords_list = [geometry['coordinates'][0]]  # List with one outer ring
        elif geometry['type'] == 'MultiPolygon':
            # Check ALL polygons, not just the first one
            coords_list = [poly[0] for poly in geometry['coordinates']]  # All outer rings
        else:
            continue
        
        # Check if any point in any polygon is within bounds
        for coords in coords_list:
            for coord in coords:
                lon, lat = coord[0], coord[1]
                
                # Check latitude
                lat_in_bounds = south <= lat <= north
                
                # Check longitude with antimeridian handling
                if crosses_antimeridian:
                    # Viewport crosses dateline: accept if lon >= west OR lon <= east
                    lon_in_bounds = lon >= west or lon <= east
                else:
                    # Normal case: west < east
                    lon_in_bounds = west <= lon <= east
                
                if lat_in_bounds and lon_in_bounds:
                    filtered_features.append(feature)
                    found_in_bounds = True
                    break
            if found_in_bounds:
                break
    
    return {
        'type': 'FeatureCollection',
        'features': filtered_features
    }

def get_country_data_for_variable(month, variable, bounds=None):
    """
    Get country data filtered for a specific variable and optional bounding box.
    
    Args:
        month: Month number (1-12)
        variable: 'temperature', 'rainfall', 'sunshine', or 'overall'
        bounds: Optional dict with 'north', 'south', 'east', 'west' keys
    
    Returns:
        GeoJSON dict with relevant data field
    """
    data = get_country_data(month)
    
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
    Get list of months for which country data is available.
    
    Returns:
        List of month numbers (1-12)
    """
    if not COUNTRIES_DIR.exists():
        return []
    
    available = []
    for month in range(1, 13):
        geojson_file = COUNTRIES_DIR / f"countries_month_{month:02d}.geojson"
        if geojson_file.exists():
            available.append(month)
    
    return available

def clear_cache():
    """Clear the country data cache."""
    global _country_cache
    _country_cache = {}
    print("Country data cache cleared")
