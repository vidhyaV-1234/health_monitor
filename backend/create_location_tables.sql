-- Location Tracking Database Schema
-- Run this SQL in your Supabase SQL Editor

-- 1. Location tracking table - stores all location points throughout the day
CREATE TABLE IF NOT EXISTS location_tracking (
    location_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    location_type TEXT, -- 'home', 'office', 'mall', 'hotel', 'restaurant', 'gym', 'park', 'other'
    location_name TEXT,
    address TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accuracy FLOAT, -- GPS accuracy in meters
    activity_type TEXT, -- 'stationary', 'walking', 'running', 'driving', 'in_vehicle'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_location_user_id ON location_tracking(id);
CREATE INDEX IF NOT EXISTS idx_location_timestamp ON location_tracking(timestamp);
CREATE INDEX IF NOT EXISTS idx_location_type ON location_tracking(location_type);

-- 2. Daily location summary table - aggregated daily patterns
CREATE TABLE IF NOT EXISTS daily_location_summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Home data
    left_home_time TIME,
    returned_home_time TIME,
    time_at_home_hours FLOAT,
    
    -- Office/Work data
    arrived_office_time TIME,
    left_office_time TIME,
    time_at_office_hours FLOAT,
    
    -- Travel data
    total_travel_time_minutes FLOAT,
    commute_time_morning_minutes FLOAT,
    commute_time_evening_minutes FLOAT,
    travel_mode TEXT, -- 'driving', 'public_transport', 'walking', 'cycling'
    
    -- Activity data
    visited_locations JSONB, -- Array of {type, name, duration_minutes, time}
    time_at_gym_minutes FLOAT,
    time_at_mall_minutes FLOAT,
    time_at_restaurant_minutes FLOAT,
    time_outdoors_minutes FLOAT,
    
    -- Movement data
    total_distance_km FLOAT,
    active_minutes FLOAT,
    sedentary_minutes FLOAT,
    
    -- Pattern analysis
    routine_type TEXT, -- 'regular_workday', 'work_from_home', 'weekend', 'irregular'
    late_night_out BOOLEAN DEFAULT FALSE,
    skipped_lunch_break BOOLEAN DEFAULT FALSE,
    excessive_commute BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_location_user_id ON daily_location_summary(id);
CREATE INDEX IF NOT EXISTS idx_daily_location_date ON daily_location_summary(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_location_user_date ON daily_location_summary(id, date);

-- 3. Saved locations table - user's frequent places
CREATE TABLE IF NOT EXISTS saved_locations (
    saved_location_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_type TEXT NOT NULL,
    location_name TEXT,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    address TEXT,
    radius_meters FLOAT DEFAULT 100, -- Geofence radius
    auto_detected BOOLEAN DEFAULT FALSE,
    visit_count INTEGER DEFAULT 0,
    last_visited TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_locations_user_id ON saved_locations(id);
CREATE INDEX IF NOT EXISTS idx_saved_locations_type ON saved_locations(location_type);

-- 4. Location preferences table
CREATE TABLE IF NOT EXISTS location_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_tracking_enabled BOOLEAN DEFAULT TRUE,
    track_in_background BOOLEAN DEFAULT TRUE,
    auto_detect_locations BOOLEAN DEFAULT TRUE,
    privacy_mode BOOLEAN DEFAULT FALSE, -- Only stores location types, not exact coordinates
    tracking_frequency_minutes INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_location_prefs_user_id ON location_preferences(id);

-- 5. Add location summary column to report table
ALTER TABLE report 
ADD COLUMN IF NOT EXISTS location_summary TEXT;

-- 6. Enable Row Level Security
ALTER TABLE location_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_location_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_preferences ENABLE ROW LEVEL SECURITY;

-- 7. RLS Policies
-- Note: For custom authentication, you may need to adjust these policies
-- For now, we'll allow all authenticated users to access their own data

CREATE POLICY "Users can view own location tracking"
    ON location_tracking FOR SELECT
    USING (true);

CREATE POLICY "Users can insert own location tracking"
    ON location_tracking FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can view own daily location summary"
    ON daily_location_summary FOR SELECT
    USING (true);

CREATE POLICY "Users can insert own daily location summary"
    ON daily_location_summary FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can update own daily location summary"
    ON daily_location_summary FOR UPDATE
    USING (true);

CREATE POLICY "Users can view own saved locations"
    ON saved_locations FOR SELECT
    USING (true);

CREATE POLICY "Users can manage own saved locations"
    ON saved_locations FOR ALL
    USING (true);

CREATE POLICY "Users can view own location preferences"
    ON location_preferences FOR SELECT
    USING (true);

CREATE POLICY "Users can manage own location preferences"
    ON location_preferences FOR ALL
    USING (true);

-- Note: In production, implement proper RLS with JWT claims
-- Example: USING (id = (current_setting('request.jwt.claims', true)::json->>'user_id')::bigint)

-- 8. Create function to calculate distance between two points (Haversine formula)
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 FLOAT, lon1 FLOAT, lat2 FLOAT, lon2 FLOAT
) RETURNS FLOAT AS $$
DECLARE
    R FLOAT := 6371; -- Earth's radius in km
    dLat FLOAT;
    dLon FLOAT;
    a FLOAT;
    c FLOAT;
BEGIN
    dLat := radians(lat2 - lat1);
    dLon := radians(lon2 - lon1);
    
    a := sin(dLat/2) * sin(dLat/2) + 
         cos(radians(lat1)) * cos(radians(lat2)) * 
         sin(dLon/2) * sin(dLon/2);
    
    c := 2 * atan2(sqrt(a), sqrt(1-a));
    
    RETURN R * c;
END;
$$ LANGUAGE plpgsql;

-- 9. Create trigger to update updated_at timestamp
CREATE TRIGGER update_daily_location_summary_updated_at
    BEFORE UPDATE ON daily_location_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_location_preferences_updated_at
    BEFORE UPDATE ON location_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Success message
SELECT 'Location tracking schema created successfully!' as message;

