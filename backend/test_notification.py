import json
import os
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv

# -----------------------------------------------------
# 1. Load all environment variables from .env
# -----------------------------------------------------
load_dotenv()  # loads .env file automatically

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")

if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("❌ Missing FIREBASE_CREDENTIALS_JSON in .env")

# -----------------------------------------------------
# 2. Initialize Firebase Admin
# -----------------------------------------------------
cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
try:
    firebase_admin.get_app()
except:
    firebase_admin.initialize_app(cred)

# -----------------------------------------------------
# 3. Initialize Supabase client
# -----------------------------------------------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------------------
# 4. Function to send a test notification
# -----------------------------------------------------
def send_notification_to_user(user_id: int):
    print(f"\n🔍 Fetching FCM token for user {user_id}...")

    response = supabase.table("push_notification_settings") \
        .select("fcm_token, notifications_enabled") \
        .eq("id", user_id).execute()

    if not response.data:
        print("❌ No notification settings found for user.")
        return
    
    data = response.data[0]
    fcm_token = data.get("fcm_token")
    enabled = data.get("notifications_enabled")

    print(f"📌 notifications_enabled: {enabled}")
    print(f"📌 fcm_token: {fcm_token}")

    if not enabled:
        print("❌ User has notifications disabled.")
        return

    if not fcm_token:
        print("❌ FCM token is empty or missing.")
        return

    # -------------------------------------------------
    # Build the test notification
    # -------------------------------------------------
    message = messaging.Message(
        notification=messaging.Notification(
            title="Test Notification",
            body="This is a test message from your backend",
        ),
        token=fcm_token,
    )

    print("\n📨 Sending notification...")

    try:
        result = messaging.send(message)
        print(f"✅ Notification sent successfully! Message ID: {result}")
    except Exception as e:
        print("\n❌ FAILED to send notification!")
        print("📌 Error details:")
        print(e)


# -----------------------------------------------------
# 5. Run test for your user
# -----------------------------------------------------
send_notification_to_user(7890)
