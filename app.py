from flask import Flask, render_template, session, make_response, request, jsonify
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
import csv
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fhhhhhhhhwkeajqouuudwNBEECNJEBBIHASKJNX9E8RU'
socketio = SocketIO(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print("Loading models...")
model_path = os.path.join(BASE_DIR, 'emotion_detection_model_v2.h5')
emotion_model = load_model(model_path, compile=False)
cascade_path = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)
if face_cascade.empty():
    print(f"FATAL ERROR: Could not load face cascade from {cascade_path}")
else:
    print("Models loaded successfully!")
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
MOTIVATIONAL_MESSAGES = {
    'happy': ["Your smile is lighting up the screen!", "Keep that positive energy going!", "You're radiating joy!"],
    'sad': ["It's okay to not be okay. Take a moment for yourself.", "Remember, tough times don't last, but tough people do.", "Sending you a virtual hug."],
    'angry': ["Take a deep breath. It's okay to feel this way.", "Channel that powerful energy into something productive.", "This feeling is temporary."],
    'neutral': ["Looking calm, cool, and collected.", "A perfect moment for clear thinking and reflection.", "A peaceful state of mind is a powerful one."],
    'surprise': ["Wow, something caught your attention!", "The world is full of amazing surprises!", "Embrace the beauty of the unexpected."],
    'fear': ["You are braver than you believe, and stronger than you seem.", "Acknowledge the fear, then show it you're in charge.", "You've got this."],
    'disgust': ["That's a strong reaction! Time to focus on something better.", "Don't let negativity bring you down.", "Shake it off and move forward!"]
}

# --- Core Prediction Function ---
def process_frame(image):
    """
    Detects faces, predicts emotions with dynamic text labels, and draws results.
    Args:
        image (np.array): The input image in BGR format.
    Returns:
        tuple: A tuple containing the processed image and a list of detected emotions.
    """
    gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if face_cascade.empty():
        print("Warning: Face cascade is not loaded. Cannot detect faces.")
        return image, []
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    emotions_found = []
    for (x, y, w, h) in faces:
        roi_gray = gray_frame[y:y + h, x:x + w]
        roi_gray = cv2.resize(roi_gray, (48, 48), interpolation=cv2.INTER_AREA)
        roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0)
        prediction = emotion_model.predict(roi, verbose=0)
        max_index = int(np.argmax(prediction))
        emotion = CLASS_NAMES[max_index]
        emotions_found.append(emotion)
        label = f"{emotion.capitalize()}"
        font_scale = max(0.5, w / 150)
        thickness = max(1, int(w / 75))
        (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        cv2.rectangle(image, (x, y - text_height - 15), (x + text_width, y), (0, 255, 0), -1)
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), thickness)
        cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
    return image, emotions_found

# --- Flask & SocketIO Routes ---
@app.route('/')
def index():
    session.clear()
    session['emotion_log'] = []
    session['emotion_counts'] = {emotion: 0 for emotion in CLASS_NAMES}
    return render_template('index.html')

@socketio.on('image')
def handle_image(data_image):
    sbuf = io.BytesIO(base64.b64decode(data_image.split(',')[1]))
    image = Image.open(sbuf).convert('RGB')
    frame = np.array(image)
    frame = frame[:, :, ::-1].copy()
    processed_frame, emotions = process_frame(frame)
    emotion = emotions[0] if emotions else None
    message = "Searching for a face..."
    if emotion:
        session['emotion_counts'][emotion] += 1
        log_entry = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'emotion': emotion}
        session['emotion_log'].append(log_entry)
        session.modified = True
        message = random.choice(MOTIVATIONAL_MESSAGES[emotion])
    _, buffer = cv2.imencode('.jpg', processed_frame)
    b64_frame = base64.b64encode(buffer).decode('utf-8')
    emit('response', {
        'image': f'data:image/jpeg;base64,{b64_frame}',
        'message': message,
        'chart_data': session.get('emotion_counts', {})
    })

# --- NEW ROUTE FOR STATIC IMAGE ANALYSIS ---
@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    try:
        image = None
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            image = Image.open(file.stream).convert('RGB')
        elif 'url' in request.form and request.form['url'] != '':
            url = request.form['url']
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            image = Image.open(response.raw).convert('RGB')
        if image is None:
            return jsonify({'error': 'No image provided.'}), 400
        frame = np.array(image)
        frame = frame[:, :, ::-1].copy()
        processed_frame, emotions = process_frame(frame)
        if emotions:
            for emotion in emotions:
                session['emotion_counts'][emotion] += 1
                log_entry = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'emotion': emotion}
                session['emotion_log'].append(log_entry)
            session.modified = True
            message = f"Detected {len(emotions)} face(s). The dominant emotion is {emotions[0]}."
        else:
            message = "No faces were detected in the image."
        _, buffer = cv2.imencode('.jpg', processed_frame)
        b64_frame = base64.b64encode(buffer).decode('utf-8')
        return jsonify({
            'image': f'data:image/jpeg;base64,{b64_frame}',
            'message': message,
            'chart_data': session.get('emotion_counts', {})
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Could not fetch image from URL: {e}'}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500


@app.route('/download_csv')
def download_csv():
    log = session.get('emotion_log', [])
    if not log:
        return "No emotion data has been logged for this session.", 404
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Timestamp', 'Detected Emotion'])
    for entry in log:
        cw.writerow([entry['timestamp'], entry['emotion']])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=emotion_log.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)