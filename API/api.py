from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import speech_recognition as sr
import asyncio
import queue
import threading
import json
import logging
import pickle
import numpy as np
from typing import Set
import modeluse
import pyaudio
from fastapi.staticfiles import StaticFiles
import redis

L=[]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
active_websockets: Set[WebSocket] = set()

# Mount the static folder for serving images and CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

class TranscriberWithAI:
    def __init__(self, model_path='model.pkl'):
        self.recognizer = sr.Recognizer()
        self.is_running = False
        self.audio_queue = queue.Queue()
        import modeluse
        model=None
        # Load AI model
        self.model = modeluse.load_model_with_custom_layer("mymodel.h5")

        '''try:
            #with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info("AI model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None'''
        
        
        # Configure recognizer
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def predict_text(self, text: str):
        Global
        """Make prediction using the loaded model"""
        try:
            if self.model is None:
                return {"error": "Model not loaded"}
            
            # Make prediction (modify this according to your model's requirements)
            text_array = np.array([text])  # Convert to correct format
            print(self.model.predict([text_array]))
            print(text_array)
            prediction = self.model.predict([text_array])[0]
            #probability = self.model.predict_proba([text_array])[0].max()
            L.append(text_array)
            return {
                "class": str(prediction),
                "scam": float(prediction)
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e)}

    async def broadcast_transcription(self, text: str):
        """Send transcription and prediction to all clients"""
        disconnected = set()
        
        # Get prediction
        prediction = self.predict_text(text)
        
        
        for websocket in active_websockets:
            try:
                await websocket.send_json({
                    "text": text,
                    "prediction": prediction
                })
            except:
                disconnected.add(websocket)
        
        active_websockets.difference_update(disconnected)

    def process_audio(self):
        """Process audio chunks from queue"""
        while self.is_running:
            try:
                audio = self.audio_queue.get(timeout=1)
                try:
                    text = self.recognizer.recognize_google(audio)
                    asyncio.run(self.broadcast_transcription(text.lower()))
                except sr.UnknownValueError:
                    logger.info("Could not understand audio")
                except sr.RequestError as e:
                    logger.error(f"Speech recognition error: {e}")
            except queue.Empty:
                continue

    def record_audio(self):
        """Record audio continuously"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Recording started")
            
            while self.is_running:
                try:
                    audio = self.recognizer.listen(source, phrase_time_limit=20)
                    self.audio_queue.put(audio)
                except Exception as e:
                    logger.error(f"Recording error: {e}")
                    continue

    def start(self):
        """Start transcription and processing"""
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.record_audio, daemon=True).start()
            threading.Thread(target=self.process_audio, daemon=True).start()
            
            #get input from index_2.html where the id is phn_num for phone number
       
            


    def stop(self):
        """Stop transcription"""
        self.is_running = False
    

# Create single instance
transcriber = TranscriberWithAI()

@app.get("/")
async def home():
    return FileResponse("index_2.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        if not transcriber.is_running:
            transcriber.start()
        
        while True:
            data = await websocket.receive_text()
            if data == "stop":
                break
    except:
        logger.info("Client disconnected")
    finally:
        active_websockets.remove(websocket)
        if not active_websockets:
            transcriber.stop()

@app.on_event("shutdown")
async def shutdown_event():
    transcriber.stop()

    

 
# ... (keep other imports)

# ... (keep existing code until the Redis connection)
'''
@app.post("/scam")
async def scam(data: dict):
    try:
        scam_num = data.get('scam')
        print(f'here it is {scam_num}')
        if scam_num is None:
            raise HTTPException(status_code=400, detail="Missing 'scam' value in request")
        return {"scam": float(scam_num)}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scam value format")

@app.post("/update_scam_score/{phone_number}")
async def update_scam_score(phone_number: str, data: dict):
    try:
        # Validate phone number format
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
            
        # Get current scam score from request
        current_score = float(data.get('scam', 0))
        
        # Get existing data from Redis
        existing_data = r.hgetall(phone_number)
        
        if existing_data:
            # Update existing record
            previous_score = float(existing_data['scam_score'])
            previous_calls = int(existing_data['calls'])
            
            # Calculate new average score
            new_score = (previous_score * previous_calls + current_score) / (previous_calls + 1)
            new_calls = previous_calls + 1
            
            # Update Redis
            r.hset(phone_number, mapping={
                "scam_score": new_score,
                "calls": new_calls
            })
        else:
            # Create new record
            r.hset(phone_number, mapping={
                "scam_score": current_score,
                "calls": 1
            })
            
        # Return updated data
        return {
            "phone_number": phone_number,
            "current_score": current_score,
            "average_score": new_score if existing_data else current_score,
            "total_calls": new_calls if existing_data else 1
        }
        
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
'''