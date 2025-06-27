// --- DOM Elements ---
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const snapButton = document.getElementById('snap');
const startCameraButton = document.getElementById('start-camera');
const fileInput = document.getElementById('file-input');
const resultImage = document.getElementById('result-image');
const loader = document.getElementById('loader');

// --- Tab Switching Logic ---
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}

// --- API Call Helper ---
async function sendImageToServer(data, headers = {}) {
    loader.style.display = 'block';
    resultImage.src = ""; // Clear previous image
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: headers,
            body: data
        });
        const result = await response.json();
        resultImage.src = result.image;
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while processing the image.');
    } finally {
        loader.style.display = 'none';
    }
}

// --- File Upload Logic ---
fileInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);
        // No headers needed for FormData, browser sets it
        sendImageToServer(formData);
    }
});

// --- Camera Logic ---
startCameraButton.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        snapButton.disabled = false;
    } catch (err) {
        console.error("Error accessing camera: ", err);
        alert("Could not access the camera. Please ensure you have granted permission.");
    }
});

snapButton.addEventListener('click', () => {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataURL = canvas.toDataURL('image/jpeg');
    
    // For JSON, we must set the Content-Type header
    const headers = { 'Content-Type': 'application/json' };
    const body = JSON.stringify({ image: dataURL });
    
    sendImageToServer(body, headers);
});