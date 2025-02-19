// static/script.js

function uploadFile() {
    let fileInput = document.getElementById('fileInput');
    if (fileInput.files.length === 0) {
        alert("Please select a file first.");
        return;
    }
    
    let formData = new FormData();
    formData.append('file', fileInput.files[0]);

    fetch('/upload', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                document.getElementById('weeksInfo').innerText = 'Weeks in dataset: ' + data.weeks;
            }
        })
        .catch(err => {
            console.error('Upload Error: ', err);
            alert('An error occurred during file upload.');
        });
}

function predictCalls() {
    let weekValue = document.getElementById('weekInput').value;
    if (!weekValue) {
        alert("Please enter a week value.");
        return;
    }

    fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ week: weekValue })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            document.getElementById('predictionResult').innerText = 'Predicted Calls: ' + data.predictions.join(', ');
        }
    })
    .catch(err => {
        console.error('Prediction Error: ', err);
        alert('An error occurred while predicting the calls.');
    });
}
