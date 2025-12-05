# Firebase FCM Setup Guide

## 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or "Add project"
3. Enter your project name (e.g., "health-monitor")
4. Enable Google Analytics (optional)
5. Click "Create project"

## 2. Enable Cloud Messaging

1. In your Firebase project, go to **Project Settings** (gear icon)
2. Click on the **Cloud Messaging** tab
3. Under **Web configuration**, click **Generate key pair** to create a VAPID key
4. Copy the VAPID key (you'll need this later)

## 3. Get Firebase Configuration

1. In **Project Settings**, go to the **General** tab
2. Scroll down to **Your apps** section
3. Click **Add app** and select **Web** (</> icon)
4. Register your app with a nickname (e.g., "health-monitor-web")
5. Copy the Firebase configuration object

## 4. Update Configuration Files

### Update `frontend/src/firebase-config.js`:

Replace the placeholder values with your actual Firebase config:

```javascript
const firebaseConfig = {
  apiKey: "your-actual-api-key",
  authDomain: "your-project-id.firebaseapp.com",
  projectId: "your-actual-project-id",
  storageBucket: "your-project-id.appspot.com",
  messagingSenderId: "your-actual-sender-id",
  appId: "your-actual-app-id",
  measurementId: "G-XXXXXXXXXX" // Optional
};

// Replace with your actual VAPID key
export const VAPID_KEY = 'your-actual-vapid-key-from-step-2';
```

### Update `frontend/public/firebase-messaging-sw.js`:

Replace the firebaseConfig object with the same values as above.

## 5. Test FCM Token Generation

1. Start your frontend development server
2. Open browser developer tools (F12)
3. Go to the Console tab
4. Enable notifications in your app
5. Look for console messages like:
   - "🔔 Attempting to get FCM token..."
   - "✅ FCM token obtained: [token]..."

## 6. Backend Configuration (Optional)

If you want to send actual push notifications from your backend, you'll need:

1. Go to **Project Settings** > **Service accounts**
2. Click **Generate new private key**
3. Download the JSON file
4. Add the path to this file in your backend environment variables

## Troubleshooting

### Common Issues:

1. **"Firebase is not configured" error**:
   - Make sure you've replaced all placeholder values in both config files
   - Check that VAPID_KEY is set correctly

2. **"Registration token not available" error**:
   - Ensure you're running on HTTPS (or localhost for development)
   - Check that notifications permission is granted
   - Verify your VAPID key is correct

3. **Service worker not registering**:
   - Make sure `firebase-messaging-sw.js` is in the `public` folder
   - Check browser console for service worker errors

### Development Mode:

If Firebase is not configured, the app will fall back to mock tokens for development. You'll see:
- "⚠️ Notifications enabled with mock token (Firebase not configured)"

This allows you to test the notification flow without Firebase setup.

## Testing Notifications

Once configured, you can test notifications by:

1. Enabling notifications in the app
2. Checking the backend logs to see if FCM tokens are being registered
3. Using Firebase Console to send test messages
4. Running the backend notification schedulers

## Security Notes

- Never commit your Firebase private key to version control
- Use environment variables for sensitive configuration
- Restrict your Firebase API keys to specific domains in production