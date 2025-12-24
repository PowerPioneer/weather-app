import requests
import json

# Test what the API is returning
response = requests.get('http://127.0.0.1:5000/api/combined?month=6&layer=countries')
data = response.json()

print(f"Status: {response.status_code}")
print(f"Response keys: {data.keys()}")

if 'data' in data:
    geojson = data['data']
    print(f"Total features: {len(geojson['features'])}")
    
    # Check South Korea and Japan
    for feature in geojson['features']:
        name = feature['properties']['name']
        if name in ['South Korea', 'Japan']:
            props = feature['properties']
            print(f"\n{name}:")
            print(f"  temp_avg: {props.get('temp_avg')}")
            print(f"  prec_mean: {props.get('prec_mean')}")
            print(f"  sunhours_mean: {props.get('sunhours_mean')}")
            print(f"  overall_score: {props.get('overall_score')}")
else:
    print(f"Unexpected response format: {json.dumps(data, indent=2)[:500]}")

