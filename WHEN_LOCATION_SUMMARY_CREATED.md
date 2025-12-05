# 📍 When Daily Location Summary is Created

## Summary Creation Triggers

The `analyze_daily_locations()` function in `location_tracking_service.py` is called in **2 scenarios**:

---

## 1. ✅ **AUTOMATIC** - When User Submits Mood Entry

**Location:** `backend_api.py` line ~855

**When:** Every time a user submits a mood entry via `/api/mood` endpoint

**Code Flow:**
```python
@app.post("/api/mood")
async def submit_mood(request: Request):
    # ... process mood data ...
    
    # 📍 AUTO-GENERATE DAILY LOCATION SUMMARY
    if location_service:
        today_summary = location_service.analyze_daily_locations(user_id)
        if today_summary:
            location_service.save_daily_summary(user_id, today_summary)
```

**Frequency:** 
- Typically **1-2 times per day** (morning mood + evening mood)
- Only generates summary **once per day** (upsert - updates if exists)

**What Happens:**
1. User submits mood entry (text/audio/image)
2. Backend automatically analyzes all location points from today
3. Generates daily summary with:
   - Time left home / returned home
   - Hours at office, gym, mall, etc.
   - Commute times
   - Total distance traveled
   - Activity levels
4. Saves to `daily_location_summary` table
5. AI uses this context for recommendations

**Example Timeline:**
```
Morning 7:00 AM - User submits mood entry
  ↓
Backend automatically:
  1. Fetches all location points from today (00:00 - 07:00)
  2. Analyzes patterns
  3. Generates partial summary
  4. Saves to database

Evening 7:00 PM - User submits mood entry
  ↓
Backend automatically:
  1. Fetches all location points from today (00:00 - 19:00)
  2. Analyzes complete day
  3. Updates summary with full day data
  4. Saves to database (upsert - replaces morning summary)
```

---

## 2. 🔧 **MANUAL** - Via API Endpoint

**Location:** `backend_api.py` line ~1488

**Endpoint:** `POST /api/location/analyze-day`

**When:** User or system explicitly calls this endpoint

**Usage:**
```bash
POST /api/location/analyze-day
Content-Type: application/x-www-form-urlencoded

user_id=7890
date=2025-12-04  # Optional - defaults to today
```

**Use Cases:**
- Manual trigger for testing
- Scheduled job to generate summaries
- Backfill historical data
- Regenerate summary if needed

**Response:**
```json
{
  "status": "success",
  "data": {
    "date": "2025-12-04",
    "left_home_time": "07:30:00",
    "returned_home_time": "20:00:00",
    "time_at_home_hours": 14.5,
    "time_at_office_hours": 9.0,
    ...
  }
}
```

---

## 📊 Summary Generation Process

### Step 1: Fetch Location Points
```python
# Gets all location_tracking entries for the day
result = supabase.table("location_tracking")\
    .select("*")\
    .eq("id", user_id)\
    .gte("timestamp", start_of_day)\
    .lte("timestamp", end_of_day)\
    .order("timestamp")\
    .execute()
```

### Step 2: Analyze Patterns
- Detects location changes (home → office → gym → home)
- Calculates time spent at each location
- Identifies commute times
- Calculates total distance
- Determines activity levels

### Step 3: Generate Summary
Creates summary dictionary with:
- Home/office arrival/departure times
- Hours spent at each location type
- Commute analysis
- Activity metrics
- Routine type detection

### Step 4: Save to Database
```python
# Upsert - updates if exists, inserts if new
supabase.table("daily_location_summary").upsert(data).execute()
```

---

## ⏰ Typical Daily Flow

```
00:00 - Day starts
  ↓
Every 2 minutes:
  📍 Location tracked → saved to location_tracking
  ↓
07:00 AM - User submits morning mood
  ↓
✅ AUTO-TRIGGER: analyze_daily_locations()
  • Analyzes 7 hours of data (00:00 - 07:00)
  • Generates partial summary
  • Saves to daily_location_summary
  ↓
07:00 - 19:00 - Continue tracking every 2 minutes
  ↓
19:00 PM - User submits evening mood
  ↓
✅ AUTO-TRIGGER: analyze_daily_locations()
  • Analyzes full day (00:00 - 19:00)
  • Generates complete summary
  • Updates daily_location_summary (upsert)
  ↓
AI uses summary for personalized recommendations
```

---

## 🎯 Key Points

1. **Automatic**: Summary is generated automatically when mood is submitted
2. **Once Per Day**: Uses upsert, so only one summary per day (last one wins)
3. **No Manual Action Needed**: User just submits mood, summary happens automatically
4. **Complete Data**: Evening mood submission generates full day summary
5. **AI Integration**: Summary is used in AI prompt for contextual recommendations

---

## 🔍 Checking Summary Status

**Query latest summary:**
```sql
SELECT * FROM daily_location_summary 
WHERE id = '7890' 
ORDER BY date DESC 
LIMIT 1;
```

**Check if summary exists for today:**
```python
GET /api/location/summary/7890
```

**Manually trigger summary:**
```bash
POST /api/location/analyze-day
user_id=7890
```

---

## ✅ Summary

**When is summary created?**
- ✅ **Automatically** when user submits mood entry (1-2x daily)
- ✅ **Manually** via `/api/location/analyze-day` endpoint

**No action needed from user** - just submit mood entries and the summary is generated automatically! 🎉

