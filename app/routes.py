from flask import Blueprint, render_template, jsonify, request
import json
from pathlib import Path
import os
from app.data_loader import get_weather_for_location, get_grid_data
from app.province_loader import get_province_data, get_province_data_for_variable, get_available_months

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Path to processed weather data
# __file__ is in app/routes.py, so parent is app/, and we need to go to app/static/data/
DATA_FILE = Path(__file__).parent / "static" / "data" / "era5_stats.json"

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
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

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
        
        return jsonify({
            'variable': variable,
            'month': month,
            'bounds': bounds,
            'grid': grid_data
        })
        
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
        
        # Get province data
        province_data = get_province_data_for_variable(month, variable)
        
        if not province_data:
            return jsonify({'error': 'Province data not available for this month'}), 404
        
        return jsonify({
            'month': month,
            'variable': variable,
            'data': province_data
        })
        
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
