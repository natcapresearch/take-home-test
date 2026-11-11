import L, { LatLngBoundsExpression } from "leaflet";

export const closeAllPopups = (map: L.Map) => {
    map.eachLayer((layer) => {
        if (layer instanceof L.Popup) {
            map.closePopup(layer);
        }
    });
};

export const worldBounds: LatLngBoundsExpression = [
    [-85.05112878, -180],
    [85.05112878, 180],
];
