const cityData = {
    "salem": { lat: 11.666, lon: 78.011 },
    "chennai": { lat: 13.082, lon: 80.270 },
    "madurai": { lat: 9.925, lon: 78.119 }
};

function getOfflineCoords(cityName) {
    let city = cityName.toLowerCase().trim();
    if(cityData[city]) {
        document.getElementById('lat').value = cityData[city].lat;
        document.getElementById('lon').value = cityData[city].lon;
    }
}