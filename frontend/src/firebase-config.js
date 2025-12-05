// Firebase configuration for FCM (Firebase Cloud Messaging)
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

// Firebase configuration - Replace with your actual Firebase project config
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "your-app-id",
  measurementId: "G-XXXXXXXXXX"
};

// Initialize Firebase
let app;
let messaging;

try {
  app = initializeApp(firebaseConfig);
  
  // Initialize Firebase Cloud Messaging and get a reference to the service
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    messaging = getMessaging(app);
  }
} catch (error) {
  console.error('Firebase initialization error:', error);
}

export { messaging };
export default app;

// VAPID key for web push notifications
// Get this from Firebase Console > Project Settings > Cloud Messaging > Web configuration
export const VAPID_KEY = 'your-vapid-key-here';

// Function to get FCM token
export const getFCMToken = async () => {
  if (!messaging) {
    console.warn('Firebase messaging not initialized');
    return null;
  }

  try {
    // Request permission for notifications
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      console.warn('Notification permission not granted');
      return null;
    }

    // Get FCM token
    const token = await getToken(messaging, {
      vapidKey: VAPID_KEY
    });
    
    if (token) {
      console.log('FCM Token generated:', token);
      return token;
    } else {
      console.warn('No registration token available');
      return null;
    }
  } catch (error) {
    console.error('Error getting FCM token:', error);
    return null;
  }
};

// Handle foreground messages
if (messaging) {
  onMessage(messaging, (payload) => {
    console.log('Message received in foreground:', payload);
    
    // Show notification to user
    if (payload.notification) {
      const { title, body } = payload.notification;
      
      // Create a custom notification or use browser notification
      if (Notification.permission === 'granted') {
        new Notification(title, {
          body: body,
          icon: '/favicon.ico',
          badge: '/favicon.ico'
        });
      }
    }
  });
}