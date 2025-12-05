-- Create table for storing daily activity recommendations
CREATE TABLE IF NOT EXISTS daily_recommendations (
    id INTEGER NOT NULL,
    date DATE NOT NULL,
    recommendations JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_daily_recommendations_id ON daily_recommendations(id);
CREATE INDEX IF NOT EXISTS idx_daily_recommendations_date ON daily_recommendations(date);
CREATE INDEX IF NOT EXISTS idx_daily_recommendations_generated_at ON daily_recommendations(generated_at);

-- Add comments for documentation
COMMENT ON TABLE daily_recommendations IS 'Stores daily personalized activity recommendations for users';
COMMENT ON COLUMN daily_recommendations.id IS 'User ID (foreign key to users table)';
COMMENT ON COLUMN daily_recommendations.date IS 'Date for which recommendations are generated';
COMMENT ON COLUMN daily_recommendations.recommendations IS 'JSON array of 5 activity recommendations';
COMMENT ON COLUMN daily_recommendations.generated_at IS 'Timestamp when recommendations were generated';
COMMENT ON COLUMN daily_recommendations.data_sources IS 'JSON object indicating which data sources were used';

-- Example of recommendations JSON structure:
-- [
--   {
--     "id": 1,
--     "title": "Morning hydration",
--     "description": "Start your day with a glass of water",
--     "full_text": "Morning hydration - Start your day with a glass of water"
--   },
--   {
--     "id": 2,
--     "title": "Desk stretches",
--     "description": "Do light stretches during work breaks",
--     "full_text": "Desk stretches - Do light stretches during work breaks"
--   }
-- ]

-- Example of data_sources JSON structure:
-- {
--   "calendar_today": true,
--   "calendar_tomorrow": true,
--   "location_data": true,
--   "notification_responses": 3,
--   "habit_data": true
-- }