#!/usr/bin/env python3
"""
FCM Token Debug Script
Helps debug and fix FCM token registration issues
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from push_notification_service import PushNotificationService

def debug_fcm_setup():
    """Debug FCM token setup and registration"""
    print("="*70)
    print("FCM TOKEN DEBUG & TESTING")
    print("="*70)
    
    # Initialize Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connection established")
        
        # Initialize notification service
        notification_service = PushNotificationService(supabase)
        print(f"✅ Push Notification Service initialized")
        print(f"   Firebase initialized: {notification_service.firebase_initialized}")
        
        # Check Firebase credentials
        print("\n1. Checking Firebase Configuration...")
        print("-" * 50)
        
        firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        
        if firebase_creds_json:
            print("✅ FIREBASE_CREDENTIALS_JSON found in environment")
            print(f"   Length: {len(firebase_creds_json)} characters")
        elif firebase_creds_path:
            print(f"✅ FIREBASE_CREDENTIALS_PATH: {firebase_creds_path}")
            if os.path.exists(firebase_creds_path):
                print("✅ Firebase credentials file exists")
            else:
                print("❌ Firebase credentials file not found")
        else:
            print("❌ No Firebase credentials configured")
            print("   Set either FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON")
            return False
        
        # Check push_notification_settings table
        print("\n2. Checking Supabase Table Structure...")
        print("-" * 50)
        
        try:
            # Try to query the table to see if it exists
            result = supabase.table("push_notification_settings").select("*").limit(1).execute()
            print("✅ push_notification_settings table exists")
            print(f"   Sample query successful")
        except Exception as table_error:
            print(f"❌ push_notification_settings table issue: {str(table_error)}")
            print("\n   Creating table structure...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS push_notification_settings (
                id INTEGER PRIMARY KEY,
                fcm_token TEXT,
                notifications_enabled BOOLEAN DEFAULT TRUE,
                calendar_authorized BOOLEAN DEFAULT FALSE,
                google_refresh_token TEXT,
                morning_notification_time TIME DEFAULT '07:00:00',
                evening_notification_time TIME DEFAULT '19:00:00',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            print(f"   SQL to run in Supabase:\n{create_table_sql}")
        
        # Check existing FCM tokens
        print("\n3. Checking Existing FCM Tokens...")
        print("-" * 50)
        
        try:
            result = supabase.table("push_notification_settings")\
                .select("id, fcm_token, notifications_enabled")\
                .not_.is_("fcm_token", "null")\
                .execute()
            
            if result.data:
                print(f"✅ Found {len(result.data)} users with FCM tokens:")
                for user in result.data:
                    token_preview = user['fcm_token'][:20] + "..." if user['fcm_token'] else "None"
                    enabled = user.get('notifications_enabled', False)
                    print(f"   User {user['id']}: {token_preview} (enabled: {enabled})")
            else:
                print("⚠️ No users with FCM tokens found")
                print("   This might be why notifications aren't working")
        except Exception as e:
            print(f"❌ Error checking FCM tokens: {str(e)}")
        
        # Test FCM token registration
        print("\n4. Testing FCM Token Registration...")
        print("-" * 50)
        
        test_user_id = input("Enter user ID to test FCM registration (or press Enter to skip): ").strip()
        
        if test_user_id:
            # Generate a test FCM token (this would normally come from the frontend)
            test_fcm_token = f"test_fcm_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"Testing with user ID: {test_user_id}")
            print(f"Test FCM token: {test_fcm_token}")
            
            success = notification_service.register_device(test_user_id, test_fcm_token)
            
            if success:
                print("✅ FCM token registration successful")
                
                # Verify it was saved
                verify_result = supabase.table("push_notification_settings")\
                    .select("fcm_token, notifications_enabled")\
                    .eq("id", test_user_id)\
                    .execute()
                
                if verify_result.data:
                    saved_token = verify_result.data[0]['fcm_token']
                    enabled = verify_result.data[0]['notifications_enabled']
                    print(f"✅ Verification: Token saved correctly")
                    print(f"   Saved token: {saved_token}")
                    print(f"   Notifications enabled: {enabled}")
                else:
                    print("❌ Verification failed: Token not found in database")
            else:
                print("❌ FCM token registration failed")
        
        # Test notification sending (if we have tokens)
        print("\n5. Testing Notification Sending...")
        print("-" * 50)
        
        if notification_service.firebase_initialized:
            print("✅ Firebase is initialized, ready to send notifications")
            
            # Get users with FCM tokens for testing
            result = supabase.table("push_notification_settings")\
                .select("id, fcm_token")\
                .eq("notifications_enabled", True)\
                .not_.is_("fcm_token", "null")\
                .limit(1)\
                .execute()
            
            if result.data:
                test_user = result.data[0]
                test_user_id = str(test_user['id'])
                
                send_test = input(f"Send test notification to user {test_user_id}? (y/N): ").strip().lower()
                
                if send_test in ['y', 'yes']:
                    print(f"Sending test notification to user {test_user_id}...")
                    
                    test_notification = {
                        'title': '🧪 FCM Test Notification',
                        'body': 'This is a test notification to verify FCM is working correctly.',
                        'data': {
                            'type': 'fcm_test',
                            'user_id': test_user_id,
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    
                    response = notification_service.send_notification(test_user_id, test_notification)
                    
                    if response:
                        print(f"✅ Test notification sent successfully!")
                        print(f"   Response ID: {response}")
                    else:
                        print("❌ Test notification failed")
            else:
                print("⚠️ No users with FCM tokens available for testing")
        else:
            print("❌ Firebase not initialized, cannot send notifications")
        
        print("\n" + "="*70)
        print("FCM DEBUG COMPLETE")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_fcm_integration_guide():
    """Show guide for proper FCM integration"""
    print("\n" + "="*70)
    print("FCM INTEGRATION GUIDE")
    print("="*70)
    
    print("""
