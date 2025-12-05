"""
Calendar Data Scheduler
Automatically fetches calendar data for all authorized users daily

Run this script using:
1. Manual: python calendar_scheduler.py
2. Cron job (Linux/Mac): Daily at 6 AM
   Example crontab entry:
   0 6 * * * cd /path/to/backend && python calendar_scheduler.py
3. Windows Task Scheduler: Daily at 6 AM
4. As a background service
"""
import os
import time
import schedule
from datetime import datetime
import logging
from dotenv import load_dotenv
from supabase import create_client
from google_calendar_service import GoogleCalendarService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('calendar_scheduler.log'),
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
calendar_service = GoogleCalendarService(supabase)

def fetch_calendar_for_all_users():
    """Fetch today's calendar data for all users with authorized calendar access"""
    logger.info("="*70)
    logger.info("RUNNING SCHEDULED CALENDAR DATA FETCH")
    logger.info("="*70)
    
    try:
        # Get all users with calendar authorization
        result = supabase.table("push_notification_settings")\
            .select("id, calendar_authorized, google_refresh_token")\
            .eq("calendar_authorized", True)\
            .not_.is_("google_refresh_token", "null")\
            .execute()
        
        if not result.data:
            logger.info("No users with authorized calendar access found")
            logger.info("="*70 + "\n")
            return
        
        total_users = len(result.data)
        successful_fetches = 0
        failed_fetches = 0
        
        logger.info(f"Found {total_users} user(s) with calendar authorization")
        logger.info("Starting calendar data fetch...\n")
        
        for user_record in result.data:
            user_id = user_record.get("id")
            if not user_id:
                continue
            
            try:
                logger.info(f"📅 Fetching calendar (today + tomorrow) for user {user_id}...")
                calendar_data = calendar_service.fetch_today_events(str(user_id))
                
                if calendar_data:
                    today_meetings = calendar_data.get('meeting_count', 0)
                    today_hours = calendar_data.get('meeting_hours', 0)
                    tomorrow_meetings = calendar_data.get('tomorrow_meeting_count', 0)
                    tomorrow_hours = calendar_data.get('tomorrow_meeting_hours', 0)
                    logger.info(f"✅ Successfully fetched calendar for user {user_id}")
                    logger.info(f"   Today - Meetings: {today_meetings}, Hours: {today_hours}")
                    logger.info(f"   Tomorrow - Meetings: {tomorrow_meetings}, Hours: {tomorrow_hours}")
                    successful_fetches += 1
                else:
                    logger.warning(f"⚠️ No calendar data returned for user {user_id}")
                    failed_fetches += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error fetching calendar for user {user_id}: {str(user_error)}")
                failed_fetches += 1
        
        logger.info("\n" + "="*70)
        logger.info("SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Successful: {successful_fetches}")
        logger.info(f"  Failed: {failed_fetches}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during scheduled calendar fetch: {str(e)}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    """Run the scheduler"""
    logger.info("📅 Calendar Data Scheduler Started")
    logger.info("Fetching calendar data daily at 7:00 PM (19:00)")
    
    # Schedule daily fetch at 7:00 PM
    schedule.every().day.at("19:00").do(fetch_calendar_for_all_users)
    
    logger.info("Scheduled time:")
    logger.info("  - 3:45 PM (15:45)")
    logger.info("\nWaiting for scheduled time...")
    logger.info("(Current time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if a job needs to run

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CALENDAR DATA SCHEDULER")
    print("="*70)
    print("\nOptions:")
    print("1. Run one-time fetch (fetch now for all users)")
    print("2. Run continuous scheduler (daily at 6 AM and 7 AM)")
    print("="*70)
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nRunning one-time calendar fetch...\n")
        fetch_calendar_for_all_users()
    elif choice == "2":
        print("\nStarting continuous scheduler...")
        print("Calendar data will be fetched daily at 6:00 AM and 7:00 AM")
        print("Press Ctrl+C to stop\n")
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    else:
        print("\nInvalid choice. Running one-time fetch...\n")
        fetch_calendar_for_all_users()

