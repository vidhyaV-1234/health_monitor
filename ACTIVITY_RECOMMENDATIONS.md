# Activity Recommendations System

## Overview

The Activity Recommendations System generates 5 personalized daily activity recommendations based on comprehensive user data including calendar schedules, location patterns, push notification responses, and user habits. **Recommendations are sent directly as push notifications to users' devices.**

## 🎯 Key Features

- **Daily 11:10 PM Schedule**: Automatically runs at 11:10 PM daily (currently set for testing)
- **5 Personalized Recommendations**: AI-generated activities tailored to each user
- **Multi-Source Data Integration**: Uses calendar, location, notifications, and habits
- **Smart Scheduling**: Considers today's and tomorrow's calendar for optimal timing
- **Stress Tracking**: Monitors stress levels and provides appropriate recommendations
- **Push Notification Delivery**: Sends recommendations directly to user devices
- **API Endpoints**: RESTful API for frontend integration

## 📅 Daily 11:10 PM Workflow (Testing Schedule)

### 1. Calendar Data Fetch ✅
- Fetches today's and tomorrow's calendar events
- Analyzes meeting count, hours, and free time blocks
- Stores data in `calendar_data` table

### 2. Location Summary Creation ✅
- Analyzes daily location patterns
- Tracks home/office/gym visits and commute times
- Creates summary in `daily_location_summary` table

### 3. Push Notification Sent ✅
- Sends morning mood check notification
- Collects user's emotional state response
- Stores responses in `push_notification_responses` table

### 4. Activity Recommendations Generation 🆕
- **NEW**: Collects all available user data
- Generates 5 personalized activity recommendations using AI
- Considers calendar schedule, location patterns, and mood
- **Sends recommendations as push notification to user's device** 📱

## 🔄 Data Flow

```
11:10 PM Daily Trigger (Testing Schedule)
├── 1. Fetch Calendar Data (today + tomorrow)
├── 2. Analyze Location Patterns
├── 3. Send Push Notification (mood check)
└── 4. Generate Activity Recommendations
    ├── Collect: Calendar + Location + Notifications + Habits
    ├── AI Analysis: AWS Bedrock Claude 3.5 Sonnet
    ├── Generate: 5 personalized activities
    └── Send: Push notification with recommendations 📱
```

## 📱 Push Notification Format

### Recommendation Notification Structure

The 5 recommendations are sent as a single push notification with this format:

```json
{
  "title": "🎯 Your Daily Activity Recommendations",
  "body": "Here are 5 personalized activities for today:\n\n1. Morning hydration - Start your day with water\n2. Desk stretches - Do light stretches during breaks\n3. Lunch walk - Take a 15-minute outdoor walk\n4. Evening stretch - Ease tension after work\n5. Early sleep prep - Prepare for tomorrow's busy day",
  "data": {
    "type": "daily_recommendations",
    "user_id": "1",
    "timestamp": "2025-01-12T23:10:00Z",
    "recommendations_count": 5
  }
}
```

### Individual Recommendation Structure (Internal)

```json
[
  {
    "id": 1,
    "title": "Morning hydration",
    "description": "Start your day with a glass of water",
    "full_text": "Morning hydration - Start your day with a glass of water"
  },
  {
    "id": 2,
    "title": "Desk stretches", 
    "description": "Do light stretches during work breaks",
    "full_text": "Desk stretches - Do light stretches during work breaks"
  }
  // ... 3 more recommendations
]
```

## 🚀 API Endpoints

### Generate Recommendations
```http
POST /api/recommendations/generate/{user_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "user_id": "1",
  "recommendations": [...],
  "mood": "neutral",
  "stress_level": 2,
  "stress_day": 1,
  "generated_at": "2025-01-12T07:00:00Z",
  "data_sources": {
    "calendar_today": true,
    "calendar_tomorrow": true,
    "location_data": true,
    "notification_responses": 3,
    "habit_data": true
  }
}
```

### Get Latest Recommendations
```http
GET /api/recommendations/latest/{user_id}
Authorization: Bearer <jwt_token>
```

### Get Recommendations History
```http
GET /api/recommendations/history/{user_id}?limit=7
Authorization: Bearer <jwt_token>
```

## 🧠 AI Recommendation Logic

The system uses **AWS Bedrock Claude 3.5 Sonnet** to generate recommendations based on:

### Input Data Sources
1. **Calendar Data** (Today & Tomorrow)
   - Meeting count and duration
   - Free time blocks
   - Lunch breaks
   - Event summaries

2. **Location Patterns**
   - Daily routine type
   - Commute times
   - Office/gym/outdoor time
   - Travel distance

