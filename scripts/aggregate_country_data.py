"""
Aggregate province-level climate data to country-level data.

This script reads the province GeoJSON files and aggregates climate data
by country, then joins it with Natural Earth country boundaries.
"""
import json
from pathlib import Path
from collections import defaultdict
import geopandas as gpd
from shapely.geometry import shape, mapping
import numpy as np

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PROVINCES_DIR = DATA_DIR / "provinces" / "aggregated"
COUNTRIES_DIR = DATA_DIR / "countries" / "aggregated"
COUNTRIES_BASE_DIR = DATA_DIR / "countries"

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
    
    # Group climate data by country with area weighting
    country_climate = defaultdict(lambda: {
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
    
    for feature in province_data['features']:
        props = feature['properties']
        province_country_name = props.get('admin', 'Unknown')
        
        # Map province country name to Natural Earth country name
        country_name = COUNTRY_NAME_MAPPING.get(province_country_name, province_country_name)
        
        # Calculate province area (in square degrees as approximation)
        geom = shape(feature['geometry'])
        area = geom.area
        
        # Collect data values with their areas (if not null)
        for key, data_key, area_key in [
            ('tmin_mean', 'tmin_values', 'tmin_areas'),
            ('tmax_mean', 'tmax_values', 'tmax_areas'),
            ('prec_mean', 'prec_values', 'prec_areas'),
            ('sunhours_mean', 'sunhours_values', 'sunhours_areas'),
            ('temp_avg', 'temp_values', 'temp_areas')
        ]:
            value = props.get(key)
            if value is not None and not (isinstance(value, float) and np.isnan(value)) and area > 0:
                country_climate[country_name][data_key].append(value)
                country_climate[country_name][area_key].append(area)
        
        country_climate[country_name]['province_count'] += 1
    
    print(f"Aggregated climate data for {len(country_climate)} countries")
    
    # Create a copy of the country GeoDataFrame for this month
    result_gdf = country_gdf.copy()
    
    # Add climate data to each country
    climate_data = []
    for idx, row in result_gdf.iterrows():
        country_name = row['name']
        
        # Get climate data for this country
        data = country_climate.get(country_name, {
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
    
    # Save to file as GeoJSON
    output_file = COUNTRIES_DIR / f"countries_month_{month:02d}.geojson"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving {len(result_gdf)} countries to: {output_file}")
    result_gdf.to_file(output_file, driver='GeoJSON')
    
    countries_with_data = sum(1 for d in climate_data if d['temp_avg'] is not None)
    print(f"✓ Successfully created country data for month {month:02d}")
    print(f"  Countries with climate data: {countries_with_data}/{len(result_gdf)}")
    return True

def create_metadata():
    """Create metadata file for country aggregated data."""
    metadata = {
        "description": "Country-level aggregated climate data",
        "source": "Aggregated from province-level data",
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
