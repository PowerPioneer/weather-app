"""
Aggregate province-level climate data to country-level data.

This script reads the province GeoJSON files and aggregates climate data
by country, then joins it with Natural Earth country boundaries.

Handles distant territories by splitting countries into separate entries
based on a distance threshold (1000 km from main landmass).

Also integrates U.S. State Department travel advisories.
"""
import json
from pathlib import Path
from collections import defaultdict
import geopandas as gpd
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, Point
from shapely.ops import transform
import numpy as np
import pyproj
from functools import partial

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PROVINCES_DIR = DATA_DIR / "provinces" / "aggregated"
COUNTRIES_DIR = DATA_DIR / "countries" / "aggregated"
COUNTRIES_BASE_DIR = DATA_DIR / "countries"
TRAVEL_ADVISORIES_FILE = DATA_DIR / "travel_advisories.json"

# Name mapping from province data names to Natural Earth country names
# Province data uses more formal names, Natural Earth uses shorter versions
COUNTRY_NAME_MAPPING = {
    # Main countries
    'Democratic Republic of the Congo': 'Dem. Rep. Congo',
    'Republic of the Congo': 'Congo',
    'United Republic of Tanzania': 'Tanzania',
    'Czech Republic': 'Czechia',
    'The former Yugoslav Republic of Macedonia': 'North Macedonia',
    'Macedonia': 'North Macedonia',
    'Republic of Serbia': 'Serbia',
    'Central African Republic': 'Central African Rep.',
    'Ivory Coast': "Côte d'Ivoire",
    "Côte d'Ivoire": "Côte d'Ivoire",
    'Dominican Republic': 'Dominican Rep.',
    'East Timor': 'Timor-Leste',
    'Swaziland': 'eSwatini',
    'Bosnia and Herzegovina': 'Bosnia and Herz.',
    'Guinea Bissau': 'Guinea-Bissau',
    'Equatorial Guinea': 'Eq. Guinea',
    'The Bahamas': 'Bahamas',
    'Republic of Korea': 'South Korea',
    "Democratic People's Republic of Korea": 'North Korea',
    'Lao PDR': 'Laos',
    'Solomon Islands': 'Solomon Is.',
    'Republic of Moldova': 'Moldova',
    'Falkland Islands': 'Falkland Is.',
    
    # Caribbean islands
    'Antigua and Barbuda': 'Antigua and Barb.',
    'Saint Kitts and Nevis': 'St. Kitts and Nevis',
    'Saint Vincent and the Grenadines': 'St. Vin. and Gren.',
    'Turks and Caicos Islands': 'Turks and Caicos Is.',
    'Cayman Islands': 'Cayman Is.',
    'British Virgin Islands': 'British Virgin Is.',
    'United States Virgin Islands': 'U.S. Virgin Is.',
    'U.S. Virgin Islands': 'U.S. Virgin Is.',
    'Saint Barthelemy': 'St-Barthélemy',
    'Saint Martin': 'St-Martin',
    
    # Pacific islands
    'Cook Islands': 'Cook Is.',
    'Northern Mariana Islands': 'N. Mariana Is.',
    'Federated States of Micronesia': 'Micronesia',
    'Pitcairn Islands': 'Pitcairn Is.',
    'Wallis and Futuna': 'Wallis and Futuna Is.',
    'Marshall Islands': 'Marshall Is.',
    'French Polynesia': 'Fr. Polynesia',
    
    # Atlantic islands
    'Cape Verde': 'Cabo Verde',
    'Sao Tome and Principe': 'São Tomé and Principe',
    'Saint Pierre and Miquelon': 'St. Pierre and Miquelon',
    'Faroe Islands': 'Faeroe Is.',
    
    # Special territories
    'Hong Kong S.A.R.': 'Hong Kong',
    'Macao S.A.R': 'Macao',
    'Aland': 'Åland',
    'West Bank': 'Palestine',
    'Gaza': 'Palestine',
    'Western Sahara': 'W. Sahara',
    'Northern Cyprus': 'N. Cyprus',
    'Somaliland': 'Somaliland',  # Keep as separate
    'Indian Ocean Territories': 'Indian Ocean Ter.',
    'Siachen Glacier': 'Siachen Glacier',
    'Akrotiri Sovereign Base Area': 'Akrotiri',
    'Dhekelia Sovereign Base Area': 'Dhekelia',
    'Baykonur Cosmodrome': 'Baikonur',
}

