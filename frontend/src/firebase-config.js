// Firebase configuration for FCM (Firebase Cloud Messaging)
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

// Firebase configuration using environment variables (secure)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};



// Initialize Firebase
let app;
let messaging;

try {
  // Validate configuration first
  const requiredFields = ['apiKey', 'authDomain', 'projectId', 'messagingSenderId', 'appId'];
  const missingFields = requiredFields.filter(field => !firebaseConfig[field]);
  
  if (missingFields.length > 0) {
    throw new Error(`Missing Firebase config fields: ${missingFields.join(', ')}`);
  }

  app = initializeApp(firebaseConfig);
  console.log('✅ Firebase app initialized');

  // Initialize Firebase Cloud Messaging and get a reference to the service
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    messaging = getMessaging(app);
    console.log('✅ Firebase messaging initialized');
  } else {
    console.warn('⚠️ Service Worker not supported or not in browser environment');
  }
} catch (error) {
  console.error('❌ Firebase initialization error:', error);
}

export { messaging };
export default app;

// VAPID key for web push notifications
// Get this from Firebase Console > Project Settings > Cloud Messaging > Web configuration
export const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY;

// Function to register service worker
const registerServiceWorker = async () => {
  if (!('serviceWorker' in navigator)) {
    throw new Error('Service Worker not supported');
  }

  try {
    let registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      console.log('Registering service worker...');
      registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      console.log('Service worker registered successfully');
    }
    
    // Wait for service worker to be ready
    await navigator.serviceWorker.ready;
    return registration;
  } catch (error) {
    console.error('Service worker registration failed:', error);
    throw error;
  }
};

// Function to get FCM token
export const getFCMToken = async () => {
  console.log('🔄 Starting FCM token generation...');
  
  if (!messaging) {
    console.error('❌ Firebase messaging not initialized');
    return null;
  }

  if (!VAPID_KEY) {
    console.error('❌ VAPID key not configured');
    return null;
  }

  try {
    // First, register the service worker
    console.log('🔄 Registering service worker...');
    await registerServiceWorker();
    console.log('✅ Service worker registered');
    
    // Request permission for notifications
    console.log('🔄 Requesting notification permission...');
    const permission = await Notification.requestPermission();
    console.log(`📋 Permission result: ${permission}`);
    
    if (permission !== 'granted') {
      console.warn('❌ Notification permission not granted');
      return null;
    }

    // Validate VAPID key format
    if (!VAPID_KEY.startsWith('B') || VAPID_KEY.length < 80) {
      console.error('❌ Invalid VAPID key format');
      return null;
    }

    // Get FCM token
    console.log('🔄 Generating FCM token with VAPID key...');
    const token = await getToken(messaging, {
      vapidKey: VAPID_KEY
    });

    if (token) {
      console.log('✅ FCM Token generated successfully!');
      console.log(`📝 Token length: ${token.length} characters`);
      console.log(`📝 Token preview: ${token.substring(0, 50)}...`);
      return token;
    } else {
      console.warn('❌ No registration token available - this usually means:');
      console.warn('   • Service worker not properly registered');
      console.warn('   • VAPID key mismatch');
      console.warn('   • Firebase project configuration issue');
      return null;
    }
  } catch (error) {
    console.error('❌ Error getting FCM token:', error);
    
    // Provide specific error guidance
    if (error.code === 'messaging/invalid-vapid-key') {
      console.error('🔑 VAPID key is invalid. Check Firebase Console > Project Settings > Cloud Messaging');
    } else if (error.code === 'messaging/registration-token-not-registered') {
      console.error('📱 Registration token not registered. Try clearing browser data and retry.');
    } else if (error.code === 'messaging/permission-blocked') {
      console.error('🚫 Notification permission blocked. Enable in browser settings.');
    } else if (error.message?.includes('service worker')) {
      console.error('⚙️ Service worker issue. Check if firebase-messaging-sw.js exists in public folder.');
    }
    
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