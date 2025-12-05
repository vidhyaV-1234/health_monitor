#!/usr/bin/env python3
"""
Test script for Activity Recommendation Service
Tests the complete flow: data collection → AI analysis → recommendation generation
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

from activity_recommendation_service import ActivityRecommendationService

def test_recommendations():
    """Test the activity recommendation service"""
    print("="*70)
    print("TESTING ACTIVITY RECOMMENDATION SERVICE")
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
        
        # Initialize recommendation service
        recommendation_service = ActivityRecommendationService(supabase)
        print("✅ Activity Recommendation Service initialized")
        
        # Test with a sample user ID (you can change this)
        test_user_id = input("\nEnter user ID to test (or press Enter for '1'): ").strip() or "1"
        
        print(f"\n🎯 Testing recommendations for user {test_user_id}")
        print("-" * 50)
        
        # Test data collection
        print("\n1. Testing data collection...")
        user_data = recommendation_service.collect_user_data(test_user_id)
        
        if 'error' in user_data:
            print(f"❌ Data collection failed: {user_data['error']}")
            return False
        
        print("✅ Data collection successful")
        print(f"   → Calendar (today): {'Yes' if user_data.get('today_calendar') else 'No'}")
        print(f"   → Calendar (tomorrow): {'Yes' if user_data.get('tomorrow_calendar') else 'No'}")
        print(f"   → Location data: {'Yes' if user_data.get('location_data') else 'No'}")
        print(f"   → Notification responses: {len(user_data.get('notification_responses', []))}")
        print(f"   → Habit data: {'Yes' if user_data.get('habit_data') else 'No'}")
        print(f"   → Morning emotion: {user_data.get('morning_emotion', 'None')}")
        
        # Test recommendation generation
        print("\n2. Testing recommendation generation...")
        result = recommendation_service.generate_recommendations(test_user_id)
        
        if result['status'] != 'success':
            print(f"❌ Recommendation generation failed: {result.get('message', 'Unknown error')}")
            return False
        
        print("✅ Recommendation generation successful")
        print(f"   → Generated at: {result['generated_at']}")
        print(f"   → Mood: {result.get('mood', 'Unknown')}")
        print(f"   → Stress level: {result.get('stress_level', 0)}/5")
        print(f"   → Stress day: {result.get('stress_day', 0)}")
        
        if result.get('stress_alert'):
            print(f"   → Stress alert: {result['stress_alert']}")
        
        # Display recommendations
        print("\n3. Generated Recommendations:")
        print("=" * 50)
        recommendations = result.get('recommendations', [])
        
        if not recommendations:
            print("❌ No recommendations generated")
            return False
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec.get('title', 'Unknown')}")
            print(f"   {rec.get('description', 'No description')}")
            print()
        
        # Test retrieval of latest recommendations
        print("4. Testing recommendation retrieval...")
        latest = recommendation_service.get_latest_recommendations(test_user_id)
        
        if latest:
            print("✅ Latest recommendations retrieved successfully")
            print(f"   → Date: {latest['date']}")
            print(f"   → Generated at: {latest['generated_at']}")
            print(f"   → Number of recommendations: {len(latest['recommendations'])}")
        else:
            print("⚠️ No latest recommendations found (this might be expected)")
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_bulk_recommendations():
    """Test bulk recommendation generation for all users"""
    print("\n" + "="*70)
    print("TESTING BULK RECOMMENDATION GENERATION")
    print("="*70)
    
    # Initialize Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        recommendation_service = ActivityRecommendationService(supabase)
        
        print("🎯 Generating recommendations for all eligible users...")
        result = recommendation_service.generate_recommendations_for_all_users()
        
        print(f"\n✅ Bulk generation completed")
        print(f"   → Total users: {result.get('total_users', 0)}")
        print(f"   → Successful: {result.get('successful', 0)}")
        print(f"   → Failed: {result.get('failed', 0)}")
        
        # Show results for each user
        for user_result in result.get('results', []):
            user_id = user_result.get('user_id', 'Unknown')
            status = user_result.get('status', 'unknown')
            
            if status == 'success':
                rec_count = len(user_result.get('recommendations', []))
                print(f"   ✅ User {user_id}: {rec_count} recommendations")
            else:
                error_msg = user_result.get('message', 'Unknown error')
                print(f"   ❌ User {user_id}: {error_msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bulk test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n🧪 ACTIVITY RECOMMENDATION SERVICE TESTS")
    print("="*70)
    
    # Test individual user recommendations
    success = test_recommendations()
    
    if success:
        # Ask if user wants to test bulk generation
        bulk_test = input("\nDo you want to test bulk recommendation generation? (y/N): ").strip().lower()
        if bulk_test in ['y', 'yes']:
            test_bulk_recommendations()
    
    print("\n🏁 Testing complete!")