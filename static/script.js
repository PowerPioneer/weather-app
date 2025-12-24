/**
 * Climate Cupid - Main Application with Leaflet.js Map
 */

console.log('Script loaded');

// Get current month (1-12)
const currentMonth = new Date().getMonth() + 1;  // getMonth() returns 0-11
console.log('Current month:', currentMonth);

// Global state
const state = {
    map: null,
    heatmapLayer: null,
    selectedLayer: null,  // Track selected province
    layers: {
        temperature: null,
        sunshine: null,
        rainfall: null
    },
    selectedMonth: currentMonth,  // Start with current month
    selectedLocation: null,
    selectedMarker: null,  // Store the location pin marker
    displayMode: 'overall',
    currentVariable: 'temperature',
    temperatureUnit: 'C',  // 'C' or 'F'
    isLoading: false,
    updateTimeout: null,
    abortController: null,
    lastFetchBounds: null,  // Track last fetched bounds
    cacheBuster: null,  // Timestamp for cache-busting when clearing cache
    combinedDataCache: {},  // Cache for combined endpoint data {month-layerType: data}
    preferences: {
        tempMin: 18,
        tempMax: 30,
        rainMin: 0,
        rainMax: 4,
        sunMin: 6,
        sunMax: 15
    }
};

// Color gradients for each variable
// Temperature scale: blue (cold) → orange (warm) → red (hot)
const colorGradients = {
    temperature: [
        { value: -50, color: [0, 60, 150] },      // Deep blue - extreme cold
        { value: -40, color: [0, 80, 180] },      // Dark blue
        { value: -30, color: [20, 100, 210] },    // Blue
        { value: -20, color: [50, 130, 230] },    // Medium blue
        { value: -10, color: [80, 150, 240] },    // Light blue
        { value: 0, color: [120, 180, 250] },     // Pale blue - freezing point
        { value: 5, color: [160, 200, 250] },     // Very pale blue
        { value: 10, color: [200, 220, 250] },    // Almost white-blue - cool
        { value: 15, color: [240, 230, 210] },    // Cream - mild
        { value: 20, color: [250, 220, 170] },    // Pale orange - pleasant
        { value: 25, color: [255, 200, 120] },    // Light orange - warm
        { value: 30, color: [255, 170, 70] },     // Orange - hot
        { value: 35, color: [255, 130, 40] },     // Dark orange - very hot
        { value: 40, color: [250, 80, 30] },      // Red-orange - scorching
        { value: 45, color: [230, 40, 20] },      // Red - extreme heat
        { value: 50, color: [180, 0, 10] }        // Dark red - deadly heat
    ],
    rainfall: [
        { value: 0, color: [255, 255, 255] },    // White (no rain)
        { value: 2, color: [230, 240, 255] },    // Very pale blue
        { value: 4, color: [200, 225, 255] },    // Pale blue
        { value: 8, color: [150, 200, 255] },    // Light blue
        { value: 12, color: [100, 170, 240] },   // Medium blue
        { value: 20, color: [50, 120, 200] }     // Deep blue (very wet)
    ],
    sunshine: [
        { value: 0, color: [200, 200, 220] },     // Pale gray (no sun)
        { value: 2, color: [255, 250, 205] },     // Lemon chiffon (little sun)
        { value: 4, color: [255, 235, 150] },     // Light yellow
        { value: 6, color: [255, 215, 0] },       // Gold
        { value: 8, color: [255, 195, 0] },       // Darker gold
        { value: 10, color: [255, 165, 0] },      // Orange
        { value: 12, color: [255, 140, 0] },      // Dark orange
        { value: 15, color: [255, 100, 0] }       // Red-orange (maximum sun)
    ]
};

// Weather layer configuration
const layerConfig = {
    temperature: {
        label: 'Temperature (°C)',
        color: '#ff6b6b',
        range: [-50, 50],
        unit: '°C',
        gradient: colorGradients.temperature
    },
    sunshine: {
        label: 'Sunshine (hours/day)',
        color: '#ffd93d',
        range: [0, 15],
        unit: 'hours/day',
        gradient: colorGradients.sunshine
    },
    rainfall: {
        label: 'Rainfall (mm/day)',
        color: '#4ecdc4',
        range: [0, 20],
        unit: 'mm/day',
        gradient: colorGradients.rainfall
    }
};

/**
 * Calculate and set dynamic header height for mobile layout
 */
function setDynamicHeaderHeight() {
    const header = document.querySelector('header');
    if (header) {
        const headerHeight = header.offsetHeight;
        document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
    }
}

/**
 * Add cache-busting parameter to URL if cache has been cleared
 */
function addCacheBuster(url) {
    if (state.cacheBuster) {
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}_cb=${state.cacheBuster}`;
    }
    return url;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Where to go for great weather Initialization ===');
    console.log('1. DOM loaded');
    console.log('2. Leaflet available:', typeof L !== 'undefined');
    
    const mapElement = document.getElementById('map');
    console.log('3. Map element:', mapElement);
    
    if (!mapElement) {
        console.error('ERROR: Map element not found!');
        return;
    }
    
    // Set dynamic header height for mobile
    setDynamicHeaderHeight();
    
    const computedStyle = window.getComputedStyle(mapElement);
    console.log('4. Map element dimensions:', {
        width: computedStyle.width,
        height: computedStyle.height,
        display: computedStyle.display,
        position: computedStyle.position
    });
    
    if (typeof L === 'undefined') {
        console.error('ERROR: Leaflet library not loaded!');
        return;
    }
    
    console.log('5. Initializing map...');
    
    // Initialize map
    initializeMap();
    
    console.log('6. Map object created:', state.map);
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Initialize rainfall info button
    initRainfallInfo();
    
    // Load initial data
    loadRegions();
    
    // Load initial country overlay after a short delay to ensure map is ready
    setTimeout(() => {
        console.log('7. Loading initial country overlay...');
        // Force country data on initial load
        createCountryOverlay();
    }, 500);
    
    // Recalculate header height on window resize
    window.addEventListener('resize', () => {
        setDynamicHeaderHeight();
        updateLegend(); // Update legend on resize to show/hide emoticons
    });
});

/**
 * Initialize Leaflet map with OpenStreetMap
 */
function initializeMap() {
    try {
        // Detect if device is mobile
        const isMobile = window.matchMedia('(max-width: 768px)').matches || ('ontouchstart' in window);
        
        // Set zoom level based on device - mobile needs wider view
        const initialZoom = isMobile ? 2 : 3;
        
        // Create map centered on world view with mobile-specific options
        state.map = L.map('map', {
            zoomControl: !isMobile,  // Disable zoom controls on mobile
            dragging: !isMobile,      // Disable single-finger drag on mobile
            touchZoom: true,          // Enable two-finger pinch zoom
            tap: true,                // Enable tap events
            tapTolerance: 15,         // Tap tolerance in pixels
            scrollWheelZoom: true,    // Enable scroll wheel zoom
            doubleClickZoom: true,    // Keep double-click zoom
            boxZoom: true,            // Keep box zoom
            keyboard: true            // Keep keyboard navigation
        }).setView([20, 0], initialZoom);
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            minZoom: 2
        }).addTo(state.map);
        
        // Add map click event for location selection
        state.map.on('click', function(e) {
            onMapClick(e);
        });
        
        // Add zoom/move event listeners with debouncing
        state.map.on('moveend', function() {
            updateMapInfo();
            // Debounce the heatmap update - longer delay for better performance
            if (state.updateTimeout) {
                clearTimeout(state.updateTimeout);
            }
            state.updateTimeout = setTimeout(updateMapLayers, 500);
        });
        state.map.on('zoomend', function() {
            updateMapInfo();
            // Debounce the heatmap update - longer delay for better performance
            if (state.updateTimeout) {
                clearTimeout(state.updateTimeout);
            }
            state.updateTimeout = setTimeout(updateMapLayers, 500);
        });
        
        console.log('✓ Map initialized with OpenStreetMap');
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

/**
 * Handle map click events
 */
function onMapClick(e) {
    // Check if this is a click on the base map (not a province/country)
    // If there's a selected layer and user clicks empty map area, deselect it
    if (state.selectedLayer && e.originalEvent && e.originalEvent.target.classList.contains('leaflet-container')) {
        // Reset the selected layer style
        if (state.heatmapLayer) {
            state.heatmapLayer.resetStyle(state.selectedLayer);
        }
        state.selectedLayer = null;
        
        // Hide weather details panel
        const weatherPanel = document.getElementById('weatherDetailsPanel');
        if (weatherPanel) {
            weatherPanel.style.display = 'none';
        }
        return;
    }
    
    const lat = e.latlng.lat.toFixed(4);
    const lng = e.latlng.lng.toFixed(4);
    
    state.selectedLocation = {
        lat: lat,
        lng: lng,
        name: `${lat}, ${lng}`
    };
    
    console.log('Location selected:', state.selectedLocation);
    
    // Show weather details panel (overlay on desktop, section on mobile)
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    const weatherPanelOverlay = document.getElementById('weatherDetailsPanelOverlay');
    const weatherPanelSection = document.getElementById('weatherDetailsPanelSection');
    
    if (isMobile && weatherPanelSection) {
        weatherPanelSection.style.display = 'block';
        // Auto-scroll to weather details on mobile
        setTimeout(() => {
            weatherPanelSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    } else if (weatherPanelOverlay) {
        weatherPanelOverlay.style.display = 'block';
    }
    
    // Fetch location name via reverse geocoding
    fetchLocationName(lat, lng);
    
    // Fetch weather data for this location
    if (state.selectedMonth) {
        fetchWeatherData(lat, lng, state.selectedMonth);
    } else {
        document.getElementById('weatherInfo').innerHTML = 
            '<p>⚠️ Selecteer eerst een maand</p>';
    }
}

/**
 * Fetch location name using Nominatim reverse geocoding
 */
async function fetchLocationName(lat, lng) {
    // Update both overlay and section elements
    const countryNameElements = document.querySelectorAll('.country-name');
    const regionNameElements = document.querySelectorAll('.region-name');
    
    // Show loading state
    countryNameElements.forEach(el => el.textContent = 'Loading...');
    regionNameElements.forEach(el => el.textContent = 'Loading...');
    
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10&addressdetails=1`,
            {
                headers: {
                    'Accept-Language': 'nl'
                }
            }
        );
        
        if (!response.ok) {
            throw new Error('Geocoding request failed');
        }
        
        const data = await response.json();
        const address = data.address || {};
        
        // Get country
        const country = address.country || 'Unknown';
        countryNameElements.forEach(el => el.textContent = country);
        
        // Get province/state or city (in order of preference)
        const region = address.state || address.province || address.city || 
                       address.town || address.municipality || address.county || 'Unknown';
        regionNameElements.forEach(el => el.textContent = region);
        
        console.log('Location info:', { country, region, fullAddress: address });
        
    } catch (error) {
        console.error('Error fetching location name:', error);
        countryNameElements.forEach(el => el.textContent = 'Not available');
        regionNameElements.forEach(el => el.textContent = 'Not available');
    }
}

