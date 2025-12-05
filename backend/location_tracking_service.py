"""
Location Tracking Service
Tracks user location throughout the day and analyzes patterns
"""

import os
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple
import json
from math import radians, cos, sin, asin, sqrt
import requests
import time

from supabase import Client


class LocationTrackingService:
    """Service for tracking and analyzing user location patterns"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        
        # Common location types (flexible - users can add custom types)
        self.LOCATION_TYPES = {
            'home': 'Home',
            'office': 'Office/Work',
            'school': 'School',
            'university': 'University/College',
            'gym': 'Gym/Fitness',
            'library': 'Library',
            'mall': 'Shopping Mall',
            'restaurant': 'Restaurant',
            'cafe': 'Cafe/Coffee Shop',
            'park': 'Park/Outdoors',
            'hospital': 'Hospital/Clinic',
            'station': 'Transit Station',
            'airport': 'Airport',
            'hotel': 'Hotel',
            'friend': 'Friend\'s Place',
            'relative': 'Relative\'s Home',
            'church': 'Church',
            'temple': 'Temple',
            'mosque': 'Mosque',
            'salon': 'Salon/Spa',
            'workshop': 'Workshop',
            'studio': 'Studio',
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
        """
        Track a single location point
        Only saves if location has changed significantly (more than 50 meters) 
        or if it's been more than 2 minutes since last update
        """
        try:
            # Get the last location point for this user
            last_location_result = self.supabase.table("location_tracking")\
                .select("latitude, longitude, timestamp, location_type, location_name")\
                .eq("id", user_id)\
                .order("timestamp", desc=True)\
                .limit(1)\
                .execute()
            
            now = datetime.now()
            should_save = True
            location_changed = False
            
            if last_location_result.data and len(last_location_result.data) > 0:
                last_loc = last_location_result.data[0]
                last_lat = last_loc.get('latitude')
                last_lon = last_loc.get('longitude')
                last_timestamp_str = last_loc.get('timestamp')
                
                # Parse last timestamp
                try:
                    if 'Z' in last_timestamp_str:
                        last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00'))
                    elif '+' in last_timestamp_str:
                        last_timestamp = datetime.fromisoformat(last_timestamp_str)
                    else:
                        last_timestamp = datetime.fromisoformat(last_timestamp_str + '+00:00')
                except:
                    last_timestamp = None
                
                if last_timestamp:
                    # Calculate distance from last location
                    distance_km = self.calculate_distance(last_lat, last_lon, latitude, longitude)
                    distance_meters = distance_km * 1000
                    
                    # Calculate time since last update
                    time_diff_minutes = (now - last_timestamp.replace(tzinfo=None)).total_seconds() / 60
                    
                    # Only save if:
                    # 1. Location changed significantly (> 50 meters), OR
                    # 2. It's been more than 2 minutes since last update
                    if distance_meters > 50:
                        location_changed = True
                        should_save = True
                        print(f"📍 Location changed: {distance_meters:.0f}m away from last location")
                    elif time_diff_minutes >= 2:
                        should_save = True
                        print(f"📍 Time-based update: {time_diff_minutes:.1f} minutes since last update")
                    else:
                        should_save = False
                        print(f"⏭️  Skipping: Location unchanged ({distance_meters:.0f}m) and only {time_diff_minutes:.1f} min ago")
            
            if not should_save:
                return True  # Not an error, just skipping duplicate
            
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
                "timestamp": now.isoformat(),
                "accuracy": accuracy,
                "activity_type": activity_type
            }
            
            self.supabase.table("location_tracking").insert(location_data).execute()
            
            change_indicator = " (CHANGED)" if location_changed else ""
            print(f"✓ Location tracked: {location_name or location_type} at {now.strftime('%H:%M')}{change_indicator}")
            return True
            
        except Exception as e:
            print(f"Error tracking location: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def detect_location_type(self, user_id: str, lat: float, lon: float) -> Tuple[str, str]:
        """Detect location type based on saved locations, with fallback to reverse geocoding"""
        try:
            # Get saved locations for user
            result = self.supabase.table("saved_locations")\
                .select("*")\
                .eq("id", user_id)\
                .execute()
            
            if not result.data:
                # No saved locations, use reverse geocoding to get address
                address = self.reverse_geocode(lat, lon)
                return 'other', address or 'Unknown Location'
            
            # Check if current location is near any saved location
            for saved_loc in result.data:
                distance = self.calculate_distance(
                    lat, lon,
                    saved_loc['latitude'], saved_loc['longitude']
                )
                
                # If within radius (converted from meters to km)
                if distance <= (saved_loc.get('radius_meters', 100) / 1000):
                    # Update visit count
                    visit_count = saved_loc.get('visit_count', 0) + 1
                    self.supabase.table("saved_locations")\
                        .update({
                            "visit_count": visit_count,
                            "last_visited": datetime.now().isoformat()
                        })\
                        .eq("saved_location_id", saved_loc['saved_location_id'])\
                        .execute()
                    
                    return saved_loc['location_type'], saved_loc.get('location_name', saved_loc['location_type'].title())
            
            # Not near any saved location, use reverse geocoding
            address = self.reverse_geocode(lat, lon)
            return 'other', address or 'Unknown Location'
            
        except Exception as e:
            print(f"Error detecting location type: {str(e)}")
            return 'other', 'Unknown Location'
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Get address from coordinates using OpenStreetMap Nominatim API (free)
        Note: Nominatim has a usage policy of max 1 request per second
        """
        try:
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'WellnessCoachApp/1.0'  # Required by Nominatim
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('address'):
                    addr = data['address']
                    # Build readable address
                    parts = []
                    if addr.get('road'):
                        parts.append(addr['road'])
                    if addr.get('suburb'):
                        parts.append(addr['suburb'])
                    if addr.get('city') or addr.get('town'):
                        parts.append(addr.get('city') or addr.get('town'))
                    if addr.get('state'):
                        parts.append(addr['state'])
                    
                    if parts:
                        address = ', '.join(parts)
                        print(f"📍 Reverse geocoded: {address}")
                        return address
                
                # Fallback to display_name
                if data.get('display_name'):
                    return data['display_name']
            
            return None
            
        except Exception as e:
            print(f"⚠️ Reverse geocoding failed: {str(e)}")
            return None
    
    def save_frequent_location(self, user_id: str, location_type: str,
                               latitude: float, longitude: float,
                               location_name: str = None, radius_meters: float = 100) -> bool:
        """
        Save a frequent location (home, office, school, etc.)
        Supports both predefined and custom location types
        """
        try:
            # Normalize location type to lowercase
            location_type = location_type.lower().strip()
            
            # Use provided name or generate from type
            if not location_name or not location_name.strip():
                # Check if it's a known type, otherwise capitalize it
                location_name = self.LOCATION_TYPES.get(location_type, location_type.title())
                print(f"ℹ️  No location_name provided, using default: {location_name}")
            else:
                location_name = location_name.strip()
                print(f"✓ Using provided location_name: {location_name}")
            
            location_data = {
                "id": user_id,
                "location_type": location_type,
                "location_name": location_name,
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "auto_detected": False
            }
            
            print(f"📝 Inserting into saved_locations table:")
            print(f"   Data: {location_data}")
            
            result = self.supabase.table("saved_locations").insert(location_data).execute()
            print(f"✅ Saved location: {location_type} ({location_name})")
            print(f"   Database response: {result.data}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving location: {str(e)}")
            import traceback
            traceback.print_exc()
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
            
            # Analyze location patterns with improved change detection
            # Track entry/exit times for each location change
            MIN_STABLE_TIME_MINUTES = 2
            
            current_location_type = None
            current_location_name = None
            current_location_entry_time = None  # Entry time for current location
            current_location_coords = None
            home_periods = []
            office_periods = []
            travel_periods = []
            location_changes = []  # Track all location changes for travel detection
            location_visits = []  # Track all location visits with entry/exit times
            
            for i, loc in enumerate(locations):
                loc_type = loc.get('location_type', 'other')
                loc_name = loc.get('location_name', '')
                loc_lat = loc.get('latitude')
                loc_lon = loc.get('longitude')
                
                # Parse timestamp - handle various formats from database
                ts_str = loc['timestamp']
                try:
                    # Try parsing with microseconds
                    if 'Z' in ts_str:
                        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    elif '+' in ts_str or ts_str.endswith('+00:00'):
                        # Already has timezone info
                        timestamp = datetime.fromisoformat(ts_str)
                    else:
                        # No timezone, assume UTC
                        timestamp = datetime.fromisoformat(ts_str + '+00:00')
                except ValueError:
                    # Fallback: try parsing without microseconds
                    try:
                        ts_clean = ts_str.split('.')[0] if '.' in ts_str else ts_str
                        if 'Z' in ts_clean:
                            timestamp = datetime.fromisoformat(ts_clean.replace('Z', '+00:00'))
                        else:
                            timestamp = datetime.fromisoformat(ts_clean + '+00:00')
                    except Exception as e:
                        print(f"Error parsing timestamp {ts_str}: {e}")
                        continue
                
                # Check if location has changed significantly (more than 50 meters)
                location_changed = False
                if current_location_coords and loc_lat and loc_lon:
                    distance_km = self.calculate_distance(
                        current_location_coords[0], current_location_coords[1],
                        loc_lat, loc_lon
                    )
                    distance_meters = distance_km * 1000
                    
                    # Consider it a change if moved more than 50 meters
                    if distance_meters > 50:
                        location_changed = True
                
                # Track location changes (type change OR significant movement)
                if location_changed or (loc_type != current_location_type and current_location_type is not None):
                    # Location changed - record exit time for previous location and entry time for new location
                    if current_location_type and current_location_entry_time:
                        duration_minutes = (timestamp - current_location_entry_time).total_seconds() / 60
                        
                        # Record exit time for previous location
                        exit_time = timestamp.strftime('%H:%M:%S')
                        
                        # Only record visit if stayed at location for at least MIN_STABLE_TIME_MINUTES
                        if duration_minutes >= MIN_STABLE_TIME_MINUTES:
                            # Record visit with entry/exit times
                            visit_info = {
                                'type': current_location_type,
                                'name': current_location_name or '',
                                'duration_minutes': round(duration_minutes, 1),
                                'entry_time': current_location_entry_time.strftime('%H:%M:%S'),
                                'exit_time': exit_time,
                                'arrival_time': current_location_entry_time.strftime('%H:%M:%S'),
                                'departure_time': exit_time,
                                'start_time': current_location_entry_time.strftime('%H:%M'),
                                'end_time': timestamp.strftime('%H:%M')
                            }
                            location_visits.append(visit_info)
                            summary['visited_locations'].append(visit_info)
                            
                            # Track location change for travel detection
                            location_changes.append({
                                'from': current_location_type,
                                'from_name': current_location_name or '',
                                'to': loc_type,
                                'to_name': loc_name or '',
                                'exit_time': exit_time,
                                'entry_time': timestamp.strftime('%H:%M:%S'),
                                'change_time': timestamp.strftime('%H:%M:%S')
                            })
                            
                            # Update specific location times
                            if current_location_type == 'home':
                                home_periods.append({
                                    'arrival': current_location_entry_time,
                                    'departure': timestamp,
                                    'duration_minutes': duration_minutes
                                })
                            elif current_location_type == 'office':
                                office_periods.append({
                                    'arrival': current_location_entry_time,
                                    'departure': timestamp,
                                    'duration_minutes': duration_minutes
                                })
                            elif current_location_type == 'gym':
                                summary['time_at_gym_minutes'] += duration_minutes
                            elif current_location_type == 'mall':
                                summary['time_at_mall_minutes'] += duration_minutes
                            elif current_location_type == 'restaurant':
                                summary['time_at_restaurant_minutes'] += duration_minutes
                            elif current_location_type == 'park':
                                summary['time_outdoors_minutes'] += duration_minutes
                        else:
                            # Short stay (< 2 minutes) - likely traveling
                            if current_location_type not in ['travel', 'other']:
                                travel_periods.append({
                                    'location': current_location_name or current_location_type,
                                    'entry_time': current_location_entry_time.strftime('%H:%M:%S'),
                                    'exit_time': exit_time,
                                    'start': current_location_entry_time,
                                    'end': timestamp,
                                    'duration_minutes': duration_minutes
                                })
                    
                    # Start tracking new location - record entry time
                    current_location_type = loc_type
                    current_location_name = loc_name
                    current_location_entry_time = timestamp  # Entry time for new location
                    current_location_coords = (loc_lat, loc_lon) if loc_lat and loc_lon else None
                    
                    print(f"  📍 Location changed: {current_location_name or current_location_type}")
                    print(f"     Entry time: {current_location_entry_time.strftime('%H:%M:%S')}")
                    
                elif current_location_type is None:
                    # First location point - record entry time
                    current_location_type = loc_type
                    current_location_name = loc_name
                    current_location_entry_time = timestamp  # Entry time for first location
                    current_location_coords = (loc_lat, loc_lon) if loc_lat and loc_lon else None
                    
                    print(f"  📍 First location: {current_location_name or current_location_type}")
                    print(f"     Entry time: {current_location_entry_time.strftime('%H:%M:%S')}")
                else:
                    # Same location, update coordinates if available
                    if loc_lat and loc_lon:
                        current_location_coords = (loc_lat, loc_lon)
                
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
            
            # Handle last location period (if still at a location at end of day)
            if current_location_type and current_location_entry_time:
                last_timestamp = timestamp  # Use the last location's timestamp
                duration_minutes = (last_timestamp - current_location_entry_time).total_seconds() / 60
                
                if duration_minutes >= MIN_STABLE_TIME_MINUTES:
                    visit_info = {
                        'type': current_location_type,
                        'name': current_location_name or '',
                        'duration_minutes': round(duration_minutes, 1),
                        'entry_time': current_location_entry_time.strftime('%H:%M:%S'),
                        'exit_time': 'Ongoing',
                        'arrival_time': current_location_entry_time.strftime('%H:%M:%S'),
                        'departure_time': 'Ongoing',
                        'start_time': current_location_entry_time.strftime('%H:%M'),
                        'end_time': 'Ongoing'
                    }
                    location_visits.append(visit_info)
                    summary['visited_locations'].append(visit_info)
                    
                    if current_location_type == 'home':
                        home_periods.append({
                            'arrival': current_location_entry_time,
                            'departure': last_timestamp,
                            'duration_minutes': duration_minutes
                        })
                    elif current_location_type == 'office':
                        office_periods.append({
                            'arrival': current_location_entry_time,
                            'departure': last_timestamp,
                            'duration_minutes': duration_minutes
                        })
            
            # Calculate aggregate times from periods
            summary['time_at_home_hours'] = sum([p['duration_minutes'] for p in home_periods]) / 60 if home_periods else 0
            summary['time_at_office_hours'] = sum([p['duration_minutes'] for p in office_periods]) / 60 if office_periods else 0
            
            # Calculate travel time from travel periods
            if travel_periods:
                total_travel_minutes = sum([p['duration_minutes'] for p in travel_periods])
                summary['total_travel_time_minutes'] += round(total_travel_minutes, 1)
            
            # Calculate in/out times from home and office periods
            if home_periods:
                # Find first departure from home (left home time)
                departures = [p['departure'] for p in home_periods if p['departure'].date() == target_date]
                if departures:
                    first_departure = min(departures)
                    summary['left_home_time'] = first_departure.strftime('%H:%M:%S')
                
                # Find last arrival at home (returned home time)
                arrivals = [p['arrival'] for p in home_periods if p['arrival'].date() == target_date]
                if arrivals:
                    last_arrival = max(arrivals)
                    summary['returned_home_time'] = last_arrival.strftime('%H:%M:%S')
            
            if office_periods:
                # Find first arrival at office
                arrivals = [p['arrival'] for p in office_periods if p['arrival'].date() == target_date]
                if arrivals:
                    first_arrival = min(arrivals)
                    summary['arrived_office_time'] = first_arrival.strftime('%H:%M:%S')
                
                # Find last departure from office
                departures = [p['departure'] for p in office_periods if p['departure'].date() == target_date]
                if departures:
                    last_departure = max(departures)
                    summary['left_office_time'] = last_departure.strftime('%H:%M:%S')
            
            # Detect frequent location changes as traveling
            if len(location_changes) > 5:
                # More than 5 location changes indicates traveling
                summary['routine_type'] = 'traveling'
            elif len(location_changes) > 3:
                summary['routine_type'] = 'irregular'
            elif summary['time_at_office_hours'] < 1:
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
            # Convert user_id to int if it's a string
            user_id_int = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            if not isinstance(user_id_int, int):
                print(f"❌ Invalid user_id type: {type(user_id_int)}, value: {user_id_int}")
                return False
            
            data = {
                "id": user_id_int,
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
            
            print(f"💾 Saving daily location summary for user {user_id_int}, date: {summary['date']}")
            
            # Check if record exists
            existing = self.supabase.table("daily_location_summary")\
                .select("id, date")\
                .eq("id", user_id_int)\
                .eq("date", summary['date'])\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                result = self.supabase.table("daily_location_summary")\
                    .update(data)\
                    .eq("id", user_id_int)\
                    .eq("date", summary['date'])\
                    .execute()
                print(f"✅ Updated daily location summary for user {user_id_int} on {summary['date']}")
            else:
                # Insert new record
                result = self.supabase.table("daily_location_summary")\
                    .insert(data)\
                    .execute()
                print(f"✅ Inserted daily location summary for user {user_id_int} on {summary['date']}")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error saving daily summary: {error_msg}")
            print(f"   User ID: {user_id}, Type: {type(user_id)}")
            print(f"   Summary date: {summary.get('date', 'N/A')}")
            import traceback
            traceback.print_exc()
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

