"""
Lightweight Preprocessor for Multimodal Inputs
Uses cloud APIs instead of heavy local models - works on Render free tier
"""

import speech_recognition as sr
import boto3
from PIL import Image
import os
import warnings
from pathlib import Path
from supabase import create_client, Client
import json

warnings.filterwarnings("ignore")

class MultimodalPreprocessor:
    """
    Lightweight preprocessor using cloud APIs:
    - Audio: Google Speech Recognition (free)
    - Image: AWS Rekognition (emotion detection)
    - No heavy models to download!
    """
    
    def __init__(self):
        """Initialize lightweight preprocessor with cloud APIs"""
        print("="*70)
        print("INITIALIZING LIGHTWEIGHT MULTIMODAL PREPROCESSOR")
        print("="*70)
        
        # Initialize speech recognizer (no model download needed!)
        print("\n🎤 Initializing Speech Recognition...")
        self.recognizer = sr.Recognizer()
        print("✓ Speech recognizer ready (using Google Speech API)")
        
        # Initialize AWS Rekognition for emotion detection
        print("\n😊 Initializing AWS Rekognition...")
        try:
            self.rekognition = boto3.client('rekognition', region_name='us-east-1')
            print("✓ AWS Rekognition initialized")
        except Exception as e:
            print(f"⚠️ AWS Rekognition initialization failed: {str(e)}")
            self.rekognition = None
        
        # Initialize Supabase client for storage operations
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self.media_bucket = os.getenv("SUPABASE_MEDIA_BUCKET", "mood_media")
            print(f"✓ Supabase initialized (bucket: {self.media_bucket})")
        else:
            self.supabase_client = None
            print("⚠️ Supabase not configured")
        
        print("\n" + "="*70)
        print("✅ LIGHTWEIGHT PREPROCESSOR READY")
        print("="*70 + "\n")
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio using Google Speech Recognition (free)
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            str: Transcribed text or None
        """
        if not audio_path or not os.path.exists(audio_path):
            return None
        
        try:
            print(f"\n🎤 Transcribing audio: {audio_path}")
            
            # Load audio file
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
            
            # Use Google Speech Recognition (free, no API key needed)
            transcript = self.recognizer.recognize_google(audio_data)
            
            print(f"✓ Transcription: '{transcript[:100]}...'")
            return transcript
            
        except sr.UnknownValueError:
            print("⚠️ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"⚠️ Speech recognition error: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Audio transcription failed: {str(e)}")
            return None
    
    def detect_emotion(self, image_path):
        """
        Detect emotion using AWS Rekognition
        
        Args:
            image_path: Path to image file
            
        Returns:
            tuple: (emotion, confidence, details) or (None, 0.0, {})
        """
        if not image_path or not os.path.exists(image_path):
            return None, 0.0, {}
        
        if not self.rekognition:
            print("⚠️ AWS Rekognition not available")
            return None, 0.0, {}
        
        try:
            print(f"\n😊 Detecting emotion from: {image_path}")
            
            # Read image
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            # Detect faces and emotions
            response = self.rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            if not response['FaceDetails']:
                print("⚠️ No face detected in image")
                return None, 0.0, {}
            
            # Get the first face's emotions
            face = response['FaceDetails'][0]
            emotions = face.get('Emotions', [])
            
            if not emotions:
                return None, 0.0, {}
            
            # Sort by confidence and get top emotion
            emotions.sort(key=lambda x: x['Confidence'], reverse=True)
            top_emotion = emotions[0]
            
            emotion_name = top_emotion['Type'].capitalize()
            confidence = top_emotion['Confidence'] / 100  # Convert to 0-1 scale
            
            # Prepare details
            details = {
                'all_emotions': {e['Type']: e['Confidence'] for e in emotions},
                'face_confidence': face.get('Confidence', 0) / 100
            }
            
            print(f"✓ Detected emotion: {emotion_name} ({confidence:.2%} confidence)")
            return emotion_name, confidence, details
            
        except Exception as e:
            print(f"❌ Emotion detection failed: {str(e)}")
            return None, 0.0, {}
    
    def preprocess(self, audio_path=None, image_path=None, text_input=None, 
                   user_id=None, analyze=False):
        """
        Preprocess multimodal inputs
        
        Args:
            audio_path: Path to audio file
            image_path: Path to image file
            text_input: Text input from user
            user_id: User ID
            analyze: Whether to call analyzer after preprocessing
            
        Returns:
            dict: Preprocessed data ready for analyzer
        """
        print("\n" + "="*70)
        print("PREPROCESSING INPUTS (LIGHTWEIGHT MODE)")
        print("="*70 + "\n")
        
        # Initialize result structure
        result = {
            "text": text_input if text_input else "",
            "audio_transcript": "",
            "emotion": "",
            "emotion_confidence": 0.0,
            "emotion_details": {},
            "has_audio": False,
            "has_image": False,
            "has_text": bool(text_input)
        }
        
        # Process audio
        if audio_path:
            transcript = self.transcribe_audio(audio_path)
            if transcript:
                result["audio_transcript"] = transcript
                result["has_audio"] = True
        
        # Process image
        if image_path:
            emotion, confidence, details = self.detect_emotion(image_path)
            if emotion:
                result["emotion"] = emotion
                result["emotion_confidence"] = confidence
                result["emotion_details"] = details
                result["has_image"] = True
        
        # Summary
        print("\n" + "="*70)
        print("PREPROCESSING COMPLETE")
        print("="*70)
        print(f"✓ Text Input: {'Yes' if result['has_text'] else 'No'}")
        print(f"✓ Audio Processed: {'Yes' if result['has_audio'] else 'No'}")
        print(f"✓ Image Processed: {'Yes' if result['has_image'] else 'No'}")
        
        if result['audio_transcript']:
            print(f"\n📤 Audio Transcript: '{result['audio_transcript'][:80]}...'")
        if result['emotion']:
            print(f"📤 Emotion: {result['emotion']} ({result['emotion_confidence']:.2%})")
        if result['text']:
            print(f"📤 Text: '{result['text'][:80]}...'")
        
        print("\n🔗 Ready for model_analyzer.py")
        print("="*70 + "\n")
        
        # Call ModelAnalyzer if enabled
        if analyze and user_id:
            try:
                from model_analyzer import ModelAnalyzer
                from report import process_user
                
                print("\n" + "="*70)
                print("CALLING ANALYZER AND REPORT GENERATOR")
                print("="*70 + "\n")
                
                # Initialize analyzer
                supabase_url = os.getenv("SUPABASE_URL", "https://cswobvpopxypghwjolnb.supabase.co")
                supabase_key = os.getenv("SUPABASE_KEY")
                
                analyzer = ModelAnalyzer(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key
                )
                
                # Call ModelAnalyzer
                print("\n🤖 Calling ModelAnalyzer...")
                analysis_result = analyzer.analyze(user_id, result)
                print("\n✅ ModelAnalyzer completed!")
                
                # Update report
                print("\n📊 Updating report...")
                process_user(user_id, preprocessed_data=result)
                print("✅ Report updated!")
                
                # Add analysis to result
                result["analysis_result"] = analysis_result
                
            except Exception as e:
                print(f"\n❌ Analyzer/Report error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return result


def main():
    """Test the lightweight preprocessor"""
    print("Testing Lightweight Multimodal Preprocessor\n")
    
    preprocessor = MultimodalPreprocessor()
    
    # Test with sample data
    result = preprocessor.preprocess(
        text_input="I'm feeling stressed today",
        user_id="test_user"
    )
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

