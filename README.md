# Where to go for great weather

Een interactieve webapp waarmee je je vakantie kan plannen op basis van weersomstandigheden wereldwijd.

## Functies

- **Interactieve wereldkaart**: Bekijk klimaatgegevens over de hele wereld met Leaflet.js
- **Weersgegevens per maand**: Kies elke maand van het jaar
- **Multiple display modes**: 
  - Overall view: Combinatie van alle factoren op basis van je voorkeuren
  - Temperature: Min/max temperatuur in °C
  - Rainfall: Maandelijkse neerslag in mm
  - Sunshine: Zonuren per dag
- **Climate Preferences**: Stel je ideale weerscondities in
- **Location details**: Klik op de kaart voor specifieke weersgegevens en locatie-informatie

## Data Bronnen

### ERA5 (ECMWF Reanalysis v5)
Temperatuur en neerslag data van ERA5 reanalysis
- **Resolutie:** 0.25 graden (~28 km)
- **Periode:** 2020-2024 (5 jaar maandelijkse data)
- **Variabelen:** Min/max temperatuur, neerslag
- **Licentie:** CC-BY 4.0 (gratis voor commercieel gebruik met naamsvermelding)
- **Website:** https://cds.climate.copernicus.eu/
- **Citatie:** Hersbach et al. (2020): ERA5 monthly averaged data on single levels. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). DOI: 10.24381/cds.f17050d7
- **Attributie:** "Generated using Copernicus Climate Change Service information"

### CRU (Climatic Research Unit)
Zonuren data van CRU Time-Series dataset v4.09
- **Resolutie:** 10 arc-minutes (~18 km)
- **Variabelen:** Maandelijkse zonuren per dag
- **Licentie:** Open Government Licence v3.0 (gratis voor commercieel gebruik met naamsvermelding)
- **Website:** https://crudata.uea.ac.uk/cru/data/hrg/
- **Citatie:** Harris, I., Osborn, T.J., Jones, P. et al. Version 4 of the CRU TS monthly high-resolution gridded multivariate climate dataset. Sci Data 7, 109 (2020). https://doi.org/10.1038/s41597-020-0453-3
- **Attributie:** "Climatic Research Unit (University of East Anglia) and NCAS"

### Natural Earth
Provincie/staat grenzen voor toekomstige features
- **Dataset:** Admin-1 States and Provinces (1:10m)
- **Licentie:** Public Domain
- **Website:** https://www.naturalearthdata.com/
- **Citatie:** Natural Earth. Free vector and raster map data @ naturalearthdata.com.

## Projectstructuur

```
Where to go for great weather/
├── app/                  # Flask applicatie
│   ├── __init__.py
│   ├── routes.py        # API endpoints
│   └── data_loader.py   # GeoTIFF data loading
├── templates/            # HTML templates
│   ├── index.html
│   └── about.html
├── static/              # CSS, JavaScript
│   ├── style.css
│   └── script.js
├── data/                # Klimaatdata
│   ├── era5/           # ERA5 data (temp, prec)
│   ├── cru/            # CRU data (sunhours)
│   ├── provinces/      # Natural Earth boundaries
│   └── README.md       # Data documentatie
├── scripts/             # Data processing scripts
│   ├── download_era5_data.py
│   ├── process_era5_data.py
│   ├── process_cru_sunshine.py
│   └── download_province_boundaries.py
├── requirements.txt     # Python dependencies
└── README.md
```

## Installatie

1. Maak een virtual environment:
```bash
python -m venv venv
```

2. Activeer het virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Installeer dependencies:
```bash
pip install -r requirements.txt
```

## Gebruik

```bash
python app.py
```

De app is dan beschikbaar op `http://localhost:5000`

## Technologie

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Kaart**: Leaflet.js met OpenStreetMap tiles
- **Data verwerking**: Rasterio, NumPy, Pandas, GeoPandas
- **Data formaat**: GeoTIFF bestanden voor raster data

## API Endpoints

- `GET /` - Hoofdpagina met interactieve kaart
- `GET /about` - About pagina met data bronnen en licenties
- `GET /api/weather?lat={lat}&lng={lng}&month={month}` - Weersgegevens voor specifieke locatie
- `GET /api/grid?variable={var}&month={month}&bounds={...}` - Grid data voor kaartvisualisatie
- `GET /api/regions` - Beschikbare regio's

## Licentie

Dit project is bedoeld voor educatieve en informatieve doeleinden.

**Klimaat data licenties:**
- ERA5: CC-BY 4.0 (gratis voor commercieel gebruik)
- CRU TS: Open Government Licence v3.0 (gratis voor commercieel gebruik)
- Natural Earth: Public Domain

**Alle databronnen zijn beschikbaar voor commercieel gebruik.**

Zie de individuele databronnen voor gedetailleerde licentie-informatie. Verifieer altijd actuele weersvoorspellingen voordat je reisbeslissingen neemt.

## Disclaimer

Deze applicatie biedt historische klimaatgegevens voor planningsdoeleinden. Voor actuele weersvoorspellingen, raadpleeg professionele weersdiensten.