# Distance threshold for splitting territories (in kilometers)
DISTANCE_THRESHOLD_KM = 1500

# Cache transformers for performance
_TRANSFORMER_TO_MOLLWEIDE = None
_TRANSFORMER_TO_WGS84 = None


def load_travel_advisories():
    """
    Load travel advisories from JSON file.
    
    Returns:
        dict: Travel advisory data by country name, or None if file doesn't exist
    """
    if not TRAVEL_ADVISORIES_FILE.exists():
        print(f"\nℹ️  Travel advisories file not found: {TRAVEL_ADVISORIES_FILE}")
        print("   Run 'python scripts/download_travel_advisories.py' to download advisories.")
        return None
    
    try:
        with open(TRAVEL_ADVISORIES_FILE, 'r', encoding='utf-8') as f:
            advisories = json.load(f)
        print(f"✓ Loaded travel advisories for {len(advisories)} countries")
        return advisories
    except Exception as e:
        print(f"⚠️  Error loading travel advisories: {e}")
        return None


def add_travel_advisories_to_gdf(gdf, travel_advisories):
    """
    Add travel advisory data to GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame with country/territory data
        travel_advisories: Dict of travel advisory data by country name
    
    Returns:
        GeoDataFrame with added travel advisory columns
    """
    print("\nAdding travel advisories to country data...")
    
    # Initialize columns
    gdf['safety_level'] = None
    gdf['safety_description'] = None
    gdf['safety_summary'] = None
    gdf['safety_url'] = None
    gdf['safety_date'] = None
    
    matched_count = 0
    for idx, row in gdf.iterrows():
        country_name = row['name']
        
        # Try exact match first
        if country_name in travel_advisories:
            advisory = travel_advisories[country_name]
            gdf.at[idx, 'safety_level'] = advisory['level']
            gdf.at[idx, 'safety_description'] = advisory['description']
            gdf.at[idx, 'safety_summary'] = advisory['summary']
            gdf.at[idx, 'safety_url'] = advisory['url']
            gdf.at[idx, 'safety_date'] = advisory['date']
            matched_count += 1
            continue
        
        # Try to match main country for territories (e.g., "France - French Polynesia" → "France")
        if ' - ' in country_name:
            main_country = country_name.split(' - ')[0]
            if main_country in travel_advisories:
                advisory = travel_advisories[main_country]
                gdf.at[idx, 'safety_level'] = advisory['level']
                gdf.at[idx, 'safety_description'] = advisory['description']
                gdf.at[idx, 'safety_summary'] = advisory['summary']
                gdf.at[idx, 'safety_url'] = advisory['url']
                gdf.at[idx, 'safety_date'] = advisory['date']
                matched_count += 1
                continue
        
        # Default to Level 1 if no match found
        gdf.at[idx, 'safety_level'] = 1
        gdf.at[idx, 'safety_description'] = "Exercise Normal Precautions"
        gdf.at[idx, 'safety_summary'] = "Exercise normal precautions when traveling to this country."
        gdf.at[idx, 'safety_url'] = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html"
        gdf.at[idx, 'safety_date'] = None
    
    print(f"✓ Matched travel advisories for {matched_count}/{len(gdf)} territories")
    
    return gdf

def _get_transformer_to_mollweide():
    """Get cached transformer to Mollweide projection."""
    global _TRANSFORMER_TO_MOLLWEIDE
    if _TRANSFORMER_TO_MOLLWEIDE is None:
        _TRANSFORMER_TO_MOLLWEIDE = pyproj.Transformer.from_crs(
            "EPSG:4326", "ESRI:54009", always_xy=True
        )
    return _TRANSFORMER_TO_MOLLWEIDE

def _get_transformer_to_wgs84():
    """Get cached transformer to WGS84."""
    global _TRANSFORMER_TO_WGS84
    if _TRANSFORMER_TO_WGS84 is None:
        _TRANSFORMER_TO_WGS84 = pyproj.Transformer.from_crs(
            "ESRI:54009", "EPSG:4326", always_xy=True
        )
    return _TRANSFORMER_TO_WGS84

def calculate_area_equal_projection(geom):
    """
    Calculate area of a geometry using equal-area projection (World Mollweide).
    
    Args:
        geom: Shapely geometry in WGS84 (EPSG:4326)
    
    Returns:
        Area in square kilometers
    """
    transformer = _get_transformer_to_mollweide()
    geom_projected = transform(transformer.transform, geom)
    # Area is in square meters, convert to square kilometers
    return geom_projected.area / 1_000_000