/**
 * Update map info display
 */
function updateMapInfo() {
    if (!state.map) return;
    
    const center = state.map.getCenter();
    const zoom = state.map.getZoom();
    
    const zoomEl = document.getElementById('zoom');
    
    if (zoomEl) {
        zoomEl.textContent = zoom;
    }
}

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    const monthSelect = document.getElementById('monthSelect');
    const mobileMonthSelect = document.getElementById('mobileMonthSelect');
    
    // Set both dropdowns to current month
    monthSelect.value = state.selectedMonth;
    if (mobileMonthSelect) {
        mobileMonthSelect.value = state.selectedMonth;
    }
    
    // Function to handle month change
    function handleMonthChange(monthNum) {
        state.selectedMonth = monthNum;
        
        // Sync both selectors
        monthSelect.value = monthNum;
        if (mobileMonthSelect) {
            mobileMonthSelect.value = monthNum;
        }
        
        console.log('Month selected:', state.selectedMonth);
        
        if (state.selectedLocation) {
            fetchWeatherData(
                state.selectedLocation.lat, 
                state.selectedLocation.lng, 
                state.selectedMonth
            );
        }
        
        updateMapLayers();
    }
    
    // Month select dropdown (desktop)
    monthSelect.addEventListener('change', function(e) {
        const monthNum = parseInt(e.target.value);
        handleMonthChange(monthNum);
    });
    
    // Mobile month select dropdown
    if (mobileMonthSelect) {
        mobileMonthSelect.addEventListener('change', function(e) {
            const monthNum = parseInt(e.target.value);
            handleMonthChange(monthNum);
        });
    }
    
    // Display mode buttons
    const modeButtons = document.querySelectorAll('.mode-btn');
    modeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const newMode = this.dataset.mode;
            console.log('Button clicked, changing mode to:', newMode);
            
            // Clear any pending map updates to prevent race conditions
            if (state.updateTimeout) {
                clearTimeout(state.updateTimeout);
                state.updateTimeout = null;
            }
            
            // Update UI
            modeButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Update state
            state.displayMode = newMode;
            console.log('Display mode updated in state:', state.displayMode);
            
            // Update visualization
            updateLegend();
            updateMapLayers();
        });
    });
    
    // Temperature range sliders
    const tempMin = document.getElementById('tempMin');
    const tempMax = document.getElementById('tempMax');
    tempMin.addEventListener('input', () => updateRangeSlider('temp', tempMin, tempMax));
    tempMax.addEventListener('input', () => updateRangeSlider('temp', tempMin, tempMax));
    
    // Rainfall range sliders
    const rainMin = document.getElementById('rainMin');
    const rainMax = document.getElementById('rainMax');
    rainMin.addEventListener('input', () => updateRangeSlider('rain', rainMin, rainMax));
    rainMax.addEventListener('input', () => updateRangeSlider('rain', rainMin, rainMax));
    
    // Sunshine range sliders
    const sunMin = document.getElementById('sunMin');
    const sunMax = document.getElementById('sunMax');
    sunMin.addEventListener('input', () => updateRangeSlider('sun', sunMin, sunMax));
    sunMax.addEventListener('input', () => updateRangeSlider('sun', sunMin, sunMax));
    
    // Initialize displays
    updateRangeSlider('temp', tempMin, tempMax);
    updateRangeSlider('rain', rainMin, rainMax);
    updateRangeSlider('sun', sunMin, sunMax);
    
    // Preferences toggle with overlay
    const preferencesToggleMobile = document.getElementById('preferencesToggle');
    const preferencesToggleDesktop = document.querySelector('.desktop-toggle');
    const preferencesSidebar = document.querySelector('.climate-preferences-sidebar');
    const preferencesOverlay = document.getElementById('preferencesOverlay');
    const preferencesCloseBtn = document.getElementById('preferencesCloseBtn');
    
    function openPreferences() {
        preferencesSidebar.classList.remove('collapsed');
        if (preferencesOverlay) {
            preferencesOverlay.classList.add('active');
        }
    }
    
    function closePreferences() {
        preferencesSidebar.classList.add('collapsed');
        if (preferencesOverlay) {
            preferencesOverlay.classList.remove('active');
        }
    }
    
    // Mobile toggle button
    if (preferencesToggleMobile) {
        preferencesToggleMobile.addEventListener('click', (e) => {
            e.stopPropagation();
            if (preferencesSidebar.classList.contains('collapsed')) {
                openPreferences();
            } else {
                closePreferences();
            }
        });
    }
    
    // Desktop toggle button
    if (preferencesToggleDesktop) {
        preferencesToggleDesktop.addEventListener('click', (e) => {
            e.stopPropagation();
            if (preferencesSidebar.classList.contains('collapsed')) {
                openPreferences();
            } else {
                closePreferences();
            }
        });
    }
    
    // Close preferences when clicking overlay
    if (preferencesOverlay) {
        preferencesOverlay.addEventListener('click', closePreferences);
    }
    
    // Close preferences with close button
    if (preferencesCloseBtn) {
        preferencesCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closePreferences();
        });
    }
    
    // Temperature unit toggle buttons
    const tempUnitButtons = document.querySelectorAll('.temp-unit-btn');
    tempUnitButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const newUnit = this.dataset.unit;
            if (newUnit !== state.temperatureUnit) {
                // Update UI
                tempUnitButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // Convert temperature preferences
                if (newUnit === 'F') {
                    // Convert C to F
                    state.preferences.tempMin = celsiusToFahrenheit(state.preferences.tempMin);
                    state.preferences.tempMax = celsiusToFahrenheit(state.preferences.tempMax);
                } else {
                    // Convert F to C
                    state.preferences.tempMin = fahrenheitToCelsius(state.preferences.tempMin);
                    state.preferences.tempMax = fahrenheitToCelsius(state.preferences.tempMax);
                }
                
                // Update state
                state.temperatureUnit = newUnit;
                
                // Update sliders and display
                const tempMin = document.getElementById('tempMin');
                const tempMax = document.getElementById('tempMax');
                
                if (newUnit === 'F') {
                    tempMin.min = -4;
                    tempMin.max = 122;
                    tempMax.min = -4;
                    tempMax.max = 122;
                } else {
                    tempMin.min = -20;
                    tempMin.max = 50;
                    tempMax.min = -20;
                    tempMax.max = 50;
                }
                
                tempMin.value = Math.round(state.preferences.tempMin);
                tempMax.value = Math.round(state.preferences.tempMax);
                
                updateRangeSlider('temp', tempMin, tempMax);
                
                // Refresh charts if there's selected location
                if (state.selectedLocation) {
                    fetchWeatherData(
                        state.selectedLocation.lat,
                        state.selectedLocation.lng,
                        state.selectedMonth
                    );
                }
                
                // Update map if in temperature or overall mode
                if (state.displayMode === 'temperature' || state.displayMode === 'overall') {
                    updateMapLayers();
                }
            }
        });
    });
    
    // Clear Cache button
    const clearCacheBtn = document.getElementById('clearCacheBtn');
    const cacheStatus = document.getElementById('cacheStatus');
    
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', async function() {
            try {
                // Disable button during operation
                clearCacheBtn.disabled = true;
                clearCacheBtn.textContent = '🔄 Clearing...';
                
                // Show status message
                cacheStatus.style.display = 'block';
                cacheStatus.className = 'cache-status info';
                cacheStatus.textContent = 'Clearing browser cache...';
                
                // Clear browser cache if API is available
                if ('caches' in window) {
                    const cacheNames = await caches.keys();
                    await Promise.all(cacheNames.map(name => caches.delete(name)));
                    console.log('Service worker caches cleared');
                }
                
                // Add cache-busting timestamp to force fresh data
                state.cacheBuster = Date.now();
                
                // Clear combined data cache
                state.combinedDataCache = {};
                console.log('Combined data cache cleared');
                
                // Force reload all current data
                console.log('Forcing reload of all layers...');
                
                // Remove current layers
                if (state.countryLayer) {
                    state.map.removeLayer(state.countryLayer);
                    state.countryLayer = null;
                }
                if (state.provinceLayer) {
                    state.map.removeLayer(state.provinceLayer);
                    state.provinceLayer = null;
                }
                if (state.heatmapOverlay) {
                    state.map.removeLayer(state.heatmapOverlay);
                    state.heatmapOverlay = null;
                }
                
                // Reload current view
                await updateMapLayers();
                
                // Show success message
                cacheStatus.className = 'cache-status success';
                cacheStatus.textContent = '✓ Cache cleared! Fresh data loaded.';
                
                // Reset button
                clearCacheBtn.disabled = false;
                clearCacheBtn.innerHTML = '<span class="icon">🔄</span> Clear Cache';
                
                // Hide status after 3 seconds
                setTimeout(() => {
                    cacheStatus.style.display = 'none';
                }, 3000);
                
            } catch (error) {
                console.error('Error clearing cache:', error);
                cacheStatus.className = 'cache-status';
                cacheStatus.style.background = '#fee2e2';
                cacheStatus.style.color = '#991b1b';
                cacheStatus.textContent = '❌ Error clearing cache';
                clearCacheBtn.disabled = false;
                clearCacheBtn.innerHTML = '<span class="icon">🔄</span> Clear Cache';
            }
        });
    }
}

