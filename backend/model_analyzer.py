import json
import boto3
from botocore.exceptions import ClientError
import warnings
import os
import re
from supabase import create_client, Client

warnings.filterwarnings('ignore')

class ModelAnalyzer:
    """
    Analyzes preprocessed data along with user history from database
    and generates personalized activity recommendations with stress tracking
    """
    
    def __init__(self, supabase_url=None, supabase_key=None):
        print("="*70)
        print("INITIALIZING MODEL ANALYZER")
        print("="*70)
        
        # Initialize Bedrock Runtime client with explicit credentials
        print(f"\n🔗 Initializing AWS Bedrock client...")
        try:
            # Get credentials from environment
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")  # For temporary credentials
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            
            if not aws_access_key or not aws_secret_key:
                raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in environment variables")
            
            print(f"  → Region: {aws_region}")
            print(f"  → Access Key: {aws_access_key[:8]}... (masked)")
            if aws_session_token:
                print(f"  → Session Token: {aws_session_token[:20]}... (temporary credentials)")
            
            # Build client kwargs
            client_kwargs = {
                "service_name": "bedrock-runtime",
                "region_name": aws_region,
                "aws_access_key_id": aws_access_key,
                "aws_secret_access_key": aws_secret_key
            }
            
            # Add session token if present (for temporary credentials)
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token
            
            self.bedrock_client = boto3.client(**client_kwargs)
            self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            print(f"✓ AWS Bedrock client initialized successfully")
            print(f"  → API: AWS Bedrock")
            print(f"  → Model: Claude 3.5 Sonnet")
        except Exception as e:
            print(f"❌ Failed to initialize Bedrock client: {str(e)}")
            raise
        
        # Initialize Supabase
        if supabase_url and supabase_key:
            print(f"\n🔗 Connecting to Supabase...")
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                print("✓ Supabase connected successfully")
            except Exception as e:
                print(f"⚠️  Supabase connection failed: {str(e)}")
                self.supabase = None
        else:
            self.supabase = None
            print("\n⚠️  Supabase not configured")
        
        print("\n" + "="*70)
        print("✅ MODEL ANALYZER READY")
        print("="*70 + "\n")
    
    def fetch_user_data(self, user_id):
        if not self.supabase:
            print("⚠️  Supabase not configured, skipping database fetch")
            return None, None, None, None, None
        
        try:
            print(f"\n📊 Fetching user data for ID: {user_id}")
            
            # Fetch all columns from 'habit' table for the user
            habit_response = self.supabase.table('habit').select('*').eq('id', user_id).execute()
            habit_data = habit_response.data[0] if habit_response.data and len(habit_response.data) > 0 else None

            # Fetch combined_report, stress_day, and emotions from 'report' table
            report_response = self.supabase.table('report').select('combined_report, stress_day, morning_emotion, evening_emotion, calendar_summary').eq('id', user_id).execute()
            if report_response.data and len(report_response.data) > 0:
                combined_report = report_response.data[0].get('combined_report')
                current_stress_day = report_response.data[0].get('stress_day', 0)
                morning_emotion = report_response.data[0].get('morning_emotion')
                evening_emotion = report_response.data[0].get('evening_emotion')
                calendar_summary = report_response.data[0].get('calendar_summary')
            else:
                combined_report = None
                current_stress_day = 0
                morning_emotion = None
                evening_emotion = None
                calendar_summary = None

            # Fetch recent push notification responses (last 7 days)
            notification_response = self.supabase.table('push_notification_responses').select('*').eq('id', user_id).order('timestamp', desc=True).limit(7).execute()
            notification_data = notification_response.data if notification_response.data else []

            # Fetch latest calendar data (today and tomorrow)
            # Get today's date and tomorrow's date
            from datetime import date, timedelta
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            # Fetch today's calendar data
            today_calendar_response = self.supabase.table('calendar_data').select('*').eq('id', user_id).eq('date', str(today)).limit(1).execute()
            today_calendar_data = today_calendar_response.data[0] if today_calendar_response.data else None
            
            # Fetch tomorrow's calendar data
            tomorrow_calendar_response = self.supabase.table('calendar_data').select('*').eq('id', user_id).eq('date', str(tomorrow)).limit(1).execute()
            tomorrow_calendar_data = tomorrow_calendar_response.data[0] if tomorrow_calendar_response.data else None
            
            # For backward compatibility, use today's data as primary
            calendar_data = today_calendar_data

            # Fetch latest location summary
            location_response = self.supabase.table('daily_location_summary').select('*').eq('id', user_id).order('date', desc=True).limit(1).execute()
            location_data = location_response.data[0] if location_response.data else None

            print(f"✓ Data fetched successfully")
            if habit_data:
                print(f"  → Habit data columns: {', '.join(habit_data.keys())}")
            else:
                print("  → No habit data found")
            print(f"  → Combined report length: {len(combined_report) if combined_report else 0} chars")
            print(f"  → Current stress_day: {current_stress_day}")
            print(f"  → Morning emotion: {morning_emotion}")
            print(f"  → Evening emotion (previous): {evening_emotion}")
            print(f"  → Notification responses: {len(notification_data)}")
            print(f"  → Calendar data (today): {'Yes' if today_calendar_data else 'No'}")
            print(f"  → Calendar data (tomorrow): {'Yes' if tomorrow_calendar_data else 'No'}")
            print(f"  → Location data: {'Yes' if location_data else 'No'}")
            
            # Combine notification, calendar, and location data
            extended_data = {
                'notification_data': notification_data,
                'calendar_data': calendar_data,  # Today's data (for backward compatibility)
                'today_calendar_data': today_calendar_data,
                'tomorrow_calendar_data': tomorrow_calendar_data,
                'location_data': location_data,
                'morning_emotion': morning_emotion,
                'evening_emotion': evening_emotion
            }
            
            return habit_data, combined_report, current_stress_day, extended_data
            
        except Exception as e:
            print(f"❌ Error fetching user data: {str(e)}")
            return None, None, 0, None
    
    def update_stress_day(self, user_id, new_stress_day):
        """Update stress_day in the report table"""
        if not self.supabase:
            print("⚠️  Supabase not configured, cannot update stress_day")
            return False
        
        try:
            print(f"\n📝 Updating stress_day to {new_stress_day} for user {user_id}")
            
            response = self.supabase.table('report').update({
                'stress_day': new_stress_day
            }).eq('id', user_id).execute()
            
            print(f"✓ stress_day updated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error updating stress_day: {str(e)}")
            return False
    
    def parse_mood_and_stress(self, response_text):
        """Extract mood and stress level from AI response"""
        try:
            # Look for patterns like "Mood:sad stress_level:2" or "MOOD: Sad, stress_level: 3"
            mood_match = re.search(r'mood:\s*(\w+)', response_text, re.IGNORECASE)
            stress_match = re.search(r'stress_level:\s*(\d+)', response_text, re.IGNORECASE)
            
            mood = mood_match.group(1).capitalize() if mood_match else "Unknown"
            stress_level = int(stress_match.group(1)) if stress_match else 0
            
            print(f"\n📊 Parsed from AI response:")
            print(f"  → Mood: {mood}")
            print(f"  → Stress Level: {stress_level}")
            
            return mood, stress_level
            
        except Exception as e:
            print(f"❌ Error parsing mood/stress: {str(e)}")
            return "Unknown", 0
    
    def process_stress_tracking(self, user_id, mood, stress_level, current_stress_day):
        """
        Process stress tracking logic:
        - If mood is Happy: reset stress_day to 0
        - If stress_level is 3: increase stress_day by 1
        - If stress_level is 4 or 5: increase stress_day by 2
        - If stress_day reaches 4: alert "You have stress"
        - If stress_day reaches 5 or 6: alert "You have high stress level"
        """
        print("\n" + "="*70)
        print("🧠 PROCESSING STRESS TRACKING")
        print("="*70)
        
        stress_alert = None
        new_stress_day = current_stress_day
        
        # Check if mood is Happy - reset stress
        if mood.lower() == "happy":
            print(f"😊 Happy mood detected! Resetting stress_day from {current_stress_day} to 0")
            new_stress_day = 0
            stress_alert = "🎉 Great mood! Your stress counter has been reset."
        else:
            # Process based on stress level
            if stress_level == 3:
                new_stress_day = current_stress_day + 1
                print(f"⚠️  Stress level 3 detected. Increasing stress_day: {current_stress_day} → {new_stress_day}")
            elif stress_level in [4, 5]:
                new_stress_day = current_stress_day + 2
                print(f"⚠️⚠️  Stress level {stress_level} detected. Increasing stress_day: {current_stress_day} → {new_stress_day}")
            else:
                print(f"ℹ️  Stress level {stress_level} - no change to stress_day")
            
            # Check for stress alerts
            if new_stress_day >= 5:
                stress_alert = "🔴 HIGH STRESS ALERT: You have high stress level! Please consider taking a break and practicing relaxation techniques."
                print(f"\n{stress_alert}")
            elif new_stress_day >= 4:
                stress_alert = "🟡 STRESS ALERT: You have stress! Consider taking some time for self-care activities."
                print(f"\n{stress_alert}")
        
        # Update database if stress_day changed
        if new_stress_day != current_stress_day:
            self.update_stress_day(user_id, new_stress_day)
        
        print("="*70 + "\n")
        
        return new_stress_day, stress_alert
    
    def extract_key_info(self, habit_data, combined_report):
        """Extract concise key information from all habit columns"""
        key_info = []
        
        if habit_data:
            # Use all relevant columns from habit_data
            if habit_data.get("free_hr_mrg"):
                key_info.append(f"Morning free time: {habit_data['free_hr_mrg']} mins")
            if habit_data.get("free_hr_eve"):
                key_info.append(f"Evening free time: {habit_data['free_hr_eve']} mins")
            if habit_data.get("sleep_pattern"):
                key_info.append(f"Sleep: {habit_data['sleep_pattern']} hours")
            if habit_data.get("work_schedule"):
                key_info.append(f"Work: {habit_data['work_schedule']} hours/day")
            if habit_data.get("screetime_daily"):
                key_info.append(f"Screen time: {habit_data['screetime_daily']} mins/day")
            if habit_data.get("preferred_exercise"):
                key_info.append(f"Preferred exercise: {habit_data['preferred_exercise']}")
            if habit_data.get("hobbies"):
                key_info.append(f"Hobbies: {habit_data['hobbies']}")
            if habit_data.get("social_preference"):
                key_info.append(f"Social preference: {habit_data['social_preference']}")
            if habit_data.get("energy_level_rating"):
                key_info.append(f"Energy level rating: {habit_data['energy_level_rating']}/5")
            if habit_data.get("meal_preferences"):
                key_info.append(f"Meal preferences: {habit_data['meal_preferences']}")
            if habit_data.get("relaxation_methods"):
                key_info.append(f"Relaxation methods: {habit_data['relaxation_methods']}")
        
        if combined_report:
            # Add recent activity summary (last 200 chars)
            if len(combined_report) > 200:
                key_info.append(f"Recent activity: {combined_report}")
            else:
                key_info.append(f"Recent activity: {combined_report}")
        
        return " | ".join(key_info) if key_info else "No historical data available"
    
    def construct_prompt(self, preprocessed_data, habit_data, combined_report, extended_data):
        print("\n🔨 Constructing prompt with extended data (notifications + calendar)...")
        
        # Extract only essential information
        user_summary = self.extract_key_info(habit_data, combined_report)
        
        # Build current state
        current_state = []
        if preprocessed_data.get('text'):
            current_state.append(f"User says: {preprocessed_data['text']}")
        if preprocessed_data.get('audio_transcript'):
            current_state.append(f"Voice message: {preprocessed_data['audio_transcript']}")
        if preprocessed_data.get('emotion'):
            current_state.append(f"Detected emotion: {preprocessed_data['emotion']} ({preprocessed_data['emotion_confidence']:.0%} confidence)")
        
        current_context = " | ".join(current_state) if current_state else "No direct input provided"
        
        # Add push notification emotion data
        notification_context = ""
        if extended_data and extended_data.get('notification_data'):
            recent_emotions = [n.get('emotion_response') for n in extended_data['notification_data'][:3]]
            if recent_emotions:
                notification_context = f"\nRecent mood check-ins: {', '.join(filter(None, recent_emotions))}"
        
        if extended_data and extended_data.get('morning_emotion'):
            notification_context += f"\nThis morning's emotion: {extended_data['morning_emotion']}"
        
        if extended_data and extended_data.get('evening_emotion'):
            notification_context += f"\nLast evening's emotion: {extended_data['evening_emotion']}"
        
        # Add calendar context (today and tomorrow)
        calendar_context = ""
        today_cal = extended_data.get('today_calendar_data') if extended_data else None
        tomorrow_cal = extended_data.get('tomorrow_calendar_data') if extended_data else None
        
        if today_cal or tomorrow_cal:
            calendar_context = ""
            
            if today_cal:
                calendar_context += f"""
CALENDAR DATA (Today's Schedule):
- {today_cal.get('meeting_count', 0)} meetings scheduled
- Total meeting hours: {today_cal.get('meeting_hours', 0)}
- Free time blocks: {today_cal.get('free_blocks', 0)}
- Lunch break: {'Yes' if today_cal.get('has_lunch_break') else 'No'}
- Events summary: {today_cal.get('events_summary', 'None')}
"""
            
            if tomorrow_cal:
                calendar_context += f"""
CALENDAR DATA (Tomorrow's Schedule):
- {tomorrow_cal.get('meeting_count', 0)} meetings scheduled
- Total meeting hours: {tomorrow_cal.get('meeting_hours', 0)}
- Free time blocks: {tomorrow_cal.get('free_blocks', 0)}
- Lunch break: {'Yes' if tomorrow_cal.get('has_lunch_break') else 'No'}
- Events summary: {tomorrow_cal.get('events_summary', 'None')}
"""
            
            if not today_cal and not tomorrow_cal:
                calendar_context = "\nCALENDAR DATA: No calendar data available\n"
        
        # Add location context
        location_context = ""
        if extended_data and extended_data.get('location_data'):
            loc = extended_data['location_data']
            location_context = f"""
LOCATION DATA (Today's Activity):
- Routine: {loc.get('routine_type', 'Unknown')}
- Left home: {loc.get('left_home_time', 'N/A')}
- Arrived office: {loc.get('arrived_office_time', 'N/A')}
- Left office: {loc.get('left_office_time', 'N/A')}
- Returned home: {loc.get('returned_home_time', 'N/A')}
- Time at office: {loc.get('time_at_office_hours', 0):.1f} hours
- Commute time: {loc.get('total_travel_time_minutes', 0):.0f} minutes
- Time at gym: {loc.get('time_at_gym_minutes', 0):.0f} minutes
- Time outdoors: {loc.get('time_outdoors_minutes', 0):.0f} minutes
- Active minutes: {loc.get('active_minutes', 0):.0f}
- Distance traveled: {loc.get('total_distance_km', 0):.1f} km
{'- ⚠️ Late night out detected' if loc.get('late_night_out') else ''}
{'- ⚠️ Excessive commute detected' if loc.get('excessive_commute') else ''}
"""
        
        # Construct user prompt for Claude API
        prompt = f"""USER CONTEXT: {user_summary}

CURRENT STATE: {current_context}{notification_context}

{calendar_context}

{location_context}

TASK: Based on the user's current emotional state, TODAY's schedule, TOMORROW's schedule, location patterns, and lifestyle, recommend exactly 5 personalized health and wellness activities for TODAY.

Guidelines:
- **Use TODAY's calendar data** to suggest activities that fit into their free time blocks today
- **Use TOMORROW's calendar data** to prepare them for tomorrow's busy schedule - if tomorrow is busy, suggest stress-reducing activities today
- **Use location data** to understand their daily routine and movement patterns
- **Use morning/evening emotions** from push notifications to gauge mood patterns
- Focus on **practical, actionable activities** tailored to:
  - Their profession and daily routine
  - Available free time TODAY (from calendar)
  - TOMORROW's schedule (if busy tomorrow, suggest relaxation/preparation activities today)
  - Current emotional state (from notifications and inputs)
  - Their actual location patterns (commute, office time, gym visits)
- Timing suggestions should reference:
  - Actual free blocks from TODAY's calendar (if available)
  - TOMORROW's schedule (if busy, suggest preparation activities)
  - Commute time (suggest activities during travel)
  - Office hours (desk exercises, lunch break activities)
  - Post-work time based on when they leave office
  - Home activities based on return time
- Include diverse activities:
  - Physical wellness (exercise, stretching, hydration)
  - Mental wellness (relaxation, breathing, mindfulness)
  - Hobby or creative activity
  - Social connection or self-care
  - Healthy routine or nutrition tip

IMPORTANT: 
- If TODAY's calendar shows a busy day, suggest quick 5-10 minute activities
- If TODAY's calendar shows free time, suggest longer activities (30-60 min)
- **If TOMORROW's calendar shows a busy schedule, suggest stress-reducing and preparation activities TODAY** (e.g., early sleep, relaxation, meal prep)
- **If TOMORROW has many meetings, suggest activities today that help prepare for a busy day** (e.g., good sleep, hydration, light exercise)
- If commute is long, suggest audio books, podcasts, or breathing exercises
- If they returned home late, suggest light evening relaxation
- If they haven't been to gym, gently encourage physical activity
- If low outdoor time, suggest fresh air activities
- Match activity intensity to user's emotional state AND energy from location data AND tomorrow's schedule

FORMAT: Output ONLY the mood, stress level, and numbered list, nothing else.

Example:
Mood: sad, stress_level: 2
1. Morning hydration - Start your day with a glass of water.
2. Eye relaxation - Before office, do a short eye exercise to reduce digital strain.
3. relaxation tip - listen to calm music if you feel stressed.
4. Evening stretch - After office, do light stretches to ease tension from sitting long hours.
5. Hobby refresh - Spend a 30 minutes of your free time on a relaxing hobby like drawing, music, or gardening.

Required format:
Mood: [Sad/Neutral/Angry/Happy/Fear/Surprise/Disgust], stress_level: [0-5]
1. [Tip name] - [General timing and description]
2. [Tip name] - [description]
3. [Tip name] - [description]
4. [Tip name] - [General timing and description]
5. [Tip name] - [free time suggestion]
"""
        
        print(f"✓ Prompt constructed ({len(prompt)} chars)")
        return prompt
    
    def generate_recommendations(self, prompt):
        print("\n🤖 Generating AI recommendations via AWS Bedrock...")
        
        # System prompt for the assistant
        system_prompt = "You are a wellness activity recommender. Generate exactly 5 specific activity recommendations with mood and stress level assessment."
        
        # Prepare request payload in the native Messages API format
        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }
        
        try:
            # Invoke the model
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(native_request)
            )
            
            # Decode the response
            model_response = json.loads(response["body"].read())
            
            # Extract text from the model's response
            response_text = model_response["content"][0]["text"]
            
            print("\n" + "="*70)
            print("🔍 DEBUG: GENERATED OUTPUT")
            print("="*70)
            print(response_text)
            print("="*70 + "\n")
            
            # Clean up response - keep mood/stress line and recommendations
            lines = response_text.split('\n')
            clean_lines = []
            mood_line_found = False
            
            for line in lines:
                stripped = line.strip()
                # Look for mood/stress line
                if not mood_line_found and ('mood:' in stripped.lower() or 'stress_level:' in stripped.lower()):
                    clean_lines.append(line)
                    mood_line_found = True
                # Look for numbered recommendations
                elif mood_line_found and (stripped.startswith('1.') or stripped.startswith('1 -') or stripped.startswith('1)')):
                    clean_lines.append(line)
                    break
            
            # Continue adding remaining recommendations
            start_adding = False
            for line in lines:
                stripped = line.strip()
                if start_adding:
                    clean_lines.append(line)
                    if len([l for l in clean_lines if any(l.strip().startswith(f'{i}.') or l.strip().startswith(f'{i} -') or l.strip().startswith(f'{i})') for i in range(1, 6))]) >= 5:
                        break
                elif stripped.startswith('1.') or stripped.startswith('1 -') or stripped.startswith('1)'):
                    start_adding = True
            
            if clean_lines:
                response_text = '\n'.join(clean_lines).strip()
            
            # Validate response
            if not response_text or len(response_text) < 20:
                response_text = "Mood: Neutral, stress_level: 0\nError: Model generated insufficient output. Please try again."
            
            print(f"✓ Final response length: {len(response_text)} chars")
            return response_text
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"❌ AWS Error: {error_code}")
            print(f"Message: {error_msg}")
            return f"Mood: Neutral, stress_level: 0\nError: {error_msg}"
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return f"Mood: Neutral, stress_level: 0\nError: An unexpected error occurred - {str(e)}"
    
    def analyze(self, user_id, preprocessed_data):
        print("\n" + "="*70)
        print("MODEL_ANALYZER.PY - RECEIVING DATA FROM PREPROCESSOR.PY")
        print("="*70)
        
        print("\n📥 RECEIVED FROM PREPROCESSOR.PY:")
        print("-" * 70)
        print(f"  ✓ Text: {'Yes' if preprocessed_data.get('has_text') else 'No'}")
        print(f"  ✓ Audio: {'Yes' if preprocessed_data.get('has_audio') else 'No'}")
        print(f"  ✓ Image: {'Yes' if preprocessed_data.get('has_image') else 'No'}")
        
        if preprocessed_data.get('audio_transcript'):
            transcript_preview = preprocessed_data['audio_transcript'][:100]
            print(f"\n  📝 Audio Transcript: '{transcript_preview}...'")
        if preprocessed_data.get('emotion'):
            print(f"  😊 Emotion: {preprocessed_data['emotion']} ({preprocessed_data['emotion_confidence']:.2%})")
        if preprocessed_data.get('text'):
            text_preview = preprocessed_data['text'][:100]
            print(f"  💬 Text: '{text_preview}...'")
        
        print("-" * 70)
        
        # Fetch user data from database (including notifications and calendar)
        habit_data, combined_report, current_stress_day, extended_data = self.fetch_user_data(user_id)
        
        # Construct prompt with all available data
        prompt = self.construct_prompt(preprocessed_data, habit_data, combined_report, extended_data)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(prompt)
        
        # Parse mood and stress level from recommendations
        mood, stress_level = self.parse_mood_and_stress(recommendations)
        
        # Process stress tracking
        new_stress_day, stress_alert = self.process_stress_tracking(
            user_id, mood, stress_level, current_stress_day
        )
        
        # Compile results
        result = {
            "analysis": recommendations,
            "mood": mood,
            "stress_level": stress_level,
            "stress_day": new_stress_day,
            "stress_alert": stress_alert,
            "inputs": {
                "user_id": user_id,
                "text": preprocessed_data['text'] if preprocessed_data['text'] else "Not provided",
                "audio_transcript": preprocessed_data['audio_transcript'] if preprocessed_data['audio_transcript'] else "Not provided",
                "emotion": preprocessed_data['emotion'] if preprocessed_data['emotion'] else "Not detected",
                "emotion_confidence": preprocessed_data['emotion_confidence'],
                "emotion_details": preprocessed_data['emotion_details'],
                "habit_data": habit_data if habit_data else "Not available",
                "combined_report": combined_report if combined_report else "Not available"
            },
            "preprocessed": preprocessed_data
        }
        
        print("\n" + "="*70)
        print("✅ ANALYSIS COMPLETE")
        print("="*70 + "\n")
        
        return result
    
    def print_results(self, result):
        print("\n" + "="*70)
        print("ANALYSIS RESULTS")
        print("="*70 + "\n")
        
        print("📥 INPUT SUMMARY:")
        print("-" * 70)
        print(f"User ID: {result['inputs']['user_id']}")
        print(f"Text: {result['inputs']['text']}")
        
        audio_transcript = result['inputs']['audio_transcript']
        if len(audio_transcript) > 100:
            print(f"Audio Transcript: {audio_transcript[:100]}...")
        else:
            print(f"Audio Transcript: {audio_transcript}")
        
        print(f"Emotion: {result['inputs']['emotion']}")
        if result['inputs']['emotion_confidence'] > 0:
            print(f"Confidence: {result['inputs']['emotion_confidence']:.2%}")
        
        print("\n📊 STRESS TRACKING:")
        print("-" * 70)
        print(f"Mood: {result['mood']}")
        print(f"Stress Level: {result['stress_level']}/5")
        print(f"Stress Days Counter: {result['stress_day']}")
        if result['stress_alert']:
            print(f"\n{result['stress_alert']}")
        
        print("\n🎯 AI RECOMMENDATIONS:")
        print("="*70)
        print(result['analysis'])
        print("="*70 + "\n")


