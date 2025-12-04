"""
Google Calendar Integration Service
Fetches calendar events and analyzes schedule patterns
"""

import os
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional
import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from supabase import Client

# Scopes required for calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class GoogleCalendarService:
    """Service for integrating with Google Calendar API"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        
    def get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """Retrieve stored Google credentials for a user"""
        try:
            # Fetch refresh token from database
            result = self.supabase.table("push_notification_settings")\
                .select("google_refresh_token")\
                .eq("id", user_id)\
                .execute()
            
            if not result.data or not result.data[0].get("google_refresh_token"):
                print(f"No Google credentials found for user {user_id}")
                return None
            
            # Parse stored credentials
            creds_dict = json.loads(result.data[0]["google_refresh_token"])
            creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                self.save_user_credentials(user_id, creds)
            
            return creds
            
        except Exception as e:
            print(f"Error retrieving credentials: {str(e)}")
            return None
    
    def save_user_credentials(self, user_id: str, credentials: Credentials):
        """Save Google credentials for a user"""
        try:
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            self.supabase.table("push_notification_settings")\
                .upsert({
                    "id": user_id,
                    "google_refresh_token": json.dumps(creds_dict),
                    "calendar_authorized": True
                })\
                .execute()
            
            print(f"Credentials saved for user {user_id}")
            
        except Exception as e:
            print(f"Error saving credentials: {str(e)}")
    
    def fetch_today_events(self, user_id: str) -> Optional[Dict]:
        """Fetch today's calendar events for a user"""
        try:
            creds = self.get_user_credentials(user_id)
            if not creds:
                return None
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Get today's date range
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # Fetch events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=today_start.isoformat() + 'Z',
                timeMax=today_end.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Analyze schedule
            calendar_context = self.analyze_schedule(events, today_start.date())
            
            # Save to database
            self.save_calendar_data(user_id, calendar_context)
            
            return calendar_context
            
        except HttpError as error:
            print(f"Calendar API error: {error}")
            return None
        except Exception as e:
            print(f"Error fetching calendar events: {str(e)}")
            return None
    
    def analyze_schedule(self, events: List[Dict], date: datetime.date) -> Dict:
        """Analyze calendar events and extract meaningful patterns"""
        analysis = {
            'date': str(date),
            'meeting_count': len(events),
            'meeting_hours': 0,
            'free_blocks': 0,
            'earliest_meeting': None,
            'latest_meeting': None,
            'has_lunch_break': False,
            'events_summary': '',
            'calendar_raw_data': events
        }
        
        if not events:
            analysis['free_blocks'] = 8  # Assume 8 free hours in workday
            return analysis
        
        # Calculate meeting hours
        total_minutes = 0
        event_times = []
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            if 'T' in start:  # Has time component
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
                duration = (end_dt - start_dt).total_seconds() / 60
                total_minutes += duration
                
                event_times.append((start_dt.time(), end_dt.time()))
        
        analysis['meeting_hours'] = round(total_minutes / 60, 2)
        
        # Find earliest and latest meetings
        if event_times:
            event_times.sort()
            analysis['earliest_meeting'] = str(event_times[0][0])
            analysis['latest_meeting'] = str(event_times[-1][1])
            
            # Check for lunch break (gap between 12:00 and 14:00)
            analysis['has_lunch_break'] = self.check_lunch_gap(event_times)
            
            # Calculate free blocks
            analysis['free_blocks'] = self.calculate_free_blocks(event_times)
        
        # Create summary
        analysis['events_summary'] = self.generate_events_summary(events, analysis)
        
        return analysis
    
    def check_lunch_gap(self, event_times: List[tuple]) -> bool:
        """Check if there's a gap during typical lunch hours (12:00-14:00)"""
        lunch_start = dt_time(12, 0)
        lunch_end = dt_time(14, 0)
        
        for i in range(len(event_times) - 1):
            current_end = event_times[i][1]
            next_start = event_times[i + 1][0]
            
            # Check if there's a gap overlapping with lunch time
            if current_end <= lunch_start and next_start >= lunch_end:
                return True
            elif current_end >= lunch_start and current_end <= lunch_end:
                if next_start >= lunch_end or (next_start.hour == lunch_end.hour):
                    return True
        
        return False
    
    def calculate_free_blocks(self, event_times: List[tuple]) -> int:
        """Calculate number of free time blocks (>30 min gaps)"""
        free_blocks = 0
        
        for i in range(len(event_times) - 1):
            current_end = event_times[i][1]
            next_start = event_times[i + 1][0]
            
            # Calculate gap in minutes
            current_end_dt = datetime.combine(datetime.today(), current_end)
            next_start_dt = datetime.combine(datetime.today(), next_start)
            gap_minutes = (next_start_dt - current_end_dt).total_seconds() / 60
            
            if gap_minutes >= 30:
                free_blocks += 1
        
        return free_blocks
    
    def generate_events_summary(self, events: List[Dict], analysis: Dict) -> str:
        """Generate a human-readable summary of events"""
        if not events:
            return "No scheduled events today"
        
        summary_parts = [
            f"{analysis['meeting_count']} event(s) scheduled",
            f"Total {analysis['meeting_hours']} hours"
        ]
        
        if analysis['earliest_meeting']:
            summary_parts.append(f"Starting at {analysis['earliest_meeting']}")
        
        if analysis['has_lunch_break']:
            summary_parts.append("Lunch break available")
        else:
            summary_parts.append("No lunch break")
        
        if analysis['free_blocks'] > 0:
            summary_parts.append(f"{analysis['free_blocks']} free block(s)")
        
        # Add event titles
        event_titles = [event.get('summary', 'Untitled') for event in events[:3]]
        if event_titles:
            summary_parts.append(f"Events: {', '.join(event_titles)}")
            if len(events) > 3:
                summary_parts.append(f"and {len(events) - 3} more")
        
        return " | ".join(summary_parts)
    
    def save_calendar_data(self, user_id: str, calendar_context: Dict):
        """Save calendar analysis to database"""
        try:
            data = {
                "id": user_id,
                "date": calendar_context['date'],
                "meeting_count": calendar_context['meeting_count'],
                "meeting_hours": calendar_context['meeting_hours'],
                "free_blocks": calendar_context['free_blocks'],
                "earliest_meeting": calendar_context['earliest_meeting'],
                "latest_meeting": calendar_context['latest_meeting'],
                "has_lunch_break": calendar_context['has_lunch_break'],
                "events_summary": calendar_context['events_summary'],
                "calendar_raw_data": json.dumps(calendar_context['calendar_raw_data'])
            }
            
            # Upsert (update if exists, insert if not)
            self.supabase.table("calendar_data").upsert(data).execute()
            print(f"Calendar data saved for user {user_id}")
            
        except Exception as e:
            print(f"Error saving calendar data: {str(e)}")
    
    def get_latest_calendar_data(self, user_id: str) -> Optional[Dict]:
        """Retrieve the most recent calendar data for a user"""
        try:
            result = self.supabase.table("calendar_data")\
                .select("*")\
                .eq("id", user_id)\
                .order("date", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"Error retrieving calendar data: {str(e)}")
            return None


def infer_mood_from_schedule(calendar_context: Dict) -> str:
    """
    Infer potential mood based on schedule patterns
    This is a simplified version - can be enhanced with ML
    """
    meeting_count = calendar_context.get('meeting_count', 0)
    meeting_hours = calendar_context.get('meeting_hours', 0)
    has_lunch_break = calendar_context.get('has_lunch_break', True)
    free_blocks = calendar_context.get('free_blocks', 0)
    
    # Logic for mood inference
    if meeting_count == 0:
        return "Relaxed day with no scheduled meetings"
    elif meeting_count >= 6 or meeting_hours >= 6:
        return "Busy day with many commitments"
    elif not has_lunch_break and meeting_hours >= 4:
        return "Packed schedule without breaks - may be stressful"
    elif free_blocks >= 3:
        return "Balanced day with good free time"
    else:
        return "Moderate schedule"

