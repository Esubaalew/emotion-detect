from flask import Flask, render_template, session, make_response
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
from tensorflow.keras.models import load_model
from PIL import Image
import io
import os
import random
from datetime import datetime

# --- Initialization ---
app = Flask(__name__)
# A secret key is required for Flask session management
app.config['SECRET_KEY'] = 'your_super_secret_key_change_me!'
socketio = SocketIO(app)

# --- Define the absolute path to the script's directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Load Models (Loaded once at startup) ---
print("Loading models...")
model_path = os.path.join(BASE_DIR, 'emotion_detection_model_v2.h5')
emotion_model = load_model(model_path, compile=False)
cascade_path = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)
print("Models loaded successfully!")

# --- Dictionaries and Data ---
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
MOTIVATIONAL_MESSAGES = {
    'happy': ["You're shining today!", "Your smile is contagious!", "Keep that positive energy going!"],
    'sad': ["It's okay to feel down. Take a moment for yourself.", "Remember, tough times don't last.", "Sending you a virtual hug."],
    'angry': ["Take a deep breath. It's okay to feel this way.", "Channel that energy into something productive.", "This feeling will pass."],
    'neutral': ["Looking calm and collected.", "A great moment to think and reflect.", "A peaceful state of mind."],
    'surprise': ["Wow, something caught your attention!", "The world is full of surprises!", "Embrace the unexpected."],
    'fear': ["You are stronger than your fears.", "Face what you're feeling. You've got this.", "It's okay to be scared sometimes."],
    'disgust': ["That's a strong reaction! Move on to better things.", "Don't let negativity stick around.", "Shake it off!"]
}

# --- Core Prediction Function (Now returns emotion too) ---
def process_frame(image):
    gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    dominant_emotion = None

    for (x, y, w, h) in faces:
        roi_gray = gray_frame[y:y + h, x:x + w]
        roi_gray = cv2.resize(roi_gray, (48, 48), interpolation=cv2.INTER_AREA)
        roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0)
        
        prediction = emotion_model.predict(roi, verbose=0)
        max_index = int(np.argmax(prediction))
        dominant_emotion = CLASS_NAMES[max_index]
        
        label = f"{dominant_emotion}"
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # We'll just process the first face found for simplicity
        break

    return image, dominant_emotion

# --- Flask & SocketIO Routes ---
@app.route('/')
def index():
    """Render the main HTML page and initialize session data."""
    session['emotion_log'] = []
    session['emotion_counts'] = {emotion: 0 for emotion in CLASS_NAMES}
    return render_template('index.html')

@socketio.on('image')
def handle_image(data_image):
    """Handle real-time video frames from the client."""
    sbuf = io.BytesIO(base64.b64decode(data_image.split(',')[1]))
    image = Image.open(sbuf).convert('RGB')
    frame = np.array(image)
    frame = frame[:, :, ::-1].copy() # RGB to BGR

    processed_frame, emotion = process_frame(frame)

    if emotion:
        # Update session data
        session['emotion_counts'][emotion] += 1
        log_entry = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'emotion': emotion}
        session['emotion_log'].append(log_entry)
        session.modified = True # Important to save session changes
        
        message = random.choice(MOTIVATIONAL_MESSAGES[emotion])
    else:
        message = "No face detected. Looking for you!"

    # Encode processed frame to send back to client
    _, buffer = cv2.imencode('.jpg', processed_frame)
    b64_frame = base64.b64encode(buffer).decode('utf-8')
    
    # Emit the results back to the client
    emit('response', {
        'image': f'data:image/jpeg;base64,{b64_frame}',
        'emotion': emotion,
        'message': message,
        'chart_data': session.get('emotion_counts', {})
    })

@app.route('/download_csv')
def download_csv():
    """Create and send a CSV file of the emotion log."""
    log = session.get('emotion_log', [])
    if not log:
        return "No data to export.", 404

    # Create a CSV in memory
    si = io.StringIO()
    cw = io.writer(si)
    cw.writerow(['Timestamp', 'Detected Emotion'])
    for entry in log:
        cw.writerow([entry['timestamp'], entry['emotion']])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=emotion_log.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    # Use socketio.run for the real-time server
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)