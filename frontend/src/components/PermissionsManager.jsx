import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import LocationManager from "./LocationManager";
import { getFCMToken } from "../firebase-config";

export default function PermissionsManager({ userId }) {
  const [permissions, setPermissions] = useState({
    location: null,
    notifications: null,
    calendar: null
  });
  
  const [tracking, setTracking] = useState({
    locationEnabled: false,
    notificationsEnabled: false,
    calendarConnected: false
  });

  const [locationData, setLocationData] = useState(null);
  const [showLocationData, setShowLocationData] = useState(false);
  const [showLocationManager, setShowLocationManager] = useState(false);
  const [currentLocationLabel, setCurrentLocationLabel] = useState(null);

  const token = localStorage.getItem("token");

  // Check current permissions on mount and start tracking if enabled
  useEffect(() => {
    checkPermissions();
    
    // Start location tracking if permission was already granted
    if ('geolocation' in navigator && userId && token) {
      navigator.permissions.query({ name: 'geolocation' }).then((result) => {
        if (result.state === 'granted') {
          console.log('📍 Location permission already granted, starting tracking...');
          startLocationTracking();
          setTracking(prev => ({ ...prev, locationEnabled: true }));
        }
      }).catch(() => {
        // Permission query not supported, try to start anyway if we have userId/token
        console.log('📍 Permission query not supported, attempting to start tracking...');
        // Don't auto-start without explicit permission
      });
    }
  }, [userId, token]);

  const checkPermissions = async () => {
    // Check Geolocation API
    if ('geolocation' in navigator) {
      navigator.permissions.query({ name: 'geolocation' }).then((result) => {
        setPermissions(prev => ({ ...prev, location: result.state }));
      }).catch(() => {
        setPermissions(prev => ({ ...prev, location: 'unknown' }));
      });
    }

    // Check Notification API
    if ('Notification' in window) {
      setPermissions(prev => ({ ...prev, notifications: Notification.permission }));
    }

    // Check if calendar is connected (from backend)
    if (userId) {
      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/calendar/check/${userId}`,
          { headers: { Authorization: `Bearer ${token}` }}
        );
        // Check if authorized and has token
        const isConnected = response.data.status === 'success' && response.data.authorized === true;
        console.log('📅 Calendar check result:', {
          status: response.data.status,
          authorized: response.data.authorized,
          has_token: response.data.has_token,
          isConnected
        });
        setTracking(prev => ({ ...prev, calendarConnected: isConnected }));
      } catch (error) {
        console.error("❌ Calendar check error:", error);
        console.error("Response:", error.response?.data);
        setTracking(prev => ({ ...prev, calendarConnected: false }));
      }
    }
  };

  // Request Location Permission
  const requestLocationPermission = async () => {
    if (!('geolocation' in navigator)) {
      alert('Geolocation is not supported by your browser');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        console.log('✓ Location permission granted');
        setPermissions(prev => ({ ...prev, location: 'granted' }));
        
        // Save user's home location automatically
        try {
          await axios.post(
            `${API_BASE_URL}/api/location/save-place`,
            new URLSearchParams({
              user_id: userId,
              location_type: 'home',
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              location_name: 'My Home',
              radius_meters: 100
            }),
            { headers: { Authorization: `Bearer ${token}` }}
          );
          
          alert('✅ Location permission granted! Your home location has been saved.');
          setTracking(prev => ({ ...prev, locationEnabled: true }));
          
          // Start background tracking
          startLocationTracking();
        } catch (error) {
          console.error('Error saving location:', error);
        }
      },
      (error) => {
        console.error('Location permission denied:', error);
        setPermissions(prev => ({ ...prev, location: 'denied' }));
        alert('Location permission denied. You can enable it in your browser settings.');
      }
    );
  };

  // Start continuous location tracking
  const startLocationTracking = () => {
    if (!('geolocation' in navigator)) {
      console.warn('📍 Geolocation not supported');
      return;
    }

    // Clear any existing interval
    if (window.locationTrackingInterval) {
      clearInterval(window.locationTrackingInterval);
    }

    console.log('📍 Starting location tracking (every 2 minutes)');

    // Track immediately
    trackLocation();

    // Then track every 2 minutes (for testing - change to 5 minutes in production)
    const trackingInterval = setInterval(() => {
      console.log('📍 Scheduled location track triggered');
      trackLocation();
    }, 2 * 60 * 1000); // Every 2 minutes

    // Save interval ID to stop later if needed
    window.locationTrackingInterval = trackingInterval;
    console.log('✅ Location tracking started, interval ID:', trackingInterval);
  };

  // Helper function to track location
  const trackLocation = async () => {
    if (!userId || !token) {
      console.warn('📍 Cannot track location: missing userId or token');
      return;
    }

    console.log('📍 Getting current position...');
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          console.log('📍 Position obtained:', {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy
          });

          const response = await axios.post(
            `${API_BASE_URL}/api/location/track`,
            new URLSearchParams({
              user_id: userId,
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            }),
            { headers: { Authorization: `Bearer ${token}` }}
          );
          
          console.log('✅ Location tracked successfully:', {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            response: response.data
          });
          
          // Get the most recent tracked location to show label
          try {
            const trackedResponse = await axios.get(
              `${API_BASE_URL}/api/location/summary/${userId}`,
              { headers: { Authorization: `Bearer ${token}` }}
            );
            
            if (trackedResponse.data && trackedResponse.data.current_location) {
              setCurrentLocationLabel(trackedResponse.data.current_location);
            }
          } catch (err) {
            console.log('ℹ️ Could not get location label:', err.message);
          }
        } catch (error) {
          console.error('❌ Error tracking location:', error);
          console.error('Error details:', error.response?.data || error.message);
        }
      },
      (error) => {
        console.error('❌ Geolocation error:', error.code, error.message);
        if (error.code === 1) {
          console.error('   Permission denied');
        } else if (error.code === 2) {
          console.error('   Position unavailable');
        } else if (error.code === 3) {
          console.error('   Timeout');
        }
      },
      { 
        enableHighAccuracy: true, 
        timeout: 10000, 
        maximumAge: 60000 // 1 minute cache
      }
    );
  };

  // Request Notification Permission
  const requestNotificationPermission = async () => {
    if (!('Notification' in window)) {
      alert('This browser does not support notifications');
      return;
    }

    if (Notification.permission === 'granted') {
      registerForNotifications();
      return;
    }

    const permission = await Notification.requestPermission();
    setPermissions(prev => ({ ...prev, notifications: permission }));

    if (permission === 'granted') {
      registerForNotifications();
    } else {
      alert('Notification permission denied. You can enable it in browser settings.');
    }
  };

  // Register for push notifications (requires FCM setup)
  const registerForNotifications = async () => {
    try {
      console.log('🔔 Attempting to get FCM token...');
      
      // Get real FCM token from Firebase
      const fcmToken = await getFCMToken();
      
      if (!fcmToken) {
        console.warn('⚠️ Could not get FCM token, using fallback');
        alert('⚠️ Firebase is not configured. Please set up Firebase configuration in firebase-config.js');
        return;
      }
      
      console.log('✅ FCM token obtained:', fcmToken.substring(0, 20) + '...');
      
      await axios.post(
        `${API_BASE_URL}/api/notifications/register`,
        new URLSearchParams({
          user_id: userId,
          fcm_token: fcmToken
        }),
        { headers: { Authorization: `Bearer ${token}` }}
      );
      
      alert('✅ Notifications enabled! You will receive mood check-ins at 7 AM and 7 PM daily.');
      setTracking(prev => ({ ...prev, notificationsEnabled: true }));
      
    } catch (error) {
      console.error('Error registering for notifications:', error);
      
      // Show specific error messages to help with debugging
      let errorMessage = '⚠️ Could not register for notifications.';
      
      if (error.message?.includes('Firebase')) {
        errorMessage += '\n\n🔥 Firebase Error: Please check your Firebase configuration in firebase-config.js';
      } else if (error.message?.includes('VAPID')) {
        errorMessage += '\n\n🔑 VAPID Key Error: Please set your VAPID key in the .env file';
      } else if (error.message?.includes('permission')) {
        errorMessage += '\n\n🔔 Permission Error: Please allow notifications in your browser';
      } else if (error.response?.status === 503) {
        errorMessage += '\n\n🔧 Service Error: Notification service is not available';
      } else {
        errorMessage += `\n\nError: ${error.message}`;
      }
      
      alert(errorMessage);
    }
  };

  // Connect Google Calendar
  const connectCalendar = async () => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/calendar/authorize/${userId}`,
        { headers: { Authorization: `Bearer ${token}` }}
      );
      
      if (response.data.status === 'success' && response.data.auth_url) {
        // Open OAuth flow in new window
        const popup = window.open(
          response.data.auth_url, 
          'Google Calendar Authorization', 
          'width=600,height=700,scrollbars=yes,resizable=yes'
        );
        
        // Listen for OAuth callback completion
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            console.log('🔄 Popup closed, refreshing calendar status...');
            // Wait a moment for backend to process callback, then refresh status
            setTimeout(() => {
              console.log('🔄 Checking calendar permissions...');
              checkPermissions();
            }, 2000);
          }
        }, 1000);
        
        alert('📅 Please authorize Google Calendar access in the popup window.\n\nAfter authorization, you can close the popup.');
      } else {
        alert('⚠️ Calendar authorization not fully configured on backend.\n\nPlease configure Google OAuth credentials.');
      }
    } catch (error) {
      console.error('Error connecting calendar:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      
      if (error.response?.status === 503) {
        alert(`⚠️ Google Calendar OAuth not configured.\n\n${errorMessage}\n\nPlease configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend .env file.`);
      } else {
        alert(`⚠️ Could not connect calendar.\n\nError: ${errorMessage}`);
      }
    }
  };

  // View Location Data
  const viewLocationData = async () => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/location/summary/${userId}`,
        { headers: { Authorization: `Bearer ${token}` }}
      );
      
      setLocationData(response.data);
      setShowLocationData(true);
    } catch (error) {
      console.error('Error fetching location data:', error);
      alert('No location data found yet. Keep the app open for a while to collect data.');
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
      <h3 className="text-2xl font-bold mb-4 flex items-center text-gray-900">
        <span className="mr-3">🔐</span>
        App Permissions
      </h3>
      
      <p className="text-gray-600 mb-6">
        Enable these features for better personalized recommendations
      </p>

      <div className="space-y-4">
        {/* Location Permission */}
        <div className="flex items-center justify-between p-4 bg-purple-50 rounded-xl">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">📍</span>
              <div>
                <h4 className="font-semibold text-gray-900">Location Tracking</h4>
                <p className="text-sm text-gray-600">
                  Track your daily routine (home, office, gym, commute)
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`text-sm px-3 py-1 rounded-full ${
              permissions.location === 'granted' ? 'bg-green-100 text-green-700' :
              permissions.location === 'denied' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {permissions.location === 'granted' ? '✓ Granted' :
               permissions.location === 'denied' ? '✗ Denied' :
               '⊘ Not Set'}
            </span>
            {permissions.location === 'granted' ? (
              <button
                onClick={() => setShowLocationManager(true)}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Manage Locations
              </button>
            ) : (
              <button
                onClick={requestLocationPermission}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Enable
              </button>
            )}
          </div>
        </div>

        {/* Notification Permission */}
        <div className="flex items-center justify-between p-4 bg-blue-50 rounded-xl">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🔔</span>
              <div>
                <h4 className="font-semibold text-gray-900">Push Notifications</h4>
                <p className="text-sm text-gray-600">
                  Receive mood check-ins at 7 AM and 7 PM daily
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`text-sm px-3 py-1 rounded-full ${
              permissions.notifications === 'granted' ? 'bg-green-100 text-green-700' :
              permissions.notifications === 'denied' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {permissions.notifications === 'granted' ? '✓ Granted' :
               permissions.notifications === 'denied' ? '✗ Denied' :
               '⊘ Not Set'}
            </span>
            {permissions.notifications !== 'granted' && (
              <button
                onClick={requestNotificationPermission}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Enable
              </button>
            )}
          </div>
        </div>

        {/* Calendar Permission */}
        <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">📅</span>
              <div>
                <h4 className="font-semibold text-gray-900">Google Calendar</h4>
                <p className="text-sm text-gray-600">
                  Sync your schedule for activity suggestions that fit your day
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`text-sm px-3 py-1 rounded-full ${
              tracking.calendarConnected ? 'bg-green-100 text-green-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {tracking.calendarConnected ? '✓ Connected' : '⊘ Not Connected'}
            </span>
            {!tracking.calendarConnected && (
              <button
                onClick={connectCalendar}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Connect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
        <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
          <span className="mr-2">💡</span>
          How These Permissions Help
        </h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Location:</strong> Suggests activities based on where you are (home, office, gym)</li>
          <li>• <strong>Notifications:</strong> Quick mood check-ins without opening the app</li>
          <li>• <strong>Calendar:</strong> Recommends activities that fit your actual free time</li>
        </ul>
      </div>

      {/* Location Tracking Status */}
      {tracking.locationEnabled && (
        <div className="mt-4 p-4 bg-green-50 rounded-xl border border-green-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-semibold text-green-900 mb-2 flex items-center">
                <span className="mr-2">📍</span>
                Location Tracking Active
              </h4>
              <div className="text-sm text-green-800 space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span>Your location is being tracked every 2 minutes</span>
                </div>
                {currentLocationLabel && (
                  <div className="flex items-center space-x-2 mt-2 p-2 bg-white rounded-lg">
                    <span className="text-lg">{
                      currentLocationLabel.type === 'home' ? '🏠' : 
                      currentLocationLabel.type === 'office' ? '💼' :
                      currentLocationLabel.type === 'school' ? '🎓' :
                      currentLocationLabel.type === 'university' ? '🏫' :
                      currentLocationLabel.type === 'gym' ? '💪' :
                      currentLocationLabel.type === 'library' ? '📚' :
                      currentLocationLabel.type === 'mall' ? '🛍️' :
                      currentLocationLabel.type === 'restaurant' ? '🍽️' :
                      currentLocationLabel.type === 'cafe' ? '☕' :
                      currentLocationLabel.type === 'park' ? '🌳' :
                      currentLocationLabel.type === 'hospital' ? '🏥' :
                      currentLocationLabel.type === 'station' ? '🚉' :
                      currentLocationLabel.type === 'airport' ? '✈️' :
                      currentLocationLabel.type === 'hotel' ? '🏨' :
                      currentLocationLabel.type === 'friend' ? '👥' :
                      currentLocationLabel.type === 'relative' ? '👨‍👩‍👧' :
                      '📍'
                    }</span>
                    <span className="font-medium text-gray-900">
                      Currently at: {currentLocationLabel.name || currentLocationLabel.type}
                    </span>
                  </div>
                )}
                <div className="text-xs text-green-700 mt-2">
                  • Location data helps suggest activities based on where you are
                  • All data is private and only used for your recommendations
                  • Keep this tab open for continuous tracking
                </div>
              </div>
            </div>
            <button
              onClick={viewLocationData}
              className="ml-4 px-3 py-1 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap"
            >
              View Data
            </button>
          </div>

          {/* Location Data Modal */}
          {showLocationData && locationData && (
            <div className="mt-4 p-3 bg-white rounded-lg border border-green-300">
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-semibold text-gray-900">Today's Location Summary</h5>
                <button
                  onClick={() => setShowLocationData(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>
              <div className="text-sm text-gray-700 space-y-1">
                {locationData.summary ? (
                  <pre className="whitespace-pre-wrap">{locationData.summary}</pre>
                ) : (
                  <p className="text-gray-500 italic">No location data collected yet. Keep tracking enabled!</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Notification Schedule Info */}
      {tracking.notificationsEnabled && (
        <div className="mt-4 p-4 bg-purple-50 rounded-xl border border-purple-200">
          <h4 className="font-semibold text-purple-900 mb-2 flex items-center">
            <span className="mr-2">⏰</span>
            Notification Schedule
          </h4>
          <div className="text-sm text-purple-800 space-y-2">
            <div className="flex items-center space-x-2">
              <span>☀️</span>
              <span><strong>7:00 AM</strong> - Morning mood check: "How are you feeling today?"</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>🌙</span>
              <span><strong>7:00 PM</strong> - Evening reflection: "How was your day?"</span>
            </div>
          </div>
        </div>
      )}

      {/* Location Manager Modal */}
      <LocationManager
        userId={userId}
        isOpen={showLocationManager}
        onClose={() => setShowLocationManager(false)}
      />
    </div>
  );
}