📱 FRONTEND FCM TOKEN GENERATION:

1. In your frontend (React/Vue/etc), add Firebase SDK:
   npm install firebase

2. Initialize Firebase in your frontend:
   ```javascript
   import { initializeApp } from 'firebase/app';
   import { getMessaging, getToken } from 'firebase/messaging';
   
   const firebaseConfig = {
     // Your Firebase config
   };
   
   const app = initializeApp(firebaseConfig);
   const messaging = getMessaging(app);
   ```

3. Request FCM token:
   ```javascript
   async function getFCMToken() {
     try {
       const token = await getToken(messaging, {
         vapidKey: 'YOUR_VAPID_KEY'
       });
       
       if (token) {
         console.log('FCM Token:', token);
         // Send this token to your backend
         await registerFCMToken(userId, token);
       }
     } catch (error) {
       console.error('Error getting FCM token:', error);
     }
   }
   ```

4. Register token with backend:
   ```javascript
   async function registerFCMToken(userId, fcmToken) {
     const formData = new FormData();
     formData.append('user_id', userId);
     formData.append('fcm_token', fcmToken);
     
     const response = await fetch('/api/notifications/register', {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${jwtToken}`
       },
       body: formData
     });
     
     if (response.ok) {
       console.log('FCM token registered successfully');
     }
   }
   ```

🔧 BACKEND REQUIREMENTS:

1. Firebase Admin SDK credentials in environment:
   FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
   
2. Supabase table structure:
   - Table: push_notification_settings
   - Columns: id, fcm_token, notifications_enabled
   
3. Test the registration endpoint:
   POST /api/notifications/register
   - user_id: string
   - fcm_token: string
   - Authorization: Bearer <jwt_token>

📋 TROUBLESHOOTING CHECKLIST:

□ Firebase project created with FCM enabled
□ Service account key generated and configured
□ Frontend generates FCM tokens correctly
□ Backend receives and saves FCM tokens
□ push_notification_settings table exists in Supabase
□ Users have notifications_enabled = true
□ Firebase Admin SDK initialized without errors
□ Test notifications work before activity recommendations
""")

if __name__ == "__main__":
    print("\n🔍 FCM TOKEN DEBUGGING TOOL")
    print("="*70)
    
    # Run debug
    success = debug_fcm_setup()
    
    if not success:
        show_fcm_integration_guide()
    
    print("\n🏁 Debug complete!")
    print("\nNext steps:")
    print("1. Fix any issues identified above")
    print("2. Test FCM token registration from frontend")
    print("3. Verify notifications work before testing activity recommendations")