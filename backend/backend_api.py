"""
FastAPI Backend for Wellness Activity Recommender
Serves HTML/JS frontend and provides API endpoints for AI analysis via AWS Bedrock Claude
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn
import os
from pathlib import Path
import json
from datetime import datetime
import logging
from typing import Optional
import jwt
from dotenv import load_dotenv
import requests
import tempfile


# Load environment variables from .env file
# Try multiple locations to ensure we find it
from pathlib import Path
backend_dir = Path(__file__).parent if '__file__' in dir() else Path.cwd()

# Ensure all entries are pathlib.Path objects (strings don't have .exists())
env_paths = [
    backend_dir / ".env",              # backend/.env
    backend_dir.parent / ".env",       # health_monitor/.env
    backend_dir.parent.parent / ".env",# project/.env
    Path(".env"),                      # Current working directory
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded .env from: {env_path.absolute()}")
        env_loaded = True
        break

if not env_loaded:
    # Fallback to default load_dotenv()
    load_dotenv()
    print("⚠️ Using default load_dotenv() - .env file may not be found")

# Debug: Check if Google credentials are loaded
import os
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
if google_client_id and google_client_secret:
    print(f"✓ Google credentials found in environment")
    print(f"  Client ID: {google_client_id[:30]}...")
else:
    print(f"⚠️ Google credentials NOT found in environment")
    print(f"  GOOGLE_CLIENT_ID: {'SET' if google_client_id else 'NOT SET'}")
    print(f"  GOOGLE_CLIENT_SECRET: {'SET' if google_client_secret else 'NOT SET'}")

# Import local modules
try:
    from model_analyzer import ModelAnalyzer
except Exception as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ Could not import ModelAnalyzer: {str(e)}")
    ModelAnalyzer = None

try:
    from report import process_user
except Exception as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ Could not import process_user: {str(e)}")
    def process_user(*args, **kwargs):
        pass

try:
    from google_calendar_service import GoogleCalendarService
    from push_notification_service import PushNotificationService
    from location_tracking_service import LocationTrackingService
except Exception as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ Could not import calendar/notification/location services: {str(e)}")
    GoogleCalendarService = None
    PushNotificationService = None
    LocationTrackingService = None

# Removed: MultimodalPreprocessor causes threading crash with torch
# Only needed for mood processing endpoints, not auth
MultimodalPreprocessor = None

from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Supabase - REQUIRED environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="Wellness Activity Recommender API",
    description="AI-powered personalized activity suggestions using AWS Bedrock Claude",
    version="2.0.0"
)

# Add CORS middleware - configure allowed origins via environment variable
raw_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://health-monitor-tan.vercel.app,https://health-monitor-1-6vo8.onrender.com"
)
ALLOWED_ORIGINS = [o.strip() for o in raw_allowed_origins.split(",") if o.strip()]

# Optional: allow origins via regex (e.g., ^https://.*\.vercel\.app$)
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", None)

logger.info(f"CORS allow_origins: {ALLOWED_ORIGINS}")
if ALLOWED_ORIGIN_REGEX:
    logger.info(f"CORS allow_origin_regex: {ALLOWED_ORIGIN_REGEX}")

# For debugging: Allow all origins temporarily (remove in production)
# ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SCRIPT_DIR = Path(__file__).parent / "script"
TEMP_DIR = Path(__file__).parent / "temp_uploads"
TEMP_DIR.mkdir(exist_ok=True)

# Initialize models
preprocessor = None
analyzer = None
calendar_service = None
notification_service = None
location_service = None

def initialize_models():
    """Initialize preprocessor and analyzer"""
    global preprocessor, analyzer
    try:
        logger.info("Initializing models...")
        
        # Initialize ultra-lightweight preprocessor
        try:
            from preprocessor_lite import MultimodalPreprocessor
            preprocessor = MultimodalPreprocessor()
            logger.info("✓ Ultra-Lightweight Preprocessor initialized (Google Speech + DeepFace <100MB)")
        except Exception as e:
            logger.warning(f"Preprocessor initialization failed: {str(e)}")
            preprocessor = None
        
        # Initialize analyzer with error handling
        try:
            from model_analyzer import ModelAnalyzer
            analyzer = ModelAnalyzer(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY
            )
            logger.info("✓ Analyzer initialized (AWS Bedrock Claude 3.5 Sonnet)")
        except Exception as e:
            logger.warning(f"Analyzer initialization failed: {str(e)}")
            analyzer = None
        
        if preprocessor and analyzer:
            logger.info("✓ All ML models initialized successfully")
        else:
            logger.warning("⚠️ Some ML models failed to initialize - will use fallback analysis")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing models: {str(e)}")
        return False
# Add these imports at the top of backend_api.py
from pydantic import BaseModel, EmailStr
import hashlib
import secrets
import jwt as pyjwt
from datetime import timedelta

# JWT Configuration - REQUIRED environment variable
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET environment variable is required")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Pydantic models for auth
class UserRegister(BaseModel):
    id: str
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Helper functions
def hash_password(password: str) -> str:
    # Use SHA-256 with salt for simplicity
    salt = secrets.token_hex(16)
    return f"{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if it's the new format (salt:hash)
        if ":" in hashed_password:
            salt, hash_part = hashed_password.split(":", 1)
            return hashlib.sha256((plain_password + salt).encode()).hexdigest() == hash_part
        else:
            # Old bcrypt format - for now, just return False to force re-registration
            # In production, you'd want to migrate old passwords
            return False
    except:
        return False

def create_access_token(user_id: str) -> str:
    """Create JWT token with user_id as string"""
    expire = datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(user_id), "exp": expire}  # Ensure it's a string
    return pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/api/auth/register")
async def register(user: UserRegister):
    """Register a new user"""
    try:
        logger.info(f"Registering new user: {user.email}")
        
        # Check if id already exists
        existing_id = supabase.table("users").select("*").eq("id", user.id).execute()
        if existing_id.data:
            raise HTTPException(status_code=400, detail="User ID already taken")
        
        # Check if email already exists
        existing_email = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing_email.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user in Supabase
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "password": hash_password(user.password),
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("users").insert(user_data).execute()
        
        logger.info(f"User registered successfully: {user.email}")
        return JSONResponse({
            "status": "success",
            "message": "User registered successfully"
        })
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login user and return JWT token"""
    try:
        logger.info(f"Login attempt for: {credentials.email}")
        
        # Fetch user from Supabase
        user_response = supabase.table("users").select("*").eq("email", credentials.email).execute()
        
        if not user_response.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user = user_response.data[0]
        
        # Verify password
        if not verify_password(credentials.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Get user id
        user_id = user["id"]
        
        # Check if user has profile
        try:
            profile_response = supabase.table("habit").select("id").eq("id", user_id).execute()
            has_profile = bool(profile_response.data)
            logger.info(f"Profile check for {user_id}: {has_profile}")
        except Exception as e:
            logger.warning(f"Profile check failed: {str(e)}")
            has_profile = False
        
        # Create JWT token with user id
        token = create_access_token(user_id)
        
        logger.info(f"Login successful for: {credentials.email} (id: {user_id})")
        return JSONResponse({
            "token": token,
            "id": user_id,
            "hasProfile": has_profile,
            "user": {
                "id": user_id,
                "email": user["email"],
                "name": user["name"],
                "hasProfile": has_profile
            }
        })
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

# Single verify_token function - properly decodes JWT
def verify_token(authorization: Optional[str] = Header(None)) -> dict:
    """Verify JWT token from header and return user_id"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        
        # Decode JWT token - token contains {"sub": user_id, "exp": ...}
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")  # "sub" contains the user_id (see create_access_token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
        
        # Return both user_id and id for compatibility
        return {"user_id": str(user_id), "id": str(user_id), "token": token}
        
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

@app.get("/api/auth/me")
async def get_current_user(user_id_obj: dict = Depends(verify_token)):
    """Get current user information"""
    try:
        user_id = user_id_obj["user_id"]
        
        # Get user from database by id
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_response.data[0]
        
        # Check if user has profile
        try:
            profile_response = supabase.table("habit").select("id").eq("id", user_id).execute()
            has_profile = bool(profile_response.data)
        except Exception as e:
            logger.warning(f"Profile check failed: {str(e)}")
            has_profile = False
        
        return JSONResponse({
            "id": user_id,
            "email": user["email"],
            "name": user["name"],
            "hasProfile": has_profile
        })
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting user info: {str(e)}")

# Initialize on startup - LAZY LOADING for memory optimization
@app.on_event("startup")
async def startup_event():
    """Initialize only analyzer on startup (lazy load preprocessor)"""
    global analyzer, calendar_service, notification_service, location_service
    try:
        # Initialize analyzer only (AWS Bedrock - no local memory)
        from model_analyzer import ModelAnalyzer
        analyzer = ModelAnalyzer(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY
        )
        logger.info("✓ Analyzer initialized (AWS Bedrock - 0MB RAM)")
        logger.info("📊 Preprocessor will lazy-load on first mood entry (saves ~100MB)")
        
        # Initialize calendar and notification services
        if GoogleCalendarService:
            calendar_service = GoogleCalendarService(supabase)
            if calendar_service.client_id and calendar_service.client_secret:
                logger.info("✓ Google Calendar Service initialized with OAuth credentials")
                logger.info(f"  Client ID: {calendar_service.client_id[:30]}...")
                logger.info(f"  Redirect URI: {calendar_service.redirect_uri}")
            else:
                logger.warning("⚠️ Google Calendar Service initialized WITHOUT OAuth credentials")
                logger.warning("   Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
                logger.warning("   Or place client_secret.json in project root")
        
        if PushNotificationService:
            notification_service = PushNotificationService(supabase)
            logger.info("✓ Push Notification Service initialized")
        
        if LocationTrackingService:
            location_service = LocationTrackingService(supabase)
            logger.info("✓ Location Tracking Service initialized")
        
    except Exception as e:
        logger.warning(f"Initialization failed: {str(e)}")
        analyzer = None

# ============================================
# STATIC FILES - SERVE HTML/JS FRONTEND
# ============================================

@app.get("/")
async def root():
    """Redirect to API info"""
    return {"message": "Wellness Activity Recommender API", "version": "2.0.1", "updated": "2025-10-24"}

# Mount static files from script folder
if SCRIPT_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(SCRIPT_DIR), html=True), name="frontend")
    logger.info(f"✓ Frontend mounted from {SCRIPT_DIR}")
else:
    logger.warning(f"⚠️ Script directory not found: {SCRIPT_DIR}")

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "service": "wellness-recommender-api",
        "models": {
            "preprocessor": "Whisper (Audio + Emotion)",
            "analyzer": "AWS Bedrock Claude 3.5 Sonnet",
            "region": "us-east-1"
        }
    }

@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )

# ============================================
# PROFILE ENDPOINTS

@app.get("/api/profile/{user_id}")
async def get_profile(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Get user profile/habit data from Supabase"""
    try:
        logger.info(f"Fetching profile for user {user_id}")
        
        # Fetch habit data from Supabase
        response = supabase.table("habit").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile_data = response.data[0]
        logger.info(f"Profile fetched successfully for user {user_id}")
        
        return JSONResponse({
            "status": "success",
            "data": profile_data
        })
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Profile fetch error: {str(e)}")

@app.post("/api/profile")
async def save_profile(
    id: str = Form(...),
    user_id_obj: dict = Depends(verify_token),
    screetime_daily: str = Form(...),
    job_description: str = Form(...),
    free_hr_activities: str = Form(...),
    travelling_hr: str = Form(...),
    weekend_mood: str = Form(...),
    week_day_mood: str = Form(...),
    free_hr_mrg: str = Form(...),
    free_hr_eve: str = Form(...),
    sleep_time: str = Form(...),
    preferred_exercise: str = Form(...),
    social_preference: str = Form(...),
    energy_level_rating: str = Form(...),
    sleep_pattern: str = Form(...),
    hobbies: str = Form(...),
    work_schedule: str = Form(...),
    meal_preferences: str = Form(...),
    relaxation_methods: str = Form(...)
):
    """Save user profile to Supabase habit table and generate initial report"""
    try:
        # Use the id from the form parameter directly
        logger.info(f"Saving profile for user {id}")
        
        # Prepare profile data
        profile_data = {
            "id": id,
            "screetime_daily": screetime_daily,
            "job_description": job_description,
            "free_hr_activities": free_hr_activities,
            "travelling_hr": travelling_hr,
            "weekend_mood": weekend_mood,
            "week_day_mood": week_day_mood,
            "free_hr_mrg": free_hr_mrg,
            "free_hr_eve": free_hr_eve,
            "sleep_time": sleep_time,
            "preferred_exercise": preferred_exercise,
            "social_preference": social_preference,
            "energy_level_rating": energy_level_rating,
            "sleep_pattern": sleep_pattern,
            "hobbies": hobbies,
            "work_schedule": work_schedule,
            "meal_preferences": meal_preferences,
            "relaxation_methods": relaxation_methods,
            "created_at": datetime.now().isoformat()
        }
        
        # Save to Supabase habit table
        response = supabase.table("habit").upsert(profile_data).execute()
        logger.info(f"Profile saved successfully for user {id}")
        
        # Generate initial report without preprocessed data
        logger.info(f"Generating initial report for user {id}")
        process_user(id, preprocessed_data=None)
        
        return JSONResponse({
            "status": "success",
            "message": "Profile saved successfully",
            "user_id": id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error saving profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Profile save error: {str(e)}")

@app.post("/api/mood")
async def submit_mood(
    request: Request
):
    """Submit mood entry: accepts JSON with URLs or form-data with files - ALL INPUTS ARE OPTIONAL"""
    global preprocessor, analyzer  # Access global model instances
    logger.info("=== MOOD ENDPOINT CALLED (OPTIONAL INPUTS) ===")
    try:
        # Log all headers for debugging
        logger.info(f"Request headers: {dict(request.headers)}")
        
        content_type = request.headers.get("content-type", "")
        logger.info(f"Content-Type: {content_type}")
        
        # Handle JSON (URLs from frontend Supabase upload)
        if "application/json" in content_type:
            import json as json_lib
            body_bytes = await request.body()
            logger.info(f"Raw body length: {len(body_bytes)}")
            logger.info(f"Raw body preview: {body_bytes[:500]}")
            
            if len(body_bytes) == 0:
                logger.error("ERROR: Request body is EMPTY!")
                raise HTTPException(status_code=400, detail="Request body is empty")
            
            try:
                data = json_lib.loads(body_bytes)
                logger.info(f"✓ Successfully parsed JSON data")
                logger.info(f"Data keys: {list(data.keys())}")
                logger.info(f"Full data: {data}")
            except Exception as parse_error:
                logger.error(f"ERROR parsing JSON: {str(parse_error)}")
                logger.error(f"Body content: {body_bytes.decode('utf-8', errors='replace')}")
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(parse_error)}")
            
            user_id = data.get("id")
            mood_text = data.get("mood_text")  # OPTIONAL
            audio_url = data.get("audio_url")  # OPTIONAL
            image_url = data.get("image_url")  # OPTIONAL
            
            # Check if at least one input is provided
            has_any_input = mood_text or audio_url or image_url
            
            logger.info(f"Processing mood entry via URLs for user: {user_id}")
            logger.info(f"Text: {'Yes' if mood_text else 'No'}")
            logger.info(f"Audio URL: {'Yes' if audio_url else 'No'}")
            logger.info(f"Image URL: {'Yes' if image_url else 'No'}")
            
            if not has_any_input:
                # Allow empty mood entry if user has push notification or calendar data
                logger.info("No media inputs provided - checking for alternative data sources...")
                # This is still valid - we'll use push notification + calendar data
            
            # Download files from URLs if provided
            import requests
            import tempfile
            
            audio_path = None
            image_path = None
            
            # Download files only if URLs are provided
            if audio_url:
                try:
                    resp = requests.get(audio_url)
                    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".audio").name
                    with open(audio_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"✓ Downloaded audio to: {audio_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to download audio: {str(e)}")
                    audio_path = None
            
            if image_url:
                try:
                    resp = requests.get(image_url)
                    image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                    with open(image_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"✓ Downloaded image to: {image_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to download image: {str(e)}")
                    image_path = None
            
            # Process with ML models
            logger.info(f"🔍 Model availability check - preprocessor: {preprocessor is not None}, analyzer: {analyzer is not None}")
            
            if not preprocessor or not analyzer:
                logger.warning("⚠️ Models not initialized, attempting to initialize...")
                initialize_models()
                logger.info(f"After init - preprocessor: {preprocessor is not None}, analyzer: {analyzer is not None}")
            
            # Use analyzer - either with preprocessor (full multimodal) or text-only
            if analyzer:
                if preprocessor:
                    # Full multimodal processing with audio/image
                    logger.info("✓ Using FULL ML pipeline (Preprocessor + Analyzer)")
                    logger.info(f"📝 Inputs - text: {mood_text[:50] if mood_text else 'None'}, audio: {audio_path}, image: {image_path}")
                    
                    try:
                        preprocessed_data = preprocessor.preprocess(
                            audio_path=audio_path,
                            image_path=image_path,
                            text_input=mood_text,
                            user_id=user_id,
                            analyze=True
                        )
                        logger.info(f"✓ Preprocessing completed successfully")
                        logger.info(f"📊 Result keys: {list(preprocessed_data.keys())}")
                    except Exception as preprocess_error:
                        logger.error(f"❌ Preprocessing error: {str(preprocess_error)}")
                        logger.error(f"Error details: {type(preprocess_error).__name__}")
                        import traceback
                        logger.error(traceback.format_exc())
                        raise
                    
                    # Cleanup temp files
                    if audio_path and os.path.exists(audio_path):
                        os.unlink(audio_path)
                    if image_path and os.path.exists(image_path):
                        os.unlink(image_path)
                    
                    analysis_result = preprocessed_data.get("analysis_result", {})
                    recommendations = analysis_result.get("analysis", "") if analysis_result else ""
                    
                    if not recommendations:
                        recommendations = "Analysis in progress - recommendations will be available shortly."
                    
                    # Save to database
                    mood_entry = {
                        "id": user_id,
                        "mood_text": mood_text,
                        "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                        "emotion": preprocessed_data.get("emotion", ""),
                        "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                        "recommendations": recommendations,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    supabase.table("mood_entries").insert(mood_entry).execute()
                    
                    return JSONResponse({
                        "status": "success",
                        "message": "Mood processed successfully with full ML pipeline",
                        "data": {
                            "user_id": user_id,
                            "mood_text": mood_text,
                            "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                            "emotion": preprocessed_data.get("emotion", ""),
                            "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                            "recommendations": recommendations,
                            "mood": analysis_result.get("mood", "") if analysis_result else "",
                            "stress_level": analysis_result.get("stress_level", 0) if analysis_result else 0,
                            "stress_day": analysis_result.get("stress_day", 0) if analysis_result else 0,
                            "stress_alert": analysis_result.get("stress_alert", None) if analysis_result else None,
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                else:
                    # Text-only mode: Use analyzer directly without preprocessor
                    logger.info("✓ Using TEXT-ONLY mode (Analyzer without preprocessor)")
                    logger.info(f"📝 Text input: {mood_text[:100] if mood_text else 'None'}")
                    logger.warning("⚠️ Audio/image processing unavailable - proceeding with text only")
                    
                    # Call analyzer directly with text
                    simple_data = {
                        "text": mood_text,
                        "audio_transcript": "",
                        "emotion": "",
                        "emotion_confidence": 0.0,
                        "has_audio": False,
                        "has_image": False,
                        "has_text": bool(mood_text)
                    }
                    
                    try:
                        analysis_result = analyzer.analyze(user_id, simple_data)
                        logger.info(f"✓ Analyzer completed successfully")
                        
                        recommendations = analysis_result.get("analysis", "") if analysis_result else ""
                        if not recommendations:
                            recommendations = "Analysis in progress - recommendations will be available shortly."
                        
                        # Save to database
                        mood_entry = {
                            "id": user_id,
                            "mood_text": mood_text,
                            "audio_transcript": "",
                            "emotion": "",
                            "emotion_confidence": 0,
                            "recommendations": recommendations,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        supabase.table("mood_entries").insert(mood_entry).execute()
                        
                        return JSONResponse({
                            "status": "success",
                            "message": "Mood processed with text-only analysis (AWS Bedrock)",
                            "data": {
                                "user_id": user_id,
                                "mood_text": mood_text,
                                "audio_transcript": "",
                                "emotion": "",
                                "emotion_confidence": 0,
                                "recommendations": recommendations,
                                "mood": analysis_result.get("mood", "") if analysis_result else "",
                                "stress_level": analysis_result.get("stress_level", 0) if analysis_result else 0,
                                "stress_day": analysis_result.get("stress_day", 0) if analysis_result else 0,
                                "stress_alert": analysis_result.get("stress_alert", None) if analysis_result else None,
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                    except Exception as analyzer_error:
                        logger.error(f"❌ Analyzer error: {str(analyzer_error)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Fall through to fallback
            
            # Fallback - models not available
            logger.warning("⚠️ USING FALLBACK ANALYSIS - ML models not available")
            logger.warning(f"Preprocessor available: {preprocessor is not None}")
            logger.warning(f"Analyzer available: {analyzer is not None}")
            mood_analysis = analyze_mood_text(mood_text)
            return JSONResponse({
                "status": "success",
                "message": "Mood processed with fallback",
                "data": {
                    "user_id": user_id,
                    "mood_text": mood_text,
                    "emotion": mood_analysis["emotion"],
                    "emotion_confidence": mood_analysis["confidence"],
                    "recommendations": mood_analysis["recommendations"],
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        # Handle multipart/form-data (legacy: files uploaded directly)
        else:
            form = await request.form()
            user_id = form.get("id")
            mood_text = form.get("mood_text")
            mood_audio = form.get("mood_audio")
            mood_image = form.get("mood_image")
            
            logger.info(f"Processing mood entry via form-data for user: {user_id}")
            
            # Save files
            audio_path = None
            image_path = None
            
            if mood_audio:
                audio_path = TEMP_DIR / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mood_audio.filename}"
                with open(audio_path, "wb") as f:
                    f.write(await mood_audio.read())
            
            if mood_image:
                image_path = TEMP_DIR / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mood_image.filename}"
                with open(image_path, "wb") as f:
                    f.write(await mood_image.read())
            
            # 📍 AUTO-GENERATE DAILY LOCATION SUMMARY (if location tracking is enabled)
            if location_service:
                try:
                    logger.info(f"📍 Auto-analyzing today's location data for user {user_id}")
                    today_summary = location_service.analyze_daily_locations(user_id)
                    if today_summary:
                        location_service.save_daily_summary(user_id, today_summary)
                        logger.info(f"✅ Daily location summary saved automatically")
                    else:
                        logger.info("ℹ️  No location data to summarize yet")
                except Exception as loc_err:
                    logger.warning(f"⚠️ Location summary generation failed: {str(loc_err)}")
            
            # 📅 AUTO-FETCH TODAY'S AND TOMORROW'S CALENDAR DATA (if calendar is authorized)
            if calendar_service:
                try:
                    logger.info(f"📅 Auto-fetching today's and tomorrow's calendar data for user {user_id}")
                    calendar_data = calendar_service.fetch_today_events(user_id)
                    if calendar_data:
                        logger.info(f"✅ Calendar data fetched and saved automatically")
                        logger.info(f"   Today - Meeting count: {calendar_data.get('meeting_count', 0)}, Hours: {calendar_data.get('meeting_hours', 0)}")
                        logger.info(f"   Tomorrow - Meeting count: {calendar_data.get('tomorrow_meeting_count', 0)}, Hours: {calendar_data.get('tomorrow_meeting_hours', 0)}")
                    else:
                        logger.info("ℹ️  No calendar data available (not authorized or no events)")
                except Exception as cal_err:
                    logger.warning(f"⚠️ Calendar fetch failed: {str(cal_err)}")
            
            # Process with ML
            if preprocessor and analyzer:
                preprocessed_data = preprocessor.preprocess(
                    audio_path=str(audio_path) if audio_path else None,
                    image_path=str(image_path) if image_path else None,
                    text_input=mood_text,
                    user_id=user_id,
                    analyze=True
                )
                
                analysis_result = preprocessed_data.get("analysis_result", {})
                recommendations = analysis_result.get("analysis", "") if analysis_result else ""
                
                return JSONResponse({
                    "status": "success",
                    "data": {
                        "user_id": user_id,
                        "recommendations": recommendations,
                        "timestamp": datetime.now().isoformat()
                    }
                })
            
            # Fallback
            mood_analysis = analyze_mood_text(mood_text)
            return JSONResponse({
                "status": "success",
                "data": {
                    "user_id": user_id,
                    "recommendations": mood_analysis["recommendations"],
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    except Exception as e:
        logger.error(f"Error processing mood: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mood processing error: {str(e)}")


def analyze_mood_text(text: str) -> dict:
    """Simple mood analysis based on keywords"""
    text_lower = text.lower()
    
    # Basic emotion detection
    positive_words = ["happy", "good", "great", "amazing", "wonderful", "excited", "joy", "love", "fantastic"]
    negative_words = ["sad", "bad", "terrible", "awful", "angry", "frustrated", "hate", "depressed", "anxious"]
    neutral_words = ["okay", "fine", "normal", "average", "neutral"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    neutral_count = sum(1 for word in neutral_words if word in text_lower)
    
    if positive_count > negative_count and positive_count > neutral_count:
        emotion = "Positive"
        confidence = min(0.8, 0.5 + (positive_count * 0.1))
    elif negative_count > positive_count and negative_count > neutral_count:
        emotion = "Negative"
        confidence = min(0.8, 0.5 + (negative_count * 0.1))
    else:
        emotion = "Neutral"
        confidence = 0.6
    
    # Basic recommendations
    if emotion == "Positive":
        recommendations = [
            "Keep up the great energy! Consider sharing your positive mood with others.",
            "This is a perfect time to tackle challenging tasks or help someone else.",
            "Consider journaling about what's making you feel good today.",
            "Use this positive energy for physical activity or creative projects.",
            "Share your happiness - it's contagious and benefits everyone around you."
        ]
    elif emotion == "Negative":
        recommendations = [
            "Take some deep breaths and remember this feeling is temporary.",
            "Consider talking to a friend or family member about how you're feeling.",
            "Try some gentle physical activity like walking or stretching.",
            "Practice self-care with activities you enjoy.",
            "Consider professional support if these feelings persist."
        ]
    else:
        recommendations = [
            "A neutral mood is a good foundation - consider what might bring you joy today.",
            "Try something new or different to add some excitement to your day.",
            "Connect with others - social interaction can boost your mood.",
            "Consider what activities usually make you feel more positive.",
            "Take a moment to appreciate the small things around you."
        ]
    
    return {
        "emotion": emotion,
        "confidence": confidence,
        "recommendations": recommendations
    }

# ============================================
# API ENDPOINTS FOR ANALYSIS
# ============================================

@app.post("/api/analyze-text")
async def analyze_text(
    user_id: str = Form(...),
    text_input: str = Form(...),
    emotion: str = Form(default=""),
    emotion_confidence: float = Form(default=0.0)
):
    """Analyze text input and generate recommendations"""
    try:
        if not analyzer:
            initialize_models()
        
        logger.info(f"Analyzing text for user {user_id}")
        
        # Prepare preprocessed data
        preprocessed_data = {
            "text": text_input,
            "audio_transcript": "",
            "emotion": emotion or "Neutral",
            "emotion_confidence": emotion_confidence,
            "emotion_details": {},
            "has_text": True,
            "has_audio": False,
            "has_image": False
        }
        
        # Analyze
        result = analyzer.analyze(user_id, preprocessed_data)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "user_id": user_id,
                "analysis": result["analysis"],
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.post("/api/analyze-audio")
async def analyze_audio(
    user_id: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Analyze audio file and generate recommendations"""
    try:
        if not preprocessor or not analyzer:
            initialize_models()
        
        logger.info(f"Analyzing audio for user {user_id}")
        
        # Save uploaded file
        file_path = TEMP_DIR / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio_file.filename}"
        with open(file_path, "wb") as f:
            f.write(await audio_file.read())
        
        # Preprocess audio
        preprocessed_data = preprocessor.preprocess(
            audio_path=str(file_path),
            image_path=None,
            text_input=None
        )
        
        # Analyze
        result = analyzer.analyze(user_id, preprocessed_data)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "user_id": user_id,
                "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                "emotion": preprocessed_data.get("emotion", ""),
                "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                "analysis": result["analysis"],
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audio analysis error: {str(e)}")

@app.post("/api/analyze-photo")
async def analyze_photo(
    user_id: str = Form(...),
    photo_file: UploadFile = File(...)
):
    """Analyze photo (emotion detection) and generate recommendations"""
    try:
        if not preprocessor or not analyzer:
            initialize_models()
        
        logger.info(f"Analyzing photo for user {user_id}")
        
        # Save uploaded file
        file_path = TEMP_DIR / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo_file.filename}"
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        
        # Preprocess photo (emotion detection)
        preprocessed_data = preprocessor.preprocess(
            audio_path=None,
            image_path=str(file_path),
            text_input=None
        )
        
        # Analyze
        result = analyzer.analyze(user_id, preprocessed_data)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "user_id": user_id,
                "emotion": preprocessed_data.get("emotion", ""),
                "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                "emotion_details": preprocessed_data.get("emotion_details", {}),
                "analysis": result["analysis"],
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Photo analysis error: {str(e)}")

@app.post("/api/analyze-multimodal")
async def analyze_multimodal(
    user_id: str = Form(...),
    text_input: str = Form(default=""),
    audio_file: UploadFile = File(default=None),
    photo_file: UploadFile = File(default=None)
):
    """Analyze multimodal input (text + audio + photo) and generate recommendations"""
    try:
        if not preprocessor or not analyzer:
            initialize_models()
        
        logger.info(f"Analyzing multimodal input for user {user_id}")
        
        audio_path = None
        image_path = None
        
        # Save audio if provided
        if audio_file:
            audio_path = TEMP_DIR / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio_file.filename}"
            with open(audio_path, "wb") as f:
                f.write(await audio_file.read())
        
        # Save photo if provided
        if photo_file:
            image_path = TEMP_DIR / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo_file.filename}"
            with open(image_path, "wb") as f:
                f.write(await photo_file.read())
        
        # Preprocess all inputs
        preprocessed_data = preprocessor.preprocess(
            audio_path=str(audio_path) if audio_path else None,
            image_path=str(image_path) if image_path else None,
            text_input=text_input if text_input else None
        )
        
        # Analyze
        result = analyzer.analyze(user_id, preprocessed_data)
        
        return JSONResponse({
            "status": "success",
            "data": {
                "user_id": user_id,
                "text_input": text_input,
                "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                "emotion": preprocessed_data.get("emotion", ""),
                "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                "analysis": result["analysis"],
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing multimodal input: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Multimodal analysis error: {str(e)}")

@app.post("/api/update-report")
async def update_report(user_id: str = Form(...)):
    """Update user report"""
    try:
        logger.info(f"Updating report for user {user_id}")
        
        # Process user and generate report
        process_user(user_id)
        
        return JSONResponse({
            "status": "success",
            "message": f"Report updated for user {user_id}",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report update error: {str(e)}")

# ============================================
# PUSH NOTIFICATION ENDPOINTS
# ============================================

@app.post("/api/notifications/register")
async def register_device_token(
    user_id: str = Form(...),
    fcm_token: str = Form(...),
    user_id_obj: dict = Depends(verify_token)
):
    """Register user's device for push notifications"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        success = notification_service.register_device(user_id, fcm_token)
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": "Device registered for notifications"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to register device")
    
    except Exception as e:
        logger.error(f"Error registering device: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/response")
async def save_notification_response(
    user_id: str = Form(...),
    notification_type: str = Form(...),
    emotion_response: str = Form(...),
    additional_notes: str = Form(default=None),
    user_id_obj: dict = Depends(verify_token)
):
    """Save user's response to push notification"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        success = notification_service.save_notification_response(
            user_id, notification_type, emotion_response, additional_notes
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": "Response saved successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save response")
    
    except Exception as e:
        logger.error(f"Error saving notification response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications/responses/{user_id}")
async def get_notification_responses(
    user_id: str,
    limit: int = 7,
    user_id_obj: dict = Depends(verify_token)
):
    """Get user's recent notification responses"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        responses = notification_service.get_latest_responses(user_id, limit)
        
        return JSONResponse({
            "status": "success",
            "data": responses,
            "count": len(responses)
        })
    
    except Exception as e:
        logger.error(f"Error retrieving responses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/send-morning")
async def trigger_morning_notification(
    user_id: str = Form(...),
    user_id_obj: dict = Depends(verify_token)
):
    """Manually trigger morning notification for testing"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        response = notification_service.send_morning_notification(user_id)
        
        if response:
            return JSONResponse({
                "status": "success",
                "message": "Morning notification sent",
                "response_id": response
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to send notification")
    
    except Exception as e:
        logger.error(f"Error sending morning notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/send-evening")
async def trigger_evening_notification(
    user_id: str = Form(...),
    user_id_obj: dict = Depends(verify_token)
):
    """Manually trigger evening notification for testing"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        response = notification_service.send_evening_notification(user_id)
        
        if response:
            return JSONResponse({
                "status": "success",
                "message": "Evening notification sent",
                "response_id": response
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to send notification")
    
    except Exception as e:
        logger.error(f"Error sending evening notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/toggle")
async def toggle_notifications(
    user_id: str = Form(...),
    enabled: bool = Form(...),
    user_id_obj: dict = Depends(verify_token)
):
    """Enable or disable notifications for a user"""
    try:
        if not notification_service:
            raise HTTPException(status_code=503, detail="Notification service not available")
        
        success = notification_service.toggle_notifications(user_id, enabled)
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Notifications {'enabled' if enabled else 'disabled'}"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to update notification settings")
    
    except Exception as e:
        logger.error(f"Error toggling notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GOOGLE CALENDAR ENDPOINTS
# ============================================

@app.get("/api/calendar/status")
async def calendar_service_status():
    """Check Google Calendar service status (for debugging)"""
    try:
        status = {
            "service_exists": calendar_service is not None,
            "client_id_set": calendar_service.client_id is not None if calendar_service else False,
            "client_secret_set": calendar_service.client_secret is not None if calendar_service else False,
            "redirect_uri": calendar_service.redirect_uri if calendar_service else None,
        }
        
        if calendar_service:
            status["client_id_preview"] = calendar_service.client_id[:30] + "..." if calendar_service.client_id else None
        
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/calendar/authorize/{user_id}")
async def authorize_calendar(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """
    Start Google Calendar authorization flow.
    
    This endpoint generates a Google OAuth URL for the user to authorize calendar access.
    
    How it works:
    1. User clicks "Connect Calendar" in frontend
    2. Frontend calls this endpoint: GET /api/calendar/authorize/{user_id}
    3. Backend generates OAuth URL with unique 'state' parameter
    4. Frontend opens URL in popup window
    5. User authorizes on Google's website
    6. Google redirects to /auth/callback with authorization code
    7. Backend exchanges code for tokens and saves them
    
    Note: The URL is generated fresh each time because Google creates a unique
    'state' parameter for security. The base URL is the same for all users.
    """
    try:
        if not calendar_service:
            logger.error("❌ Calendar service is None - service not initialized")
            raise HTTPException(status_code=503, detail="Calendar service not available. Please restart the backend server.")
        
        # Check if service has credentials before generating URL
        if not calendar_service.client_id or not calendar_service.client_secret:
            logger.error(f"❌ Calendar service missing credentials!")
            logger.error(f"   calendar_service exists: {calendar_service is not None}")
            logger.error(f"   client_id: {'SET (' + calendar_service.client_id[:30] + '...)' if calendar_service.client_id else 'NOT SET'}")
            logger.error(f"   client_secret: {'SET' if calendar_service.client_secret else 'NOT SET'}")
            logger.error(f"   Check .env file and restart backend server!")
            raise HTTPException(
                status_code=503, 
                detail="Google Calendar OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env file and restart the backend server."
            )
        
        # Convert user_id to int (database stores id as BIGINT)
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Invalid user_id format: {user_id}")
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {user_id}")
        
        # Generate authorization URL with unique state for this user
        # This is standard OAuth 2.0 - Google handles the authorization flow
        auth_url = calendar_service.get_authorization_url(user_id_int)
        
        if not auth_url:
            logger.error(f"❌ Failed to generate authorization URL for user {user_id}")
            raise HTTPException(
                status_code=503, 
                detail="Failed to generate Google Calendar authorization URL. Check backend logs for details."
            )
        
        logger.info(f"✓ Generated OAuth URL for user {user_id}")
        
        return JSONResponse({
            "status": "success",
            "auth_url": auth_url,
            "message": "Please authorize Google Calendar access"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting calendar auth: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")

@app.get("/auth/callback")
async def calendar_oauth_callback_legacy(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Handle Google OAuth callback at /auth/callback (matches configured redirect URI)"""
    # Forward to the main callback handler
    return await calendar_oauth_callback(code, state, error)

@app.get("/api/calendar/callback")
async def calendar_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Handle Google OAuth callback"""
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            # Return HTML page for better UX
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Calendar Authorization</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: red; }}
                </style>
            </head>
            <body>
                <h1 class="error">❌ Authorization Failed</h1>
                <p>{error}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=400)
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing authorization code or state")
        
        # Extract user_id from database using state
        result = supabase.table("push_notification_settings")\
            .select("id")\
            .eq("oauth_state", state)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Invalid or expired authorization state")
        
        # user_id from database is already BIGINT (int), but ensure it's int
        user_id = result.data[0]["id"]
        if not isinstance(user_id, int):
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid user_id from database: {user_id} (type: {type(user_id)})")
                raise HTTPException(status_code=500, detail="Invalid user ID format in database")
        
        # Exchange code for tokens
        success = calendar_service.handle_oauth_callback(user_id, code, state)
        
        if success:
            logger.info(f"Calendar authorized successfully for user {user_id}")
            # Return HTML page for better UX
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Calendar Authorization</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: green; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ Authorization Successful!</h1>
                <p>Google Calendar has been connected successfully.</p>
                <p>You can close this window now.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            logger.error(f"❌ OAuth callback failed for user {user_id}")
            logger.error(f"   Check backend logs for details")
            # Return HTML error page instead of JSON
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Calendar Authorization</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1 class="error">❌ Authorization Failed</h1>
                <p>Failed to complete authorization. Please check backend logs for details.</p>
                <p>You can close this window and try again.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=500)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Authorization callback failed: {str(e)}")

@app.post("/api/calendar/fetch/{user_id}")
async def fetch_calendar_data(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Fetch today's calendar events for user"""
    try:
        if not calendar_service:
            raise HTTPException(status_code=503, detail="Calendar service not available")
        
        calendar_data = calendar_service.fetch_today_events(user_id)
        
        if calendar_data:
            return JSONResponse({
                "status": "success",
                "data": calendar_data,
                "today": calendar_data.get('today', {}),
                "tomorrow": calendar_data.get('tomorrow', {})
            })
        else:
            return JSONResponse({
                "status": "no_data",
                "message": "No calendar data available. Please authorize Google Calendar."
            })
    
    except Exception as e:
        logger.error(f"Error fetching calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/calendar/check/{user_id}")
async def check_calendar_authorization(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Check if user has authorized Google Calendar access"""
    try:
        if not calendar_service:
            raise HTTPException(status_code=503, detail="Calendar service not available")
        
        # Convert user_id to int
        try:
            user_id_int = int(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {user_id}")
        
        # Check if user has authorized calendar
        result = supabase.table("push_notification_settings")\
            .select("calendar_authorized, google_refresh_token")\
            .eq("id", user_id_int)\
            .execute()
        
        if result.data and len(result.data) > 0:
            is_authorized = result.data[0].get("calendar_authorized", False)
            has_token = bool(result.data[0].get("google_refresh_token"))
            
            return JSONResponse({
                "status": "success",
                "authorized": is_authorized and has_token,
                "has_token": has_token
            })
        else:
            return JSONResponse({
                "status": "success",
                "authorized": False,
                "has_token": False
            })
    
    except Exception as e:
        logger.error(f"Error checking calendar authorization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/calendar/latest/{user_id}")
async def get_latest_calendar_data(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Get the most recent calendar data for user"""
    try:
        if not calendar_service:
            raise HTTPException(status_code=503, detail="Calendar service not available")
        
        calendar_data = calendar_service.get_latest_calendar_data(user_id)
        
        if calendar_data:
            return JSONResponse({
                "status": "success",
                "data": calendar_data
            })
        else:
            return JSONResponse({
                "status": "no_data",
                "message": "No calendar data found"
            })
    
    except Exception as e:
        logger.error(f"Error retrieving calendar data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# LOCATION TRACKING ENDPOINTS
# ============================================

@app.post("/api/location/track")
async def track_location(
    user_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    activity_type: str = Form(default=None),
    accuracy: float = Form(default=None),
    user_id_obj: dict = Depends(verify_token)
):
    """Track user's current location"""
    try:
        if not location_service:
            raise HTTPException(status_code=503, detail="Location service not available")
        
        success = location_service.track_location(
            user_id, latitude, longitude, activity_type, accuracy
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": "Location tracked successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to track location")
    
    except Exception as e:
        logger.error(f"Error tracking location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/location/save-place")
async def save_frequent_place(
    user_id: str = Form(...),
    location_type: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_name: str = Form(default=None),
    radius_meters: float = Form(default=100),
    user_id_obj: dict = Depends(verify_token)
):
    """Save a frequent location (home, office, etc.)"""
    try:
        # Log what we received
        logger.info(f"📍 Received save location request:")
        logger.info(f"  user_id: {user_id}")
        logger.info(f"  location_type: {location_type}")
        logger.info(f"  location_name: {location_name}")
        logger.info(f"  latitude: {latitude}")
        logger.info(f"  longitude: {longitude}")
        logger.info(f"  radius_meters: {radius_meters}")
        
        if not location_service:
            raise HTTPException(status_code=503, detail="Location service not available")
        
        success = location_service.save_frequent_location(
            user_id, location_type, latitude, longitude, location_name, radius_meters
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"{location_name or location_type.capitalize()} location saved"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save location")
    
    except Exception as e:
        logger.error(f"Error saving location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/location/analyze-day")
async def analyze_daily_location(
    user_id: str = Form(...),
    date: str = Form(default=None),
    user_id_obj: dict = Depends(verify_token)
):
    """Analyze location data for a specific day"""
    try:
        if not location_service:
            raise HTTPException(status_code=503, detail="Location service not available")
        
        from datetime import datetime
        target_date = datetime.fromisoformat(date).date() if date else None
        
        summary = location_service.analyze_daily_locations(user_id, target_date)
        
        if summary:
            # Save summary to database
            location_service.save_daily_summary(user_id, summary)
            
            return JSONResponse({
                "status": "success",
                "data": summary
            })
        else:
            return JSONResponse({
                "status": "no_data",
                "message": "No location data available for this day"
            })
    
    except Exception as e:
        logger.error(f"Error analyzing location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/location/summary/{user_id}")
async def get_location_summary(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Get latest daily location summary"""
    try:
        if not location_service:
            raise HTTPException(status_code=503, detail="Location service not available")
        
        summary = location_service.get_latest_summary(user_id)
        
        if summary:
            return JSONResponse({
                "status": "success",
                "data": summary
            })
        else:
            return JSONResponse({
                "status": "no_data",
                "message": "No location summary available"
            })
    
    except Exception as e:
        logger.error(f"Error retrieving location summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/location/saved/{user_id}")
async def get_saved_locations(
    user_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Get user's saved locations"""
    try:
        # Convert to int to match database type (BIGINT)
        user_id_int = int(user_id)
        
        result = supabase.table("saved_locations")\
            .select("*")\
            .eq("id", user_id_int)\
            .execute()
        
        logger.info(f"📍 Retrieved {len(result.data) if result.data else 0} saved locations for user {user_id_int}")
        
        return JSONResponse({
            "status": "success",
            "locations": result.data if result.data else []
        })
    
    except ValueError:
        logger.error(f"Invalid user_id format: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error(f"Error retrieving saved locations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/location/saved/{saved_location_id}")
async def delete_saved_location(
    saved_location_id: str,
    user_id_obj: dict = Depends(verify_token)
):
    """Delete a saved location"""
    try:
        # Get user_id from token (verify_token returns {"user_id": str(user_id), "id": str(user_id), "token": token})
        user_id_str = user_id_obj.get('user_id') or user_id_obj.get('id')
        if not user_id_str:
            logger.error(f"Token object missing user_id: {user_id_obj}")
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
        
        # Convert user_id to int (database stores id as BIGINT/int)
        try:
            user_id = int(user_id_str)
        except ValueError:
            logger.error(f"Invalid user_id format: {user_id_str} (type: {type(user_id_str)})")
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {user_id_str}")
        logger.info(f"🗑️ Deleting location: {saved_location_id} for user: {user_id} (type: {type(user_id).__name__})")
        
        # First verify the location exists and belongs to the user
        check_result = supabase.table("saved_locations")\
            .select("saved_location_id, id, location_name")\
            .eq("saved_location_id", saved_location_id)\
            .eq("id", user_id)\
            .execute()
        
        logger.info(f"🔍 Verification query result: {len(check_result.data) if check_result.data else 0} location(s) found")
        
        if not check_result.data:
            logger.warning(f"⚠️ Location {saved_location_id} not found or doesn't belong to user {user_id}")
            logger.warning(f"   Checking all locations for user {user_id}...")
            all_locs = supabase.table("saved_locations")\
                .select("saved_location_id, id, location_name")\
                .eq("id", user_id)\
                .execute()
            logger.warning(f"   User has {len(all_locs.data) if all_locs.data else 0} total locations")
            raise HTTPException(status_code=404, detail="Location not found or access denied")
        
        location_name = check_result.data[0].get('location_name', 'Unknown')
        logger.info(f"✓ Verified location '{location_name}' (ID: {saved_location_id}) belongs to user {user_id}")
        
        # Delete the location
        # Include both saved_location_id AND id to satisfy RLS policies
        # Supabase delete() returns APIResponse with deleted row(s) in result.data
        result = supabase.table("saved_locations")\
            .delete()\
            .eq("saved_location_id", saved_location_id)\
            .eq("id", user_id)\
            .execute()
        
        # Check if deletion was successful
        # Supabase returns deleted rows in result.data
        deleted_data = result.data if result.data else []
        deleted_count = len(deleted_data) if deleted_data else 0
        
        if deleted_count > 0:
            logger.info(f"✅ Location '{location_name}' deleted successfully (deleted {deleted_count} row(s))")
            return JSONResponse({
                "status": "success",
                "message": f"Location '{location_name}' deleted successfully"
            })
        else:
            # This shouldn't happen since we verified it exists
            logger.warning(f"⚠️ Delete returned no rows - location may have already been deleted")
            raise HTTPException(status_code=404, detail="Location not found or already deleted")
    
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"❌ Type conversion error: {str(ve)}")
        logger.error(f"   user_id_obj['id'] = {user_id_obj.get('id')} (type: {type(user_id_obj.get('id')).__name__})")
        raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(ve)}")
    except Exception as e:
        logger.error(f"❌ Error deleting location: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error args: {e.args if hasattr(e, 'args') else 'N/A'}")
        import traceback
        logger.error(f"   Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to delete location: {str(e)}")


# ============================================
# STRESS NOTIFICATION ENDPOINTS
# ============================================

@app.get("/api/check-stress/{user_id}")
async def check_user_stress(user_id: str):
    """Check stress level and get notification for a specific user"""
    try:
        from stress_notification_system import StressNotificationSystem
        
        logger.info(f"Checking stress level for user {user_id}")
        
        notification_system = StressNotificationSystem()
        result = notification_system.check_user_stress(user_id)
        
        return JSONResponse({
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking stress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stress check error: {str(e)}")

@app.get("/api/stress-notifications/all")
async def check_all_stress_levels():
    """Check stress levels for all users and send notifications"""
    try:
        from stress_notification_system import StressNotificationSystem
        
        logger.info("Checking stress levels for all users")
        
        notification_system = StressNotificationSystem()
        results = notification_system.check_all_users()
        
        return JSONResponse({
            "status": "success",
            "data": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking all stress levels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stress check error: {str(e)}")

@app.get("/api/stress-notifications/history/{user_id}")
async def get_notification_history(user_id: str, limit: int = 10):
    """Get notification history for a user"""
    try:
        logger.info(f"Fetching notification history for user {user_id}")
        
        result = supabase.table("notification_log")\
            .select("*")\
            .eq("id", user_id)\
            .order("sent_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return JSONResponse({
            "status": "success",
            "data": {
                "user_id": user_id,
                "notifications": result.data,
                "count": len(result.data)
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching notification history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"History fetch error: {str(e)}")

# ============================================
# INFO ENDPOINTS
# ============================================

@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "Wellness Activity Recommender API",
        "version": "2.0.0",
        "description": "AI-powered personalized activity suggestions using AWS Bedrock Claude",
        "endpoints": {
            "frontend": "/app - HTML/JS interface",
            "health": "/health - Health check",
            "profile": "POST /api/profile - Save user profile",
            "mood": "POST /api/mood - Submit mood entry",
            "text_analysis": "POST /api/analyze-text",
            "audio_analysis": "POST /api/analyze-audio",
            "photo_analysis": "POST /api/analyze-photo",
            "multimodal_analysis": "POST /api/analyze-multimodal",
            "update_report": "POST /api/update-report"
        },
        "models": {
            "preprocessor": "OpenAI Whisper (Audio Transcription + Emotion Detection)",
            "analyzer": "AWS Bedrock Claude 3.5 Sonnet",
            "model_id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        },
        "features": [
            "Text analysis",
            "Audio transcription and emotion detection",
            "Photo emotion detection",
            "Multimodal analysis",
            "User profile management",
            "Personalized recommendations",
            "Report generation"
        ]
    }

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    
    logger.info("🚀 Starting Wellness Activity Recommender API...")
    logger.info(f"📍 Frontend: https://health-monitor-tan.vercel.app/")
    logger.info(f"📍 API: https://health-monitor-tan.vercel.app/")
    logger.info(f"📍 Health: http://localhost:{port}/health")
    logger.info(f"📍 Info: http://localhost:{port}/api/info")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
