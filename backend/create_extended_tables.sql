-- Extended database schema for push notifications and calendar integration
-- Run this SQL in your Supabase SQL Editor

-- 1. Add new columns to mood_entries table for optional inputs
ALTER TABLE mood_entries 
ADD COLUMN IF NOT EXISTS audio_url TEXT,
ADD COLUMN IF NOT EXISTS image_url TEXT,
ADD COLUMN IF NOT EXISTS has_audio BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS has_image BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS has_text BOOLEAN DEFAULT FALSE;

-- 2. Create push_notification_responses table
CREATE TABLE IF NOT EXISTS push_notification_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL, -- 'morning' or 'evening'
    emotion_response TEXT, -- e.g., 'energized', 'tired', 'neutral', 'stressed'
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    additional_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_push_responses_user_id ON push_notification_responses(id);
CREATE INDEX IF NOT EXISTS idx_push_responses_timestamp ON push_notification_responses(timestamp);

-- 3. Create calendar_data table
CREATE TABLE IF NOT EXISTS calendar_data (
    calendar_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meeting_count INTEGER DEFAULT 0,
    meeting_hours FLOAT DEFAULT 0,
    free_blocks INTEGER DEFAULT 0,
    earliest_meeting TIME,
    latest_meeting TIME,
    has_lunch_break BOOLEAN DEFAULT TRUE,
    events_summary TEXT,
    calendar_raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_user_id ON calendar_data(id);
CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_data(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_user_date ON calendar_data(id, date);

-- 4. Add calendar and notification columns to report table
ALTER TABLE report 
ADD COLUMN IF NOT EXISTS morning_emotion TEXT,
ADD COLUMN IF NOT EXISTS evening_emotion TEXT,
ADD COLUMN IF NOT EXISTS calendar_summary TEXT;

-- 5. Create push notification settings table (for storing FCM tokens)
CREATE TABLE IF NOT EXISTS push_notification_settings (
    settings_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token TEXT,
    calendar_authorized BOOLEAN DEFAULT FALSE,
    google_refresh_token TEXT,
    morning_notification_time TIME DEFAULT '07:00:00',
    evening_notification_time TIME DEFAULT '19:00:00',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_push_settings_user_id ON push_notification_settings(id);

-- 6. Add Row Level Security (RLS) policies
ALTER TABLE push_notification_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_notification_settings ENABLE ROW LEVEL SECURITY;

-- Allow users to read/write their own data
CREATE POLICY "Users can view own push responses"
    ON push_notification_responses FOR SELECT
    USING (id = current_user);

CREATE POLICY "Users can insert own push responses"
    ON push_notification_responses FOR INSERT
    WITH CHECK (id = current_user);

CREATE POLICY "Users can view own calendar data"
    ON calendar_data FOR SELECT
    USING (id = current_user);

CREATE POLICY "Users can insert own calendar data"
    ON calendar_data FOR INSERT
    WITH CHECK (id = current_user);

CREATE POLICY "Users can update own calendar data"
    ON calendar_data FOR UPDATE
    USING (id = current_user);

CREATE POLICY "Users can view own notification settings"
    ON push_notification_settings FOR SELECT
    USING (id = current_user);

CREATE POLICY "Users can insert own notification settings"
    ON push_notification_settings FOR INSERT
    WITH CHECK (id = current_user);

CREATE POLICY "Users can update own notification settings"
    ON push_notification_settings FOR UPDATE
    USING (id = current_user);

-- 7. Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 8. Create triggers for updated_at
CREATE TRIGGER update_calendar_data_updated_at
    BEFORE UPDATE ON calendar_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_push_notification_settings_updated_at
    BEFORE UPDATE ON push_notification_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Success message
SELECT 'Extended database schema created successfully!' as message;

