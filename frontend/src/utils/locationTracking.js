/**
 * Location Tracking Utility
 * Handles background location tracking and sending data to backend
 */

import axios from 'axios';
import { API_BASE_URL } from '../config';

let watchId = null;
let trackingInterval = null;

/**
 * Start background location tracking
 * @param {string} userId - User ID
 * @param {string} token - Auth token
 * @param {number} intervalMinutes - Tracking frequency in minutes (default: 15)
 */
export const startLocationTracking = (userId, token, intervalMinutes = 15) => {
  if (!('geolocation' in navigator)) {
    console.warn('Geolocation not supported');
    return false;
  }

  // Clear any existing tracking
  stopLocationTracking();

  console.log(`📍 Starting location tracking (every ${intervalMinutes} minutes)`);

  // Track immediately
  trackCurrentLocation(userId, token);

  // Then track periodically
  trackingInterval = setInterval(() => {
    trackCurrentLocation(userId, token);
  }, intervalMinutes * 60 * 1000);

  return true;
};

/**
 * Track current location and send to backend
 */
const trackCurrentLocation = async (userId, token) => {
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        // Detect activity type (if available from device)
        let activityType = 'stationary';
        
        // Send to backend
        await axios.post(
          `${API_BASE_URL}/api/location/track`,
          new URLSearchParams({
            user_id: userId,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            activity_type: activityType,
            accuracy: position.coords.accuracy
          }),
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );
        
        console.log('✓ Location tracked:', position.coords.latitude, position.coords.longitude);
      } catch (error) {
        console.error('Error tracking location:', error);
      }
    },
    (error) => {
      console.error('Geolocation error:', error);
    },
    {
      enableHighAccuracy: false,
      timeout: 10000,
      maximumAge: 300000 // 5 minute cache
    }
  );
};

/**
 * Stop background location tracking
 */
export const stopLocationTracking = () => {
  if (trackingInterval) {
    clearInterval(trackingInterval);
    trackingInterval = null;
    console.log('📍 Location tracking stopped');
  }
  
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId);
    watchId = null;
  }
};

/**
 * Save a frequent location (home, office, gym, etc.)
 */
export const saveFrequentLocation = async (userId, token, locationType, locationName) => {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const response = await axios.post(
            `${API_BASE_URL}/api/location/save-place`,
            new URLSearchParams({
              user_id: userId,
              location_type: locationType,
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              location_name: locationName,
              radius_meters: 100
            }),
            {
              headers: { Authorization: `Bearer ${token}` }
            }
          );
          
          console.log(`✓ Saved ${locationType} location`);
          resolve(response.data);
        } catch (error) {
          console.error('Error saving location:', error);
          reject(error);
        }
      },
      (error) => {
        console.error('Geolocation error:', error);
        reject(error);
      }
    );
  });
};

/**
 * Get today's location summary
 */
export const getLocationSummary = async (userId, token) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/location/summary/${userId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error getting location summary:', error);
    return null;
  }
};

/**
 * Analyze today's location data
 */
export const analyzeTodayLocations = async (userId, token) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/location/analyze-day`,
      new URLSearchParams({ user_id: userId }),
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error analyzing locations:', error);
    return null;
  }
};