def calculate_centroid_equal_projection(geom):
    """
    Calculate centroid of a geometry using equal-area projection.
    
    Args:
        geom: Shapely geometry in WGS84 (EPSG:4326)
    
    Returns:
        Point centroid in WGS84
    """
    to_mollweide = _get_transformer_to_mollweide()
    to_wgs84 = _get_transformer_to_wgs84()
    
    geom_projected = transform(to_mollweide.transform, geom)
    centroid_projected = geom_projected.centroid
    centroid_wgs84 = transform(to_wgs84.transform, centroid_projected)
    return centroid_wgs84

def calculate_distance_km(point1, point2):
    """
    Calculate distance between two points in kilometers using equal-area projection.
    
    Args:
        point1, point2: Shapely Point objects in WGS84
    
    Returns:
        Distance in kilometers
    """
    transformer = _get_transformer_to_mollweide()
    p1_projected = transform(transformer.transform, point1)
    p2_projected = transform(transformer.transform, point2)
    
    # Distance in meters, convert to kilometers
    return p1_projected.distance(p2_projected) / 1000

def split_country_by_distance(country_name, geom, distance_threshold_km=DISTANCE_THRESHOLD_KM):
    """
    Split a country's MultiPolygon into separate territories based on distance threshold.
    Groups nearby polygons together to avoid excessive splitting.
    
    Args:
        country_name: Name of the country
        geom: Shapely geometry (Polygon or MultiPolygon) in WGS84
        distance_threshold_km: Distance threshold in kilometers
    
    Returns:
        List of tuples: [(territory_name, polygon_geom, area_km2), ...]
    """
    # Ensure we have a MultiPolygon
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        return [(country_name, geom, calculate_area_equal_projection(geom))]
    
    # If only one polygon, no splitting needed
    if len(polygons) == 1:
        area = calculate_area_equal_projection(polygons[0])
        return [(country_name, polygons[0], area)]
    
    # Calculate area and centroid for each polygon
    polygon_data = []
    for poly in polygons:
        area = calculate_area_equal_projection(poly)
        centroid = calculate_centroid_equal_projection(poly)
        polygon_data.append({
            'polygon': poly,
            'area': area,
            'centroid': centroid,
            'group': None
        })
    
    # Find the largest polygon (main landmass)
    polygon_data.sort(key=lambda x: x['area'], reverse=True)
    main_landmass = polygon_data[0]
    main_centroid = main_landmass['centroid']
    
    # Group polygons: those within threshold of main landmass are "main territory"
    # Others are grouped by proximity to each other
    main_territory_polygons = [main_landmass]
    distant_polygons = []
    
    for data in polygon_data[1:]:
        distance = calculate_distance_km(main_centroid, data['centroid'])
        
        if distance <= distance_threshold_km:
            # Part of main landmass
            main_territory_polygons.append(data)
        else:
            # Distant territory
            distant_polygons.append(data)
    
    # Group distant polygons by proximity (cluster polygons within threshold)
    territory_groups = []
    for poly_data in distant_polygons:
        # Try to find an existing group this polygon belongs to
        added_to_group = False
        for group in territory_groups:
            # Check if this polygon is within threshold of any polygon in the group
            for group_poly in group:
                distance = calculate_distance_km(poly_data['centroid'], group_poly['centroid'])
                if distance <= distance_threshold_km:
                    group.append(poly_data)
                    added_to_group = True
                    break
            if added_to_group:
                break
        
        # If not added to any group, create a new group
        if not added_to_group:
            territory_groups.append([poly_data])
    
    # Create result list
    result = []
    
    # Add main territory
    if len(main_territory_polygons) == 1:
        main_geom = main_territory_polygons[0]['polygon']
    else:
        main_geom = MultiPolygon([p['polygon'] for p in main_territory_polygons])
    main_area = calculate_area_equal_projection(main_geom)
    result.append((country_name, main_geom, main_area))
    
    # Add distant territory groups
    for group in territory_groups:
        # Calculate group centroid for naming
        if len(group) == 1:
            group_geom = group[0]['polygon']
            group_centroid = group[0]['centroid']
        else:
            group_geom = MultiPolygon([p['polygon'] for p in group])
            group_centroid = calculate_centroid_equal_projection(group_geom)
        
        group_area = calculate_area_equal_projection(group_geom)
        territory_name = f"{country_name} - {get_territory_name(group_centroid)}"
        result.append((territory_name, group_geom, group_area))
    
    return result

