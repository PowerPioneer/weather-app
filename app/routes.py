from flask import Blueprint, render_template, jsonify, request, make_response
import json
import hashlib
from pathlib import Path
import os
from app.data_loader import get_weather_for_location, get_grid_data
from app.province_loader import get_province_data, get_province_data_for_variable, get_available_months
from app.country_loader import get_country_data_for_variable, get_available_months as get_available_country_months

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Path to processed weather data
# __file__ is in app/routes.py, so parent is app/, and we need to go to app/static/data/
DATA_FILE = Path(__file__).parent / "static" / "data" / "era5_stats.json"

def cached_jsonify(data, max_age=86400, etag_base=None):
    """
    Create a JSON response with HTTP caching headers.
    
    Args:
        data: Data to jsonify
        max_age: Cache duration in seconds (default: 24 hours)
        etag_base: String to use for ETag generation (default: use data hash)
    
    Returns:
        Flask response with Cache-Control and ETag headers
    """
    response = make_response(jsonify(data))
    
    # Add Cache-Control header
    response.headers['Cache-Control'] = f'public, max-age={max_age}'
    
    # Generate ETag based on content or provided base
    if etag_base:
        etag = hashlib.md5(etag_base.encode()).hexdigest()
    else:
        # Use hash of JSON string
        etag = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    response.headers['ETag'] = f'"{etag}"'
    
    # Check if client's cached version matches
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match.strip('"') == etag:
        # Client has current version, return 304 Not Modified
        response.status_code = 304
        response.data = b''
    
    return response

def load_weather_data():
    """Load the processed ERA5 data from file."""
    print(f"DEBUG: Looking for data file at: {DATA_FILE}")
    print(f"DEBUG: File exists: {DATA_FILE.exists()}")
    
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            print(f"DEBUG: Successfully loaded data with {len(data.get('data', {}))} variables")
            return data
        except Exception as e:
            print(f"Error loading weather data: {e}")
            return None
    else:
        print(f"ERROR: Data file not found at {DATA_FILE}")
        return None

@main_bp.route('/')
def index():
    """Render the main application page."""
    # Get current month (1-12)
    from datetime import datetime
    current_month = datetime.now().month
    
    # Preload country data for current month to speed up initial load
    # This embeds the data directly in HTML, avoiding the first API call
    initial_country_data = get_country_data_for_variable(current_month, 'overall')
    
    # Convert to JSON string for embedding in script tag
    import json
    initial_data_json = json.dumps(initial_country_data) if initial_country_data else 'null'
    
    return render_template('index.html', 
                         current_month=current_month,
                         initial_country_data=initial_data_json)

@main_bp.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@main_bp.route('/privacy')
def privacy():
    """Render the privacy policy page."""
    return render_template('privacy.html')

@main_bp.route('/terms')
def terms():
    """Render the terms of service page."""
    return render_template('terms.html')

@main_bp.route('/cookies')
def cookies():
    """Render the cookie policy page."""
    return render_template('cookies.html')

@api_bp.route('/weather', methods=['GET'])
def get_weather():
    """Get weather data for a specific location and month."""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    month = request.args.get('month')
    
    # Validate parameters
    if not all([lat, lng, month]):
        return jsonify({
            'error': 'Missing parameters: lat, lng, month required'
        }), 400
    
    try:
        lat = float(lat)
        lng = float(lng)
        month = int(month)
        
        if not (1 <= month <= 12):
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        
        # Get location-specific weather data from GeoTIFF files
        print(f"DEBUG: Fetching weather for lat={lat}, lng={lng}, month={month}")
        location_data = get_weather_for_location(lat, lng, month)
        
        # Build response with actual values for this location
        response = {
            'location': {'lat': lat, 'lng': lng},
            'month': month,
            'data': {}
        }
        
        # Add each variable's value
        if location_data.get('tmin') is not None:
            response['data']['tmin'] = {
                'value': location_data['tmin'],
                'unit': '°C'
            }
        
        if location_data.get('tmax') is not None:
            response['data']['tmax'] = {
                'value': location_data['tmax'],
                'unit': '°C'
            }
        
        if location_data.get('prec') is not None:
            response['data']['prec'] = {
                'value': location_data['prec'],
                'unit': 'mm/dag'
            }
        
        if location_data.get('sunhours') is not None:
            response['data']['sunhours'] = {
                'value': location_data['sunhours'],
                'unit': 'uren/dag'
            }
        
        print(f"DEBUG: Response data: {response['data']}")
        return jsonify(response)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/weather/yearly', methods=['GET'])
