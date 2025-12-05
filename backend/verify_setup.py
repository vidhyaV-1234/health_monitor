"""
Comprehensive Setup Verification Script
Checks all requirements for notifications to work properly
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client

print("\n" + "="*70)
print("🔍 COMPREHENSIVE SETUP VERIFICATION")
print("="*70)

# Load environment variables
load_dotenv()

all_checks_passed = True

# 1. Check Firebase Credentials
print("\n1️⃣  FIREBASE CREDENTIALS")
print("-" * 70)
firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if not firebase_json:
    print("❌ FIREBASE_CREDENTIALS_JSON not found in .env file!")
    all_checks_passed = False
else:
    print(f"✅ Environment variable found ({len(firebase_json)} chars)")
    
    try:
        cred_dict = json.loads(firebase_json)
        print("✅ Valid JSON format")
        
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing = [f for f in required_fields if f not in cred_dict]
        
        if missing:
            print(f"❌ Missing fields: {', '.join(missing)}")
            all_checks_passed = False
        else:
            print(f"✅ All required fields present")
            print(f"   Project: {cred_dict.get('project_id')}")
            print(f"   Email: {cred_dict.get('client_email')}")
            
            # Test Firebase initialization
            try:
                from firebase_admin import credentials, initialize_app
                import firebase_admin
                
                # Clean up existing
                if firebase_admin._apps:
                    for app in firebase_admin._apps.values():
                        firebase_admin.delete_app(app)
                
                cred = credentials.Certificate(cred_dict)
                initialize_app(cred)
                print("✅ Firebase Admin SDK initialized successfully!")
                
            except Exception as e:
                print(f"❌ Firebase initialization failed: {e}")
                all_checks_passed = False
                
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        print("\nThe JSON must be on ONE line in .env:")
        print('FIREBASE_CREDENTIALS_JSON=\'{"type":"service_account",...}\'')
        all_checks_passed = False

# 2. Check Supabase Connection
print("\n2️⃣  SUPABASE CONNECTION")
print("-" * 70)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("❌ SUPABASE_URL or SUPABASE_KEY missing!")
    all_checks_passed = False
else:
    print("✅ Supabase credentials found")
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Test connection by checking users table
        result = supabase.table("users").select("id").limit(1).execute()
        print("✅ Successfully connected to Supabase")
        
        # Check push_notification_settings table
        result = supabase.table("push_notification_settings").select("id, notifications_enabled").limit(1).execute()
        print("✅ push_notification_settings table exists")
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        all_checks_passed = False

# 3. Check User Has Registered Device
print("\n3️⃣  USER DEVICE REGISTRATION")
print("-" * 70)
try:
    supabase = create_client(supabase_url, supabase_key)
    result = supabase.table("push_notification_settings")\
        .select("id, fcm_token, notifications_enabled")\
        .eq("notifications_enabled", True)\
        .execute()
    
    if result.data and len(result.data) > 0:
        print(f"✅ {len(result.data)} user(s) registered for notifications:")
        for user in result.data:
            token_preview = user.get('fcm_token', '')[:20] + "..." if user.get('fcm_token') else "None"
            print(f"   • User ID: {user.get('id')}, Token: {token_preview}")
    else:
        print("⚠️  No users have registered for notifications yet")
        print("   → Go to the frontend and click 'Enable Notifications'")
        all_checks_passed = False
        
except Exception as e:
    print(f"❌ Failed to check registrations: {e}")
    all_checks_passed = False

# 4. Check Scheduler Files
print("\n4️⃣  SCHEDULER FILES")
print("-" * 70)
scheduler_files = [
    "run_schedulers.py",
    "mood_notification_scheduler.py",
    "calendar_scheduler.py",
    "location_scheduler.py"
]

for filename in scheduler_files:
    if os.path.exists(filename):
        print(f"✅ {filename} exists")
    else:
        print(f"❌ {filename} missing!")
        all_checks_passed = False

# 5. Check Schedule Times
print("\n5️⃣  SCHEDULED TIMES")
print("-" * 70)
print("📅 Calendar fetch: 5:55 PM (17:55)")
print("📍 Location summary: 5:55 PM (17:55)")
print("🔔 Mood notifications: 5:55 PM (17:55)")
print("\n⚠️  All tasks run at the SAME time for testing")

# Final Summary
print("\n" + "="*70)
if all_checks_passed:
    print("✅ ALL CHECKS PASSED!")
    print("="*70)
    print("\n📋 NEXT STEPS:")
    print("\n1. Fix Firebase credentials in .env (if needed)")
    print("   → Use single-line JSON format")
    print("\n2. Test notification registration:")
    print("   → Go to frontend: https://health-monitor-tan.vercel.app")
    print("   → Login and enable notifications")
    print("\n3. Update Render environment variables:")
    print("   → Set FIREBASE_CREDENTIALS_JSON on Render")
    print("   → Use the same single-line JSON")
    print("\n4. Create Render Background Worker:")
    print("   → Name: health-monitor-scheduler")
    print("   → Start command: cd health_monitor/backend && python run_schedulers.py 2")
    print("   → Copy ALL env vars from web service")
    print("\n5. Test locally (before 5:55 PM):")
    print("   → cd health_monitor/backend")
    print("   → python run_schedulers.py 3")
    print("   → This runs tasks immediately + starts scheduler")
    print("\n6. At 5:55 PM:")
    print("   → Check logs for notification sends")
    print("   → Check your device for push notifications")
else:
    print("❌ SOME CHECKS FAILED!")
    print("="*70)
    print("\nPlease fix the issues above before proceeding.")

print("\n" + "="*70 + "\n")