def get_territory_name(centroid):
    """
    Generate a descriptive name for a distant territory based on its centroid.
    
    Args:
        centroid: Shapely Point in WGS84
    
    Returns:
        String describing the territory location
    """
    lon, lat = centroid.x, centroid.y
    
    # Determine general region
    if lat > 0:
        ns = "N"
    else:
        ns = "S"
    
    if lon < -120:
        region = "Pacific"
    elif lon < -30:
        region = "Atlantic"
    elif lon < 60:
        region = "Atlantic/Africa"
    elif lon < 130:
        region = "Indian Ocean"
    else:
        region = "Pacific"
    
    return f"{region} {abs(int(lat))}°{ns}"

def aggregate_month_to_countries(month, country_gdf):
    """
    Aggregate province data for a specific month to country level.
    
    Args:
        month: Month number (1-12)
        country_gdf: GeoDataFrame with country boundaries from Natural Earth
    """
    print(f"\n{'='*60}")
    print(f"Processing month {month:02d}")
    print(f"{'='*60}")
    
    # Load province data
    province_file = PROVINCES_DIR / f"provinces_month_{month:02d}.geojson"
    
    if not province_file.exists():
        print(f"ERROR: Province file not found: {province_file}")
        return False
    
    print(f"Loading: {province_file}")
    with open(province_file, 'r', encoding='utf-8') as f:
        province_data = json.load(f)
    
    print(f"Loaded {len(province_data['features'])} provinces")
    
    # First, split country boundaries by distance threshold
    print("Splitting countries into main territories and distant territories...")
    split_countries = []
    for idx, row in country_gdf.iterrows():
        country_name = row['name']
        geom = row['geometry']
        
        territories = split_country_by_distance(country_name, geom)
        for territory_name, territory_geom, territory_area in territories:
            split_countries.append({
                'name': territory_name,
                'original_name': country_name,
                'geometry': territory_geom,
                'area_km2': territory_area
            })
    
    print(f"Split {len(country_gdf)} countries into {len(split_countries)} territories")
    
    # Group climate data by country/territory with area weighting
    territory_climate = defaultdict(lambda: {
        'tmin_values': [],
        'tmin_areas': [],
        'tmax_values': [],
        'tmax_areas': [],
        'prec_values': [],
        'prec_areas': [],
        'sunhours_values': [],
        'sunhours_areas': [],
        'temp_values': [],
        'temp_areas': [],
        'province_count': 0,
        'province_names': []  # Track province names for naming distant territories
    })
    
    for feature in province_data['features']:
        props = feature['properties']
        province_country_name = props.get('admin', 'Unknown')
        
        # Map province country name to Natural Earth country name
        country_name = COUNTRY_NAME_MAPPING.get(province_country_name, province_country_name)
        
        # Get province geometry and centroid
        province_geom = shape(feature['geometry'])
        province_centroid = calculate_centroid_equal_projection(province_geom)
        
        # Calculate province area using equal-area projection
        area_km2 = calculate_area_equal_projection(province_geom)
        
        # Find which territory this province belongs to
        # Use intersection area to assign provinces to territories
        matched_territory = None
        best_intersection_area = 0
        
        for territory in split_countries:
            if territory['original_name'] == country_name:
                try:
                    # Calculate intersection area between province and territory
                    intersection = province_geom.intersection(territory['geometry'])
                    if not intersection.is_empty:
                        intersection_area = calculate_area_equal_projection(intersection)
                        
                        # Assign to territory with largest intersection
                        if intersection_area > best_intersection_area:
                            best_intersection_area = intersection_area
                            matched_territory = territory['name']
                except Exception as e:
                    # If intersection fails, fall back to centroid distance
                    if territory['geometry'].contains(province_centroid):
                        matched_territory = territory['name']
                        break
                    else:
                        territory_centroid = calculate_centroid_equal_projection(territory['geometry'])
                        distance = calculate_distance_km(province_centroid, territory_centroid)
                        # Use distance as a proxy (smaller distance = better match)
                        # Convert to pseudo-area for comparison
                        pseudo_area = max(0, 1000000 - distance * 1000)
                        if pseudo_area > best_intersection_area:
                            best_intersection_area = pseudo_area
                            matched_territory = territory['name']
        
        # If no match found, use original country name
        if matched_territory is None:
            matched_territory = country_name
        
        # Collect data values with their areas (if not null)
        for key, data_key, area_key in [
            ('tmin_mean', 'tmin_values', 'tmin_areas'),
            ('tmax_mean', 'tmax_values', 'tmax_areas'),
            ('prec_mean', 'prec_values', 'prec_areas'),
            ('sunhours_mean', 'sunhours_values', 'sunhours_areas'),
            ('temp_avg', 'temp_values', 'temp_areas')
        ]:
            value = props.get(key)
            if value is not None and not (isinstance(value, float) and np.isnan(value)) and area_km2 > 0:
                territory_climate[matched_territory][data_key].append(value)
                territory_climate[matched_territory][area_key].append(area_km2)
        
        territory_climate[matched_territory]['province_count'] += 1
        
        # Track province name and area for naming territories
        province_name = props.get('name', '')
        if province_name:
            territory_climate[matched_territory]['province_names'].append((province_name, area_km2))
    
    print(f"Aggregated climate data for {len(territory_climate)} territories")
    
    # Update territory names using actual province names for distant territories
    for territory in split_countries:
        territory_name = territory['name']
        if territory_name in territory_climate:
            province_names = territory_climate[territory_name].get('province_names', [])
            
            # If this is a distant territory (has " - " in name), use the largest province name
            if ' - ' in territory_name and province_names:
                # Sort by area (descending) and get the largest province name
                province_names.sort(key=lambda x: x[1], reverse=True)
                largest_province_name = province_names[0][0]
                
                # Update the territory name
                old_name = territory_name
                territory['name'] = largest_province_name
                
                # Update the climate data key
                territory_climate[largest_province_name] = territory_climate.pop(old_name)
    
    # Create GeoDataFrame from split territories
    result_gdf = gpd.GeoDataFrame(split_countries, crs="EPSG:4326")
    
    # Add climate data to each territory
    climate_data = []
    for idx, row in result_gdf.iterrows():
        territory_name = row['name']
        
        # Get climate data for this territory
        data = territory_climate.get(territory_name, {
            'tmin_values': [],
            'tmin_areas': [],
            'tmax_values': [],
            'tmax_areas': [],
            'prec_values': [],
            'prec_areas': [],
            'sunhours_values': [],
            'sunhours_areas': [],
            'temp_values': [],
            'temp_areas': [],
            'province_count': 0
        })
        
        # Calculate area-weighted mean values
        def weighted_mean(values, areas):
            if not values or not areas or len(values) != len(areas):
                return None
            values = np.array(values)
            areas = np.array(areas)
            return np.sum(values * areas) / np.sum(areas)
        
        tmin_mean = weighted_mean(data['tmin_values'], data['tmin_areas'])
        tmax_mean = weighted_mean(data['tmax_values'], data['tmax_areas'])
        prec_mean = weighted_mean(data['prec_values'], data['prec_areas'])
        sunhours_mean = weighted_mean(data['sunhours_values'], data['sunhours_areas'])
        temp_avg = weighted_mean(data['temp_values'], data['temp_areas'])
        
        # Calculate overall score (same formula as provinces)
        if all(v is not None for v in [temp_avg, prec_mean, sunhours_mean]):
            # Normalize to 0-1 range
            # Temperature: optimal around 20-25°C
            temp_score = max(0, 1 - abs(temp_avg - 22.5) / 30)
            # Rainfall: optimal around 1-3 mm/day
            rain_score = max(0, 1 - abs(prec_mean - 2) / 20)
            # Sunshine: optimal around 6-10 hours/day
            sun_score = max(0, 1 - abs(sunhours_mean - 8) / 12)
            overall_score = (temp_score + rain_score + sun_score) / 3
        else:
            overall_score = None
        
        climate_data.append({
            'tmin_mean': float(tmin_mean) if tmin_mean is not None else None,
            'tmax_mean': float(tmax_mean) if tmax_mean is not None else None,
            'prec_mean': float(prec_mean) if prec_mean is not None else None,
            'sunhours_mean': float(sunhours_mean) if sunhours_mean is not None else None,
            'temp_avg': float(temp_avg) if temp_avg is not None else None,
            'overall_score': float(overall_score) if overall_score is not None else None,
            'province_count': data['province_count']
        })
    
    # Add climate columns to GeoDataFrame
    for col in ['tmin_mean', 'tmax_mean', 'prec_mean', 'sunhours_mean', 'temp_avg', 'overall_score', 'province_count']:
        result_gdf[col] = [d[col] for d in climate_data]
    
    # Load and add travel advisories
    travel_advisories = load_travel_advisories()
    if travel_advisories:
        result_gdf = add_travel_advisories_to_gdf(result_gdf, travel_advisories)
    
    # 
    # Filter out territories with no climate data (no provinces matched)
    # These are typically tiny uninhabited islands that have no province-level data
    territories_before = len(result_gdf)
    result_gdf = result_gdf[result_gdf['province_count'] > 0].copy()
    territories_removed = territories_before - len(result_gdf)
    
    if territories_removed > 0:
        print(f"Removed {territories_removed} empty territories (no provinces matched)")
    
    # Save to file as GeoJSON
    output_file = COUNTRIES_DIR / f"countries_month_{month:02d}.geojson"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving {len(result_gdf)} territories to: {output_file}")
    result_gdf.to_file(output_file, driver='GeoJSON')
    
    territories_with_data = sum(1 for d in climate_data if d['temp_avg'] is not None)
    print(f"✓ Successfully created country/territory data for month {month:02d}")
    print(f"  Territories with data: {len(result_gdf)} (filtered from {territories_before})")
    return True