def get_weather_yearly():
    """Get weather data for a specific location for all 12 months."""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    # Validate parameters
    if not all([lat, lng]):
        return jsonify({
            'error': 'Missing parameters: lat, lng required'
        }), 400
    
    try:
        lat = float(lat)
        lng = float(lng)
        
        # Get data for all 12 months
        monthly_data = {
            'tmin': [],
            'tmax': [],
            'prec': [],
            'sunhours': []
        }
        
        for month in range(1, 13):
            location_data = get_weather_for_location(lat, lng, month)
            
            monthly_data['tmin'].append(location_data.get('tmin'))
            monthly_data['tmax'].append(location_data.get('tmax'))
            monthly_data['prec'].append(location_data.get('prec'))
            monthly_data['sunhours'].append(location_data.get('sunhours'))
        
        response = {
            'location': {'lat': lat, 'lng': lng},
            'data': monthly_data
        }
        
        return jsonify(response)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/grid', methods=['GET'])
def get_grid():
    """Get grid data for heatmap visualization."""
    variable = request.args.get('variable')
    month = request.args.get('month')
    north = request.args.get('north')
    south = request.args.get('south')
    east = request.args.get('east')
    west = request.args.get('west')
    resolution = request.args.get('resolution', 50)
    
    # Validate parameters
    if not all([variable, month, north, south, east, west]):
        return jsonify({
            'error': 'Missing parameters: variable, month, north, south, east, west required'
        }), 400
    
    try:
        month = int(month)
        bounds = {
            'north': float(north),
            'south': float(south),
            'east': float(east),
            'west': float(west)
        }
        resolution = int(resolution)
        
        if not (1 <= month <= 12):
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        
        if variable not in ['tmin', 'tmax', 'prec', 'sunhours']:
            return jsonify({'error': 'Variable must be tmin, tmax, prec, or sunhours'}), 400
        
        # Get grid data
        grid_data = get_grid_data(variable, month, bounds, resolution)
        
        if not grid_data:
            return jsonify({'error': 'Failed to load grid data'}), 500
        
        # Use shorter cache duration for grid data (1 hour) since bounds vary
        etag_base = f"grid-{variable}-{month}-{north}-{south}-{east}-{west}-{resolution}"
        return cached_jsonify({
            'variable': variable,
            'month': month,
            'bounds': bounds,
            'grid': grid_data
        }, max_age=3600, etag_base=etag_base)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR in /grid: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/regions', methods=['GET'])
def get_regions():
    """Get available regions."""
    weather_data = load_weather_data()
    
    if not weather_data:
        return jsonify({
            'regions': [],
            'message': 'Data not loaded yet'
        }), 503
    
    return jsonify({
        'regions': [],
        'message': 'Regions data available',
        'variables': weather_data.get('variables', []),
        'period': weather_data.get('period')
    })

@api_bp.route('/status', methods=['GET'])
def get_status():
    """Get data loading status."""
    weather_data = load_weather_data()
    
    if weather_data:
        return jsonify({
            'status': 'ready',
            'generated': weather_data.get('generated'),
            'variables': weather_data.get('variables'),
            'data_points': sum(len(v) for v in weather_data.get('data', {}).values())
        })
    else:
        return jsonify({
            'status': 'not_loaded',
            'message': 'Run: python scripts/process_era5_data.py'
        }), 503

@api_bp.route('/provinces', methods=['GET'])
def get_provinces():
    """Get province-level climate data for a specific month and variable."""
    month = request.args.get('month')
    variable = request.args.get('variable', 'overall')
    
    # Optional viewport bounds for filtering
    north = request.args.get('north')
    south = request.args.get('south')
    east = request.args.get('east')
    west = request.args.get('west')
    
    # Validate parameters
    if not month:
        return jsonify({
            'error': 'Missing parameter: month required'
        }), 400
    
    try:
        month = int(month)
        
        if not (1 <= month <= 12):
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        
        if variable not in ['temperature', 'rainfall', 'sunshine', 'overall']:
            return jsonify({'error': 'Variable must be temperature, rainfall, sunshine, or overall'}), 400
        
        # Parse bounds if provided
        bounds = None
        if all([north, south, east, west]):
            bounds = {
                'north': float(north),
                'south': float(south),
                'east': float(east),
                'west': float(west)
            }
        
        # Get province data with optional viewport filtering
        province_data = get_province_data_for_variable(month, variable, bounds)
        
        if not province_data:
            return jsonify({'error': 'Province data not available for this month'}), 404
        
        response_data = {
            'month': month,
            'variable': variable,
            'data': province_data
        }
        
        # Add debug info about filtering
        if bounds:
            response_data['filtered'] = True
            response_data['feature_count'] = len(province_data.get('features', []))
        
        # Cache for 24 hours - province data is static
        etag_base = f"provinces-{month}-{variable}"
        return cached_jsonify(response_data, max_age=86400, etag_base=etag_base)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR in /provinces: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/provinces/available', methods=['GET'])
