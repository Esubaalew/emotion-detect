document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // --- DOM Elements ---
    const video = document.getElementById('video');
    const resultImageLive = document.getElementById('result-image-live');
    const resultImageStatic = document.getElementById('result-image-static');
    const canvas = document.getElementById('canvas');
    const loader = document.getElementById('loader');

    // Live Analysis Elements
    const startButton = document.getElementById('start-camera');
    const stopButton = document.getElementById('stop-camera');
    
    // Static Analysis Elements
    const fileInput = document.getElementById('file-input');
    const urlInput = document.getElementById('url-input');
    const urlSubmitBtn = document.getElementById('url-submit-btn');

    // Shared Elements
    const messageBox = document.querySelector('#message-box p');
    const downloadLink = document.getElementById('download-link');
    
    let stream;
    let intervalId;

    // --- Chart.js Initialization ---
    const ctx = document.getElementById('emotionChart').getContext('2d');
    const emotionChart = new Chart(ctx, { /* ... Chart config remains the same ... */ 
        type: 'bar',
        data: {
            labels: ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise'],
            datasets: [{
                label: 'Emotion Count',
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: 'rgba(74, 144, 226, 0.6)',
                borderColor: 'rgba(74, 144, 226, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: { beginAtZero: true, ticks: { color: '#fff', stepSize: 1 } },
                x: { ticks: { color: '#fff' } }
            },
            plugins: { legend: { display: false } },
            maintainAspectRatio: false
        }
    });

    // --- General UI Functions ---
    function updateUI(data) {
        messageBox.textContent = data.message;
        const chartData = emotionChart.data.datasets[0].data;
        const labels = emotionChart.data.labels;
        Object.keys(data.chart_data).forEach((emotion) => {
            const index = labels.findIndex(label => label.toLowerCase() === emotion.toLowerCase());
            if(index !== -1) chartData[index] = data.chart_data[emotion];
        });
        emotionChart.update();
        downloadLink.classList.remove('disabled');
    }

    // --- Tab Switching Logic ---
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            stopCamera(); // Stop live analysis when switching tabs
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(button.dataset.tab).classList.add('active');
        });
    });

    // --- Real-Time Analysis Logic ---
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            
            startButton.disabled = true;
            stopButton.disabled = false;
            messageBox.textContent = "Analysis started. Looking for a face...";

            intervalId = setInterval(() => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    const context = canvas.getContext('2d');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    const data = canvas.toDataURL('image/jpeg', 0.8);
                    socket.emit('image', data);
                }
            }, 250);
        } catch (err) {
            console.error("Error accessing camera: ", err);
            alert("Could not access the camera.");
        }
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        clearInterval(intervalId);
        intervalId = null;
        startButton.disabled = false;
        stopButton.disabled = true;
    }

    startButton.addEventListener('click', startCamera);
    stopButton.addEventListener('click', () => {
        stopCamera();
        messageBox.textContent = "Live analysis stopped.";
    });

    socket.on('response', (data) => {
        resultImageLive.src = data.image;
        updateUI(data);
    });

    // --- Static Image Analysis Logic ---
    async function analyzeStaticImage(formData) {
        loader.style.display = 'block';
        resultImageStatic.style.opacity = '0.5';
        try {
            const response = await fetch('/analyze_image', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server error');
            }
            const data = await response.json();
            resultImageStatic.src = data.image;
            updateUI(data);
        } catch (error) {
            console.error('Error analyzing image:', error);
            alert(`Analysis failed: ${error.message}`);
        } finally {
            loader.style.display = 'none';
            resultImageStatic.style.opacity = '1';
        }
    }

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            analyzeStaticImage(formData);
        }
    });

    urlSubmitBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (url) {
            const formData = new FormData();
            formData.append('url', url);
            analyzeStaticImage(formData);
        } else {
            alert('Please enter a valid image URL.');
        }
    });
});