3. **Push Notification Responses**
   - Recent mood check-ins
   - Morning/evening emotions
   - Stress indicators

4. **User Habits & Preferences**
   - Sleep patterns
   - Exercise preferences
   - Hobbies and interests
   - Social preferences

### Recommendation Categories
1. **Physical Wellness** - Exercise, stretching, hydration
2. **Mental Wellness** - Relaxation, breathing, mindfulness
3. **Hobby/Creative** - Personal interests and creative activities
4. **Social Connection** - Social interactions or self-care
5. **Healthy Routine** - Nutrition, sleep, productivity tips

### Smart Timing Logic
- **Busy Today**: Suggests quick 5-10 minute activities
- **Free Time Today**: Suggests longer 30-60 minute activities
- **Busy Tomorrow**: Suggests preparation activities today (early sleep, meal prep)
- **Long Commute**: Suggests audio content or breathing exercises
- **Low Outdoor Time**: Suggests fresh air activities
- **High Stress**: Suggests relaxation and stress-reduction activities

## 🔧 Configuration & Setup

### 1. Environment Variables
Ensure these are set in your `.env` file:
```bash
# AWS Bedrock (for AI recommendations)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Supabase (for data storage)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 2. Database Setup
Run the SQL script to create the recommendations table:
```bash
# Execute the SQL file in your Supabase dashboard
cat backend/create_recommendations_table.sql
```

### 3. Start the Scheduler
```bash
cd backend
python run_schedulers.py
# Choose option 2 for continuous scheduler
```

## 🧪 Testing

### Test Individual User
```bash
cd backend
python test_recommendations.py
```

### Test via API
```bash
# Generate recommendations for user 1
curl -X POST "http://localhost:8000/api/recommendations/generate/1" \
  -H "Authorization: Bearer <your_jwt_token>"

# Get latest recommendations
curl "http://localhost:8000/api/recommendations/latest/1" \
  -H "Authorization: Bearer <your_jwt_token>"
```

## 📊 Monitoring & Logs

### Scheduler Logs
- File: `backend/schedulers.log`
- Shows daily execution results
- Tracks success/failure rates

### Log Example
```
2025-01-12 07:00:00 - RUNNING SCHEDULED ACTIVITY RECOMMENDATIONS
2025-01-12 07:00:01 - Found 3 eligible users
2025-01-12 07:00:05 - ✅ User 1: 5 recommendations generated
2025-01-12 07:00:08 - ✅ User 2: 5 recommendations generated
2025-01-12 07:00:10 - ❌ User 3: No calendar data available
2025-01-12 07:00:10 - SUMMARY: Total: 3, Successful: 2, Failed: 1
```

## 🚀 Deployment

### Render Deployment
The system is configured for Render deployment with:
- `render.yaml` configuration
- Automatic daily scheduling
- Environment variable management
- Database integration

### Manual Deployment Steps
1. Deploy backend with environment variables
2. Run database migration (create_recommendations_table.sql)
3. Start the scheduler service
4. Verify API endpoints are accessible

## 🔮 Future Enhancements

1. **Recommendation Feedback**: Track user completion and satisfaction
2. **Machine Learning**: Improve recommendations based on user behavior
3. **Weather Integration**: Consider weather conditions for outdoor activities
4. **Social Features**: Group activities and challenges
5. **Wearable Integration**: Use fitness tracker data for better recommendations
6. **Notification Delivery**: Send recommendations via push notifications

## 📝 Example Recommendations

### For a Busy Professional
```
1. Morning hydration - Start your day with a glass of water before your 9 AM meeting
2. Desk breathing - Take 3 deep breaths between your back-to-back meetings
3. Lunch walk - Use your 30-minute lunch break for a quick outdoor walk
4. Evening stretch - After your 6 PM finish, do light stretches to ease tension
5. Early sleep prep - Since tomorrow has 6 meetings, prepare for bed 30 minutes early
```

### For a Flexible Schedule
```
1. Morning yoga - Start with 20 minutes of gentle yoga in your free morning
2. Creative time - Spend 45 minutes on your photography hobby this afternoon
3. Social connection - Call a friend during your 2-hour free block
4. Outdoor activity - Take advantage of good weather for a nature walk
5. Meal prep - Prepare healthy meals for tomorrow's busy schedule
```

## 🎯 Success Metrics

- **Daily Generation Rate**: % of eligible users receiving recommendations
- **Data Completeness**: % of users with all data sources available
- **API Response Time**: Average time to generate recommendations
- **User Engagement**: Future metric for recommendation completion rates

---

**Status**: ✅ **IMPLEMENTED AND READY**

The Activity Recommendations System is now fully integrated into the 7 AM daily workflow and ready for production use.