def create_metadata():
    """Create metadata file for country aggregated data."""
    metadata = {
        "description": "Country-level aggregated climate data with distant territories split",
        "source": "Aggregated from province-level data",
        "distance_threshold_km": DISTANCE_THRESHOLD_KM,
        "note": "Countries with territories >1000km from main landmass are split into separate entries",
        "variables": {
            "tmin_mean": {
                "description": "Mean minimum temperature",
                "units": "°C"
            },
            "tmax_mean": {
                "description": "Mean maximum temperature",
                "units": "°C"
            },
            "prec_mean": {
                "description": "Mean precipitation",
                "units": "mm/day"
            },
            "sunhours_mean": {
                "description": "Mean sunshine hours",
                "units": "hours/day"
            },
            "temp_avg": {
                "description": "Average temperature (mean of tmin and tmax)",
                "units": "°C"
            },
            "overall_score": {
                "description": "Overall climate score (0-1, higher is better)",
                "units": "dimensionless"
            },
            "safety_level": {
                "description": "U.S. State Dept travel advisory level (1=Normal, 2=Caution, 3=Reconsider, 4=Do Not Travel)",
                "units": "level",
                "source": "U.S. Department of State Travel Advisories",
                "license": "Public Domain (U.S. Government data)"
            },
            "safety_description": {
                "description": "Travel advisory level description",
                "units": "text"
            },
            "safety_summary": {
                "description": "Brief summary of travel advisory",
                "units": "text"
            },
            "safety_url": {
                "description": "URL to detailed travel advisory",
                "units": "url"
            },
            "safety_date": {
                "description": "Date of travel advisory data",
                "units": "YYYY-MM-DD"
            }
        },
        "months": list(range(1, 13)),
        "format": "GeoJSON",
        "created": "2024"
    }
    
    metadata_file = COUNTRIES_DIR / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✓ Created metadata file: {metadata_file}")

