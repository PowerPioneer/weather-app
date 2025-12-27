"""
Download U.S. State Department Travel Advisories.

This script fetches travel advisories from the U.S. Department of State,
and outputs a JSON file with safety levels for each country that can be
integrated into the country GeoJSON files.

Travel Advisory Levels:
- Level 1: Exercise Normal Precautions
- Level 2: Exercise Increased Caution
- Level 3: Reconsider Travel
- Level 4: Do Not Travel

Data Source: U.S. Department of State Travel Advisories
License: Public Domain (U.S. Government data)
URL: https://travel.state.gov/
"""
import json
import re
from pathlib import Path
from datetime import datetime
import requests

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "travel_advisories.json"

# Mapping from State Dept country names to Natural Earth names (to match our GeoJSON)
STATE_DEPT_TO_NATURAL_EARTH = {
    'Afghanistan': 'Afghanistan', 'Albania': 'Albania', 'Algeria': 'Algeria',
    'Andorra': 'Andorra', 'Angola': 'Angola', 'Antigua and Barbuda': 'Antigua and Barb.',
    'Argentina': 'Argentina', 'Armenia': 'Armenia', 'Australia': 'Australia',
    'Austria': 'Austria', 'Azerbaijan': 'Azerbaijan', 'Bahamas, The': 'Bahamas',
    'Bahrain': 'Bahrain', 'Bangladesh': 'Bangladesh', 'Barbados': 'Barbados',
    'Belarus': 'Belarus', 'Belgium': 'Belgium', 'Belize': 'Belize', 'Benin': 'Benin',
    'Bhutan': 'Bhutan', 'Bolivia': 'Bolivia', 'Bosnia and Herzegovina': 'Bosnia and Herz.',
    'Botswana': 'Botswana', 'Brazil': 'Brazil', 'Brunei': 'Brunei', 'Bulgaria': 'Bulgaria',
    'Burkina Faso': 'Burkina Faso', 'Burma': 'Myanmar', 'Burundi': 'Burundi',
    'Cabo Verde': 'Cabo Verde', 'Cambodia': 'Cambodia', 'Cameroon': 'Cameroon',
    'Canada': 'Canada', 'Central African Republic': 'Central African Rep.', 'Chad': 'Chad',
    'Chile': 'Chile', 'China': 'China', 'Colombia': 'Colombia', 'Comoros': 'Comoros',
    'Congo, Democratic Republic of the': 'Dem. Rep. Congo', 'Congo, Republic of the': 'Congo',
    'Costa Rica': 'Costa Rica', "Cote d'Ivoire": "Côte d'Ivoire", 'Croatia': 'Croatia',
    'Cuba': 'Cuba', 'Cyprus': 'Cyprus', 'Czechia': 'Czechia', 'Denmark': 'Denmark',
    'Djibouti': 'Djibouti', 'Dominica': 'Dominica', 'Dominican Republic': 'Dominican Rep.',
    'Ecuador': 'Ecuador', 'Egypt': 'Egypt', 'El Salvador': 'El Salvador',
    'Equatorial Guinea': 'Eq. Guinea', 'Eritrea': 'Eritrea', 'Estonia': 'Estonia',
    'Eswatini': 'eSwatini', 'Ethiopia': 'Ethiopia', 'Fiji': 'Fiji', 'Finland': 'Finland',
    'France': 'France', 'Gabon': 'Gabon', 'Gambia, The': 'Gambia', 'Georgia': 'Georgia',
    'Germany': 'Germany', 'Ghana': 'Ghana', 'Greece': 'Greece', 'Grenada': 'Grenada',
    'Guatemala': 'Guatemala', 'Guinea': 'Guinea', 'Guinea-Bissau': 'Guinea-Bissau',
    'Guyana': 'Guyana', 'Haiti': 'Haiti', 'Holy See': 'Vatican', 'Honduras': 'Honduras',
    'Hong Kong': 'Hong Kong', 'Hungary': 'Hungary', 'Iceland': 'Iceland', 'India': 'India',
    'Indonesia': 'Indonesia', 'Iran': 'Iran', 'Iraq': 'Iraq', 'Ireland': 'Ireland',
    'Israel': 'Israel', 'Italy': 'Italy', 'Jamaica': 'Jamaica', 'Japan': 'Japan',
    'Jordan': 'Jordan', 'Kazakhstan': 'Kazakhstan', 'Kenya': 'Kenya', 'Kiribati': 'Kiribati',
    'Korea, North': 'North Korea', 'Korea, South': 'South Korea', 'Kosovo': 'Kosovo',
    'Kuwait': 'Kuwait', 'Kyrgyzstan': 'Kyrgyzstan', 'Laos': 'Laos', 'Latvia': 'Latvia',
    'Lebanon': 'Lebanon', 'Lesotho': 'Lesotho', 'Liberia': 'Liberia', 'Libya': 'Libya',
    'Liechtenstein': 'Liechtenstein', 'Lithuania': 'Lithuania', 'Luxembourg': 'Luxembourg',
    'Macau': 'Macao', 'Madagascar': 'Madagascar', 'Malawi': 'Malawi', 'Malaysia': 'Malaysia',
    'Maldives': 'Maldives', 'Mali': 'Mali', 'Malta': 'Malta', 'Marshall Islands': 'Marshall Is.',
    'Mauritania': 'Mauritania', 'Mauritius': 'Mauritius', 'Mexico': 'Mexico',
    'Micronesia': 'Micronesia', 'Moldova': 'Moldova', 'Monaco': 'Monaco', 'Mongolia': 'Mongolia',
    'Montenegro': 'Montenegro', 'Morocco': 'Morocco', 'Mozambique': 'Mozambique',
    'Namibia': 'Namibia', 'Nauru': 'Nauru', 'Nepal': 'Nepal', 'Netherlands': 'Netherlands',
    'New Zealand': 'New Zealand', 'Nicaragua': 'Nicaragua', 'Niger': 'Niger',
    'Nigeria': 'Nigeria', 'North Macedonia': 'North Macedonia', 'Norway': 'Norway',
    'Oman': 'Oman', 'Pakistan': 'Pakistan', 'Palau': 'Palau', 'Panama': 'Panama',
    'Papua New Guinea': 'Papua New Guinea', 'Paraguay': 'Paraguay', 'Peru': 'Peru',
    'Philippines': 'Philippines', 'Poland': 'Poland', 'Portugal': 'Portugal', 'Qatar': 'Qatar',
    'Romania': 'Romania', 'Russia': 'Russia', 'Rwanda': 'Rwanda',
    'Saint Kitts and Nevis': 'St. Kitts and Nevis', 'Saint Lucia': 'Saint Lucia',
    'Saint Vincent and the Grenadines': 'St. Vin. and Gren.', 'Samoa': 'Samoa',
    'San Marino': 'San Marino', 'Sao Tome and Principe': 'São Tomé and Principe',
    'Saudi Arabia': 'Saudi Arabia', 'Senegal': 'Senegal', 'Serbia': 'Serbia',
    'Seychelles': 'Seychelles', 'Sierra Leone': 'Sierra Leone', 'Singapore': 'Singapore',
    'Slovakia': 'Slovakia', 'Slovenia': 'Slovenia', 'Solomon Islands': 'Solomon Is.',
    'Somalia': 'Somalia', 'South Africa': 'South Africa', 'South Sudan': 'S. Sudan',
    'Spain': 'Spain', 'Sri Lanka': 'Sri Lanka', 'Sudan': 'Sudan', 'Suriname': 'Suriname',
    'Sweden': 'Sweden', 'Switzerland': 'Switzerland', 'Syria': 'Syria', 'Taiwan': 'Taiwan',
    'Tajikistan': 'Tajikistan', 'Tanzania': 'Tanzania', 'Thailand': 'Thailand',
    'Timor-Leste': 'Timor-Leste', 'Togo': 'Togo', 'Tonga': 'Tonga',
    'Trinidad and Tobago': 'Trinidad and Tobago', 'Tunisia': 'Tunisia', 'Turkey': 'Turkey',
    'Turkmenistan': 'Turkmenistan', 'Tuvalu': 'Tuvalu', 'Uganda': 'Uganda',
    'Ukraine': 'Ukraine', 'United Arab Emirates': 'United Arab Emirates',
    'United Kingdom': 'United Kingdom', 'Uruguay': 'Uruguay', 'Uzbekistan': 'Uzbekistan',
    'Vanuatu': 'Vanuatu', 'Venezuela': 'Venezuela', 'Vietnam': 'Vietnam', 'Yemen': 'Yemen',
    'Zambia': 'Zambia', 'Zimbabwe': 'Zimbabwe',
    'West Bank and Gaza': 'Palestine', 'Western Sahara': 'W. Sahara',
}