/**
 * Convert Celsius to Fahrenheit
 */
function celsiusToFahrenheit(celsius) {
    return (celsius * 9/5) + 32;
}

/**
 * Convert Fahrenheit to Celsius
 */
function fahrenheitToCelsius(fahrenheit) {
    return (fahrenheit - 32) * 5/9;
}

/**
 * Update month display
 */
function updateMonthDisplay() {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    const displayMonth = document.getElementById('displayMonth');
    if (displayMonth) {
        displayMonth.textContent = monthNames[state.selectedMonth - 1];
    }
}

/**
 * Update range slider values and trigger map update
 */
function updateRangeSlider(type, minSlider, maxSlider) {
    let minVal = parseFloat(minSlider.value);
    let maxVal = parseFloat(maxSlider.value);
    
    // Ensure min is always less than max
    if (minVal > maxVal) {
        [minVal, maxVal] = [maxVal, minVal];
        minSlider.value = minVal;
        maxSlider.value = maxVal;
    }
    
    // Update state
    if (type === 'temp') {
        state.preferences.tempMin = minVal;
        state.preferences.tempMax = maxVal;
        const unit = state.temperatureUnit === 'C' ? '°C' : '°F';
        document.getElementById('tempRange').textContent = `${Math.round(minVal)}${unit} - ${Math.round(maxVal)}${unit}`;
    } else if (type === 'rain') {
        state.preferences.rainMin = minVal;
        state.preferences.rainMax = maxVal;
        document.getElementById('rainRange').textContent = `${minVal} - ${maxVal} mm/day`;
    } else if (type === 'sun') {
        state.preferences.sunMin = minVal;
        state.preferences.sunMax = maxVal;
        document.getElementById('sunRange').textContent = `${minVal} - ${maxVal} h/day`;
    }
    
    // Trigger map update if in overall mode
    if (state.displayMode === 'overall') {
        if (state.updateTimeout) {
            clearTimeout(state.updateTimeout);
        }
        state.updateTimeout = setTimeout(updateMapLayers, 300);
    }
}

/**
 * Initialize rainfall info button and tooltip
 */
function initRainfallInfo() {
    const infoBtn = document.getElementById('rainfallInfoBtn');
    const tooltip = document.getElementById('rainfallInfoTooltip');
    
    if (!infoBtn || !tooltip) return;
    
    // Toggle tooltip on button click
    infoBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        tooltip.classList.toggle('show');
    });
    
    // Close tooltip when clicking outside
    document.addEventListener('click', function(e) {
        if (!infoBtn.contains(e.target) && !tooltip.contains(e.target)) {
            tooltip.classList.remove('show');
        }
    });
    
    // Prevent tooltip from closing when clicking inside it
    tooltip.addEventListener('click', function(e) {
        e.stopPropagation();
    });
}

/**
 * Update map layers based on display mode and zoom level
 */
async function updateMapLayers() {
    // Set current variable based on display mode
    if (state.displayMode === 'overall') {
        state.currentVariable = 'overall';
    } else {
        state.currentVariable = state.displayMode;
    }
    
    console.log('Display mode:', state.displayMode, 'Variable:', state.currentVariable);
    
    // Update legend
    updateLegend();
    
    // Get current zoom level
    const zoom = state.map.getZoom();
    const COUNTRY_ZOOM_THRESHOLD = 5; // Show countries when zoom < 5, provinces when zoom >= 5
    
    // Update visualization based on zoom level
    if (state.selectedMonth) {
        if (zoom < COUNTRY_ZOOM_THRESHOLD) {
            console.log(`Zoom ${zoom} < ${COUNTRY_ZOOM_THRESHOLD}: Using country data for month:`, state.selectedMonth);
            await createCountryOverlay();
        } else {
            console.log(`Zoom ${zoom} >= ${COUNTRY_ZOOM_THRESHOLD}: Using province data for month:`, state.selectedMonth);
            await createProvinceOverlay();
        }
    }
}

/**
 * Update legend based on display mode
 */
