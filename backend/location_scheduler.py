"""
Location Data Scheduler
Automatically analyzes location data for all users daily

Run this script using:
1. Manual: python location_scheduler.py
2. Cron job (Linux/Mac): Daily at 10:40 AM (for testing)
   Example crontab entry:
   40 10 * * * cd /path/to/backend && python location_scheduler.py
3. Windows Task Scheduler: Daily at 10:40 AM
4. As a background service
"""
import os
import time
import schedule
from datetime import datetime
import logging
from dotenv import load_dotenv
from supabase import create_client
from location_tracking_service import LocationTrackingService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('location_scheduler.log'),
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
location_service = LocationTrackingService(supabase)

def analyze_locations_for_all_users():
    """Analyze location data for all users who have location tracking enabled"""
    logger.info("="*70)
    logger.info("RUNNING SCHEDULED LOCATION DATA ANALYSIS")
    logger.info("="*70)
    
    try:
        # Get all users (we'll check if they have location data)
        # For now, analyze for any user with location_tracking entries today
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
                logger.info(f"📍 Analyzing locations for user {user_id}...")
                summary = location_service.analyze_daily_locations(str(user_id))
                
                if summary:
                    location_service.save_daily_summary(str(user_id), summary)
                    logger.info(f"✅ Successfully analyzed locations for user {user_id}")
                    logger.info(f"   Left home: {summary.get('left_home_time', 'N/A')}")
                    logger.info(f"   Returned home: {summary.get('returned_home_time', 'N/A')}")
                    successful_analyses += 1
                else:
                    logger.warning(f"⚠️ No location summary generated for user {user_id}")
                    failed_analyses += 1
                    
            except Exception as user_error:
                logger.error(f"❌ Error analyzing locations for user {user_id}: {str(user_error)}")
                failed_analyses += 1
        
        logger.info("\n" + "="*70)
        logger.info("SUMMARY:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Successful: {successful_analyses}")
        logger.info(f"  Failed: {failed_analyses}")
        logger.info("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error during scheduled location analysis: {str(e)}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    """Run the scheduler"""
    logger.info("📍 Location Data Scheduler Started")
    logger.info("Analyzing location data daily at 7:00 AM")
    
    # Schedule daily analysis at 7:00 AM
    schedule.every().day.at("07:00").do(analyze_locations_for_all_users)
    
    logger.info("Scheduled time:")
    logger.info("  - 7:00 AM")
    logger.info("\nWaiting for scheduled time...")
    logger.info("(Current time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if a job needs to run

if __name__ == "__main__":
    print("\n" + "="*70)
    print("LOCATION DATA SCHEDULER")
    print("="*70)
    print("\nOptions:")
    print("1. Run one-time analysis (analyze now for all users)")
    print("2. Run continuous scheduler (daily at 7:00 AM)")
    print("="*70)
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nRunning one-time location analysis...\n")
        analyze_locations_for_all_users()
    elif choice == "2":
        print("\nStarting continuous scheduler...")
        print("Location data will be analyzed daily at 7:00 AM")
        print("Press Ctrl+C to stop\n")
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
    else:
        print("\nInvalid choice. Running one-time analysis...\n")
        analyze_locations_for_all_users()

