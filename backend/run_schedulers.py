"""
Activity Recommendation Scheduler
Daily 7 AM workflow for personalized activity recommendations

Usage:
  python run_schedulers.py

This runs the complete 7 AM daily workflow:
- Calendar data fetch & save ✅
- Location summary creation ✅  
- Push notification sent ✅
- 5 Activity recommendations generated 🆕

Based on collected data, generates 5 personalized activity recommendations using AI.
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
from push_notification_service import PushNotificationService
from activity_recommendation_service import ActivityRecommendationService

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
notification_service = PushNotificationService(supabase)
recommendation_service = ActivityRecommendationService(supabase)

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

def send_morning_notifications():
    """Send morning mood check notifications to all users"""
    logger.info("="*70)
    logger.info("RUNNING MORNING MOOD NOTIFICATIONS (7 AM)")
    logger.info("="*70)
    
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
        logger.info("Sending morning mood notifications...\n")
        
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
    logger.info("RUNNING EVENING MOOD NOTIFICATIONS (7 PM)")
    logger.info("="*70)
    
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
        logger.info("Sending evening mood notifications...\n")
        
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

def generate_activity_recommendations():
    """Generate 5 personalized activity recommendations for all users"""
    logger.info("="*70)
    logger.info("RUNNING SCHEDULED ACTIVITY RECOMMENDATIONS")
    logger.info("="*70)
    
    try:
        # Generate recommendations for all eligible users
        result = recommendation_service.generate_recommendations_for_all_users()
        
        if result['status'] == 'success':
            logger.info(f"✅ Activity recommendations generation completed")
            logger.info(f"   Total users processed: {result['total_users']}")
            logger.info(f"   Successful: {result['successful']}")
            logger.info(f"   Failed: {result['failed']}")
            
            # Log details for each user
            for user_result in result.get('results', []):
                user_id = user_result.get('user_id', 'Unknown')
                if user_result.get('status') == 'success':
                    recommendations = user_result.get('recommendations', [])
                    logger.info(f"   ✅ User {user_id}: {len(recommendations)} recommendations generated")
                    
                    # Log the recommendations briefly
                    for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
                        logger.info(f"      {i}. {rec.get('title', 'Unknown')}")
                    if len(recommendations) > 3:
                        logger.info(f"      ... and {len(recommendations) - 3} more")
                        
                else:
                    error_msg = user_result.get('message', 'Unknown error')
                    logger.warning(f"   ⚠️ User {user_id}: {error_msg}")
        else:
            logger.error(f"❌ Activity recommendations generation failed: {result.get('message', 'Unknown error')}")
        
        logger.info("\n" + "="*70)
        logger.info("ACTIVITY RECOMMENDATIONS SUMMARY:")
        logger.info(f"  Total users: {result.get('total_users', 0)}")
        logger.info(f"  Successful: {result.get('successful', 0)}")
        logger.info(f"  Failed: {result.get('failed', 0)}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during activity recommendations generation: {str(e)}")
        import traceback
        traceback.print_exc()

def run_morning_workflow():
    """Run morning workflow: Calendar fetch, location analysis, morning notifications, recommendations"""
    logger.info("="*70)
    logger.info("MORNING WORKFLOW (7 AM)")
    logger.info("="*70)
    logger.info("Tasks:")
    logger.info("  1. 📅 Fetch calendar data for today & tomorrow")
    logger.info("  2. 📍 Analyze location data from yesterday")
    logger.info("  3. 🔔 Send morning mood check notifications")
    logger.info("  4. 🎯 Generate activity recommendations")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Step 1: Fetch calendar data
        logger.info("STEP 1: Fetching calendar data...")
        fetch_calendar_for_all_users()
        
        # Step 2: Analyze location data
        logger.info("\nSTEP 2: Analyzing location data...")
        analyze_locations_for_all_users()
        
        # Step 3: Send morning notifications
        logger.info("\nSTEP 3: Sending morning notifications...")
        send_morning_notifications()
        
        # Step 4: Generate recommendations (after data collection)
        logger.info("\nSTEP 4: Generating activity recommendations...")
        generate_activity_recommendations()
        
        logger.info("\n" + "="*70)
        logger.info("✅ MORNING WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"❌ Error in morning workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def run_evening_workflow():
    """Run evening workflow: Calendar fetch, location analysis, evening notifications"""
    logger.info("="*70)
    logger.info("EVENING WORKFLOW (7 PM)")
    logger.info("="*70)
    logger.info("Tasks:")
    logger.info("  1. 📅 Fetch calendar data for tomorrow")
    logger.info("  2. 📍 Analyze location data from today")
    logger.info("  3. 🔔 Send evening mood check notifications")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Step 1: Fetch calendar data
        logger.info("STEP 1: Fetching calendar data...")
        fetch_calendar_for_all_users()
        
        # Step 2: Analyze location data
        logger.info("\nSTEP 2: Analyzing location data...")
        analyze_locations_for_all_users()
        
        # Step 3: Send evening notifications
        logger.info("\nSTEP 3: Sending evening notifications...")
        send_evening_notifications()
        
        logger.info("\n" + "="*70)
        logger.info("✅ EVENING WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"❌ Error in evening workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def run_all_schedulers():
    """Run calendar, location, mood notification, and activity recommendation schedulers"""
    logger.info("="*70)
    logger.info("ACTIVITY RECOMMENDATION SCHEDULER STARTED")
    logger.info("="*70)
    logger.info("Scheduled tasks:")
    logger.info("  📅 Calendar fetch & backup: 7 AM & 7 PM")
    logger.info("  📍 Location analysis & summary: 7 AM & 7 PM")
    logger.info("  🔔 Mood notifications: 7 AM (morning) & 7 PM (evening)")
    logger.info("  🎯 Activity recommendations: 7 AM (morning)")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Schedule morning workflow at 7 AM
    schedule.every().day.at("07:00").do(run_morning_workflow)
    
    # Schedule evening workflow at 7 PM
    schedule.every().day.at("19:00").do(run_evening_workflow)
    
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
    import sys
    
    # Check for command line arguments (for GitHub Actions)
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "morning":
            print("\n" + "="*70)
            print("RUNNING MORNING WORKFLOW (7 AM)")
            print("="*70)
            run_morning_workflow()
        elif mode == "evening":
            print("\n" + "="*70)
            print("RUNNING EVENING WORKFLOW (7 PM)")
            print("="*70)
            run_evening_workflow()
        elif mode == "test":
            print("\n" + "="*70)
            print("RUNNING TEST: All tasks now")
            print("="*70)
            fetch_calendar_for_all_users()
            analyze_locations_for_all_users()
            send_morning_notifications()
            generate_activity_recommendations()
        else:
            print(f"\nUnknown mode: {mode}")
            print("Usage: python run_schedulers.py [morning|evening|test]")
            sys.exit(1)
    else:
        # Interactive mode
        print("\n" + "="*70)
        print("ACTIVITY RECOMMENDATION SCHEDULER")
        print("="*70)
        print("\nOptions:")
        print("1. Run morning workflow now (calendar + location + morning notifications + recommendations)")
        print("2. Run evening workflow now (calendar + location + evening notifications)")
        print("3. Run continuous scheduler (runs daily at 7 AM & 7 PM)")
        print("4. Test: Run all tasks now")
        print("="*70)
        
        choice = input("\nEnter choice (1, 2, 3, or 4): ").strip()
        
        if choice == "1":
            print("\nRunning morning workflow...\n")
            run_morning_workflow()
        elif choice == "2":
            print("\nRunning evening workflow...\n")
            run_evening_workflow()
        elif choice == "3":
            print("\nStarting continuous scheduler...")
            print("Workflows will run at:")
            print("  - Morning (7 AM): Calendar + Location + Morning Notifications + Recommendations")
            print("  - Evening (7 PM): Calendar + Location + Evening Notifications")
            print("\n⚠️  IMPORTANT: The scheduler must be running at the scheduled times!")
            print("   If you start it after the scheduled time, tasks will run tomorrow.")
            print("\nPress Ctrl+C to stop\n")
            try:
                run_all_schedulers()
            except KeyboardInterrupt:
                print("\n\nScheduler stopped by user")
        elif choice == "4":
            print("\nRunning test: all tasks now...\n")
            fetch_calendar_for_all_users()
            analyze_locations_for_all_users()
            send_morning_notifications()
            generate_activity_recommendations()
        else:
            print("\nInvalid choice. Running morning workflow...\n")
            run_morning_workflow()

