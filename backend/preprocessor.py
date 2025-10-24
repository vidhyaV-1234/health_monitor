import whisper
import warnings
from transformers import AutoImageProcessor, ViTForImageClassification
from PIL import Image
import torch
import torch.nn.functional as F
import os
from io import BytesIO
from pathlib import Path
from supabase import create_client, Client
import json

warnings.filterwarnings("ignore")

class MultimodalPreprocessor:
    """
    Preprocesses multimodal inputs (audio, image, text) before sending to the analyzer
    """
    
    def __init__(self, whisper_model="base", emotion_model="abhilash88/face-emotion-detection"):
        """
        Initialize preprocessing models
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            emotion_model: Hugging Face model for emotion detection
        """
        print("="*70)
        print("INITIALIZING MULTIMODAL PREPROCESSOR")
        print("="*70)
        
        # Load Whisper model for audio transcription
        print(f"\n📢 Loading Whisper model: {whisper_model}...")
        self.whisper_model = whisper.load_model(whisper_model)
        print("✓ Whisper model loaded successfully")
        
        # Load emotion detection model
        print(f"\n😊 Loading emotion detection model: {emotion_model}...")
        self.emotion_processor = AutoImageProcessor.from_pretrained(emotion_model)
        self.emotion_model = ViTForImageClassification.from_pretrained(emotion_model)
        print("✓ Emotion detection model loaded successfully")
        
        # Emotion labels
        self.emotion_labels = {
            0: 'Angry',
            1: 'Disgust',
            2: 'Fear',
            3: 'Happy',
            4: 'Sad',
            5: 'Surprise',
            6: 'Neutral'
        }
        
        print("\n" + "="*70)
        print("✅ PREPROCESSOR READY")
        print("="*70 + "\n")
        
        # Supabase client for storage retrieval
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                print("✓ Supabase client initialized for storage retrieval")
            except Exception as e:
                print(f"⚠️  Supabase client init failed: {str(e)}")
                self.supabase = None
        else:
            self.supabase = None
            print("⚠️  SUPABASE_URL/KEY missing; storage retrieval disabled")
        
        # Prefer underscore bucket by default; will fallback to dash variant during fetch
        self.media_bucket = os.getenv("SUPABASE_MEDIA_BUCKET", "mood_media")
        self.temp_dir = Path(__file__).parent / "temp_uploads"
        self.temp_dir.mkdir(exist_ok=True)
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio file using Whisper
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            str: Transcribed text
        """
        try:
            if not audio_path or not os.path.exists(audio_path):
                print(f"⚠️  Audio file not found: {audio_path}")
                return ""
            
            print(f"🎤 Transcribing audio: {audio_path}")
            result = self.whisper_model.transcribe(audio_path)
            transcript = result["text"].strip()
            
            print(f"✓ Transcription complete: '{transcript[:100]}...'")
            return transcript
            
        except Exception as e:
            print(f"❌ Error transcribing audio: {str(e)}")
            return ""
    
    def detect_emotion(self, image_path):
        """
        Detect emotion from facial image
        
        Args:
            image_path: Path to image file
            
        Returns:
            tuple: (emotion_name, confidence, all_emotions_dict)
        """
        try:
            if not image_path or not os.path.exists(image_path):
                print(f"⚠️  Image file not found: {image_path}")
                return "Unknown", 0.0, {}
            
            print(f"😊 Analyzing emotion from image: {image_path}")
            
            # Load and process image
            image = Image.open(image_path).convert("RGB")
            inputs = self.emotion_processor(images=image, return_tensors="pt")
            
            # Run inference
            with torch.no_grad():
                outputs = self.emotion_model(**inputs)
            
            # Get probabilities
            logits = outputs.logits
            probabilities = F.softmax(logits, dim=1).squeeze()
            
            # Get prediction
            predicted_index = torch.argmax(probabilities).item()
            dominant_emotion = self.emotion_labels[predicted_index]
            confidence = probabilities[predicted_index].item()
            
            # Get all emotion scores
            all_emotions = {
                self.emotion_labels[i]: probabilities[i].item() 
                for i in self.emotion_labels.keys()
            }
            
            print(f"✓ Emotion detected: {dominant_emotion} (confidence: {confidence:.2%})")
            return dominant_emotion, confidence, all_emotions
            
        except Exception as e:
            print(f"❌ Error detecting emotion: {str(e)}")
            return "Unknown", 0.0, {}
    
    def preprocess(self, audio_path=None, image_path=None, text_input=None, user_id=None, analyze=True):
        """
        Preprocess all inputs and return structured data
        Optionally calls ModelAnalyzer and process_user after preprocessing
        
        Args:
            audio_path: Path to audio file (optional)
            image_path: Path to image file (optional)
            text_input: Text input from user (optional)
            user_id: User ID for analysis (optional)
            analyze: Whether to call ModelAnalyzer and process_user (default: True)
            
        Returns:
            dict: Preprocessed data ready for model analyzer
        """
        print("\n" + "="*70)
        print("PREPROCESSING INPUTS")
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
            if emotion != "Unknown":
                result["emotion"] = emotion
                result["emotion_confidence"] = confidence
                result["emotion_details"] = details
                result["has_image"] = True
        
        # Summary
        print("\n" + "="*70)
        print("PREPROCESSING COMPLETE - DATA READY FOR MODEL_ANALYZER.PY")
        print("="*70)
        print(f"✓ Text Input: {'Yes' if result['has_text'] else 'No'}")
        print(f"✓ Audio Processed: {'Yes' if result['has_audio'] else 'No'}")
        print(f"✓ Image Processed: {'Yes' if result['has_image'] else 'No'}")
        
        if result['audio_transcript']:
            print(f"\n📤 Sending to analyzer - Audio Transcript: '{result['audio_transcript'][:80]}...'")
        if result['emotion']:
            print(f"📤 Sending to analyzer - Emotion: {result['emotion']} ({result['emotion_confidence']:.2%})")
        if result['text']:
            print(f"📤 Sending to analyzer - Text: '{result['text'][:80]}...'")
        
        print("\n🔗 This preprocessed_data dictionary will be passed to model_analyzer.py")
        print("="*70 + "\n")
        
        # CALL ModelAnalyzer and process_user if enabled and user_id provided
        if analyze and user_id:
            try:
                from model_analyzer import ModelAnalyzer
                from report import process_user
                
                print("\n" + "="*70)
                print("CALLING ANALYZER AND REPORT GENERATOR")
                print("="*70 + "\n")
                
                # Initialize analyzer
                import os
                supabase_url = os.getenv("SUPABASE_URL", "https://cswobvpopxypghwjolnb.supabase.co")
                supabase_key = os.getenv("SUPABASE_KEY", 
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzd29idnBvcHh5cGdod2pvbG5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA4NzQ5ODMsImV4cCI6MjA3NjQ1MDk4M30.P_E9zrpgOAI-mDVCCSWQDYLbfSXbng67EIApxujhNtQ")
                
                analyzer = ModelAnalyzer(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key
                )
                
                # Call ModelAnalyzer
                print("\n🤖 Calling ModelAnalyzer with preprocessed data...")
                analysis_result = analyzer.analyze(user_id, result)
                print("\n✅ ModelAnalyzer completed successfully!")
                
                # Process user and update report with preprocessed mood data
                print("\n📊 Updating report with preprocessed mood data using process_user...")
                process_user(user_id, preprocessed_data=result)
                print("✅ Report updated with mood data!")
                
                print("\n" + "="*70)
                print("✅ ANALYSIS PIPELINE COMPLETE")
                print("="*70 + "\n")
                
                # Include analysis result in the return value
                result['analysis_result'] = analysis_result
                return result
                
            except Exception as e:
                import traceback
                print(f"\n❌ Error in analysis pipeline: {str(e)}")
                print(f"Full traceback:\n{traceback.format_exc()}")
                print("Returning preprocessed data without analysis")
                # Add empty analysis_result to avoid key errors
                result['analysis_result'] = {
                    "analysis": f"Error during analysis: {str(e)}",
                    "mood": "Unknown",
                    "stress_level": 0,
                    "stress_day": 0,
                    "stress_alert": None
                }
                return result
        
        # If analyze is False or no user_id, return without analysis
        print("\nℹ️  Skipping analysis (analyze=False or no user_id)")
        result['analysis_result'] = None
        return result

    def preprocess_from_supabase(self, user_id: str, analyze: bool = True):
        """
        Fetch latest audio/image/text for the user from Supabase Storage and preprocess.
        Files are expected under bucket/<user_id>/ with timestamped names.
        """
        if not self.supabase:
            print("❌ Supabase client not available; cannot fetch from storage")
            return self.preprocess(audio_path=None, image_path=None, text_input=None, user_id=user_id, analyze=analyze)
        
        try:
            folder = f"{user_id}"
            # List files in the user's folder, trying primary bucket then fallback alias
            bucket_used = self.media_bucket
            try:
                items = self.supabase.storage.from_(bucket_used).list(path=folder)
            except Exception:
                items = None
            if not items:
                alt_bucket = "mood-media" if bucket_used == "mood_media" else "mood_media"
                try:
                    items = self.supabase.storage.from_(alt_bucket).list(path=folder)
                    if items:
                        bucket_used = alt_bucket
                        print(f"ℹ️  Using fallback storage bucket: {bucket_used}")
                except Exception:
                    items = None
            if not items:
                print(f"⚠️  No items found in storage for user {user_id}")
                return self.preprocess(audio_path=None, image_path=None, text_input=None, user_id=user_id, analyze=analyze)
            
            # Pick latest by name (timestamp prefix) per type
            audio_exts = (".wav", ".mp3", ".m4a", ".ogg")
            image_exts = (".jpg", ".jpeg", ".png")
            text_name_suffix = "_text.txt"
            
            audio_candidates = sorted([i["name"] for i in items if any(i["name"].lower().endswith(ext) for ext in audio_exts)], reverse=True)
            image_candidates = sorted([i["name"] for i in items if any(i["name"].lower().endswith(ext) for ext in image_exts)], reverse=True)
            text_candidates = sorted([i["name"] for i in items if i["name"].lower().endswith(text_name_suffix)], reverse=True)
            
            latest_audio_path = f"{folder}/{audio_candidates[0]}" if audio_candidates else None
            latest_image_path = f"{folder}/{image_candidates[0]}" if image_candidates else None
            latest_text_path = f"{folder}/{text_candidates[0]}" if text_candidates else None
            
            # Download to temp files
            local_audio = None
            local_image = None
            text_input = None
            
            if latest_audio_path:
                audio_bytes = self.supabase.storage.from_(bucket_used).download(latest_audio_path)
                local_audio = self.temp_dir / latest_audio_path.replace("/", "_")
                with open(local_audio, "wb") as f:
                    f.write(audio_bytes)
                print(f"✓ Downloaded audio to {local_audio}")
            
            if latest_image_path:
                image_bytes = self.supabase.storage.from_(bucket_used).download(latest_image_path)
                local_image = self.temp_dir / latest_image_path.replace("/", "_")
                with open(local_image, "wb") as f:
                    f.write(image_bytes)
                print(f"✓ Downloaded image to {local_image}")
            
            if latest_text_path:
                text_bytes = self.supabase.storage.from_(bucket_used).download(latest_text_path)
                try:
                    text_input = text_bytes.decode("utf-8")
                except Exception:
                    text_input = text_bytes.decode("latin-1", errors="ignore")
                print(f"✓ Loaded text ({len(text_input)} chars)")
            
            return self.preprocess(
                audio_path=str(local_audio) if local_audio else None,
                image_path=str(local_image) if local_image else None,
                text_input=text_input,
                user_id=user_id,
                analyze=analyze,
            )
        except Exception as e:
            print(f"❌ Error fetching from Supabase Storage: {str(e)}")
            return self.preprocess(audio_path=None, image_path=None, text_input=None, user_id=user_id, analyze=analyze)
    
    def print_detailed_results(self, preprocessed_data):
        """Print detailed preprocessing results"""
        print("\n" + "="*70)
        print("DETAILED PREPROCESSING RESULTS")
        print("="*70 + "\n")
        
        if preprocessed_data['text']:
            print("📝 TEXT INPUT:")
            print(f"   {preprocessed_data['text']}\n")
        
        if preprocessed_data['audio_transcript']:
            print("🎤 AUDIO TRANSCRIPT:")
            print(f"   {preprocessed_data['audio_transcript']}\n")
        
        if preprocessed_data['emotion']:
            print("😊 EMOTION ANALYSIS:")
            print(f"   Dominant: {preprocessed_data['emotion']}")
            print(f"   Confidence: {preprocessed_data['emotion_confidence']:.2%}")
            print("\n   All Emotions:")
            for emotion, score in sorted(preprocessed_data['emotion_details'].items(), 
                                        key=lambda x: x[1], reverse=True):
                print(f"   - {emotion:<10}: {score:.2%}")
        
        print("\n" + "="*70 + "\n")


def main():
    """Test the preprocessor"""
    print("MULTIMODAL PREPROCESSOR TEST\n")
    
    # Initialize preprocessor
    preprocessor = MultimodalPreprocessor(whisper_model="base")
    
    # Example files (update these paths)
    audio_file = "output.wav"
    image_file = "angry.jpg"
    text = "I'm feeling stressed today after a long meeting."
    
    # Check file existence
    audio_path = audio_file if os.path.exists(audio_file) else None
    image_path = image_file if os.path.exists(image_file) else None
    
    # Preprocess with user_id to trigger analysis
    result = preprocessor.preprocess(
        audio_path=audio_path,
        image_path=image_path,
        text_input=text,
        user_id="123456",
        analyze=True
    )
    
    # Print detailed results
    preprocessor.print_detailed_results(result)
    
    return result


if __name__ == "__main__":
    main()