function updateLegend() {
    const legendContent = document.getElementById('legend-content-horizontal');
    const isMobile = window.innerWidth <= 768;
    
    if (state.displayMode === 'overall') {
        if (isMobile) {
            // Mobile legend without emoticons
            legendContent.innerHTML = `
                <div class="legend-item">
                    <div class="legend-colors">
                        <span class="legend-color" style="background: #4ade80;">Perfect Match</span>
                        <span class="legend-color" style="background: #facc15;">Good Option</span>
                        <span class="legend-color" style="background: #fb923c;">Acceptable</span>
                        <span class="legend-color" style="background: #ef4444;">Avoid</span>
                    </div>
                </div>
            `;
        } else {
            // Desktop legend with emoticons
            legendContent.innerHTML = `
                <div class="legend-item">
                    <div class="legend-colors">
                        <span class="legend-color" style="background: #4ade80;">🌟 Perfect Match</span>
                        <span class="legend-color" style="background: #facc15;">✓ Good Option</span>
                        <span class="legend-color" style="background: #fb923c;">~ Acceptable</span>
                        <span class="legend-color" style="background: #ef4444;">✗ Avoid</span>
                    </div>
                </div>
            `;
        }
    } else {
        const config = layerConfig[state.displayMode];
        if (config) {
            const gradient = config.gradient;
            const gradientStops = gradient.map((stop, i) => {
                const percent = (i / (gradient.length - 1)) * 100;
                return `rgb(${stop.color[0]}, ${stop.color[1]}, ${stop.color[2]}) ${percent}%`;
            }).join(', ');
            
            let minVal = gradient[0].value;
            let maxVal = gradient[gradient.length - 1].value;
            let unit = config.unit;
            
            // Convert temperature values if in Fahrenheit mode
            if (state.displayMode === 'temperature' && state.temperatureUnit === 'F') {
                minVal = Math.round(celsiusToFahrenheit(minVal));
                maxVal = Math.round(celsiusToFahrenheit(maxVal));
                unit = '°F';
            }
            
            legendContent.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-weight: 600; white-space: nowrap;">${config.label}</span>
                    <span style="font-size: 0.75rem; color: #666;">${minVal}</span>
                    <div style="
                        width: 200px;
                        height: 12px;
                        background: linear-gradient(to right, ${gradientStops});
                        border-radius: 3px;
                        border: 1px solid #ccc;
                    "></div>
                    <span style="font-size: 0.75rem; color: #666;">${maxVal} ${unit}</span>
                </div>
            `;
        }
    }
}

/**
 * Load regions from API
 */
function loadRegions() {
    const url = addCacheBuster('/api/regions');
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Regions loaded:', data);
        })
        .catch(error => console.error('Error loading regions:', error));
}

/**
 * Fetch weather data from API (yearly data for charts)
 */
function fetchWeatherData(lat, lng, month) {
    const baseUrl = `/api/weather/yearly?lat=${lat}&lng=${lng}`;
    const url = addCacheBuster(baseUrl);
    
    console.log('Fetching yearly weather data:', url);
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Yearly weather data:', data);
            displayWeatherCharts(data, month);
        })
        .catch(error => {
            console.error('Error fetching weather data:', error);
            document.querySelectorAll('.weather-info').forEach(el => {
                el.innerHTML = `<p>⚠️ Error fetching data</p>`;
            });
        });
}

// Store chart instances for cleanup
let weatherCharts = {
    temperature: null,
    rainfall: null,
    sunshine: null
};

/**
 * Display weather information as charts
 */
function displayWeatherCharts(data, currentMonth) {
    // Update both overlay and section weather info containers
    const weatherInfoContainers = document.querySelectorAll('.weather-info');
    
    if (data.error) {
        weatherInfoContainers.forEach(container => {
            container.innerHTML = `<p>⚠️ ${data.error}</p>`;
        });
        return;
    }
    
    if (!data.data) {
        weatherInfoContainers.forEach(container => {
            container.innerHTML = `
                <p style="margin-top: 1rem; font-size: 0.85rem; color: #999;">
                    No data available for this location
                </p>
            `;
        });
        return;
    }
    
    // Destroy existing charts
    Object.values(weatherCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
    
    // Convert temperature data if needed
    const tempUnit = state.temperatureUnit === 'C' ? '°C' : '°F';
    const tmaxData = state.temperatureUnit === 'F' 
        ? data.data.tmax.map(t => celsiusToFahrenheit(t))
        : data.data.tmax;
    const tminData = state.temperatureUnit === 'F'
        ? data.data.tmin.map(t => celsiusToFahrenheit(t))
        : data.data.tmin;
    
    // Create HTML structure for charts in both containers
    const chartHTML = `
        <div style="padding: 1rem 0;">
            <div style="margin-bottom: 1.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">🌡️ Temperature</h4>
                <canvas class="temp-chart" style="max-height: 150px;"></canvas>
            </div>
            <div style="margin-bottom: 1.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">🌧️ Rainfall</h4>
                <canvas class="rain-chart" style="max-height: 120px;"></canvas>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">☀️ Sunshine</h4>
                <canvas class="sun-chart" style="max-height: 120px;"></canvas>
            </div>
        </div>
    `;
    
    weatherInfoContainers.forEach(container => {
        container.innerHTML = chartHTML;
    });
    
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    // Create charts for all canvases
    document.querySelectorAll('.temp-chart').forEach(canvas => {
        const tempCtx = canvas.getContext('2d');
        new Chart(tempCtx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Max',
                    data: tmaxData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#ef4444'
                },
                {
                    label: 'Min',
                    data: tminData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#3b82f6'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { boxWidth: 12, font: { size: 10 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + tempUnit;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return value + tempUnit;
                        },
                        font: { size: 9 }
                    }
                },
                x: {
                    ticks: { font: { size: 9 } }
                }
            }
        }
    });
    });
    
    // Rainfall bar chart
    document.querySelectorAll('.rain-chart').forEach(canvas => {
        const rainCtx = canvas.getContext('2d');
        new Chart(rainCtx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Rainfall',
                data: data.data.prec,
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + ' mm/day';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + ' mm';
                        },
                        font: { size: 9 }
                    }
                },
                x: {
                    ticks: { font: { size: 9 } }
                }
            }
        }
    });
    });
    
    // Sunshine bar chart
    document.querySelectorAll('.sun-chart').forEach(canvas => {
        const sunCtx = canvas.getContext('2d');
        new Chart(sunCtx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Sunshine',
                data: data.data.sunhours,
                backgroundColor: '#fbbf24',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + ' hours/day';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + ' h';
                        },
                        font: { size: 9 }
                    }
                },
                x: {
                    ticks: { font: { size: 9 } }
                }
            }
        }
    });
    });
}

/**
 * Get color for a value based on gradient
 */
function getColorForValue(value, gradient) {
    if (value === null || value === undefined) {
        return [200, 200, 200, 0.3]; // Gray for no data
    }
    
    // Find the two gradient stops this value falls between
    for (let i = 0; i < gradient.length - 1; i++) {
        const lower = gradient[i];
        const upper = gradient[i + 1];
        
        if (value >= lower.value && value <= upper.value) {
            // Interpolate between the two colors
            const ratio = (value - lower.value) / (upper.value - lower.value);
            const r = Math.round(lower.color[0] + ratio * (upper.color[0] - lower.color[0]));
            const g = Math.round(lower.color[1] + ratio * (upper.color[1] - lower.color[1]));
            const b = Math.round(lower.color[2] + ratio * (upper.color[2] - lower.color[2]));
            return [r, g, b, 0.6];
        }
    }
    
    // Value is outside range
    if (value < gradient[0].value) {
        return [...gradient[0].color, 0.6];
    }
    return [...gradient[gradient.length - 1].color, 0.6];
}

/**
 * Recalculate overall colors from cached data without fetching
 * Used when only slider preferences change but map hasn't moved
 */
async function recalculateOverallColors(cachedData, mapBounds, resolution) {
    const { lats, lngs, tempValues, precValues, sunValues } = cachedData;
    
    console.log('Recalculating colors from cached data...');
    
    // Calculate cell size
    let latStep, lngStep;
    if (lats.length > 1) {
        latStep = Math.abs(lats[1] - lats[0]);
    } else {
        latStep = 0.1;
    }
    if (lngs.length > 1) {
        lngStep = Math.abs(lngs[1] - lngs[0]);
    } else {
        lngStep = 0.1;
    }
    
    // Create rectangles with new colors based on current preferences
    const rectangles = [];
    
    for (let i = 0; i < lats.length; i++) {
        for (let j = 0; j < lngs.length; j++) {
            const tempAvg = tempValues[i][j];
            const prec = precValues[i][j];
            const sunhours = sunValues[i][j];
            
            const result = calculateOverallScore(tempAvg, prec, sunhours);
            
            if (result) {
                const [r, g, b, a] = result.color;
                
                const cellNorth = lats[i] + latStep/2;
                const cellSouth = lats[i] - latStep/2;
                const cellWest = lngs[j] - lngStep/2;
                const cellEast = lngs[j] + lngStep/2;
                
                const cellBounds = [
                    [cellSouth, cellWest],
                    [cellNorth, cellEast]
                ];
                
                const rect = L.rectangle(cellBounds, {
                    color: 'transparent',
                    weight: 0,
                    fillColor: `rgb(${r}, ${g}, ${b})`,
                    fillOpacity: a,
                    interactive: false
                });
                rectangles.push(rect);
            }
        }
    }
    
    // Remove old layer and add new one
    if (state.heatmapLayer) {
        state.map.removeLayer(state.heatmapLayer);
        state.heatmapLayer = null;
    }
    
    state.heatmapLayer = L.layerGroup(rectangles);
    state.heatmapLayer.addTo(state.map);
    
    console.log(`Overall heatmap recalculated with ${rectangles.length} cells (no fetch)`);
}

/**
 * Create overall heatmap by fetching all three variables
 */
async function createOverallHeatmap(mapBounds, resolution, month, signal) {
    try {
        // Fetch all variables including tmin and tmax for average temperature
        const baseUrl = `/api/grid?month=${month}&` +
                       `north=${mapBounds.north}&south=${mapBounds.south}&` +
                       `east=${mapBounds.east}&west=${mapBounds.west}&resolution=${resolution}`;
        
        console.log('Fetching all variables for overall view...');
        
        const [tminResponse, tmaxResponse, precResponse, sunResponse] = await Promise.all([
            fetch(addCacheBuster(baseUrl + '&variable=tmin'), { signal }),
            fetch(addCacheBuster(baseUrl + '&variable=tmax'), { signal }),
            fetch(addCacheBuster(baseUrl + '&variable=prec'), { signal }),
            fetch(addCacheBuster(baseUrl + '&variable=sunhours'), { signal })
        ]);
        
        // Check if map bounds changed
        const currentBounds = state.map.getBounds();
        const boundsChanged = Math.abs(currentBounds.getNorth() - mapBounds.north) > 0.5 ||
                             Math.abs(currentBounds.getSouth() - mapBounds.south) > 0.5 ||
                             Math.abs(currentBounds.getEast() - mapBounds.east) > 0.5 ||
                             Math.abs(currentBounds.getWest() - mapBounds.west) > 0.5;
        
        if (boundsChanged) {
            console.log('Map bounds changed significantly during fetch, triggering new request');
            setTimeout(updateMapLayers, 100);
            return;
        }
        
        const tminData = await tminResponse.json();
        const tmaxData = await tmaxResponse.json();
        const precData = await precResponse.json();
        const sunData = await sunResponse.json();
        
        if (tminData.error || tmaxData.error || precData.error || sunData.error) {
            console.error('Error fetching grid data');
            state.isLoading = false;
            return;
        }
        
        const { lats, lngs } = tminData.grid;
        const tminValues = tminData.grid.values;
        const tmaxValues = tmaxData.grid.values;
        const precValues = precData.grid.values;
        const sunValues = sunData.grid.values;
        
        // Calculate average temperature
        const tempAvgValues = [];
        for (let i = 0; i < lats.length; i++) {
            tempAvgValues[i] = [];
            for (let j = 0; j < lngs.length; j++) {
                const tmin = tminValues[i][j];
                const tmax = tmaxValues[i][j];
                
                if (tmin !== null && tmin !== undefined && tmax !== null && tmax !== undefined) {
                    tempAvgValues[i][j] = (tmin + tmax) / 2;
                } else {
                    tempAvgValues[i][j] = null;
                }
            }
        }
        
        // Cache the fetched data for quick recalculation
        state.cachedOverallData = {
            lats, lngs, tempValues: tempAvgValues, precValues, sunValues, mapBounds, resolution
        };
        
        console.log(`Grid size: ${lats.length}x${lngs.length}`);
        
        // Calculate cell size
        let latStep, lngStep;
        if (lats.length > 1) {
            latStep = Math.abs(lats[1] - lats[0]);
        } else {
            latStep = 0.1;
        }
        if (lngs.length > 1) {
            lngStep = Math.abs(lngs[1] - lngs[0]);
        } else {
            lngStep = 0.1;
        }
        
        console.log(`Cell dimensions: latStep=${latStep.toFixed(4)}, lngStep=${lngStep.toFixed(4)}`);
        
        // Create rectangles for overall view
        const rectangles = [];
        
        for (let i = 0; i < lats.length; i++) {
            for (let j = 0; j < lngs.length; j++) {
                const tempAvg = tempAvgValues[i][j];
                const prec = precValues[i][j];
                const sunhours = sunValues[i][j];
                
                const result = calculateOverallScore(tempAvg, prec, sunhours);
                
                if (result) {
                    const [r, g, b, a] = result.color;
                    
                    const cellNorth = lats[i] + latStep/2;
                    const cellSouth = lats[i] - latStep/2;
                    const cellWest = lngs[j] - lngStep/2;
                    const cellEast = lngs[j] + lngStep/2;
                    
                    const cellBounds = [
                        [cellSouth, cellWest],
                        [cellNorth, cellEast]
                    ];
                    
                    const rect = L.rectangle(cellBounds, {
                        color: 'transparent',
                        weight: 0,
                        fillColor: `rgb(${r}, ${g}, ${b})`,
                        fillOpacity: a,
                        interactive: false
                    });
                    rectangles.push(rect);
                }
            }
        }
        
        // Remove old layer and add new one
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
            state.heatmapLayer = null;
        }
        
        state.heatmapLayer = L.layerGroup(rectangles);
        state.heatmapLayer.addTo(state.map);
        
        console.log(`Overall heatmap created with ${rectangles.length} cells`);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Fetch aborted');
        } else {
            console.error('Error creating overall heatmap:', error);
        }
    }
}

/**
 * Calculate overall match score for a location
 * Returns: { score: 0-1, color: [r,g,b,a] }
 * @param {number} tempAvg - Average temperature (tmin + tmax) / 2
 * @param {number} prec - Precipitation in mm/day
 * @param {number} sunhours - Sunshine hours per day
 */
function calculateOverallScore(tempAvg, prec, sunhours) {
    const prefs = state.preferences;
    let matchCount = 0;
    let totalCriteria = 0;
    
    // Temperature match (using average of tmin and tmax)
    // Note: tempAvg from data is always in Celsius, so convert if user is in Fahrenheit
    if (tempAvg !== null && tempAvg !== undefined) {
        totalCriteria++;
        let tempToCompare = tempAvg;
        let minTemp = prefs.tempMin;
        let maxTemp = prefs.tempMax;
        
        // If user preferences are in Fahrenheit, convert the data temperature
        if (state.temperatureUnit === 'F') {
            tempToCompare = celsiusToFahrenheit(tempAvg);
        }
        
        if (tempToCompare >= minTemp && tempToCompare <= maxTemp) {
            matchCount++;
        }
    }
    
    // Rainfall match
    if (prec !== null && prec !== undefined) {
        totalCriteria++;
        if (prec >= prefs.rainMin && prec <= prefs.rainMax) {
            matchCount++;
        }
    }
    
    // Sunshine match
    if (sunhours !== null && sunhours !== undefined) {
        totalCriteria++;
        if (sunhours >= prefs.sunMin && sunhours <= prefs.sunMax) {
            matchCount++;
        }
    }
    
    // No data available
    if (totalCriteria === 0) return null;
    
    // Color coding based on number of matches
    let color;
    if (matchCount === totalCriteria) {
        // All criteria match: Green
        color = [74, 222, 128, 0.7];  // #4ade80 - bright green
    } else if (matchCount === 2 || (matchCount === 1 && totalCriteria === 2)) {
        // 2 out of 3 match (or 1 out of 2): Yellow
        color = [250, 204, 21, 0.7];  // #facc15 - bright yellow
    } else if (matchCount === 1) {
        // Only 1 out of 3 matches: Orange
        color = [251, 146, 60, 0.7];  // #fb923c - bright orange
    } else {
        // No matches: Red
        color = [239, 68, 68, 0.7];  // #ef4444 - bright red
    }
    
    const score = matchCount / totalCriteria;
    return { score, color, matchCount, totalCriteria };
}

/**
 * Fetch combined data for all 4 variables (temperature, rainfall, sunshine, overall) in one request.
 * Uses the combined endpoint to reduce API calls from 4 to 1.
 * 
 * @param {number} month - Month number (1-12)
 * @param {string} layerType - 'countries' or 'provinces'
 * @param {object} bounds - Optional viewport bounds {north, south, east, west}
 * @returns {object|null} Combined GeoJSON data with all variables, or null if error
 */
async function fetchCombinedData(month, layerType, bounds = null) {
    const cacheKey = `${month}-${layerType}`;
    
    // Check cache first (combined data contains all variables)
    if (state.combinedDataCache[cacheKey]) {
        console.log(`Using cached combined data for ${layerType} month ${month}`);
        return state.combinedDataCache[cacheKey];
    }
    
    try {
        // Build URL with optional bounds
        let url = `/api/combined?month=${month}&layer=${layerType}`;
        if (bounds) {
            url += `&north=${bounds.north}&south=${bounds.south}&east=${bounds.east}&west=${bounds.west}`;
        }
        
        const finalUrl = addCacheBuster(url);
        console.log(`Fetching combined data: ${finalUrl}`);
        
        const response = await fetch(finalUrl);
        const result = await response.json();
        
        if (result.error) {
            console.error('Error fetching combined data:', result.error);
            return null;
        }
        
        console.log(`✓ Combined data loaded: ${result.variables.length} variables, ${result.data.features.length} features`);
        
        // Cache the data (without bounds key since bounds are applied server-side)
        state.combinedDataCache[cacheKey] = result.data;
        
        return result.data;
    } catch (error) {
        console.error('Error fetching combined data:', error);
        return null;
    }
}

/**
 * Create country-based map visualization
 * Uses pre-aggregated country data for zoomed-out views
 */
async function createCountryOverlay() {
    const variable = state.currentVariable;
    const month = state.selectedMonth;
    
    console.log(`createCountryOverlay: variable=${variable}, month=${month}`);
    
    if (!month || !variable) {
        console.log('No month or variable selected');
        return;
    }
    
    state.isLoading = true;
    
    try {
        // Check if we have preloaded data (only on initial load with default viewport)
        let geojsonData;
        
        // Use preloaded data only if it exists and matches the current month
        if (window.PRELOADED_COUNTRY_DATA && 
            window.PRELOADED_COUNTRY_DATA.month === month && 
            window.PRELOADED_COUNTRY_DATA.data) {
            console.log('Using preloaded country data from HTML');
            geojsonData = window.PRELOADED_COUNTRY_DATA.data;
            // Clear preloaded data after use to free memory
            window.PRELOADED_COUNTRY_DATA = null;
        } else {
            // Get current viewport bounds for filtering
            const bounds = state.map.getBounds();
            const mapBounds = {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
            
            // Try to fetch from combined endpoint first (more efficient - one request for all variables)
            geojsonData = await fetchCombinedData(month, 'countries', mapBounds);
            
            // If combined endpoint fails or is not available, fall back to single variable endpoint
            if (!geojsonData) {
                console.log('Combined endpoint failed, falling back to single variable endpoint');
                const baseUrl = `/api/countries?month=${month}&variable=${variable}&` +
                           `north=${mapBounds.north}&south=${mapBounds.south}&` +
                           `east=${mapBounds.east}&west=${mapBounds.west}`;
                const url = addCacheBuster(baseUrl);
                console.log(`Fetching country data: ${url}`);
                
                const response = await fetch(url);
                const result = await response.json();
                
                if (result.error) {
                    console.error('Error fetching country data:', result.error);
                    state.isLoading = false;
                    return;
                }
                
                geojsonData = result.data;
                
                // Log filtering stats if available
                if (result.filtered) {
                    console.log(`Viewport filtering: ${result.feature_count} countries in view`);
                }
            }
        }
        
        // Map variable names to data field names
        const variableFieldMap = {
            'temperature': 'temp_avg',
            'rainfall': 'prec_mean',
            'sunshine': 'sunhours_mean',
            'overall': 'overall_score'
        };
        
        const dataField = variableFieldMap[variable];
        
        // Create style function based on variable
        const styleFunction = (feature) => {
            const props = feature.properties;
            const value = props[dataField];
            
            // No data - show very light gray
            if (value === null || value === undefined) {
                return {
                    fillColor: '#ccc',
                    fillOpacity: 0.1,
                    color: '#b8c9c6',
                    weight: 0.5,
                    opacity: 0.3
                };
            }
            
            let fillColor, fillOpacity;
            
            if (variable === 'overall') {
                // Calculate overall score based on current user preferences
                const tempAvg = props.temp_avg;
                const prec = props.prec_mean;
                const sunhours = props.sunhours_mean;
                
                const result = calculateOverallScore(tempAvg, prec, sunhours);
                
                if (result) {
                    const [r, g, b, a] = result.color;
                    fillColor = `rgb(${r}, ${g}, ${b})`;
                    fillOpacity = a;
                } else {
                    fillColor = '#ccc';
                    fillOpacity = 0.1;
                }
            } else {
                // Use gradient for specific variables
                const gradient = layerConfig[variable].gradient;
                const [r, g, b, a] = getColorForValue(value, gradient);
                fillColor = `rgb(${r}, ${g}, ${b})`;
                fillOpacity = a;
            }
            
            return {
                fillColor: fillColor,
                fillOpacity: fillOpacity,
                color: '#b8c9c6',
                weight: 0.5,
                opacity: 0.3
            };
        };
        
        // Remove old layer
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
            state.heatmapLayer = null;
        }
        
        // Create new GeoJSON layer
        state.heatmapLayer = L.geoJSON(geojsonData, {
            style: styleFunction,
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                const value = props[dataField];
                
                // Format value for display
                let valueStr = 'No data';
                if (value !== null && value !== undefined) {
                    if (variable === 'overall') {
                        valueStr = `Match: ${(value * 100).toFixed(0)}%`;
                    } else if (variable === 'temperature') {
                        const tempC = value;
                        const tempF = (tempC * 9/5) + 32;
                        valueStr = state.temperatureUnit === 'C' 
                            ? `${tempC.toFixed(1)}°C` 
                            : `${tempF.toFixed(1)}°F`;
                    } else if (variable === 'rainfall') {
                        valueStr = `${value.toFixed(1)} mm/day`;
                    } else if (variable === 'sunshine') {
                        valueStr = `${value.toFixed(1)} hours/day`;
                    }
                }
                
                const countryName = props.name || 'Unknown';
                
                // Bind popup
                layer.bindPopup(
                    `<strong>${countryName}</strong><br>${valueStr}`,
                    { closeButton: false, autoPan: false }
                );
                
                // Add hover and click highlighting
                layer.on('mouseover', function(e) {
                    const layer = e.target;
                    layer.setStyle({
                        weight: 2,
                        opacity: 0.7,
                        color: '#2c5f4f'
                    });
                    layer.openPopup();
                });
                
                layer.on('mouseout', function(e) {
                    const layer = e.target;
                    // Only reset if this isn't the selected layer
                    if (state.selectedLayer !== layer) {
                        layer.setStyle({
                            weight: 0.5,
                            opacity: 0.3,
                            color: '#b8c9c6'
                        });
                        layer.closePopup();
                    }
                });
                
                layer.on('click', function(e) {
                    const currentLayer = e.target;
                    const props = currentLayer.feature.properties;
                    
                    // If clicking the same country, deselect it
                    if (state.selectedLayer === currentLayer) {
                        currentLayer.setStyle({
                            weight: 0.5,
                            opacity: 0.3,
                            color: '#b8c9c6'
                        });
                        currentLayer.closePopup();
                        state.selectedLayer = null;
                        
                        // Hide weather details panel
                        const weatherPanel = document.getElementById('weatherDetailsPanel');
                        if (weatherPanel) {
                            weatherPanel.style.display = 'none';
                        }
                        return;
                    }
                    
                    // Deselect previous selection
                    if (state.selectedLayer) {
                        state.heatmapLayer.resetStyle(state.selectedLayer);
                        state.selectedLayer.closePopup();
                    }
                    
                    // Highlight clicked country
                    currentLayer.setStyle({
                        weight: 2,
                        opacity: 0.9,
                        color: '#2c5f4f'
                    });
                    currentLayer.openPopup();
                    
                    state.selectedLayer = currentLayer;
                    
                    // Get country center for weather data
                    const bounds = currentLayer.getBounds();
                    const center = bounds.getCenter();
                    const lat = center.lat.toFixed(4);
                    const lng = center.lng.toFixed(4);
                    
                    // Store selected location
                    state.selectedLocation = {
                        lat: lat,
                        lng: lng,
                        name: props.name || `${lat}, ${lng}`
                    };
                    
                    // Show weather details panel (overlay on desktop, section on mobile)
                    const isMobile = window.matchMedia('(max-width: 768px)').matches;
                    const weatherPanelOverlay = document.getElementById('weatherDetailsPanelOverlay');
                    const weatherPanelSection = document.getElementById('weatherDetailsPanelSection');
                    
                    if (isMobile && weatherPanelSection) {
                        weatherPanelSection.style.display = 'block';
                        // Auto-scroll to weather details on mobile
                        setTimeout(() => {
                            weatherPanelSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }, 100);
                    } else if (weatherPanelOverlay) {
                        weatherPanelOverlay.style.display = 'block';
                    }
                    
                    // Update location info in both panels (country only, no region)
                    document.querySelectorAll('.country-name').forEach(el => {
                        el.textContent = props.name || 'Unknown';
                    });
                    document.querySelectorAll('.region-name').forEach(el => {
                        el.textContent = '';  // No region for countries
                    });
                    
                    // Fetch weather data for country center
                    if (state.selectedMonth) {
                        fetchWeatherData(lat, lng, state.selectedMonth);
                    }
                });
            }
        }).addTo(state.map);
        
        console.log('✓ Country overlay created');
        
    } catch (error) {
        console.error('Error creating country overlay:', error);
    } finally {
        state.isLoading = false;
    }
}

/**
 * Create province-based map visualization
 * Uses pre-aggregated province data instead of grid-based heatmap
 */
async function createProvinceOverlay() {
    const variable = state.currentVariable;
    const month = state.selectedMonth;
    
    console.log(`createProvinceOverlay: variable=${variable}, month=${month}`);
    
    if (!month || !variable) {
        console.log('No month or variable selected');
        return;
    }
    
    state.isLoading = true;
    
    try {
        // Get current viewport bounds for filtering
        const bounds = state.map.getBounds();
        const mapBounds = {
            north: bounds.getNorth(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            west: bounds.getWest()
        };
        
        // Try to fetch from combined endpoint first (more efficient - one request for all variables)
        let geojsonData = await fetchCombinedData(month, 'provinces', mapBounds);
        
        // If combined endpoint fails or is not available, fall back to single variable endpoint
        if (!geojsonData) {
            console.log('Combined endpoint failed, falling back to single variable endpoint');
            const baseUrl = `/api/provinces?month=${month}&variable=${variable}&` +
                       `north=${mapBounds.north}&south=${mapBounds.south}&` +
                       `east=${mapBounds.east}&west=${mapBounds.west}`;
            const url = addCacheBuster(baseUrl);
            console.log(`Fetching province data: ${url}`);
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.error) {
                console.error('Error fetching province data:', result.error);
                state.isLoading = false;
                return;
            }
            
            geojsonData = result.data;
            
            // Log filtering stats if available
            if (result.filtered) {
                console.log(`Viewport filtering: ${result.feature_count} provinces in view`);
            }
        }
        
        // Map variable names to data field names
        const variableFieldMap = {
            'temperature': 'temp_avg',
            'rainfall': 'prec_mean',
            'sunshine': 'sunhours_mean',
            'overall': 'overall_score'
        };
        
        const dataField = variableFieldMap[variable];
        
        // Create style function based on variable
        const styleFunction = (feature) => {
            const props = feature.properties;
            const value = props[dataField];
            
            // No data - show very light gray
            if (value === null || value === undefined) {
                return {
                    fillColor: '#ccc',
                    fillOpacity: 0.1,
                    color: '#b8c9c6',
                    weight: 0.1,
                    opacity: 0.1
                };
            }
            
            let fillColor, fillOpacity;
            
            if (variable === 'overall') {
                // Calculate overall score based on current user preferences
                const tempAvg = props.temp_avg;
                const prec = props.prec_mean;
                const sunhours = props.sunhours_mean;
                
                const result = calculateOverallScore(tempAvg, prec, sunhours);
                
                if (result) {
                    const [r, g, b, a] = result.color;
                    fillColor = `rgb(${r}, ${g}, ${b})`;
                    fillOpacity = a;
                } else {
                    fillColor = '#ccc';
                    fillOpacity = 0.1;
                }
            } else {
                // Use gradient for specific variables
                const gradient = layerConfig[variable].gradient;
                const [r, g, b, a] = getColorForValue(value, gradient);
                fillColor = `rgb(${r}, ${g}, ${b})`;
                fillOpacity = a;
            }
            
            return {
                fillColor: fillColor,
                fillOpacity: fillOpacity,
                color: '#b8c9c6',
                weight: 0.1,
                opacity: 0.1
            };
        };
        
        // Remove old layer
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
            state.heatmapLayer = null;
            state.selectedLayer = null;  // Clear selected layer when removing overlay
        }
        
        // Add new GeoJSON layer
        state.heatmapLayer = L.geoJSON(geojsonData, {
            style: styleFunction,
            interactive: true,
            bubblingMouseEvents: false,
            onEachFeature: (feature, layer) => {
                // Disable keyboard interaction to prevent focus rectangle
                if (layer._path) {
                    layer._path.setAttribute('tabindex', '-1');
                }
                
                // Add tooltip on hover
                const props = feature.properties;
                const value = props[dataField];
                
                if (value !== null && value !== undefined) {
                    let valueStr;
                    if (variable === 'overall') {
                        valueStr = (value * 100).toFixed(0) + '% match';
                    } else if (variable === 'temperature') {
                        // Convert temperature if in Fahrenheit mode
                        const displayValue = state.temperatureUnit === 'F' 
                            ? celsiusToFahrenheit(value)
                            : value;
                        const unit = state.temperatureUnit === 'F' ? '°F' : '°C';
                        valueStr = displayValue.toFixed(1) + ' ' + unit;
                    } else {
                        valueStr = value.toFixed(1) + ' ' + layerConfig[variable].unit;
                    }
                    
                    const provinceName = props.name || 'Unknown';
                    const countryName = props.admin || '';
                    
                    layer.bindTooltip(
                        `<strong>${provinceName}</strong><br>${countryName}<br>${valueStr}`,
                        { sticky: true }
                    );
                }
                
                // Add hover and click highlighting that follows province shape
                layer.on({
                    mouseover: function(e) {
                        const currentLayer = e.target;
                        // Don't highlight on mouseover if this layer is selected
                        if (state.selectedLayer !== currentLayer) {
                            currentLayer.setStyle({
                                weight: 2,
                                color: '#4a7d78',
                                opacity: 0.8
                            });
                            currentLayer.bringToFront();
                        }
                    },
                    mouseout: function(e) {
                        const currentLayer = e.target;
                        // Don't reset style on mouseout if this layer is selected
                        if (state.selectedLayer !== currentLayer) {
                            currentLayer.setStyle({
                                weight: 0.1,
                                color: '#b8c9c6',
                                opacity: 0.1
                            });
                        }
                    },
                    click: function(e) {
                        const currentLayer = e.target;
                        const props = currentLayer.feature.properties;
                        
                        // If clicking the same province, deselect it
                        if (state.selectedLayer === currentLayer) {
                            currentLayer.setStyle({
                                weight: 0.1,
                                color: '#b8c9c6',
                                opacity: 0.1
                            });
                            state.selectedLayer = null;
                            
                            // Hide weather details panel
                            const weatherPanel = document.getElementById('weatherDetailsPanel');
                            if (weatherPanel) {
                                weatherPanel.style.display = 'none';
                            }
                            return;
                        }
                        
                        // Reset previously selected layer
                        if (state.selectedLayer) {
                            state.selectedLayer.setStyle({
                                weight: 0.1,
                                color: '#b8c9c6',
                                opacity: 0.1
                            });
                        }
                        
                        // Highlight clicked province
                        currentLayer.setStyle({
                            weight: 3,
                            color: '#2d4f4c',
                            opacity: 1
                        });
                        currentLayer.bringToFront();
                        
                        // Store as selected layer
                        state.selectedLayer = currentLayer;
                        
                        // Get province center for weather data
                        const bounds = currentLayer.getBounds();
                        const center = bounds.getCenter();
                        const lat = center.lat.toFixed(4);
                        const lng = center.lng.toFixed(4);
                        
                        // Store selected location
                        state.selectedLocation = {
                            lat: lat,
                            lng: lng,
                            name: props.name || `${lat}, ${lng}`
                        };
                        
                        // Show weather details panel (overlay on desktop, section on mobile)
                        const isMobile = window.matchMedia('(max-width: 768px)').matches;
                        const weatherPanelOverlay = document.getElementById('weatherDetailsPanelOverlay');
                        const weatherPanelSection = document.getElementById('weatherDetailsPanelSection');
                        
                        if (isMobile && weatherPanelSection) {
                            weatherPanelSection.style.display = 'block';
                            // Auto-scroll to weather details on mobile
                            setTimeout(() => {
                                weatherPanelSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }, 100);
                        } else if (weatherPanelOverlay) {
                            weatherPanelOverlay.style.display = 'block';
                        }
                        
                        // Update location info in both panels
                        document.querySelectorAll('.country-name').forEach(el => {
                            el.textContent = props.admin || 'Unknown';
                        });
                        document.querySelectorAll('.region-name').forEach(el => {
                            el.textContent = props.name || 'Unknown';
                        });
                        
                        // Fetch weather data for province center
                        if (state.selectedMonth) {
                            fetchWeatherData(lat, lng, state.selectedMonth);
                        }
                    }
                });
            }
        });
        
        state.heatmapLayer.addTo(state.map);
        
        console.log('Province overlay created successfully');
        
    } catch (error) {
        console.error('Error creating province overlay:', error);
    } finally {
        state.isLoading = false;
    }
}

/**
 * Create heatmap overlay based on current variable and month
 */
async function createHeatmapOverlay() {
    const variable = state.currentVariable;
    const month = state.selectedMonth;
    
    // Cancel any pending request
    if (state.abortController) {
        state.abortController.abort();
        state.abortController = null;
    }

    // Create new controller for this request
    state.abortController = new AbortController();
    const signal = state.abortController.signal;
    
    console.log(`createHeatmapOverlay: variable=${variable}, month=${month}`);
    
    if (!month || !variable) {
        console.log('No month or variable selected');
        return;
    }
    
    state.isLoading = true;
    
    console.log(`Creating heatmap for ${variable}, month ${month}`);
    
    // Get current map bounds FRESH for this request
    const bounds = state.map.getBounds();
    const mapBounds = {
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest()
    };
    
    console.log('Current map bounds:', mapBounds);
    
    // Calculate resolution based on zoom level
    const zoom = state.map.getZoom();
    let resolution;
    if (zoom <= 3) {
        resolution = 120;  // Base world view
    } else if (zoom <= 5) {
        resolution = 150;  // Reduced for better performance
    } else if (zoom <= 7) {
        resolution = 220;  // Reduced for better performance
    } else {
        resolution = 300;  // Reduced significantly for deep zoom performance
    }
    
    console.log(`Zoom level: ${zoom}, Resolution: ${resolution}`);
    
    // Check if bounds have changed significantly since last fetch
    const boundsChanged = !state.lastFetchBounds ||
                         Math.abs(state.lastFetchBounds.north - mapBounds.north) > 1.0 ||
                         Math.abs(state.lastFetchBounds.south - mapBounds.south) > 1.0 ||
                         Math.abs(state.lastFetchBounds.east - mapBounds.east) > 1.0 ||
                         Math.abs(state.lastFetchBounds.west - mapBounds.west) > 1.0;
    
    // For overall mode, we need to fetch all three variables
    if (variable === 'overall') {
        // Only fetch if bounds changed or no cached data
        if (boundsChanged || !state.cachedOverallData) {
            await createOverallHeatmap(mapBounds, resolution, month, signal);
            state.lastFetchBounds = {...mapBounds};
        } else {
            // Recalculate colors with current preferences without fetching
            console.log('Bounds unchanged - recalculating colors from cached data');
            await recalculateOverallColors(state.cachedOverallData, mapBounds, resolution);
        }
        state.isLoading = false;
        return;
    }
    
    // For temperature, we need to fetch both tmin and tmax to calculate average
    let data;
    
    if (variable === 'temperature') {
        console.log(`Fetching temperature data (tmin + tmax) (zoom=${zoom}, resolution=${resolution})`);
        
        const baseUrl = `/api/grid?month=${month}&` +
                       `north=${mapBounds.north}&south=${mapBounds.south}&` +
                       `east=${mapBounds.east}&west=${mapBounds.west}&resolution=${resolution}`;
        
        try {
            const [tminResponse, tmaxResponse] = await Promise.all([
                fetch(addCacheBuster(baseUrl + '&variable=tmin'), { signal }),
                fetch(addCacheBuster(baseUrl + '&variable=tmax'), { signal })
            ]);
            
            const tminData = await tminResponse.json();
            const tmaxData = await tmaxResponse.json();
            
            if (tminData.error || tmaxData.error) {
                console.error('Error fetching temperature grid data');
                state.isLoading = false;
                return;
            }
            
            // Calculate average temperature
            const { lats, lngs } = tminData.grid;
            const tminValues = tminData.grid.values;
            const tmaxValues = tmaxData.grid.values;
            const avgValues = [];
            
            for (let i = 0; i < lats.length; i++) {
                avgValues[i] = [];
                for (let j = 0; j < lngs[0].length || j < tminValues[i].length; j++) {
                    const tmin = tminValues[i][j];
                    const tmax = tmaxValues[i][j];
                    
                    if (tmin !== null && tmin !== undefined && tmax !== null && tmax !== undefined) {
                        avgValues[i][j] = (tmin + tmax) / 2;
                    } else {
                        avgValues[i][j] = null;
                    }
                }
            }
            
            data = {
                grid: {
                    lats: lats,
                    lngs: lngs,
                    values: avgValues
                }
            };
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Fetch aborted');
                return;
            }
            throw error;
        }
    } else {
        // For other variables, fetch normally
        const variableMap = {
            'rainfall': 'prec',
            'sunshine': 'sunhours'
        };
        
        const apiVariable = variableMap[variable];
        
        if (!apiVariable) {
            console.error('Unknown variable:', variable);
            state.isLoading = false;
            return;
        }
        
        const url = `/api/grid?variable=${apiVariable}&month=${month}&` +
                    `north=${mapBounds.north}&south=${mapBounds.south}&` +
                    `east=${mapBounds.east}&west=${mapBounds.west}&resolution=${resolution}`;
        const cacheBustedUrl = addCacheBuster(url);
        
        console.log(`Fetching grid data (zoom=${zoom}, resolution=${resolution})`);
        
        try {
            const response = await fetch(cacheBustedUrl, { signal });
            data = await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Fetch aborted');
                return;
            }
            throw error;
        }
    }
    
    try {
        
        // Check if this request is still valid (map hasn't moved significantly)
        const currentBounds = state.map.getBounds();
        const boundsChanged = Math.abs(currentBounds.getNorth() - mapBounds.north) > 0.5 ||
                             Math.abs(currentBounds.getSouth() - mapBounds.south) > 0.5 ||
                             Math.abs(currentBounds.getEast() - mapBounds.east) > 0.5 ||
                             Math.abs(currentBounds.getWest() - mapBounds.west) > 0.5;
        
        if (boundsChanged) {
            console.log('Map bounds changed significantly during fetch, triggering new request');
            // Don't update isLoading here - let the new request handle it
            setTimeout(updateMapLayers, 100);
            return;
        }
        
        if (data.error) {
            console.error('Grid data error:', data.error);
            return;
        }
        
        const { grid } = data;
        const { lats, lngs, values } = grid;
        
        // Debug: Log first and last coordinates
        console.log('Grid coordinates:', {
            firstLat: lats[0],
            lastLat: lats[lats.length - 1],
            firstLng: lngs[0],
            lastLng: lngs[lngs.length - 1],
            mapBounds: mapBounds,
            gridSize: `${lats.length}x${lngs.length}`
        });
        
        // Verify: lats should go from north to south (decreasing)
        if (lats[0] < lats[lats.length - 1]) {
            console.warn('WARNING: Latitude array is inverted! Should go from north to south.');
        }
        
        // Calculate min/max for color scaling
        let minVal = Infinity;
        let maxVal = -Infinity;
        
        for (let row of values) {
            for (let val of row) {
                if (val !== null && val !== undefined) {
                    minVal = Math.min(minVal, val);
                    maxVal = Math.max(maxVal, val);
                }
            }
        }
        
        console.log(`Grid data range: ${minVal.toFixed(2)} to ${maxVal.toFixed(2)}`);
        
        // Create canvas overlay
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size based on grid resolution
        canvas.width = lngs.length;
        canvas.height = lats.length;
        
        // Get color gradient for this variable
        const gradient = layerConfig[variable].gradient;
        const [rangeMin, rangeMax] = layerConfig[variable].range;
        
        // Draw grid on canvas
        for (let i = 0; i < lats.length; i++) {
            for (let j = 0; j < lngs.length; j++) {
                const value = values[i][j];
                
                if (value !== null && value !== undefined) {
                    // Use the configured range for color mapping
                    const normalized = Math.max(0, Math.min(1, (value - rangeMin) / (rangeMax - rangeMin)));
                    
                    // Get color for this value
                    const [r, g, b, a] = getColorForValue(value, gradient);
                    
                    // Draw pixel with transparency
                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
                    ctx.fillRect(j, i, 1, 1);
                }
            }
        }
        
        // Calculate cell size based on actual data coordinates
        // lats go from north to south (values decrease), lngs go west to east (values increase)
        // Calculate the step between adjacent grid points
        let latStep, lngStep;
        
        if (lats.length > 1) {
            latStep = Math.abs(lats[1] - lats[0]);  // Distance between adjacent points
        } else {
            latStep = 0.1;  // Default fallback
        }
        
        if (lngs.length > 1) {
            lngStep = Math.abs(lngs[1] - lngs[0]);  // Distance between adjacent points
        } else {
            lngStep = 0.1;  // Default fallback
        }
        
        console.log(`Cell dimensions: latStep=${latStep.toFixed(4)}, lngStep=${lngStep.toFixed(4)}`);
        console.log(`First lat: ${lats[0]}, Last lat: ${lats[lats.length-1]}`);
        console.log(`First lng: ${lngs[0]}, Last lng: ${lngs[lngs.length-1]}`);
        
        // Create a layer group to hold all rectangles
        const rectangles = [];
        
        for (let i = 0; i < lats.length; i++) {
            for (let j = 0; j < lngs.length; j++) {
                const value = values[i][j];
                if (value !== null && value !== undefined) {
                    const [r, g, b, a] = getColorForValue(value, gradient);
                    
                    // Calculate bounds for this cell
                    // Each cell extends half a step in each direction from its center point
                    const cellNorth = lats[i] + latStep/2;
                    const cellSouth = lats[i] - latStep/2;
                    const cellWest = lngs[j] - lngStep/2;
                    const cellEast = lngs[j] + lngStep/2;
                    
                    const cellBounds = [
                        [cellSouth, cellWest],  // southwest corner
                        [cellNorth, cellEast]   // northeast corner
                    ];
                    
                    const rect = L.rectangle(cellBounds, {
                        color: 'transparent',
                        weight: 0,
                        fillColor: `rgb(${r}, ${g}, ${b})`,
                        fillOpacity: a,
                        interactive: false
                    });
                    rectangles.push(rect);
                }
            }
        }
        
        // Remove old layer and add new one atomically
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
            state.heatmapLayer = null;
        }
        
        // Add all rectangles in one batch for better performance
        state.heatmapLayer = L.layerGroup(rectangles);
        state.heatmapLayer.addTo(state.map);
        
        console.log(`Heatmap created with ${rectangles.length} cells`);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Fetch aborted');
        } else {
            console.error('Error creating heatmap:', error);
        }
    } finally {
        if (state.abortController && state.abortController.signal === signal) {
            state.isLoading = false;
            state.abortController = null;
        }
    }
}

// Hamburger menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const dropdownMenu = document.getElementById('dropdownMenu');
    
    if (hamburgerMenu && dropdownMenu) {
        hamburgerMenu.addEventListener('click', function(e) {
            e.stopPropagation();
            hamburgerMenu.classList.toggle('active');
            dropdownMenu.classList.toggle('active');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!hamburgerMenu.contains(e.target) && !dropdownMenu.contains(e.target)) {
                hamburgerMenu.classList.remove('active');
                dropdownMenu.classList.remove('active');
            }
        });
        
        // Close dropdown when clicking a link
        const dropdownLinks = dropdownMenu.querySelectorAll('.dropdown-link');
        dropdownLinks.forEach(link => {
            link.addEventListener('click', function() {
                hamburgerMenu.classList.remove('active');
                dropdownMenu.classList.remove('active');
            });
        });
    }
});

// Mobile weather details expandable panel
if (window.innerWidth <= 768) {
    const weatherPanel = document.getElementById('weatherDetailsPanelSection');
    let startY = 0;
    let currentY = 0;
    let isDragging = false;
    
    if (weatherPanel) {
        // Expand panel when scrolling up at the top
        weatherPanel.addEventListener('scroll', function() {
            if (weatherPanel.scrollTop > 50 && !weatherPanel.classList.contains('expanded')) {
                weatherPanel.classList.add('expanded');
            }
        });
        
        // Touch handling for collapsing
        weatherPanel.addEventListener('touchstart', function(e) {
            if (weatherPanel.scrollTop === 0) {
                startY = e.touches[0].clientY;
                isDragging = true;
            }
        });
        
        weatherPanel.addEventListener('touchmove', function(e) {
            if (isDragging && weatherPanel.scrollTop === 0) {
                currentY = e.touches[0].clientY;
                const diff = currentY - startY;
                
                // Only allow dragging down
                if (diff > 0) {
                    e.preventDefault();
                }
            }
        });
        
        weatherPanel.addEventListener('touchend', function(e) {
            if (isDragging) {
                const diff = currentY - startY;
                
                // If dragged down more than 50px, collapse
                if (diff > 50 && weatherPanel.classList.contains('expanded')) {
                    weatherPanel.classList.remove('expanded');
                    weatherPanel.scrollTop = 0;
                }
                
                isDragging = false;
            }
        });
    }
}
