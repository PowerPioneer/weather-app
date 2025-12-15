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
            const tmax = tempValues[i][j];
            const prec = precValues[i][j];
            const sunhours = sunValues[i][j];
            
            const result = calculateOverallScore(tmax, prec, sunhours);
            
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
