// FCM Debug Utility
import { getFCMToken } from '../firebase-config';

export const debugFCM = async () => {
  console.log('🔍 FCM Debug Information:');
  
  // Check if service worker is supported
  if ('serviceWorker' in navigator) {
    console.log('✅ Service Worker supported');
    
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) {
        console.log('✅ Service Worker registered:', registration.scope);
      } else {
        console.log('⚠️ No Service Worker registration found');
      }
    } catch (error) {
      console.error('❌ Service Worker check failed:', error);
    }
  } else {
    console.log('❌ Service Worker not supported');
  }
  
  // Check notification permission
  if ('Notification' in window) {
    console.log('✅ Notifications API supported');
    console.log('📋 Notification permission:', Notification.permission);
  } else {
    console.log('❌ Notifications API not supported');
  }
  
  // Check if we're on HTTPS or localhost
  const isSecure = location.protocol === 'https:' || location.hostname === 'localhost';
  console.log('🔒 Secure context:', isSecure);
  
  // Try to get FCM token
  try {
    console.log('🔔 Attempting to get FCM token...');
    const token = await getFCMToken();
    
    if (token) {
      console.log('✅ FCM Token generated successfully!');
      console.log('📝 Token (first 50 chars):', token.substring(0, 50) + '...');
      console.log('📏 Token length:', token.length);
      return token;
    } else {
      console.log('❌ FCM Token generation failed');
      return null;
    }
  } catch (error) {
    console.error('❌ FCM Token error:', error);
    return null;
  }
};

// Add to window for easy debugging
if (typeof window !== 'undefined') {
  window.debugFCM = debugFCM;
}