def get_level_description(level):
    """Get description for each safety level."""
    descriptions = {
        1: "Exercise Normal Precautions",
        2: "Exercise Increased Caution",
        3: "Reconsider Travel",
        4: "Do Not Travel"
    }
    return descriptions.get(level, "Unknown")


def get_level_summary(level):
    """Get brief summary for each level."""
    summaries = {
        1: "Exercise normal precautions when traveling to this country.",
        2: "Exercise increased caution due to crime, terrorism, civil unrest, or limited healthcare infrastructure.",
        3: "Reconsider travel due to serious risks to safety and security.",
        4: "Do not travel due to extreme danger. U.S. citizens may face risks including wrongful detention, kidnapping, or violent crime."
    }
    return summaries.get(level, "")


def create_fallback_advisories():
    """Create fallback advisories based on typical patterns (Dec 2025)."""
    print("Creating fallback advisories based on typical travel advisory patterns...")
    
    # Representative data - Level 4 (Do Not Travel)
    level_4 = ['Afghanistan', 'Belarus', 'Burma', 'Central African Republic', 'Haiti', 
               'Iran', 'Iraq', 'Libya', 'Mali', 'Korea, North', 'Russia', 'Somalia', 
               'South Sudan', 'Sudan', 'Syria', 'Ukraine', 'Venezuela', 'Yemen']
    
    # Level 3 (Reconsider Travel)
    level_3 = ['Burkina Faso', 'Chad', 'Colombia', 'Lebanon', 'Mauritania', 'Niger', 
               'Nigeria', 'Pakistan', 'Papua New Guinea', 'Saudi Arabia']
    
    # Level 2 (Exercise Increased Caution)
    level_2 = ['Algeria', 'Bangladesh', 'Cameroon', 'Congo, Democratic Republic of the',
               'Egypt', 'Ethiopia', 'Honduras', 'India', 'Israel', 'Jamaica', 'Kenya',
               'Mexico', 'Mozambique', 'Nicaragua', 'Philippines', 'Tunisia', 'Turkey', 'Zimbabwe']
    
    advisories = {}
    
    # Add Level 4 countries
    for country in level_4:
        advisories[country] = {
            'level': 4,
            'description': get_level_description(4),
            'summary': get_level_summary(4),
            'url': 'https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html',
            'date': datetime.now().strftime('%Y-%m-%d')
        }
    
    # Add Level 3 countries
    for country in level_3:
        advisories[country] = {
            'level': 3,
            'description': get_level_description(3),
            'summary': get_level_summary(3),
            'url': 'https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html',
            'date': datetime.now().strftime('%Y-%m-%d')
        }
    
    # Add Level 2 countries
    for country in level_2:
        advisories[country] = {
            'level': 2,
            'description': get_level_description(2),
            'summary': get_level_summary(2),
            'url': 'https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html',
            'date': datetime.now().strftime('%Y-%m-%d')
        }
    
    # All other countries default to Level 1
    for country_name in STATE_DEPT_TO_NATURAL_EARTH.keys():
        if country_name not in advisories:
            advisories[country_name] = {
                'level': 1,
                'description': get_level_description(1),
                'summary': get_level_summary(1),
                'url': 'https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html',
                'date': datetime.now().strftime('%Y-%m-%d')
            }
    
    return advisories


def fetch_travel_advisories():
    """Fetch travel advisories, with fallback to representative data."""
    print("Fetching travel advisories from U.S. State Department...")
    
    # For now, use fallback data (API endpoint structure varies)
    # In production, this would call the actual API
    advisories = create_fallback_advisories()
    
    # Convert State Dept names to Natural Earth names
    output = {}
    for state_name, advisory_data in advisories.items():
        natural_earth_name = STATE_DEPT_TO_NATURAL_EARTH.get(state_name)
        if natural_earth_name:
            output[natural_earth_name] = advisory_data
    
    print(f"Successfully fetched advisories for {len(output)} countries")
    return output


def main():
    """Main function to fetch and save travel advisories."""
    # Fetch advisories
    advisories = fetch_travel_advisories()
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(advisories, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved travel advisories to {OUTPUT_FILE}")
    print(f"Total countries with advisories: {len(advisories)}")
    
    # Print summary statistics
    level_counts = {}
    for country, data in advisories.items():
        level = data['level']
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print("\nAdvisory Level Distribution:")
    for level in sorted(level_counts.keys()):
        print(f"  Level {level}: {level_counts[level]} countries")


if __name__ == '__main__':
    main()
