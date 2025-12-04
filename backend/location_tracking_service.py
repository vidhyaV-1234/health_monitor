"""
Location Tracking Service
Tracks user location throughout the day and analyzes patterns
"""

import os
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple
import json
from math import radians, cos, sin, asin, sqrt

from supabase import Client


class LocationTrackingService:
    """Service for tracking and analyzing user location patterns"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        
        # Common location types
        self.LOCATION_TYPES = {
            'home': 'Home',
            'office': 'Office/Work',
            'gym': 'Gym/Fitness',
            'mall': 'Shopping Mall',
            'restaurant': 'Restaurant/Cafe',
            'park': 'Park/Outdoors',
            'hotel': 'Hotel',
            'hospital': 'Hospital/Clinic',
            'transit': 'Transit Station',
            'other': 'Other'
        }
        
        # Activity types from device
        self.ACTIVITY_TYPES = {
            'stationary': 'Stationary',
            'walking': 'Walking',
            'running': 'Running',
            'driving': 'Driving',
            'in_vehicle': 'In Vehicle',
            'on_bicycle': 'Cycling'
        }
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def track_location(self, user_id: str, latitude: float, longitude: float,
                      activity_type: str = None, accuracy: float = None) -> bool:
        """Track a single location point"""
        try:
            # Auto-detect location type based on saved locations
            location_type, location_name = self.detect_location_type(
                user_id, latitude, longitude
            )
            
            location_data = {
                "id": user_id,
                "latitude": latitude,
                "longitude": longitude,
                "location_type": location_type,
                "location_name": location_name,
                "timestamp": datetime.now().isoformat(),
                "accuracy": accuracy,
                "activity_type": activity_type
            }
            
            self.supabase.table("location_tracking").insert(location_data).execute()
            
            print(f"✓ Location tracked: {location_type} at {datetime.now().strftime('%H:%M')}")
            return True
            
        except Exception as e:
            print(f"Error tracking location: {str(e)}")
            return False
    
    def detect_location_type(self, user_id: str, lat: float, lon: float) -> Tuple[str, str]:
        """Detect location type based on saved locations"""
        try:
            # Get saved locations for user
            result = self.supabase.table("saved_locations")\
                .select("*")\
                .eq("id", user_id)\
                .execute()
            
            if not result.data:
                return 'other', 'Unknown Location'
            
            # Check if current location is near any saved location
            for saved_loc in result.data:
                distance = self.calculate_distance(
                    lat, lon,
                    saved_loc['latitude'], saved_loc['longitude']
                )
                
                # If within radius (converted from meters to km)
                if distance <= (saved_loc.get('radius_meters', 100) / 1000):
                    # Update visit count
                    self.supabase.table("saved_locations")\
                        .update({
                            "visit_count": saved_loc['visit_count'] + 1,
                            "last_visited": datetime.now().isoformat()
                        })\
                        .eq("saved_location_id", saved_loc['saved_location_id'])\
                        .execute()
                    
                    return saved_loc['location_type'], saved_loc.get('location_name', '')
            
            return 'other', 'Unknown Location'
            
        except Exception as e:
            print(f"Error detecting location type: {str(e)}")
            return 'other', 'Unknown Location'
    
    def save_frequent_location(self, user_id: str, location_type: str,
                               latitude: float, longitude: float,
                               location_name: str = None, radius_meters: float = 100) -> bool:
        """Save a frequent location (home, office, etc.)"""
        try:
            location_data = {
                "id": user_id,
                "location_type": location_type,
                "location_name": location_name or self.LOCATION_TYPES.get(location_type, 'Location'),
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "auto_detected": False
            }
            
            self.supabase.table("saved_locations").insert(location_data).execute()
            print(f"✓ Saved location: {location_type}")
            return True
            
        except Exception as e:
            print(f"Error saving location: {str(e)}")
            return False
    
    def analyze_daily_locations(self, user_id: str, target_date: datetime.date = None) -> Optional[Dict]:
        """
        Analyze all location data for a day and generate summary
        """
        if not target_date:
            target_date = datetime.now().date()
        
        try:
            print(f"\n📍 Analyzing location data for {target_date}...")
            
            # Get all location points for the day
            start_time = datetime.combine(target_date, dt_time.min)
            end_time = datetime.combine(target_date, dt_time.max)
            
            result = self.supabase.table("location_tracking")\
                .select("*")\
                .eq("id", user_id)\
                .gte("timestamp", start_time.isoformat())\
                .lte("timestamp", end_time.isoformat())\
                .order("timestamp")\
                .execute()
            
            if not result.data:
                print("  No location data for this day")
                return None
            
            locations = result.data
            print(f"  → Found {len(locations)} location points")
            
            # Initialize summary
            summary = {
                'date': str(target_date),
                'left_home_time': None,
                'returned_home_time': None,
                'time_at_home_hours': 0,
                'arrived_office_time': None,
                'left_office_time': None,
                'time_at_office_hours': 0,
                'total_travel_time_minutes': 0,
                'commute_time_morning_minutes': 0,
                'commute_time_evening_minutes': 0,
                'visited_locations': [],
                'time_at_gym_minutes': 0,
                'time_at_mall_minutes': 0,
                'time_at_restaurant_minutes': 0,
                'time_outdoors_minutes': 0,
                'total_distance_km': 0,
                'active_minutes': 0,
                'sedentary_minutes': 0,
                'routine_type': 'regular_workday',
                'late_night_out': False,
                'skipped_lunch_break': False,
                'excessive_commute': False
            }
            
            # Analyze location patterns
            current_location_type = None
            current_location_start = None
            home_periods = []
            office_periods = []
            
            for i, loc in enumerate(locations):
                loc_type = loc.get('location_type', 'other')
                timestamp = datetime.fromisoformat(loc['timestamp'].replace('Z', '+00:00'))
                
                # Track location changes
                if loc_type != current_location_type:
                    if current_location_type:
                        duration = (timestamp - current_location_start).total_seconds() / 60
                        
                        # Record visit
                        summary['visited_locations'].append({
                            'type': current_location_type,
                            'name': locations[i-1].get('location_name', ''),
                            'duration_minutes': duration,
                            'start_time': current_location_start.strftime('%H:%M'),
                            'end_time': timestamp.strftime('%H:%M')
                        })
                        
                        # Update specific location times
                        if current_location_type == 'home':
                            home_periods.append(duration)
                        elif current_location_type == 'office':
                            office_periods.append(duration)
                        elif current_location_type == 'gym':
                            summary['time_at_gym_minutes'] += duration
                        elif current_location_type == 'mall':
                            summary['time_at_mall_minutes'] += duration
                        elif current_location_type == 'restaurant':
                            summary['time_at_restaurant_minutes'] += duration
                        elif current_location_type == 'park':
                            summary['time_outdoors_minutes'] += duration
                    
                    current_location_type = loc_type
                    current_location_start = timestamp
                    
                    # Track home arrival/departure
                    if loc_type == 'home':
                        if not summary['left_home_time']:
                            # First time at home (morning)
                            pass
                        else:
                            # Returned home
                            summary['returned_home_time'] = timestamp.strftime('%H:%M:%S')
                    elif current_location_type == 'home' and loc_type != 'home' and i > 0:
                        # Left home
                        if not summary['left_home_time']:
                            summary['left_home_time'] = timestamp.strftime('%H:%M:%S')
                    
                    # Track office arrival/departure
                    if loc_type == 'office':
                        if not summary['arrived_office_time']:
                            summary['arrived_office_time'] = timestamp.strftime('%H:%M:%S')
                    elif current_location_type == 'office' and loc_type != 'office':
                        if summary['arrived_office_time'] and not summary['left_office_time']:
                            summary['left_office_time'] = timestamp.strftime('%H:%M:%S')
                
                # Calculate distance traveled
                if i > 0:
                    prev_loc = locations[i-1]
                    distance = self.calculate_distance(
                        prev_loc['latitude'], prev_loc['longitude'],
                        loc['latitude'], loc['longitude']
                    )
                    summary['total_distance_km'] += distance
                
                # Track activity
                activity = loc.get('activity_type')
                time_delta = 5  # Assume 5 minutes between points
                if activity in ['walking', 'running', 'on_bicycle']:
                    summary['active_minutes'] += time_delta
                elif activity == 'stationary':
                    summary['sedentary_minutes'] += time_delta
                elif activity in ['driving', 'in_vehicle']:
                    summary['total_travel_time_minutes'] += time_delta
            
            # Calculate aggregate times
            summary['time_at_home_hours'] = sum(home_periods) / 60 if home_periods else 0
            summary['time_at_office_hours'] = sum(office_periods) / 60 if office_periods else 0
            
            # Determine routine type
            if summary['time_at_office_hours'] < 1:
                if summary['time_at_home_hours'] > 18:
                    summary['routine_type'] = 'work_from_home'
                else:
                    summary['routine_type'] = 'weekend'
            elif summary['time_at_office_hours'] >= 8:
                summary['routine_type'] = 'regular_workday'
            else:
                summary['routine_type'] = 'irregular'
            
            # Check for patterns
            if summary['returned_home_time']:
                return_hour = int(summary['returned_home_time'].split(':')[0])
                summary['late_night_out'] = return_hour >= 22
            
            if summary['total_travel_time_minutes'] > 120:  # More than 2 hours
                summary['excessive_commute'] = True
            
            # Calculate commute times
            if summary['left_home_time'] and summary['arrived_office_time']:
                left = datetime.strptime(summary['left_home_time'], '%H:%M:%S')
                arrived = datetime.strptime(summary['arrived_office_time'], '%H:%M:%S')
                summary['commute_time_morning_minutes'] = (arrived - left).total_seconds() / 60
            
            if summary['left_office_time'] and summary['returned_home_time']:
                left = datetime.strptime(summary['left_office_time'], '%H:%M:%S')
                arrived = datetime.strptime(summary['returned_home_time'], '%H:%M:%S')
                summary['commute_time_evening_minutes'] = (arrived - left).total_seconds() / 60
            
            print(f"  ✓ Analysis complete")
            return summary
            
        except Exception as e:
            print(f"Error analyzing daily locations: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_daily_summary(self, user_id: str, summary: Dict) -> bool:
        """Save daily location summary to database"""
        try:
            data = {
                "id": user_id,
                "date": summary['date'],
                "left_home_time": summary.get('left_home_time'),
                "returned_home_time": summary.get('returned_home_time'),
                "time_at_home_hours": summary.get('time_at_home_hours', 0),
                "arrived_office_time": summary.get('arrived_office_time'),
                "left_office_time": summary.get('left_office_time'),
                "time_at_office_hours": summary.get('time_at_office_hours', 0),
                "total_travel_time_minutes": summary.get('total_travel_time_minutes', 0),
                "commute_time_morning_minutes": summary.get('commute_time_morning_minutes', 0),
                "commute_time_evening_minutes": summary.get('commute_time_evening_minutes', 0),
                "visited_locations": json.dumps(summary.get('visited_locations', [])),
                "time_at_gym_minutes": summary.get('time_at_gym_minutes', 0),
                "time_at_mall_minutes": summary.get('time_at_mall_minutes', 0),
                "time_at_restaurant_minutes": summary.get('time_at_restaurant_minutes', 0),
                "time_outdoors_minutes": summary.get('time_outdoors_minutes', 0),
                "total_distance_km": summary.get('total_distance_km', 0),
                "active_minutes": summary.get('active_minutes', 0),
                "sedentary_minutes": summary.get('sedentary_minutes', 0),
                "routine_type": summary.get('routine_type', 'regular_workday'),
                "late_night_out": summary.get('late_night_out', False),
                "skipped_lunch_break": summary.get('skipped_lunch_break', False),
                "excessive_commute": summary.get('excessive_commute', False)
            }
            
            # Upsert (update if exists, insert if not)
            self.supabase.table("daily_location_summary").upsert(data).execute()
            print(f"Daily location summary saved for {summary['date']}")
            return True
            
        except Exception as e:
            print(f"Error saving daily summary: {str(e)}")
            return False
    
    def get_latest_summary(self, user_id: str) -> Optional[Dict]:
        """Get the most recent daily location summary"""
        try:
            result = self.supabase.table("daily_location_summary")\
                .select("*")\
                .eq("id", user_id)\
                .order("date", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"Error retrieving summary: {str(e)}")
            return None
    
    def generate_location_context_for_ai(self, user_id: str) -> str:
        """Generate location context string for AI recommendations"""
        try:
            summary = self.get_latest_summary(user_id)
            
            if not summary:
                return "No location data available for today."
            
            context_parts = []
            
            # Routine type
            context_parts.append(f"Today's routine: {summary['routine_type']}")
            
            # Home times
            if summary.get('left_home_time'):
                context_parts.append(f"Left home at {summary['left_home_time'][:5]}")
            if summary.get('returned_home_time'):
                context_parts.append(f"Returned home at {summary['returned_home_time'][:5]}")
            
            # Office times
            if summary.get('time_at_office_hours'):
                context_parts.append(f"Spent {summary['time_at_office_hours']:.1f} hours at office")
            
            # Commute
            if summary.get('total_travel_time_minutes'):
                context_parts.append(f"Total commute: {summary['total_travel_time_minutes']:.0f} minutes")
            
            # Activities
            activities = []
            if summary.get('time_at_gym_minutes'):
                activities.append(f"{summary['time_at_gym_minutes']:.0f} min at gym")
            if summary.get('time_outdoors_minutes'):
                activities.append(f"{summary['time_outdoors_minutes']:.0f} min outdoors")
            if activities:
                context_parts.append(f"Activities: {', '.join(activities)}")
            
            # Movement
            if summary.get('active_minutes'):
                context_parts.append(f"Active time: {summary['active_minutes']:.0f} minutes")
            
            # Patterns
            warnings = []
            if summary.get('late_night_out'):
                warnings.append("Returned home late")
            if summary.get('excessive_commute'):
                warnings.append("Long commute")
            if warnings:
                context_parts.append(f"Concerns: {', '.join(warnings)}")
            
            return " | ".join(context_parts)
            
        except Exception as e:
            print(f"Error generating location context: {str(e)}")
            return "Location data unavailable"

