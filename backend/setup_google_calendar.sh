#!/bin/bash

# Setup script for Google Calendar API credentials
# Run this to add Google Calendar credentials to your .env file

echo "🔧 Setting up Google Calendar API credentials..."

# Get credentials from user input or JSON file
if [ -f "../client_secret.json" ]; then
    echo "📄 Found client_secret.json file"
    # Extract credentials from JSON file using jq or manual parsing
    GOOGLE_CLIENT_ID=$(grep -o '"client_id":"[^"]*' ../client_secret.json | cut -d'"' -f4)
    GOOGLE_CLIENT_SECRET=$(grep -o '"client_secret":"[^"]*' ../client_secret.json | cut -d'"' -f4)
    GOOGLE_PROJECT_ID=$(grep -o '"project_id":"[^"]*' ../client_secret.json | cut -d'"' -f4)
else
    echo "⚠️  client_secret.json not found in parent directory"
    echo "Please enter your Google Calendar API credentials:"
    read -p "Client ID: " GOOGLE_CLIENT_ID
    read -p "Client Secret: " GOOGLE_CLIENT_SECRET
    read -p "Project ID: " GOOGLE_PROJECT_ID
fi

# Path to .env file
ENV_FILE="$(dirname "$0")/.env"

echo "📝 Updating .env file at: $ENV_FILE"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found. Creating from env.example..."
    if [ -f "$(dirname "$0")/env.example" ]; then
        cp "$(dirname "$0")/env.example" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi
fi

# Function to add or update environment variable
update_env_var() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing variable
        sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        echo "   ✓ Updated ${key}"
    else
        # Add new variable
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "   ✓ Added ${key}"
    fi
}

# Add Google Calendar credentials
echo ""
echo "Adding Google Calendar credentials:"
update_env_var "GOOGLE_CLIENT_ID" "$GOOGLE_CLIENT_ID"
update_env_var "GOOGLE_CLIENT_SECRET" "$GOOGLE_CLIENT_SECRET"
update_env_var "GOOGLE_PROJECT_ID" "$GOOGLE_PROJECT_ID"

# Clean up backup file if it was created
rm -f "${ENV_FILE}.bak"

echo ""
echo "✅ Google Calendar credentials configured!"
echo ""
echo "📋 Credentials added:"
echo "   • Client ID: ${GOOGLE_CLIENT_ID:0:20}..."
echo "   • Client Secret: ${GOOGLE_CLIENT_SECRET:0:15}..."
echo "   • Project ID: $GOOGLE_PROJECT_ID"
echo ""
echo "🚀 Next steps:"
echo "   1. Restart your backend server"
echo "   2. Test calendar integration: python test_calendar_integration.py"
echo "   3. Authorize calendar access via /api/calendar/authorize/{user_id}"
echo ""

