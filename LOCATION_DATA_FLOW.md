# 📍 Location Data Flow & Table Updates

## Overview
This document explains when each location-related table gets updated and how the data flows through the system.

---

## 📊 Database Tables

### 1. **`location_tracking`** - Raw Location Points
**Purpose:** Stores every individual location point tracked throughout the day

**When Updated:**
- ✅ **Every 2 minutes** (automatic, when location permission is granted)
- Triggered by: Frontend `PermissionsManager` component
- Method: `track_location()` in `location_tracking_service.py`

**What Gets Stored:**
```json
{
  "id": "7890",
  "latitude": 11.0418,
  "longitude": 77.0445,
  "location_type": "home",        // Auto-detected from saved_locations
  "location_name": "My Home",      // Auto-detected from saved_locations
  "timestamp": "2025-12-04T15:30:00",
  "accuracy": 10.5,
  "activity_type": "stationary"
}
```

**Frequency:** Every 2 minutes (can be changed in `PermissionsManager.jsx`)

---

### 2. **`saved_locations`** - User's Labeled Places
**Purpose:** Stores user-defined locations with custom names

**When Updated:**
- ✅ **When user saves a location** via "Manage Locations" modal
- Triggered by: User clicking "Save Location" button
- Method: `save_frequent_location()` in `location_tracking_service.py`

**What Gets Stored:**
```json
{
  "saved_location_id": "uuid-here",
  "id": "7890",
  "location_type": "home",
  "location_name": "My Sweet Home",
  "latitude": 11.0418,
  "longitude": 77.0445,
  "radius_meters": 100,
  "visit_count": 5,                // Auto-incremented
  "last_visited": "2025-12-04T15:30:00",
  "auto_detected": false,
  "created_at": "2025-12-04T09:55:01"
}
```

**Visit Count Updates:**
- Auto-increments when user is detected within 100m of this location
- Updates every time `track_location()` detects the user at this place

---

### 3. **`daily_location_summary`** - Daily Movement Summary
**Purpose:** Aggregates all location points into a daily summary

**When Updated:**
- ✅ **Automatically when user submits mood entry** (NEW! Just added)
- ✅ **Manually via API**: `/api/location/analyze-day`
- Triggered by: `analyze_daily_locations()` in `location_tracking_service.py`
- Frequency: Once per day (when first mood entry is submitted)

**What Gets Stored:**
```json
{
  "id": "7890",
  "date": "2025-12-04",
  "left_home_time": "07:30:00",
  "returned_home_time": "20:00:00",
  "time_at_home_hours": 14.5,
  "arrived_office_time": "09:00:00",
  "left_office_time": "18:00:00",
  "time_at_office_hours": 9.0,
  "total_travel_time_minutes": 120,
  "commute_time_morning_minutes": 60,
  "commute_time_evening_minutes": 60,
  "visited_locations": ["home", "office", "gym", "restaurant"],
  "time_at_gym_minutes": 90,
  "time_at_mall_minutes": 0,
  "time_at_restaurant_minutes": 45,
  "time_outdoors_minutes": 30,
  "total_distance_km": 25.5,
  "active_minutes": 120,
  "sedentary_minutes": 540,
  "routine_type": "regular_workday",
  "late_night_out": false,
  "weekend_activity": false,
  "skipped_lunch_break": false,
  "excessive_commute": false,
  "summary_text": "Regular workday with gym visit",
  "created_at": "2025-12-04T21:00:00"
}
```

**Analysis Triggers:**
1. 🔄 **Auto-trigger**: When user submits mood entry (happens 1-2 times daily)
2. 📱 **Manual trigger**: User can call `/api/location/analyze-day` endpoint

---

### 4. **`location_preferences`** - User's Location-Based Preferences
**Purpose:** Stores user preferences for activities at specific location types

**When Updated:**
- ✅ **When user sets preferences** via preferences API
- Triggered by: User saving preferences (can be added to UI)
- Method: `/api/location/preferences/save` endpoint

**What Gets Stored:**
```json
{
  "id": "7890",
  "location_type": "gym",
  "preferred_activities": ["yoga", "cardio", "weight training"],
  "avoid_activities": ["loud music", "group classes"],
  "preferred_time_of_day": "evening",
  "notes": "I prefer quiet workout times",
  "last_updated": "2025-12-04T10:00:00"
}
```

**Usage:**
- Used by AI to provide contextually relevant recommendations
- Example: "You're at the gym → suggest preferred workout type"

---

