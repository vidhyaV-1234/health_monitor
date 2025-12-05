"""
Combined Scheduler Runner
Runs both calendar and location schedulers together

Usage:
  python run_schedulers.py

This will run both schedulers in the same process:
- Calendar data fetch: 3:45 PM (15:45)
- Location data analysis: 3:45 PM (15:45)
"""
import os
import time
import schedule
from datetime import datetime
import logging
from dotenv import load_dotenv
from supabase import create_client
from google_calendar_service import GoogleCalendarService
from location_tracking_service import LocationTrackingService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('schedulers.log'),
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
location_service = LocationTrackingService(supabase)

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
                user_id_str = str(user_id)
                logger.info(f"📅 Fetching calendar (today + tomorrow) for user {user_id_str}...")
                calendar_data = calendar_service.fetch_today_events(user_id_str)
                
                if calendar_data:
                    today_meetings = calendar_data.get('meeting_count', 0)
                    today_hours = calendar_data.get('meeting_hours', 0)
                    tomorrow_meetings = calendar_data.get('tomorrow_meeting_count', 0)
                    tomorrow_hours = calendar_data.get('tomorrow_meeting_hours', 0)
                    logger.info(f"✅ Successfully fetched calendar for user {user_id_str}")
                    logger.info(f"   Today - Meetings: {today_meetings}, Hours: {today_hours}")
                    logger.info(f"   Tomorrow - Meetings: {tomorrow_meetings}, Hours: {tomorrow_hours}")
                    logger.info(f"   ✅ Calendar data should be saved to Supabase")
                    successful_fetches += 1
                else:
                    logger.warning(f"⚠️ No calendar data returned for user {user_id_str}")
                    failed_fetches += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error fetching calendar for user {user_id}: {str(user_error)}")
                import traceback
                traceback.print_exc()
                failed_fetches += 1
        
        logger.info("\n" + "="*70)
        logger.info("CALENDAR FETCH SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Successful: {successful_fetches}")
        logger.info(f"  Failed: {failed_fetches}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during scheduled calendar fetch: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_locations_for_all_users():
    """Analyze location data for all users who have location tracking enabled"""
    logger.info("="*70)
    logger.info("RUNNING SCHEDULED LOCATION DATA ANALYSIS")
    logger.info("="*70)
    
    try:
        from datetime import date
        today = date.today().isoformat()
        
        # Get users who have location data today
        result = supabase.table("location_tracking")\
            .select("id")\
            .gte("timestamp", f"{today}T00:00:00")\
            .execute()
        
        if not result.data:
            logger.info("No users with location data found today")
            logger.info("="*70 + "\n")
            return
        
        # Get unique user IDs
        user_ids = list(set([record.get("id") for record in result.data if record.get("id")]))
        
        if not user_ids:
            logger.info("No valid user IDs found")
            logger.info("="*70 + "\n")
            return
        
        total_users = len(user_ids)
        successful_analyses = 0
        failed_analyses = 0
        
        logger.info(f"Found {total_users} user(s) with location data today")
        logger.info("Starting location analysis...\n")
        
        for user_id in user_ids:
            try:
                # Ensure user_id is converted to string for the service
                user_id_str = str(user_id)
                logger.info(f"📍 Analyzing locations for user {user_id_str}...")
                
                summary = location_service.analyze_daily_locations(user_id_str)
                
                if summary:
                    save_result = location_service.save_daily_summary(user_id_str, summary)
                    if save_result:
                        logger.info(f"✅ Successfully analyzed and saved locations for user {user_id_str}")
                        logger.info(f"   Left home: {summary.get('left_home_time', 'N/A')}")
                        logger.info(f"   Returned home: {summary.get('returned_home_time', 'N/A')}")
                        successful_analyses += 1
                    else:
                        logger.error(f"❌ Failed to save location summary for user {user_id_str}")
                        failed_analyses += 1
                else:
                    logger.warning(f"⚠️ No location summary generated for user {user_id_str}")
                    failed_analyses += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error analyzing locations for user {user_id}: {str(user_error)}")
                import traceback
                traceback.print_exc()
                failed_analyses += 1
        
        logger.info("\n" + "="*70)
        logger.info("LOCATION ANALYSIS SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Successful: {successful_analyses}")
        logger.info(f"  Failed: {failed_analyses}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during scheduled location analysis: {str(e)}")
        import traceback
        traceback.print_exc()

def run_all_schedulers():
    """Run both calendar and location schedulers"""
    logger.info("="*70)
    logger.info("COMBINED SCHEDULER STARTED")
    logger.info("="*70)
    logger.info("Scheduled tasks:")
    logger.info("  📅 Calendar fetch: 3:45 PM (15:45)")
    logger.info("  📍 Location analysis: 3:45 PM (15:45)")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Schedule calendar fetches at 3:45 PM
    schedule.every().day.at("15:45").do(fetch_calendar_for_all_users)
    
    # Schedule location analysis at 3:45 PM
    schedule.every().day.at("15:45").do(analyze_locations_for_all_users)
    
    # Run immediately for testing (if current time is close to scheduled time)
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    # If it's close to 3:45 PM (within 5 minutes), run immediately
    if current_hour == 15 and 40 <= current_minute <= 50:
        logger.info("⏰ Current time is close to 3:45 PM, running tasks immediately...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
    
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
        logger.debug(f"⏰ Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run pending jobs
        jobs_run = schedule.run_pending()
        if jobs_run:
            logger.info(f"✅ Ran {len(jobs_run)} job(s) at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
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
    print("COMBINED SCHEDULER")
    print("="*70)
    print("\nOptions:")
    print("1. Run one-time tasks now (fetch calendar + analyze locations)")
    print("2. Run continuous scheduler (runs daily at scheduled times)")
    print("3. Test: Run tasks now + start scheduler")
    print("="*70)
    
    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        print("\nRunning one-time tasks...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
    elif choice == "2":
        print("\nStarting continuous scheduler...")
        print("Tasks will run at:")
        print("  - Calendar: 3:45 PM (15:45)")
        print("  - Location: 3:45 PM (15:45)")
        print("\n⚠️  IMPORTANT: The scheduler must be running at 3:45 PM for tasks to execute!")
        print("   If you start it after 3:45 PM, tasks will run tomorrow at 3:45 PM.")
        print("\nPress Ctrl+C to stop\n")
        try:
            run_all_schedulers()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    elif choice == "3":
        print("\nRunning tasks now, then starting scheduler...\n")
        print("="*70)
        print("RUNNING TASKS NOW")
        print("="*70)
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
        print("\n" + "="*70)
        print("STARTING CONTINUOUS SCHEDULER")
        print("="*70)
        print("\nTasks will run at:")
        print("  - Calendar: 3:45 PM (15:45)")
        print("  - Location: 3:45 PM (15:45)")
        print("\nPress Ctrl+C to stop\n")
        try:
            run_all_schedulers()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    else:
        print("\nInvalid choice. Running one-time tasks...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()

