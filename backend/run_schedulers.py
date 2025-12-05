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

def send_mood_notifications():
    """Send mood check notifications to all users"""
    logger.info("="*70)
    logger.info("RUNNING SCHEDULED MOOD NOTIFICATIONS")
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
        logger.info("Sending mood notifications...\n")
        
        for user_record in result.data:
            user_id = str(user_record.get("id"))
            if not user_id:
                continue
            
            try:
                # Determine if morning or evening based on hour
                current_hour = datetime.now().hour
                if current_hour < 12:
                    logger.info(f"☀️ Sending morning notification to user {user_id}...")
                    response = notification_service.send_morning_notification(user_id)
                else:
                    logger.info(f"🌙 Sending evening notification to user {user_id}...")
                    response = notification_service.send_evening_notification(user_id)
                
                if response:
                    logger.info(f"✅ Notification sent to user {user_id}")
                    sent_count += 1
                else:
                    logger.warning(f"⚠️ Failed to send to user {user_id}")
                    failed_count += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error sending to user {user_id}: {str(user_error)}")
                failed_count += 1
        
        logger.info("\n" + "="*70)
        logger.info("MOOD NOTIFICATIONS SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Sent: {sent_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during mood notifications: {str(e)}")
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

def run_all_schedulers():
    """Run calendar, location, mood notification, and activity recommendation schedulers"""
    logger.info("="*70)
    logger.info("ACTIVITY RECOMMENDATION SCHEDULER STARTED")
    logger.info("="*70)
    logger.info("Scheduled tasks:")
    logger.info("  📅 Calendar fetch & backup: 10:00 PM (22:00) - TESTING")
    logger.info("  📍 Location analysis & summary: 10:00 PM (22:00) - TESTING")
    logger.info("  🔔 Mood notifications: 10:00 PM (22:00) - TESTING")
    logger.info("  🎯 Activity recommendations: 10:00 PM (22:00) - TESTING")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Schedule ALL tasks at 10:00 PM (for testing)
    schedule.every().day.at("22:00").do(fetch_calendar_for_all_users)
    schedule.every().day.at("22:00").do(analyze_locations_for_all_users)
    schedule.every().day.at("22:00").do(send_mood_notifications)
    schedule.every().day.at("22:00").do(generate_activity_recommendations)
    
    # Run immediately for testing (if current time is close to scheduled time)
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    # If it's close to 10:00 PM (within 10 minutes), run all tasks immediately
    if current_hour == 22 and 0 <= current_minute <= 10:
        logger.info("⏰ Current time is close to 10:00 PM, running all tasks immediately...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
        send_mood_notifications()
        generate_activity_recommendations()
    elif current_hour == 21 and current_minute >= 50:
        logger.info("⏰ Current time is close to 10:00 PM, running all tasks immediately...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
        send_mood_notifications()
        generate_activity_recommendations()
    
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
    print("ACTIVITY RECOMMENDATION SCHEDULER")
    print("="*70)
    print("\nOptions:")
    print("1. Run one-time tasks now (calendar + location + notifications + recommendations)")
    print("2. Run continuous scheduler (runs daily at scheduled times)")
    print("3. Test: Run all tasks now + start scheduler")
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
        send_mood_notifications()
        generate_activity_recommendations()
    elif choice == "2":
        print("\nStarting continuous scheduler...")
        print("All tasks will run at:")
        print("  - Calendar fetch & backup: 10:00 PM (22:00) - TESTING")
        print("  - Location analysis & summary: 10:00 PM (22:00) - TESTING")
        print("  - Mood notifications: 10:00 PM (22:00) - TESTING")
        print("  - Activity recommendations: 10:00 PM (22:00) - TESTING")
        print("\n⚠️  IMPORTANT: The scheduler must be running at the scheduled times!")
        print("   If you start it after the scheduled time, tasks will run tomorrow.")
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
        send_mood_notifications()
        generate_activity_recommendations()
        print("\n" + "="*70)
        print("STARTING CONTINUOUS SCHEDULER")
        print("="*70)
        print("\nAll tasks will run at:")
        print("  - Calendar fetch & backup: 10:00 PM (22:00) - TESTING")
        print("  - Location analysis & summary: 10:00 PM (22:00) - TESTING")
        print("  - Mood notifications: 10:00 PM (22:00) - TESTING")
        print("  - Activity recommendations: 10:00 PM (22:00) - TESTING")
        print("\nPress Ctrl+C to stop\n")
        try:
            run_all_schedulers()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    else:
        print("\nInvalid choice. Running one-time tasks...\n")
        fetch_calendar_for_all_users()
        analyze_locations_for_all_users()
        send_mood_notifications()
        generate_activity_recommendations()