def main():
    """Main execution function."""
    print("="*60)
    print("Country-Level Climate Data Aggregation")
    print("="*60)
    
    # Check if country boundaries exist
    country_geojson = COUNTRIES_BASE_DIR / "countries.geojson"
    
    if not country_geojson.exists():
        print(f"\n❌ ERROR: Country boundaries not found: {country_geojson}")
        print("\nPlease run the following command first:")
        print("  python scripts/download_country_boundaries.py")
        return
    
    # Load country boundaries
    print(f"\nLoading country boundaries from: {country_geojson}")
    country_gdf = gpd.read_file(country_geojson)
    print(f"✓ Loaded {len(country_gdf)} country boundaries")
    
    # Check if province data exists
    if not PROVINCES_DIR.exists():
        print(f"\n❌ ERROR: Province data directory not found: {PROVINCES_DIR}")
        return
    
    # Create output directory
    COUNTRIES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each month
    success_count = 0
    for month in range(1, 13):
        if aggregate_month_to_countries(month, country_gdf):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: Successfully processed {success_count}/12 months")
    print(f"{'='*60}")
    
    # Create metadata
    if success_count > 0:
        create_metadata()
    
    print("\n✓ Country aggregation complete!")
    print(f"\nOutput files saved to: {COUNTRIES_DIR}")


if __name__ == '__main__':
    main()
