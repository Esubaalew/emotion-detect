document.addEventListener('DOMContentLoaded', () => {
    // --- Socket.IO Connection ---
    const socket = io();

    // --- DOM Elements ---
    const video = document.getElementById('video');
    const resultImage = document.getElementById('result-image');
    const canvas = document.getElementById('canvas');
    const startButton = document.getElementById('start-camera');
    const stopButton = document.getElementById('stop-camera');
    const messageBox = document.querySelector('#message-box p');
    const downloadLink = document.getElementById('download-link');

    let stream;
    let intervalId;

    // --- Chart.js Initialization ---
    const ctx = document.getElementById('emotionChart').getContext('2d');
    const emotionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise'],
            datasets: [{
                label: 'Emotion Count',
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(153, 102, 255, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(201, 203, 207, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 159, 64, 0.5)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(201, 203, 207, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            scales: { y: { beginAtZero: true, ticks: { color: '#fff' } }, x: { ticks: { color: '#fff' } } },
            plugins: { legend: { display: false } }
        }
    });

    // --- Functions ---
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            video.style.display = 'block';
            resultImage.style.display = 'none';

            startButton.disabled = true;
            stopButton.disabled = false;
            downloadLink.classList.remove('disabled');

            // Send frames to the server every 200ms
            intervalId = setInterval(() => {
                const context = canvas.getContext('2d');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                const data = canvas.toDataURL('image/jpeg', 0.8);
                socket.emit('image', data);
            }, 200);
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

        video.style.display = 'none';
        resultImage.style.display = 'block';
        resultImage.src = "https://via.placeholder.com/640x480.png?text=Camera+Off";
        
        startButton.disabled = false;
        stopButton.disabled = true;
    }

    // --- Event Listeners ---
    startButton.addEventListener('click', startCamera);
    stopButton.addEventListener('click', stopCamera);

    // Listen for responses from the server
    socket.on('response', (data) => {
        resultImage.src = data.image;
        messageBox.textContent = data.message;

        // Update the chart
        const chartData = emotionChart.data.datasets[0].data;
        Object.keys(data.chart_data).forEach((emotion, index) => {
            chartData[index] = data.chart_data[emotion];
        });
        emotionChart.update();
    });
});