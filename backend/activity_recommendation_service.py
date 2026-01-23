"""
Activity Recommendation Service
Generates 5 personalized activity recommendations based on:
- Calendar data (today & tomorrow)
- Location summary
- Push notification responses
- User habits and preferences
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import logging
from supabase import Client
from dotenv import load_dotenv
from model_analyzer import ModelAnalyzer

# Load environment variables from .env file
load_dotenv()

class ActivityRecommendationService:
    """Service for generating personalized activity recommendations"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.model_analyzer = ModelAnalyzer(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY")
        )
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
    
    def collect_user_data(self, user_id: str) -> Dict:
        """Collect all relevant data for generating recommendations"""
        self.logger.info(f"📊 Collecting comprehensive data for user {user_id}")
        
        try:
            user_data = {
                'user_id': user_id,
                'calendar_data': None,
                'location_data': None,
                'notification_responses': [],
                'habit_data': None,
                'combined_report': None,
                'morning_emotion': None,
                'evening_emotion': None
            }
            
            # Get today and tomorrow dates
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            # 1. Fetch calendar data (today and tomorrow)
            today_calendar = self.supabase.table('calendar_data')\
                .select('*')\
                .eq('id', user_id)\
                .eq('date', str(today))\
                .limit(1)\
                .execute()
            
            tomorrow_calendar = self.supabase.table('calendar_data')\
                .select('*')\
                .eq('id', user_id)\
                .eq('date', str(tomorrow))\
                .limit(1)\
                .execute()
            
            user_data['today_calendar'] = today_calendar.data[0] if today_calendar.data else None
            user_data['tomorrow_calendar'] = tomorrow_calendar.data[0] if tomorrow_calendar.data else None
            
            # 2. Fetch latest location summary
            location_result = self.supabase.table('daily_location_summary')\
                .select('*')\
                .eq('id', user_id)\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            user_data['location_data'] = location_result.data[0] if location_result.data else None
            
            # 3. Fetch recent push notification responses (last 7 days)
            notification_result = self.supabase.table('push_notification_responses')\
                .select('*')\
                .eq('id', user_id)\
                .order('timestamp', desc=True)\
                .limit(7)\
                .execute()
            
            user_data['notification_responses'] = notification_result.data if notification_result.data else []
            
            # 4. Fetch habit data
            habit_result = self.supabase.table('habit')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            user_data['habit_data'] = habit_result.data[0] if habit_result.data else None
            
            # 5. Fetch report data (combined_report, emotions)
            report_result = self.supabase.table('report')\
                .select('combined_report, morning_emotion, evening_emotion, stress_day')\
                .eq('id', user_id)\
                .execute()
            
            if report_result.data:
                report_data = report_result.data[0]
                user_data['combined_report'] = report_data.get('combined_report')
                user_data['morning_emotion'] = report_data.get('morning_emotion')
                user_data['evening_emotion'] = report_data.get('evening_emotion')
                user_data['stress_day'] = report_data.get('stress_day', 0)
            
            self.logger.info(f"✅ Data collection complete for user {user_id}")
            self.logger.info(f"  → Today's calendar: {'Yes' if user_data['today_calendar'] else 'No'}")
            self.logger.info(f"  → Tomorrow's calendar: {'Yes' if user_data['tomorrow_calendar'] else 'No'}")
            self.logger.info(f"  → Location data: {'Yes' if user_data['location_data'] else 'No'}")
            self.logger.info(f"  → Notification responses: {len(user_data['notification_responses'])}")
            self.logger.info(f"  → Habit data: {'Yes' if user_data['habit_data'] else 'No'}")
            self.logger.info(f"  → Morning emotion: {user_data['morning_emotion']}")
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"❌ Error collecting user data: {str(e)}")
            return {'user_id': user_id, 'error': str(e)}
    
    def generate_recommendations(self, user_id: str) -> Dict:
        """Generate 5 personalized activity recommendations"""
        self.logger.info(f"🎯 Generating recommendations for user {user_id}")
        
        try:
            # Collect all user data
            user_data = self.collect_user_data(user_id)
            
            if 'error' in user_data:
                return {
                    'status': 'error',
                    'message': f"Failed to collect user data: {user_data['error']}",
                    'recommendations': []
                }
            
            # Use model_analyzer - it already handles:
            # - Fetching calendar data from DB
            # - Fetching location data from DB  
            # - Fetching notification responses from DB
            # - Constructing comprehensive prompt
            # - Calling AWS Bedrock/Claude
            morning_emotion = user_data.get('morning_emotion') or 'neutral'
            
            # Prepare minimal preprocessed_data - model_analyzer will fetch everything else from DB
            preprocessed_data = {
                'text': "Generate personalized activity recommendations based on my schedule, location, and mood.",
                'has_text': True,
                'has_audio': False,
                'has_image': False,
                'audio_transcript': None,
                'emotion': morning_emotion,
                'emotion_confidence': 0.8,
                'emotion_details': {}
            }
            
            # Use model analyzer - it handles all the data fetching and prompt construction
            self.logger.info("🤖 Calling model_analyzer (it will fetch calendar/location/notifications from DB)...")
            result = self.model_analyzer.analyze(user_id, preprocessed_data)
            
            # Parse recommendations from the analysis text
            analysis_text = result.get('analysis', '')
            self.logger.info(f"📄 AI Response received: {len(analysis_text)} characters")
            self.logger.info(f"📄 AI Response (first 500 chars): {analysis_text[:500]}")
            self.logger.info(f"📄 AI Response (full): {analysis_text}")
            
            # Parse recommendations from the analysis
            recommendations = self.parse_recommendations(analysis_text)
            
            self.logger.info(f"✅ Parsed {len(recommendations)} recommendations")
            if recommendations:
                self.logger.info(f"   First recommendation: {recommendations[0]}")
                self.logger.info(f"   All recommendations: {recommendations}")
            
            # Check if we got recommendations
            if not recommendations or len(recommendations) == 0:
                self.logger.error("❌ No recommendations parsed from AI response")
                self.logger.error(f"   Full AI response: {analysis_text}")
                return {
                    'status': 'error',
                    'message': 'Failed to parse recommendations from AI response. Check logs for details.',
                    'user_id': user_id,
                    'recommendations': [],
                    'ai_response': analysis_text[:1000],  # Include first 1000 chars for debugging
                    'mood': result.get('mood', 'neutral'),
                    'stress_level': result.get('stress_level', 0),
                    'stress_day': result.get('stress_day', 0),
                    'stress_alert': result.get('stress_alert')
                }
            
            # Send recommendations as push notification (only if we have recommendations)
            if recommendations:
                notification_sent = self.send_recommendations_as_notifications(user_id, recommendations)
            
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': recommendations,
                'mood': result.get('mood', 'neutral'),
                'stress_level': result.get('stress_level', 0),
                'stress_day': result.get('stress_day', 0),
                'stress_alert': result.get('stress_alert'),
                'generated_at': datetime.now().isoformat(),
                'data_sources': {
                    'calendar_today': bool(user_data['today_calendar']),
                    'calendar_tomorrow': bool(user_data['tomorrow_calendar']),
                    'location_data': bool(user_data['location_data']),
                    'notification_responses': len(user_data['notification_responses']),
                    'habit_data': bool(user_data['habit_data'])
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error generating recommendations: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'recommendations': []
            }
    
    def parse_recommendations(self, analysis_text: str) -> List[Dict]:
        """Parse the AI-generated recommendations into structured format"""
        recommendations = []
        
        if not analysis_text or len(analysis_text.strip()) == 0:
            self.logger.error("❌ Empty analysis text received from AI")
            return []
        
        try:
            lines = analysis_text.split('\n')
            self.logger.info(f"📝 Parsing {len(lines)} lines from AI response")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Look for numbered recommendations (1., 2., etc.) or (1), (2), etc.
                import re
                
                # Pattern 1: "1. Title - Description" or "1) Title - Description"
                match = re.match(r'^(\d+)[.)]\s*(.+)$', line)
                if match:
                    number = int(match.group(1))
                    content = match.group(2).strip()
                    
                    # Split title and description if separated by " - " or ":"
                    if ' - ' in content:
                        title, description = content.split(' - ', 1)
                    elif ': ' in content and len(content.split(': ')) == 2:
                        title, description = content.split(': ', 1)
                    else:
                        # If no separator, use first few words as title
                        words = content.split()
                        if len(words) > 4:
                            title = ' '.join(words[:3])
                            description = ' '.join(words[3:])
                        else:
                            title = content
                            description = content
                    
                    recommendations.append({
                        'id': number,
                        'title': title.strip(),
                        'description': description.strip(),
                        'full_text': content.strip()
                    })
                    self.logger.debug(f"  ✓ Parsed recommendation {number}: {title[:30]}...")
                    continue
                
                # Pattern 2: Look for lines that might be recommendations without numbers
                # (fallback for AI that doesn't follow format exactly)
                if line_num <= 10 and len(line) > 20:  # Only check first 10 lines
                    # Check if it looks like a recommendation (has action words)
                    action_words = ['take', 'do', 'try', 'practice', 'go', 'start', 'drink', 'walk', 'exercise']
                    if any(word in line.lower() for word in action_words):
                        # Try to extract as a recommendation
                        if ' - ' in line:
                            parts = line.split(' - ', 1)
                            title = parts[0].strip()
                            description = parts[1].strip()
                        else:
                            words = line.split()
                            if len(words) > 3:
                                title = ' '.join(words[:3])
                                description = ' '.join(words[3:])
                            else:
                                title = line
                                description = line
                        
                        recommendations.append({
                            'id': len(recommendations) + 1,
                            'title': title.strip(),
                            'description': description.strip(),
                            'full_text': line.strip()
                        })
                        self.logger.debug(f"  ✓ Parsed unnumbered recommendation: {title[:30]}...")
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_recommendations = []
            for rec in recommendations:
                title_lower = rec['title'].lower()
                if title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    unique_recommendations.append(rec)
            recommendations = unique_recommendations
            
            self.logger.info(f"✅ Parsed {len(recommendations)} unique recommendations")
            
            # Return what we parsed - no fallback, no filling
            if len(recommendations) >= 5:
                recommendations = recommendations[:5]
                self.logger.info(f"✅ Successfully parsed 5 recommendations")
            elif len(recommendations) > 0:
                self.logger.warning(f"⚠️ Only parsed {len(recommendations)} recommendations (expected 5)")
                self.logger.warning(f"   Returning {len(recommendations)} recommendations as-is")
            else:
                self.logger.error(f"❌ Failed to parse any recommendations from AI response")
                self.logger.error(f"   AI response: {analysis_text}")
            
            return recommendations[:5]  # Return up to 5, even if fewer
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing recommendations: {str(e)}")
            self.logger.error(f"   Analysis text: {analysis_text}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []  # Return empty list instead of fallback
    
    def send_recommendations_as_notifications(self, user_id: str, recommendations: List[Dict]) -> bool:
        """Send the 5 activity recommendations as push notifications to user"""
        try:
            from push_notification_service import PushNotificationService
            
            # Initialize notification service
            notification_service = PushNotificationService(self.supabase)
            
            # Create a single notification with all 5 recommendations
            recommendations_text = "\n".join([
                f"{i}. {rec.get('title', 'Activity')} - {rec.get('description', '')}"
                for i, rec in enumerate(recommendations, 1)
            ])
            
            notification = {
                'title': '🎯 Your Daily Activity Recommendations',
                'body': f'Here are 5 personalized activities for today:\n\n{recommendations_text}',
                'data': {
                    'type': 'daily_recommendations',
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat(),
                    'recommendations_count': len(recommendations)
                }
            }
            
            # Send the notification
            response = notification_service.send_notification(user_id, notification)
            
            if response:
                self.logger.info(f"✅ Recommendations sent as notification to user {user_id}")
                return True
            else:
                self.logger.warning(f"⚠️ Failed to send recommendations notification to user {user_id}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error sending recommendations notification: {str(e)}")
            return False
    
    def get_latest_recommendations(self, user_id: str) -> Optional[Dict]:
        """Note: Recommendations are now sent as notifications, not stored in database"""
        self.logger.info(f"ℹ️ Recommendations are sent as push notifications to user {user_id}")
        return {
            'message': 'Recommendations are sent as push notifications, not stored in database',
            'user_id': user_id,
            'notification_type': 'daily_recommendations'
        }
    
    def generate_recommendations_for_all_users(self) -> Dict:
        """Generate recommendations for all users with complete data"""
        self.logger.info("🎯 Generating recommendations for all eligible users")
        
        try:
            # Get users who have recent calendar data or location data
            today = date.today().isoformat()
            
            # Get users with calendar data today
            calendar_users = self.supabase.table('calendar_data')\
                .select('id')\
                .eq('date', today)\
                .execute()
            
            # Get users with location data today
            location_users = self.supabase.table('daily_location_summary')\
                .select('id')\
                .eq('date', today)\
                .execute()
            
            # Get users with push notification responses (recent activity)
            notification_users = self.supabase.table('push_notification_responses')\
                .select('id')\
                .gte('timestamp', f"{today}T00:00:00")\
                .execute()
            
            # Combine all user IDs
            all_user_ids = set()
            
            if calendar_users.data:
                all_user_ids.update([str(u['id']) for u in calendar_users.data])
            
            if location_users.data:
                all_user_ids.update([str(u['id']) for u in location_users.data])
            
            if notification_users.data:
                all_user_ids.update([str(u['id']) for u in notification_users.data])
            
            if not all_user_ids:
                self.logger.info("No eligible users found for recommendations")
                return {
                    'status': 'success',
                    'total_users': 0,
                    'successful': 0,
                    'failed': 0,
                    'results': []
                }
            
            self.logger.info(f"Found {len(all_user_ids)} eligible users")
            
            # Generate recommendations for each user
            results = []
            successful = 0
            failed = 0
            
            for user_id in all_user_ids:
                try:
                    self.logger.info(f"🎯 Generating recommendations for user {user_id}")
                    result = self.generate_recommendations(user_id)
                    
                    if result['status'] == 'success':
                        successful += 1
                        self.logger.info(f"✅ Recommendations generated for user {user_id}")
                    else:
                        failed += 1
                        self.logger.warning(f"⚠️ Failed to generate recommendations for user {user_id}: {result.get('message', 'Unknown error')}")
                    
                    results.append(result)
                    
                except Exception as user_error:
                    failed += 1
                    self.logger.error(f"❌ Error processing user {user_id}: {str(user_error)}")
                    results.append({
                        'status': 'error',
                        'user_id': user_id,
                        'message': str(user_error)
                    })
            
            summary = {
                'status': 'success',
                'total_users': len(all_user_ids),
                'successful': successful,
                'failed': failed,
                'results': results,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Bulk recommendation generation complete")
            self.logger.info(f"  → Total users: {len(all_user_ids)}")
            self.logger.info(f"  → Successful: {successful}")
            self.logger.info(f"  → Failed: {failed}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Error in bulk recommendation generation: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'total_users': 0,
                'successful': 0,
                'failed': 0
            }