## 🔄 Complete Data Flow

```
1. User grants location permission
   ↓
2. Frontend tracks location every 2 minutes
   ↓
3. Each point saved to `location_tracking` table
   • If near saved location (< 100m):
     - Auto-labeled with location_type and location_name
     - Visit counter incremented in `saved_locations`
   ↓
4. User submits mood entry (once or twice daily)
   ↓
5. Backend AUTO-ANALYZES today's location points
   ↓
6. Summary saved to `daily_location_summary` table
   ↓
7. AI receives summary for personalized recommendations
```

---

## ⏰ Timeline Example

**Morning:**
```
07:00 - Location tracked: home
07:02 - Location tracked: home
07:04 - Location tracked: home (visit_count: home +1)
...
07:30 - Location tracked: transit (leaving home)
08:00 - Location tracked: office (arrived_office_time recorded)
```

**Throughout Day:**
```
08:00-17:00 - Location tracked every 2 minutes at office
12:30 - Location tracked: restaurant (lunch)
```

**Evening:**
```
18:00 - Location tracked: gym (time_at_gym starts)
19:30 - Location tracked: transit (leaving gym)
20:00 - Location tracked: home (returned_home_time recorded)
```

**When User Submits Mood (20:30):**
```
20:30 - User submits mood entry
       ↓
       Backend automatically:
       1. Fetches all location points from today (7:00-20:30)
       2. Analyzes patterns
       3. Generates summary:
          • Left home: 07:30
          • Time at office: 9 hours
          • Gym visit: 90 minutes
          • Returned home: 20:00
       4. Saves to `daily_location_summary`
       5. AI uses this context for recommendations
```

---

## 🎯 AI Integration

The AI receives location context in the prompt:

```
LOCATION SUMMARY:
Today's Pattern: Regular workday with gym visit
- Left home at 7:30 AM
- Worked 9 hours at office
- Gym session: 90 minutes
- Home by 8:00 PM
- Total travel: 2 hours

CURRENT LOCATION: Home
TYPICAL ROUTINE: Regularly visits gym in evening

Based on this, AI suggests:
- Post-workout recovery activities
- Home-based relaxation (since user is home)
- Evening wind-down activities
- Tomorrow's preparation suggestions
```

---

## 📱 API Endpoints

### Location Tracking
- `POST /api/location/track` - Track single location point (auto-called every 2 min)
- `POST /api/location/save-place` - Save a labeled location
- `GET /api/location/saved/{user_id}` - Get all saved locations
- `DELETE /api/location/saved/{location_id}` - Delete a saved location

### Daily Summary
- `POST /api/location/analyze-day` - Generate daily summary (manual trigger)
- `GET /api/location/summary/{user_id}` - Get latest daily summary

### Preferences
- `GET /api/location/preferences/{user_id}` - Get user preferences
- `POST /api/location/preferences/save` - Save location preferences

---

## 🔧 Configuration

**Change Tracking Frequency:**
Edit `PermissionsManager.jsx`:
```javascript
// Current: Every 2 minutes
const trackingInterval = setInterval(() => {
  trackLocation();
}, 2 * 60 * 1000);

// Change to 5 minutes:
}, 5 * 60 * 1000);

// Change to 15 minutes:
}, 15 * 60 * 1000);
```

**Change Detection Radius:**
Default is 100m. To change, edit when saving location:
```javascript
radius_meters: 100  // Change to 50, 200, etc.
```

---

## 📊 Database Queries (for debugging)

**Check today's location points:**
```sql
SELECT * FROM location_tracking 
WHERE id = '7890' 
AND DATE(timestamp) = CURRENT_DATE 
ORDER BY timestamp;
```

**Check daily summaries:**
```sql
SELECT * FROM daily_location_summary 
WHERE id = '7890' 
ORDER BY date DESC 
LIMIT 7;
```

**Check saved locations:**
```sql
SELECT location_name, location_type, visit_count, last_visited 
FROM saved_locations 
WHERE id = '7890';
```

---

## 🚀 Summary

| Table | Update Frequency | Trigger | Purpose |
|-------|-----------------|---------|---------|
| `location_tracking` | Every 2 minutes | Automatic | Raw location points |
| `saved_locations` | On user action | Manual | Labeled places |
| `daily_location_summary` | Once per day | Auto (mood submit) | Daily patterns |
| `location_preferences` | On user action | Manual | Activity preferences |

**All systems are working! Just need to submit a mood entry to trigger the daily summary generation.** 🎉

