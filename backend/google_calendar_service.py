"""
Google Calendar Integration Service
Fetches calendar events and analyzes schedule patterns
"""

import os
from datetime import datetime, timedelta, time as dt_time, timezone
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv
try:
    import pytz
except ImportError:
    pytz = None
from pathlib import Path

# Load environment variables - try multiple locations
# First try current directory, then backend directory, then project root
env_paths = [
    Path(__file__).parent / ".env" if '__file__' in dir() else None,  # backend/.env
    Path(__file__).parent.parent / ".env" if '__file__' in dir() else None,  # health_monitor/.env
    Path(__file__).parent.parent.parent / ".env" if '__file__' in dir() else None,  # project/.env
    ".env",  # Current directory
]

for env_path in env_paths:
    if env_path and Path(env_path).exists():
        load_dotenv(env_path)
        print(f"✓ Loaded .env from: {env_path}")
        break
else:
    # Fallback: try default load_dotenv()
    load_dotenv()

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
        
        # Ensure .env is loaded (in case service is imported before backend_api loads it)
        load_dotenv()
        
        # Load OAuth credentials from environment or file
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        # Default redirect URI - use /auth/callback which is already configured in Google Cloud
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
        
        # Debug: Log what we found
        if self.client_id and self.client_secret:
            print(f"✓ Google OAuth credentials loaded from environment variables")
            print(f"  Client ID: {self.client_id[:30]}...")
            print(f"  Redirect URI: {self.redirect_uri}")
        else:
            print(f"⚠️ Google OAuth credentials NOT found in environment variables")
            print(f"  GOOGLE_CLIENT_ID: {'SET' if self.client_id else 'NOT SET'}")
            print(f"  GOOGLE_CLIENT_SECRET: {'SET' if self.client_secret else 'NOT SET'}")
            print(f"  Will try to load from client_secret.json file...")
        
        # Try to load from credentials file if env vars not set
        if not self.client_id or not self.client_secret:
            try:
                import glob
                from pathlib import Path
                
                # Get backend directory and project root
                backend_dir = Path(__file__).parent if '__file__' in dir() else Path.cwd()
                project_root = backend_dir.parent.parent
                
                # Check multiple possible locations for credentials file
                possible_paths = [
                    os.getenv("GOOGLE_CREDENTIALS_FILE"),  # Explicit env var
                    str(project_root / "client_secret*.json"),  # Project root with glob
                    str(backend_dir.parent / "client_secret*.json"),  # health_monitor dir
                    str(backend_dir / "client_secret*.json"),  # backend dir
                    "client_secret.json",  # Current dir
                    "../client_secret.json",  # Parent dir
                    "../../client_secret.json",  # Grandparent dir
                ]
                
                creds_file = None
                for path in possible_paths:
                    if not path:
                        continue
                    # Handle glob pattern
                    if '*' in path:
                        matches = glob.glob(path)
                        if matches:
                            # Prefer exact match, then any match
                            exact_match = next((m for m in matches if 'client_secret.json' == os.path.basename(m)), None)
                            creds_file = exact_match or matches[0]
                            break
                    elif os.path.exists(path):
                        creds_file = path
                        break
                
                if creds_file and os.path.exists(creds_file):
                    import json as json_lib
                    with open(creds_file, 'r') as f:
                        creds_data = json_lib.load(f)
                        if 'web' in creds_data:
                            self.client_id = creds_data['web']['client_id']
                            self.client_secret = creds_data['web']['client_secret']
                            # Use first redirect_uri from config, or default to our endpoint
                            if 'redirect_uris' in creds_data['web'] and creds_data['web']['redirect_uris']:
                                # Prefer localhost:8000 callback if available, otherwise use first one
                                localhost_callback = next(
                                    (uri for uri in creds_data['web']['redirect_uris'] 
                                     if 'localhost:8000' in uri and 'callback' in uri),
                                    creds_data['web']['redirect_uris'][0]
                                )
                                self.redirect_uri = localhost_callback
                            print(f"✓ Loaded Google OAuth credentials from {creds_file}")
                            print(f"  Client ID: {self.client_id[:30]}...")
                            print(f"  Redirect URI: {self.redirect_uri}")
                            print(f"✅ Google Calendar OAuth is configured and ready!")
                        elif 'installed' in creds_data:
                            # Handle installed app credentials (for testing)
                            self.client_id = creds_data['installed']['client_id']
                            self.client_secret = creds_data['installed']['client_secret']
                            if 'redirect_uris' in creds_data['installed'] and creds_data['installed']['redirect_uris']:
                                self.redirect_uri = creds_data['installed']['redirect_uris'][0]
                            print(f"✓ Loaded Google OAuth credentials (installed app) from {creds_file}")
            except Exception as e:
                print(f"⚠️ Warning: Could not load Google credentials: {e}")
                import traceback
                traceback.print_exc()
                print(f"   Current directory: {os.getcwd()}")
                print(f"   __file__ location: {__file__ if '__file__' in dir() else 'N/A'}")
        
        # Final check - log status
        if self.client_id and self.client_secret:
            print(f"✅ Google Calendar Service initialized with OAuth credentials")
        else:
            print(f"⚠️ Google Calendar Service initialized WITHOUT OAuth credentials")
            print(f"   Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars")
            print(f"   Or place client_secret.json in project root")
    
    def get_authorization_url(self, user_id) -> Optional[str]:
        """
        Generate Google OAuth authorization URL for a user.
        
        Note: The URL structure is the same for all users, but each call generates
        a unique 'state' parameter for security (CSRF protection). We store this
        state with the user_id so we can verify it when Google redirects back.
        
        This is standard OAuth 2.0 flow - no custom API needed, Google handles everything.
        """
        try:
            if not self.client_id or not self.client_secret:
                print("⚠️ Google OAuth credentials not configured")
                return None
            
            from google_auth_oauthlib.flow import Flow
            
            # Create OAuth flow with your credentials
            # This is the same for all users - just your Google OAuth app credentials
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            # Generate authorization URL with unique state parameter
            # Google generates a random 'state' for security (prevents CSRF attacks)
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            
            # Store state with user_id so we can verify it when Google redirects back
            # This links the OAuth flow to the specific user
            # Ensure user_id is int (database stores id as BIGINT)
            try:
                user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
            except (ValueError, TypeError):
                print(f"❌ Invalid user_id format: {user_id} (type: {type(user_id)})")
                return None
            
            try:
                # Use upsert with on_conflict to handle existing records
                # If record exists, update oauth_state; if not, insert new record
                self.supabase.table("push_notification_settings")\
                    .upsert({
                        "id": user_id_int,
                        "oauth_state": state
                    }, on_conflict="id")\
                    .execute()
            except Exception as db_error:
                error_msg = str(db_error)
                if "oauth_state" in error_msg.lower() or "column" in error_msg.lower():
                    print(f"❌ Database schema error: Missing 'oauth_state' column in push_notification_settings table")
                    print(f"   Please run the SQL migration: add_google_calendar_columns.sql")
                    print(f"   Error details: {error_msg}")
                    return None
                elif "bigint" in error_msg.lower() or "22P02" in error_msg:
                    print(f"❌ Database type error: user_id must be integer (BIGINT)")
                    print(f"   Received: {user_id} (type: {type(user_id)})")
                    print(f"   Error details: {error_msg}")
                    return None
                elif "23505" in error_msg or "unique constraint" in error_msg.lower():
                    # Unique constraint violation - try update instead
                    print(f"⚠️ Unique constraint violation, trying update instead...")
                    try:
                        self.supabase.table("push_notification_settings")\
                            .update({"oauth_state": state})\
                            .eq("id", user_id_int)\
                            .execute()
                        print(f"✓ Updated oauth_state for existing record")
                    except Exception as update_error:
                        print(f"❌ Failed to update oauth_state: {update_error}")
                        return None
                else:
                    print(f"❌ Unexpected database error: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            print(f"✓ Generated OAuth URL for user {user_id} (state: {state[:20]}...)")
            return authorization_url
            
        except Exception as e:
            print(f"❌ Error generating authorization URL: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def handle_oauth_callback(self, user_id, authorization_code: str, state: str) -> bool:
        """Exchange authorization code for tokens"""
        try:
            if not self.client_id or not self.client_secret:
                print("❌ Google OAuth credentials not configured")
                return False
            
            # Convert user_id to int (database stores id as BIGINT)
            try:
                user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
            except (ValueError, TypeError):
                print(f"❌ Invalid user_id format: {user_id} (type: {type(user_id)})")
                return False
            
            # Verify state matches what we stored
            result = self.supabase.table("push_notification_settings")\
                .select("oauth_state")\
                .eq("id", user_id_int)\
                .execute()
            
            if not result.data:
                print(f"❌ No OAuth state found for user {user_id_int}")
                return False
            
            stored_state = result.data[0].get("oauth_state")
            if stored_state != state:
                print(f"❌ Invalid OAuth state: expected {stored_state[:20]}..., got {state[:20]}...")
                return False
            
            print(f"✓ OAuth state verified for user {user_id_int}")
            
            from google_auth_oauthlib.flow import Flow
            from google.auth.transport.requests import Request
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            # Exchange code for tokens
            print(f"🔄 Exchanging authorization code for tokens...")
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            if not credentials:
                print("❌ Failed to get credentials from Google")
                return False
            
            print(f"✓ Received credentials from Google")
            
            # Save credentials
            self.save_user_credentials(user_id_int, credentials)
            
            # Clear OAuth state
            self.supabase.table("push_notification_settings")\
                .update({"oauth_state": None})\
                .eq("id", user_id_int)\
                .execute()
            
            print(f"✅ OAuth callback completed successfully for user {user_id_int}")
            return True
            
        except Exception as e:
            print(f"❌ Error handling OAuth callback: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def get_user_credentials(self, user_id) -> Optional[Credentials]:
        """Retrieve stored Google credentials for a user"""
        try:
            # Convert user_id to int (database stores id as BIGINT)
            try:
                user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
            except (ValueError, TypeError):
                print(f"❌ Invalid user_id format: {user_id} (type: {type(user_id)})")
                return None
            
            # Fetch refresh token from database
            result = self.supabase.table("push_notification_settings")\
                .select("google_refresh_token")\
                .eq("id", user_id_int)\
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
    
    def save_user_credentials(self, user_id, credentials: Credentials):
        """Save Google credentials for a user"""
        try:
            # Convert user_id to int (database stores id as BIGINT)
            try:
                user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
            except (ValueError, TypeError):
                print(f"❌ Invalid user_id format: {user_id} (type: {type(user_id)})")
                return
            
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # Check if record exists first
            existing = self.supabase.table("push_notification_settings")\
                .select("id")\
                .eq("id", user_id_int)\
                .execute()
            
            update_data = {
                "google_refresh_token": json.dumps(creds_dict),
                "calendar_authorized": True
            }
            
            if existing.data and len(existing.data) > 0:
                # Record exists, use update
                print(f"📝 Updating existing credentials for user {user_id_int}")
                result = self.supabase.table("push_notification_settings")\
                    .update(update_data)\
                    .eq("id", user_id_int)\
                    .execute()
            else:
                # Record doesn't exist, use insert
                print(f"➕ Inserting new credentials for user {user_id_int}")
                update_data["id"] = user_id_int
                result = self.supabase.table("push_notification_settings")\
                    .insert(update_data)\
                    .execute()
            
            # Verify it was saved
            verify = self.supabase.table("push_notification_settings")\
                .select("calendar_authorized, google_refresh_token")\
                .eq("id", user_id_int)\
                .execute()
            
            if verify.data:
                is_authorized = verify.data[0].get("calendar_authorized", False)
                has_token = bool(verify.data[0].get("google_refresh_token"))
                print(f"✅ Credentials saved for user {user_id_int}")
                print(f"   calendar_authorized: {is_authorized}")
                print(f"   has_token: {has_token}")
            else:
                print(f"⚠️ Warning: Could not verify credentials were saved")
            
        except Exception as e:
            print(f"❌ Error saving credentials: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def fetch_today_events(self, user_id: str) -> Optional[Dict]:
        """Fetch today's and tomorrow's calendar events for a user"""
        try:
            creds = self.get_user_credentials(user_id)
            if not creds:
                return None
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Get calendar timezone first
            try:
                calendar_info = service.calendars().get(calendarId='primary').execute()
                calendar_tz = calendar_info.get('timeZone', 'UTC')
            except:
                calendar_tz = 'UTC'
            
            # Get today's and tomorrow's date range in calendar's timezone
            # Get current time in calendar's timezone
            if pytz:
                try:
                    tz = pytz.timezone(calendar_tz)
                    now_local = datetime.now(tz)
                except:
                    # Fallback to UTC if timezone not found
                    tz = timezone.utc
                    now_local = datetime.now(timezone.utc)
            else:
                # Fallback to UTC if pytz not available
                tz = timezone.utc
                now_local = datetime.now(timezone.utc)
            
            # Get start of today in calendar's timezone
            today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start_local = today_start_local + timedelta(days=1)
            tomorrow_end_local = tomorrow_start_local + timedelta(days=1)
            
            # Convert to UTC for API (Google Calendar API expects UTC)
            today_start_utc = today_start_local.astimezone(timezone.utc)
            tomorrow_start_utc = tomorrow_start_local.astimezone(timezone.utc)
            tomorrow_end_utc = tomorrow_end_local.astimezone(timezone.utc)
            
            # Convert to UTC ISO format strings
            today_min = today_start_utc.isoformat().replace('+00:00', 'Z')
            today_max = tomorrow_start_utc.isoformat().replace('+00:00', 'Z')
            tomorrow_min = tomorrow_start_utc.isoformat().replace('+00:00', 'Z')
            tomorrow_max = tomorrow_end_utc.isoformat().replace('+00:00', 'Z')
            
            print(f"📅 Fetching calendar events:")
            print(f"   Today: {today_min} to {today_max}")
            print(f"   Tomorrow: {tomorrow_min} to {tomorrow_max}")
            
            # Fetch today's events
            today_events_result = service.events().list(
                calendarId='primary',
                timeMin=today_min,
                timeMax=today_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100  # Increase limit
            ).execute()
            
            today_events = today_events_result.get('items', [])
            print(f"   Found {len(today_events)} event(s) for today")
            
            # Fetch tomorrow's events
            tomorrow_events_result = service.events().list(
                calendarId='primary',
                timeMin=tomorrow_min,
                timeMax=tomorrow_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100  # Increase limit
            ).execute()
            
            tomorrow_events = tomorrow_events_result.get('items', [])
            print(f"   Found {len(tomorrow_events)} event(s) for tomorrow")
            
            # Debug: Print event details
            if today_events:
                print(f"\n   Today's events:")
                for event in today_events[:5]:  # Show first 5
                    start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                    summary = event.get('summary', 'No title')
                    print(f"     - {summary} at {start}")
            
            if tomorrow_events:
                print(f"\n   Tomorrow's events:")
                for event in tomorrow_events[:5]:  # Show first 5
                    start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                    summary = event.get('summary', 'No title')
                    print(f"     - {summary} at {start}")
            
            # Analyze both schedules
            today_context = self.analyze_schedule(today_events, today_start_local.date())
            tomorrow_context = self.analyze_schedule(tomorrow_events, tomorrow_start_local.date())
            
            # Save both to database
            self.save_calendar_data(user_id, today_context)
            self.save_calendar_data(user_id, tomorrow_context)
            
            # Return combined context
            return {
                'today': today_context,
                'tomorrow': tomorrow_context,
                'meeting_count': today_context.get('meeting_count', 0),  # For backward compatibility
                'meeting_hours': today_context.get('meeting_hours', 0),  # For backward compatibility
                'tomorrow_meeting_count': tomorrow_context.get('meeting_count', 0),
                'tomorrow_meeting_hours': tomorrow_context.get('meeting_hours', 0)
            }
            
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
            # Convert user_id to int if it's a string
            user_id_int = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            if not isinstance(user_id_int, int):
                print(f"❌ Invalid user_id type: {type(user_id_int)}, value: {user_id_int}")
                return
            
            data = {
                "id": user_id_int,
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
            
            print(f"💾 Saving calendar data for user {user_id_int}, date: {calendar_context['date']}")
            
            # Check if record exists for this date
            existing = self.supabase.table("calendar_data")\
                .select("id, date")\
                .eq("id", user_id_int)\
                .eq("date", calendar_context['date'])\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                result = self.supabase.table("calendar_data")\
                    .update(data)\
                    .eq("id", user_id_int)\
                    .eq("date", calendar_context['date'])\
                    .execute()
                print(f"✅ Updated calendar data for user {user_id_int} on {calendar_context['date']}")
            else:
                # Insert new record
                result = self.supabase.table("calendar_data")\
                    .insert(data)\
                    .execute()
                print(f"✅ Inserted calendar data for user {user_id_int} on {calendar_context['date']}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error saving calendar data: {error_msg}")
            print(f"   User ID: {user_id}, Type: {type(user_id)}")
            print(f"   Calendar date: {calendar_context.get('date', 'N/A')}")
            if "23505" in error_msg or "duplicate key" in error_msg.lower():
                # Duplicate key - try update instead
                try:
                    user_id_int = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
                    self.supabase.table("calendar_data")\
                        .update(data)\
                        .eq("id", user_id_int)\
                        .eq("date", calendar_context['date'])\
                        .execute()
                    print(f"✅ Updated calendar data (after duplicate key error) for user {user_id_int}")
                except Exception as update_err:
                    print(f"❌ Error updating calendar data: {update_err}")
                    import traceback
                    traceback.print_exc()
            else:
                import traceback
                traceback.print_exc()
    
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

