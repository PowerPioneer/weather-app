import requests
import json

# Test what the API is returning
response = requests.get('http://127.0.0.1:5000/api/combined?month=12&layer=countries')
data = response.json()

print(f"Status: {response.status_code}")
print(f"Response keys: {data.keys()}")

if 'data' in data:
    geojson = data['data']
    print(f"Total features: {len(geojson['features'])}")
    
    # Check Brazil territories
    brazil = [f['properties']['name'] for f in geojson['features'] if 'Brazil' in f['properties']['name']]
    print(f"\nBrazil territories: {brazil}")
    
    # Check Canada territories  
    canada = [f['properties']['name'] for f in geojson['features'] if 'Canada' in f['properties']['name']]
    print(f"Canada territories: {canada}")
else:
    print(f"Unexpected response format: {json.dumps(data, indent=2)[:500]}")
