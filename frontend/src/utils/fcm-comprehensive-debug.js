// Comprehensive FCM Debug Utility
import { getFCMToken } from '../firebase-config';

export const comprehensiveFCMDebug = async () => {
  console.log('🔍 COMPREHENSIVE FCM DEBUG STARTED');
  console.log('=' .repeat(60));
  
  const results = {
    environment: {},
    permissions: {},
    firebase: {},
    serviceWorker: {},
    token: null,
    errors: []
  };

  // 1. Check Environment Variables
  console.log('\n1️⃣ CHECKING ENVIRONMENT VARIABLES');
  console.log('-'.repeat(40));
  
  const envVars = {
    'VITE_FIREBASE_API_KEY': import.meta.env.VITE_FIREBASE_API_KEY,
    'VITE_FIREBASE_AUTH_DOMAIN': import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    'VITE_FIREBASE_PROJECT_ID': import.meta.env.VITE_FIREBASE_PROJECT_ID,
    'VITE_FIREBASE_STORAGE_BUCKET': import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    'VITE_FIREBASE_MESSAGING_SENDER_ID': import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    'VITE_FIREBASE_APP_ID': import.meta.env.VITE_FIREBASE_APP_ID,
    'VITE_FIREBASE_VAPID_KEY': import.meta.env.VITE_FIREBASE_VAPID_KEY
  };

  for (const [key, value] of Object.entries(envVars)) {
    const status = value && value !== 'undefined' && !value.includes('PASTE_YOUR') ? '✅' : '❌';
    const displayValue = value ? (value.length > 20 ? value.substring(0, 20) + '...' : value) : 'NOT SET';
    console.log(`${status} ${key}: ${displayValue}`);
    results.environment[key] = { value: displayValue, valid: status === '✅' };
  }

  // 2. Check Browser Support
  console.log('\n2️⃣ CHECKING BROWSER SUPPORT');
  console.log('-'.repeat(40));
  
  const browserChecks = {
    'Service Worker': 'serviceWorker' in navigator,
    'Notifications API': 'Notification' in window,
    'Push Manager': 'PushManager' in window,
    'HTTPS/Localhost': location.protocol === 'https:' || location.hostname === 'localhost'
  };

  for (const [feature, supported] of Object.entries(browserChecks)) {
    const status = supported ? '✅' : '❌';
    console.log(`${status} ${feature}: ${supported}`);
    results.permissions[feature] = supported;
  }

  // 3. Check Notification Permission
  console.log('\n3️⃣ CHECKING NOTIFICATION PERMISSION');
  console.log('-'.repeat(40));
  
  if ('Notification' in window) {
    console.log(`📋 Current permission: ${Notification.permission}`);
    results.permissions.notificationPermission = Notification.permission;
    
    if (Notification.permission === 'default') {
      console.log('⚠️ Permission not requested yet');
    } else if (Notification.permission === 'denied') {
      console.log('❌ Permission denied - FCM tokens cannot be generated');
      results.errors.push('Notification permission denied');
    } else {
      console.log('✅ Permission granted');
    }
  }

  // 4. Check Service Worker Registration
  console.log('\n4️⃣ CHECKING SERVICE WORKER');
  console.log('-'.repeat(40));
  
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) {
        console.log('✅ Service Worker registered');
        console.log(`   Scope: ${registration.scope}`);
        console.log(`   State: ${registration.active?.state || 'unknown'}`);
        results.serviceWorker.registered = true;
        results.serviceWorker.scope = registration.scope;
      } else {
        console.log('❌ No Service Worker registration found');
        results.serviceWorker.registered = false;
        results.errors.push('Service Worker not registered');
      }
    } catch (error) {
      console.log('❌ Service Worker check failed:', error.message);
      results.serviceWorker.error = error.message;
      results.errors.push(`Service Worker error: ${error.message}`);
    }
  }

  // 5. Test Firebase Configuration
  console.log('\n5️⃣ TESTING FIREBASE CONFIGURATION');
  console.log('-'.repeat(40));
  
  try {
    // Import Firebase modules to test
    const { initializeApp } = await import('firebase/app');
    const { getMessaging, isSupported } = await import('firebase/messaging');
    
    // Check if messaging is supported
    const messagingSupported = await isSupported();
    console.log(`📱 Firebase Messaging supported: ${messagingSupported ? '✅' : '❌'}`);
    results.firebase.messagingSupported = messagingSupported;
    
    if (!messagingSupported) {
      results.errors.push('Firebase Messaging not supported in this browser');
    }
    
    // Test Firebase config
    const firebaseConfig = {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
      measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
    };
    
    // Validate config
    const requiredFields = ['apiKey', 'authDomain', 'projectId', 'messagingSenderId', 'appId'];
    const missingFields = requiredFields.filter(field => !firebaseConfig[field]);
    
    if (missingFields.length > 0) {
      console.log(`❌ Missing Firebase config fields: ${missingFields.join(', ')}`);
      results.errors.push(`Missing Firebase config: ${missingFields.join(', ')}`);
    } else {
      console.log('✅ Firebase config appears complete');
      results.firebase.configValid = true;
    }
    
  } catch (error) {
    console.log('❌ Firebase import/test failed:', error.message);
    results.firebase.error = error.message;
    results.errors.push(`Firebase error: ${error.message}`);
  }

  // 6. Test VAPID Key
  console.log('\n6️⃣ TESTING VAPID KEY');
  console.log('-'.repeat(40));
  
  const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY;
  if (!vapidKey || vapidKey.includes('PASTE_YOUR')) {
    console.log('❌ VAPID key not configured');
    results.errors.push('VAPID key not configured');
  } else if (!vapidKey.startsWith('B')) {
    console.log('❌ VAPID key format invalid (should start with B)');
    results.errors.push('VAPID key format invalid');
  } else {
    console.log(`✅ VAPID key configured: ${vapidKey.substring(0, 10)}...`);
    results.firebase.vapidKeyValid = true;
  }

  // 7. Test FCM Token Generation
  console.log('\n7️⃣ TESTING FCM TOKEN GENERATION');
  console.log('-'.repeat(40));
  
  try {
    console.log('🔄 Attempting to generate FCM token...');
    const token = await getFCMToken();
    
    if (token) {
      console.log('✅ FCM Token generated successfully!');
      console.log(`📝 Token length: ${token.length} characters`);
      console.log(`📝 Token preview: ${token.substring(0, 50)}...`);
      results.token = token;
    } else {
      console.log('❌ FCM Token generation returned null');
      results.errors.push('FCM token generation returned null');
    }
  } catch (error) {
    console.log('❌ FCM Token generation failed:', error.message);
    results.errors.push(`FCM token generation failed: ${error.message}`);
  }

  // 8. Summary
  console.log('\n8️⃣ SUMMARY');
  console.log('='.repeat(60));
  
  if (results.errors.length === 0) {
    console.log('🎉 ALL CHECKS PASSED! FCM should be working.');
  } else {
    console.log('❌ ISSUES FOUND:');
    results.errors.forEach((error, index) => {
      console.log(`   ${index + 1}. ${error}`);
    });
    
    console.log('\n🔧 RECOMMENDED FIXES:');
    if (results.errors.some(e => e.includes('permission'))) {
      console.log('   • Allow notifications in browser settings');
    }
    if (results.errors.some(e => e.includes('Service Worker'))) {
      console.log('   • Check if firebase-messaging-sw.js exists in public folder');
    }
    if (results.errors.some(e => e.includes('VAPID'))) {
      console.log('   • Get VAPID key from Firebase Console > Cloud Messaging');
    }
    if (results.errors.some(e => e.includes('Firebase config'))) {
      console.log('   • Check Firebase project configuration');
    }
  }
  
  console.log('\n' + '='.repeat(60));
  return results;
};

// Add to window for easy access
if (typeof window !== 'undefined') {
  window.comprehensiveFCMDebug = comprehensiveFCMDebug;
}