def get_available_province_months():
    """Get list of months for which province data is available."""
    try:
        available_months = get_available_months()
        return jsonify({
            'available_months': available_months,
            'count': len(available_months)
        })
    except Exception as e:
        print(f"ERROR in /provinces/available: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/countries', methods=['GET'])
def get_countries():
    """Get country-level climate data for a specific month and variable."""
    month = request.args.get('month')
    variable = request.args.get('variable', 'overall')
    
    # Optional viewport bounds for filtering
    north = request.args.get('north')
    south = request.args.get('south')
    east = request.args.get('east')
    west = request.args.get('west')
    
    # Validate parameters
    if not month:
        return jsonify({
            'error': 'Missing parameter: month required'
        }), 400
    
    try:
        month = int(month)
        
        if not (1 <= month <= 12):
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        
        if variable not in ['temperature', 'rainfall', 'sunshine', 'overall']:
            return jsonify({'error': 'Variable must be temperature, rainfall, sunshine, or overall'}), 400
        
        # Parse bounds if provided
        bounds = None
        if all([north, south, east, west]):
            bounds = {
                'north': float(north),
                'south': float(south),
                'east': float(east),
                'west': float(west)
            }
        
        # Get country data with optional viewport filtering
        country_data = get_country_data_for_variable(month, variable, bounds)
        
        if not country_data:
            return jsonify({'error': 'Country data not available for this month'}), 404
        
        response_data = {
            'month': month,
            'variable': variable,
            'data': country_data
        }
        
        # Add debug info about filtering
        if bounds:
            response_data['filtered'] = True
            response_data['feature_count'] = len(country_data.get('features', []))
        
        # Cache for 24 hours - country data is static
        etag_base = f"countries-{month}-{variable}"
        return cached_jsonify(response_data, max_age=86400, etag_base=etag_base)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR in /countries: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/countries/available', methods=['GET'])
def get_available_country_months_route():
    """Get list of months for which country data is available."""
    try:
        available_months = get_available_country_months()
        return jsonify({
            'available_months': available_months,
            'count': len(available_months)
        })
    except Exception as e:
        print(f"ERROR in /countries/available: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/combined', methods=['GET'])
def get_combined_data():
    """
    Get combined climate data for all 4 variables in one request.
    Reduces API calls from 4 to 1 for improved performance.
    
    This endpoint returns data for temperature, rainfall, sunshine, and overall score
    in a single response, with pre-computed overall scores on the server side.
    """
    month = request.args.get('month')
    layer_type = request.args.get('layer', 'countries')  # 'countries' or 'provinces'
    
    # Optional viewport bounds for filtering
    north = request.args.get('north')
    south = request.args.get('south')
    east = request.args.get('east')
    west = request.args.get('west')
    
    # Validate parameters
    if not month:
        return jsonify({
            'error': 'Missing parameter: month required'
        }), 400
    
    try:
        month = int(month)
        
        if not (1 <= month <= 12):
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        
        if layer_type not in ['countries', 'provinces']:
            return jsonify({'error': 'Layer must be countries or provinces'}), 400
        
        # Parse bounds if provided
        bounds = None
        if all([north, south, east, west]):
            bounds = {
                'north': float(north),
                'south': float(south),
                'east': float(east),
                'west': float(west)
            }
        
        # Load data based on layer type
        if layer_type == 'countries':
            # Get base country data (contains all variables)
            from app.country_loader import get_country_data
            data = get_country_data(month)
            
            if bounds:
                from app.country_loader import filter_by_bounds
                data = filter_by_bounds(
                    data,
                    bounds.get('north'),
                    bounds.get('south'),
                    bounds.get('east'),
                    bounds.get('west')
                )
        else:  # provinces
            # Get base province data (contains all variables)
            from app.province_loader import get_province_data
            data = get_province_data(month)
            
            if bounds:
                from app.province_loader import filter_by_bounds
                data = filter_by_bounds(
                    data,
                    bounds.get('north'),
                    bounds.get('south'),
                    bounds.get('east'),
                    bounds.get('west')
                )
        
        if not data:
            return jsonify({'error': f'{layer_type.capitalize()} data not available for this month'}), 404
        
        # Data already contains all variables (temp_avg, prec_mean, sunhours_mean, overall_score)
        # No need to filter - frontend can extract what it needs
        
        response_data = {
            'month': month,
            'layer_type': layer_type,
            'data': data,
            'variables': ['temperature', 'rainfall', 'sunshine', 'overall']
        }
        
        # Add debug info
        if bounds:
            response_data['filtered'] = True
            response_data['feature_count'] = len(data.get('features', []))
        
        # Cache for 24 hours - combined data is static
        # Include bounds in ETag when filtering to avoid cache collisions across different viewports
        if bounds:
            etag_base = f"combined-{layer_type}-{month}-{bounds['north']}-{bounds['south']}-{bounds['east']}-{bounds['west']}"
        else:
            etag_base = f"combined-{layer_type}-{month}"
        return cached_jsonify(response_data, max_age=86400, etag_base=etag_base)
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter format: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR in /combined: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@api_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics for performance monitoring."""
    from app.data_loader import get_value_at_coordinate