def main():
    print("MODEL ANALYZER TEST (AWS Bedrock Claude with Stress Tracking)\n")
    print("="*70)
    print("NOTE: Using AWS Bedrock with Claude 3.5 Sonnet")
    print("="*70 + "\n")
    
    # Configuration
    supabase_url = os.getenv("SUPABASE_URL", "https://cswobvpopxypghwjolnb.supabase.co")
    supabase_key = os.getenv("SUPABASE_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzd29idnBvcHh5cGdod2pvbG5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA4NzQ5ODMsImV4cCI6MjA3NjQ1MDk4M30.P_E9zrpgOAI-mDVCCSWQDYLbfSXbng67EIApxujhNtQ")
    
    # Initialize analyzer
    analyzer = ModelAnalyzer(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )
    
    # Example preprocessed data
    preprocessed_data = {
        "text": "I'm feeling stressed today",
        "audio_transcript": "I just had lunch, ate a salad. Feeling okay but not super energetic.",
        "emotion": "Sad",
        "emotion_confidence": 0.75,
        "emotion_details": {
            "Sad": 0.75,
            "Neutral": 0.15,
            "Angry": 0.05,
            "Happy": 0.03,
            "Fear": 0.01,
            "Surprise": 0.01,
            "Disgust": 0.00
        },
        "has_audio": True,
        "has_image": True,
        "has_text": True
    }
    
    # Analyze
    result = analyzer.analyze(
        user_id="123456",
        preprocessed_data=preprocessed_data
    )
    
    # Print results
    analyzer.print_results(result)
    
    return result


if __name__ == "__main__":
    main()