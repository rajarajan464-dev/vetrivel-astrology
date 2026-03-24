document.querySelector('button').addEventListener('click', function() {
    
    // HTML-ல் இருந்து பயனர் உள்ளிட்ட தகவல்களை எடுத்தல்
    const inputs = document.querySelectorAll('input');
    const dob = inputs[0].value; 
    const tob = inputs[1].value;
    const lat = inputs[2].value;
    const lon = inputs[3].value;

    const resultDiv = document.querySelector('div.results') || document.body; // முடிவுகளைக் காட்டும் இடம்
    
    // பைதான் சர்வருக்குத் தகவலை அனுப்புதல்
    fetch('http://127.0.0.1:5000/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            dob: dob,
            tob: tob,
            lat: lat,
            lon: lon
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === "success") {
            alert(`கணக்கீடு வெற்றி!\nலக்னம்: ${data.lagna} பாகை\nசந்திரன்: ${data.moon} பாகை`);
        } else {
            alert(`பிழை: ${data.message}`);
        }
    })
    .catch((error) => {
        alert("சர்வரைத் தொடர்புகொள்ள முடியவில்லை. Python Server ஓடுகிறதா என சரிபார்க்கவும்.");
    });
});
