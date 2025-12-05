"""
Push Notification Service
Sends and manages push notifications for mood tracking
"""

import os
from datetime import datetime, time
from typing import Dict, List, Optional
import json

from firebase_admin import credentials, initialize_app, messaging
import firebase_admin

from supabase import Client


class PushNotificationService:
    """Service for managing push notifications via Firebase Cloud Messaging"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.firebase_initialized = False
        
        # Initialize Firebase Admin SDK
        try:
            firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            
            if firebase_credentials_json:
                # Parse JSON string from environment variable
                cred_dict = json.loads(firebase_credentials_json)
                cred = credentials.Certificate(cred_dict)
            elif firebase_credentials_path:
                cred = credentials.Certificate(firebase_credentials_path)
            else:
                print("⚠️ Firebase credentials not configured")
                return
            
            # Check if already initialized
            if not firebase_admin._apps:
                initialize_app(cred)
            
            self.firebase_initialized = True
            print("✓ Firebase Admin SDK initialized")
            
        except Exception as e:
            print(f"⚠️ Firebase initialization failed: {str(e)}")
            self.firebase_initialized = False
    
    def register_device(self, user_id: str, fcm_token: str) -> bool:
        """Register a user's device token for push notifications"""
        try:
            # Convert user_id to int if it's a string
            user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
            
            # Use upsert with on_conflict to handle both insert and update atomically
            self.supabase.table("push_notification_settings")\
                .upsert({
                    "id": user_id_int,
                    "fcm_token": fcm_token,
                    "notifications_enabled": True
                }, on_conflict="id")\
                .execute()
            
            print(f"✅ Device registered/updated for user {user_id_int}")
            return True
            
        except Exception as e:
            print(f"❌ Error registering device: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_morning_notification(self, user_id: str) -> Optional[str]:
        """Send morning mood check notification"""
        notification = {
            'title': '☀️ Good morning!',
            'body': 'How are you feeling today?',
            'data': {
                'type': 'morning_mood_check',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Actions for user to tap
        actions = [
            {'id': 'energized', 'title': '💪 Energized'},
            {'id': 'tired', 'title': '😴 Tired'},
            {'id': 'neutral', 'title': '😐 Neutral'},
            {'id': 'stressed', 'title': '😰 Stressed'}
        ]
        
        notification['data']['actions'] = json.dumps(actions)
        
        return self.send_notification(user_id, notification)
    
    def send_evening_notification(self, user_id: str) -> Optional[str]:
        """Send evening mood check notification"""
        notification = {
            'title': '🌙 How was your day?',
            'body': 'Take a moment to reflect',
            'data': {
                'type': 'evening_mood_check',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Actions for user to tap
        actions = [
            {'id': 'great', 'title': '😊 Great day!'},
            {'id': 'okay', 'title': '😌 It was okay'},
            {'id': 'difficult', 'title': '😔 Difficult'},
            {'id': 'exhausted', 'title': '😫 Exhausted'}
        ]
        
        notification['data']['actions'] = json.dumps(actions)
        
        return self.send_notification(user_id, notification)
    
    def send_notification(self, user_id: str, notification_data: Dict) -> Optional[str]:
        """Send a push notification to a specific user"""
        if not self.firebase_initialized:
            print("Firebase not initialized, cannot send notification")
            return None
        
        try:
            # Get user's FCM token
            result = self.supabase.table("push_notification_settings")\
                .select("fcm_token, notifications_enabled")\
                .eq("id", user_id)\
                .execute()
            
            if not result.data or not result.data[0].get("fcm_token"):
                print(f"No FCM token found for user {user_id}")
                return None
            
            if not result.data[0].get("notifications_enabled", True):
                print(f"Notifications disabled for user {user_id}")
                return None
            
            fcm_token = result.data[0]["fcm_token"]
            
            # Create FCM message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=notification_data.get('title', ''),
                    body=notification_data.get('body', '')
                ),
                data=notification_data.get('data', {}),
                token=fcm_token
            )
            
            # Send message
            response = messaging.send(message)
            print(f"Notification sent to user {user_id}: {response}")
            
            # Log notification
            self.log_notification(user_id, notification_data, response)
            
            return response
            
        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            return None
    
    def log_notification(self, user_id: str, notification_data: Dict, response: str):
        """Log sent notification to database"""
        try:
            self.supabase.table("notification_log").insert({
                "id": user_id,
                "notification_type": notification_data.get('data', {}).get('type', 'unknown'),
                "title": notification_data.get('title', ''),
                "body": notification_data.get('body', ''),
                "response_id": response,
                "sent_at": datetime.now().isoformat()
            }).execute()
            
        except Exception as e:
            print(f"Error logging notification: {str(e)}")
    
    def save_notification_response(self, user_id: str, notification_type: str, 
                                   emotion_response: str, additional_notes: str = None) -> bool:
        """Save user's response to a push notification"""
        try:
            self.supabase.table("push_notification_responses").insert({
                "id": user_id,
                "notification_type": notification_type,
                "emotion_response": emotion_response,
                "additional_notes": additional_notes,
                "timestamp": datetime.now().isoformat()
            }).execute()
            
            print(f"Notification response saved for user {user_id}")
            
            # Update report with emotion data
            self.update_report_emotions(user_id, notification_type, emotion_response)
            
            return True
            
        except Exception as e:
            print(f"Error saving notification response: {str(e)}")
            return False
    
    def update_report_emotions(self, user_id: str, notification_type: str, emotion: str):
        """Update report table with morning/evening emotions"""
        try:
            column = "morning_emotion" if notification_type == "morning_mood_check" else "evening_emotion"
            
            self.supabase.table("report").update({
                column: emotion
            }).eq("id", user_id).execute()
            
        except Exception as e:
            print(f"Error updating report emotions: {str(e)}")
    
    def get_latest_responses(self, user_id: str, limit: int = 7) -> List[Dict]:
        """Get user's recent notification responses"""
        try:
            result = self.supabase.table("push_notification_responses")\
                .select("*")\
                .eq("id", user_id)\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error retrieving responses: {str(e)}")
            return []
    
    def send_bulk_notifications(self, notification_type: str = "morning") -> Dict:
        """Send notifications to all users with notifications enabled"""
        if not self.firebase_initialized:
            return {"status": "error", "message": "Firebase not initialized"}
        
        try:
            # Get all users with notifications enabled
            result = self.supabase.table("push_notification_settings")\
                .select("id, fcm_token")\
                .eq("notifications_enabled", True)\
                .not_.is_("fcm_token", "null")\
                .execute()
            
            if not result.data:
                return {"status": "success", "sent": 0, "message": "No users to notify"}
            
            sent_count = 0
            failed_count = 0
            
            for user_setting in result.data:
                user_id = user_setting["id"]
                
                if notification_type == "morning":
                    response = self.send_morning_notification(user_id)
                else:
                    response = self.send_evening_notification(user_id)
                
                if response:
                    sent_count += 1
                else:
                    failed_count += 1
            
            return {
                "status": "success",
                "sent": sent_count,
                "failed": failed_count,
                "total": len(result.data)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def toggle_notifications(self, user_id: str, enabled: bool) -> bool:
        """Enable or disable notifications for a user"""
        try:
            self.supabase.table("push_notification_settings")\
                .update({"notifications_enabled": enabled})\
                .eq("id", user_id)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error toggling notifications: {str(e)}")
            return False
    
    def update_notification_times(self, user_id: str, 
                                  morning_time: time = None, 
                                  evening_time: time = None) -> bool:
        """Update preferred notification times for a user"""
        try:
            updates = {}
            if morning_time:
                updates["morning_notification_time"] = morning_time.isoformat()
            if evening_time:
                updates["evening_notification_time"] = evening_time.isoformat()
            
            if updates:
                self.supabase.table("push_notification_settings")\
                    .update(updates)\
                    .eq("id", user_id)\
                    .execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating notification times: {str(e)}")
            return False

