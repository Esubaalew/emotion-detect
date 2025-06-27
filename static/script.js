document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // DOM Elements
    const video = document.getElementById('video');
    const resultImage = document.getElementById('result-image');
    const canvas = document.getElementById('canvas');
    const startButton = document.getElementById('start-camera');
    const stopButton = document.getElementById('stop-camera');
    const messageBox = document.querySelector('#message-box p');
    const downloadLink = document.getElementById('download-link');

    let stream;
    let intervalId;

    // Chart.js Initialization
    const ctx = document.getElementById('emotionChart').getContext('2d');
    const emotionChart = new Chart(ctx, {
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

    // --- Core Functions ---
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            
            startButton.disabled = true;
            stopButton.disabled = false;
            downloadLink.classList.remove('disabled');
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
            }, 250); // Send frame every 250ms
        } catch (err) {
            console.error("Error accessing camera: ", err);
            alert("Could not access the camera. Please grant permission and try again.");
        }
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        clearInterval(intervalId);

        if (!resultImage.src.startsWith('data:image')) {
            resultImage.src = "https://via.placeholder.com/640x480/23272a/99aab5?text=Analysis+Stopped";
        }
        
        startButton.disabled = false;
        stopButton.disabled = true;
        
        messageBox.textContent = "Analysis stopped. This is your final result.";
    }

    // --- Event Listeners ---
    startButton.addEventListener('click', startCamera);
    stopButton.addEventListener('click', stopCamera);

    // Listen for responses from the server
    socket.on('response', (data) => {
        resultImage.src = data.image;
        messageBox.textContent = data.message;

        const chartData = emotionChart.data.datasets[0].data;
        const labels = emotionChart.data.labels;
        Object.keys(data.chart_data).forEach((emotion) => {
            const index = labels.findIndex(label => label.toLowerCase() === emotion.toLowerCase());
            if(index !== -1){
                chartData[index] = data.chart_data[emotion];
            }
        });
        emotionChart.update();
    });
});