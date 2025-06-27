from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
from tensorflow.keras.models import load_model
from PIL import Image
import io
import os # Import the os module

# --- Initialization ---
app = Flask(__name__)

# --- Define the absolute path to the script's directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Load Models (Loaded once at startup) ---
print("Loading emotion detection model...")
model_path = os.path.join(BASE_DIR, 'emotion_detection_model_v2.h5')
emotion_model = load_model(model_path, compile=False)

print("Loading face cascade classifier...")
cascade_path = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)

# --- Add a check to see if the models loaded correctly ---
if face_cascade.empty():
    print(f"FATAL ERROR: Could not load face cascade from {cascade_path}")
    # You might want to exit or handle this error more gracefully
else:
    print("Models loaded successfully!")


# --- Emotion Dictionary ---
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
EMOJI_MAP = {"angry": "😠", "disgust": "🤢", "fear": "😨", "happy": "😊", "neutral": "😐", "sad": "😢", "surprise": "😮"}


# --- Core Prediction Function ---
def predict_and_draw(image):
    gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Check if the cascade is loaded before using it
    if face_cascade.empty():
        print("Warning: Face cascade is not loaded. Cannot detect faces.")
        return image # Return the original image if cascade is not loaded

    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        roi_gray = gray_frame[y:y + h, x:x + w]
        roi_gray = cv2.resize(roi_gray, (48, 48), interpolation=cv2.INTER_AREA)
        roi_color = np.expand_dims(roi_gray, axis=-1)
        roi_color = np.expand_dims(roi_color, axis=0)
        
        prediction = emotion_model.predict(roi_color, verbose=0)
        max_index = int(np.argmax(prediction))
        predicted_emotion = CLASS_NAMES[max_index]
        emoji = EMOJI_MAP.get(predicted_emotion, "")
        
        label = f"{predicted_emotion} {emoji}"
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return image


# --- Flask Routes ---
@app.route('/')
def index():
    """Render the main HTML page."""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Receive an image, process it, and return the result."""
    if 'file' in request.files:
        # Handle file upload
        file = request.files['file']
        image = Image.open(file.stream).convert('RGB')
        image = np.array(image)
        image = image[:, :, ::-1].copy() # Convert RGB to BGR
    else:
        # Handle camera snapshot (sent as a base64 string)
        data = request.json['image']
        img_data = base64.b64decode(data.split(',')[1])
        image = Image.open(io.BytesIO(img_data)).convert('RGB')
        image = np.array(image)
        image = image[:, :, ::-1].copy() # Convert RGB to BGR

    # Process the image
    result_image = predict_and_draw(image)
    
    # Encode the processed image back to base64 to send to the browser
    _, buffer = cv2.imencode('.jpg', result_image)
    image_str = base64.b64encode(buffer).decode('utf-8')
    
    return jsonify({'image': f'data:image/jpeg;base64,{image_str}'})


if __name__ == '__main__':
    # Changed debug=True for easier development
    app.run(debug=True)