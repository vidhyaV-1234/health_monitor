// Simple FCM Test - Step by step debugging
export const simpleFCMTest = async () => {
  console.log('🧪 SIMPLE FCM TEST STARTED');
  console.log('=' .repeat(50));
  
  // Step 1: Check if we're in a supported environment
  console.log('\n1️⃣ Environment Check');
  console.log(`- Protocol: ${location.protocol}`);
  console.log(`- Hostname: ${location.hostname}`);
  console.log(`- Service Worker support: ${'serviceWorker' in navigator}`);
  console.log(`- Notification support: ${'Notification' in window}`);
  
  if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
    console.error('❌ FCM requires HTTPS or localhost');
    return false;
  }
  
  // Step 2: Check notification permission
  console.log('\n2️⃣ Notification Permission');
  console.log(`- Current permission: ${Notification.permission}`);
  
  if (Notification.permission === 'denied') {
    console.error('❌ Notification permission denied');
    return false;
  }
  
  if (Notification.permission === 'default') {
    console.log('🔄 Requesting notification permission...');
    const permission = await Notification.requestPermission();
    console.log(`- New permission: ${permission}`);
    
    if (permission !== 'granted') {
      console.error('❌ Permission not granted');
      return false;
    }
  }
  
  // Step 3: Register service worker
  console.log('\n3️⃣ Service Worker Registration');
  try {
    let registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      console.log('🔄 Registering service worker...');
      registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      console.log('✅ Service worker registered');
    } else {
      console.log('✅ Service worker already registered');
    }
    
    console.log(`- Scope: ${registration.scope}`);
    console.log(`- State: ${registration.active?.state || 'unknown'}`);
    
    // Wait for service worker to be ready
    await navigator.serviceWorker.ready;
    console.log('✅ Service worker ready');
    
  } catch (error) {
    console.error('❌ Service worker registration failed:', error);
    return false;
  }
  
  // Step 4: Check environment variables
  console.log('\n4️⃣ Environment Variables');
  const requiredVars = [
    'VITE_FIREBASE_API_KEY',
    'VITE_FIREBASE_AUTH_DOMAIN', 
    'VITE_FIREBASE_PROJECT_ID',
    'VITE_FIREBASE_MESSAGING_SENDER_ID',
    'VITE_FIREBASE_APP_ID',
    'VITE_FIREBASE_VAPID_KEY'
  ];
  
  let allVarsPresent = true;
  for (const varName of requiredVars) {
    const value = import.meta.env[varName];
    const present = value && value !== 'undefined' && !value.includes('PASTE_YOUR');
    console.log(`- ${varName}: ${present ? '✅' : '❌'}`);
    if (!present) allVarsPresent = false;
  }
  
  if (!allVarsPresent) {
    console.error('❌ Missing required environment variables');
    return false;
  }
  
  // Step 5: Initialize Firebase and get token
  console.log('\n5️⃣ Firebase Initialization & Token Generation');
  try {
    const { initializeApp } = await import('firebase/app');
    const { getMessaging, getToken, isSupported } = await import('firebase/messaging');
    
    // Check if messaging is supported
    const supported = await isSupported();
    console.log(`- Messaging supported: ${supported ? '✅' : '❌'}`);
    
    if (!supported) {
      console.error('❌ Firebase messaging not supported');
      return false;
    }
    
    // Initialize Firebase
    const firebaseConfig = {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
      measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
    };
    
    console.log('🔄 Initializing Firebase...');
    const app = initializeApp(firebaseConfig);
    console.log('✅ Firebase initialized');
    
    console.log('🔄 Getting messaging instance...');
    const messaging = getMessaging(app);
    console.log('✅ Messaging instance created');
    
    console.log('🔄 Generating FCM token...');
    const token = await getToken(messaging, {
      vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY
    });
    
    if (token) {
      console.log('✅ FCM Token generated successfully!');
      console.log(`- Token length: ${token.length}`);
      console.log(`- Token preview: ${token.substring(0, 50)}...`);
      return token;
    } else {
      console.error('❌ No token received');
      return false;
    }
    
  } catch (error) {
    console.error('❌ Firebase/Token generation failed:', error);
    console.error('Error details:', {
      name: error.name,
      message: error.message,
      code: error.code,
      stack: error.stack
    });
    return false;
  }
};

// Add to window for easy testing
if (typeof window !== 'undefined') {
  window.simpleFCMTest = simpleFCMTest;
}