/**
 * Web Worker for TopoJSON to GeoJSON conversion
 * Offloads CPU-intensive conversion from main thread to improve TBT
 */

// Import topojson-client library
importScripts('https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js');

/**
 * Handle incoming messages from main thread
 * Expected message format: { topojsonData, objectName }
 */
self.onmessage = function(e) {
    const { topojsonData, objectName } = e.data;
    
    try {
        // Find the object name in the TopoJSON
        const objectKeys = Object.keys(topojsonData.objects || {});
        
        // Try to find the requested object, fall back to first available
        let targetObject = objectName;
        if (!topojsonData.objects || !topojsonData.objects[targetObject]) {
            targetObject = objectKeys[0];
        }
        
        if (!targetObject || !topojsonData.objects[targetObject]) {
            self.postMessage({ 
                error: `No objects found in TopoJSON. Available: ${objectKeys.join(', ')}` 
            });
            return;
        }
        
        // Convert to GeoJSON using topojson-client
        const geojson = topojson.feature(topojsonData, topojsonData.objects[targetObject]);
        
        // Send result back to main thread
        self.postMessage({ geojson });
        
    } catch (error) {
        self.postMessage({ error: error.message });
    }
};
