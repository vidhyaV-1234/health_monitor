"""
Mood Notification Scheduler
Sends morning and evening mood check notifications to all users

Morning: 7:00 AM
Evening: 7:00 PM (19:00)

Run this script using:
1. Manual: python mood_notification_scheduler.py
2. As part of combined scheduler: run_schedulers.py
"""
import os
import time
import schedule
from datetime import datetime
import logging
from dotenv import load_dotenv
from supabase import create_client
from push_notification_service import PushNotificationService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mood_notifications.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
notification_service = PushNotificationService(supabase)

def send_morning_notifications():
    """Send morning mood check notifications to all users"""
    logger.info("="*70)
    logger.info("SENDING MORNING MOOD NOTIFICATIONS")
    logger.info("="*70)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get all users with notifications enabled
        result = supabase.table("push_notification_settings")\
            .select("id, fcm_token")\
            .eq("notifications_enabled", True)\
            .not_.is_("fcm_token", "null")\
            .execute()
        
        if not result.data:
            logger.info("No users with notifications enabled")
            logger.info("="*70 + "\n")
            return
        
        total_users = len(result.data)
        sent_count = 0
        failed_count = 0
        
        logger.info(f"Found {total_users} user(s) with notifications enabled")
        logger.info("Sending morning notifications...\n")
        
        for user_record in result.data:
            user_id = str(user_record.get("id"))
            if not user_id:
                continue
            
            try:
                logger.info(f"☀️ Sending morning notification to user {user_id}...")
                response = notification_service.send_morning_notification(user_id)
                
                if response:
                    logger.info(f"✅ Morning notification sent to user {user_id}")
                    sent_count += 1
                else:
                    logger.warning(f"⚠️ Failed to send to user {user_id}")
                    failed_count += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error sending to user {user_id}: {str(user_error)}")
                failed_count += 1
        
        logger.info("\n" + "="*70)
        logger.info("MORNING NOTIFICATIONS SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Sent: {sent_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during morning notifications: {str(e)}")
        import traceback
        traceback.print_exc()

def send_evening_notifications():
    """Send evening mood check notifications to all users"""
    logger.info("="*70)
    logger.info("SENDING EVENING MOOD NOTIFICATIONS")
    logger.info("="*70)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get all users with notifications enabled
        result = supabase.table("push_notification_settings")\
            .select("id, fcm_token")\
            .eq("notifications_enabled", True)\
            .not_.is_("fcm_token", "null")\
            .execute()
        
        if not result.data:
            logger.info("No users with notifications enabled")
            logger.info("="*70 + "\n")
            return
        
        total_users = len(result.data)
        sent_count = 0
        failed_count = 0
        
        logger.info(f"Found {total_users} user(s) with notifications enabled")
        logger.info("Sending evening notifications...\n")
        
        for user_record in result.data:
            user_id = str(user_record.get("id"))
            if not user_id:
                continue
            
            try:
                logger.info(f"🌙 Sending evening notification to user {user_id}...")
                response = notification_service.send_evening_notification(user_id)
                
                if response:
                    logger.info(f"✅ Evening notification sent to user {user_id}")
                    sent_count += 1
                else:
                    logger.warning(f"⚠️ Failed to send to user {user_id}")
                    failed_count += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error sending to user {user_id}: {str(user_error)}")
                failed_count += 1
        
        logger.info("\n" + "="*70)
        logger.info("EVENING NOTIFICATIONS SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Sent: {sent_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during evening notifications: {str(e)}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    """Run the notification scheduler"""
    logger.info("="*70)
    logger.info("MOOD NOTIFICATION SCHEDULER STARTED")
    logger.info("="*70)
    logger.info("Scheduled times:")
    logger.info("  ☀️ Morning: 5:35 PM (17:35) - for testing")
    logger.info("  🌙 Evening: 5:35 PM (17:35) - for testing")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Schedule morning notifications at 5:35 PM (for testing)
    schedule.every().day.at("17:35").do(send_morning_notifications)
    
    # Schedule evening notifications at 5:35 PM (for testing)
    # In production, change evening to "19:00" (7 PM)
    schedule.every().day.at("17:35").do(send_evening_notifications)
    
    # Run immediately for testing if current time is close to scheduled time
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    # If it's close to 5:35 PM (within 5 minutes), run immediately
    if current_hour == 17 and 30 <= current_minute <= 40:
        logger.info("⏰ Current time is close to 5:35 PM, running notifications immediately...\n")
        send_morning_notifications()
        send_evening_notifications()
    
    logger.info("Waiting for scheduled times...")
    logger.info("Press Ctrl+C to stop\n")
    
    # Log all scheduled jobs
    logger.info("📋 Scheduled jobs:")
    for job in schedule.jobs:
        logger.info(f"   - {job}")
    logger.info("")
    
    # Keep running
    while True:
        # Check current time and next run times
        now = datetime.now()
        
        # Run pending jobs
        schedule.run_pending()
        
        # Log next run times every 5 minutes
        if now.minute % 5 == 0 and now.second < 10:
            logger.info(f"⏰ Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            for job in schedule.jobs:
                next_run = job.next_run
                if next_run:
                    logger.info(f"   Next run: {job} at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        time.sleep(60)  # Check every minute if a job needs to run

if __name__ == "__main__":
    print("\n" + "="*70)
    print("MOOD NOTIFICATION SCHEDULER")
    print("="*70)
    print("\nOptions:")
    print("1. Send morning notifications now")
    print("2. Send evening notifications now")
    print("3. Run both now")
    print("4. Run continuous scheduler (daily at 5:35 PM)")
    print("="*70)
    
    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nEnter choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        print("\nSending morning notifications...\n")
        send_morning_notifications()
    elif choice == "2":
        print("\nSending evening notifications...\n")
        send_evening_notifications()
    elif choice == "3":
        print("\nSending both notifications...\n")
        send_morning_notifications()
        send_evening_notifications()
    elif choice == "4":
        print("\nStarting continuous scheduler...")
        print("Notifications will be sent daily at 7:00 PM (19:00)")
        print("\n⚠️  IMPORTANT: The scheduler must be running at 7:00 PM for notifications to send!")
        print("   If you start it after 7:00 PM, notifications will send tomorrow at 7:00 PM.")
        print("\nPress Ctrl+C to stop\n")
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    else:
        print("\nInvalid choice. Sending both notifications...\n")
        send_morning_notifications()
        send_evening_notifications()

