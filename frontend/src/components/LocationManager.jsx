import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";

export default function LocationManager({ userId, isOpen, onClose }) {
  const [savedLocations, setSavedLocations] = useState([]);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [locationName, setLocationName] = useState("");
  const [locationType, setLocationType] = useState("home");
  const [addressName, setAddressName] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetchingLocation, setFetchingLocation] = useState(false);

  const token = localStorage.getItem("token");

  const [customType, setCustomType] = useState("");
  const [showCustomType, setShowCustomType] = useState(false);

  const locationTypes = [
    { value: "home", label: "🏠 Home", color: "blue" },
    { value: "office", label: "💼 Office/Work", color: "purple" },
    { value: "school", label: "🎓 School", color: "indigo" },
    { value: "university", label: "🏫 University/College", color: "violet" },
    { value: "gym", label: "💪 Gym/Fitness", color: "green" },
    { value: "library", label: "📚 Library", color: "cyan" },
    { value: "mall", label: "🛍️ Mall/Shopping", color: "pink" },
    { value: "restaurant", label: "🍽️ Restaurant", color: "orange" },
    { value: "cafe", label: "☕ Cafe/Coffee Shop", color: "amber" },
    { value: "park", label: "🌳 Park/Outdoors", color: "emerald" },
    { value: "hospital", label: "🏥 Hospital/Clinic", color: "red" },
    { value: "station", label: "🚉 Transit Station", color: "slate" },
    { value: "airport", label: "✈️ Airport", color: "sky" },
    { value: "hotel", label: "🏨 Hotel", color: "rose" },
    { value: "friend", label: "👥 Friend's Place", color: "indigo" },
    { value: "relative", label: "👨‍👩‍👧 Relative's Home", color: "fuchsia" },
    { value: "custom", label: "✏️ Custom (Type your own)", color: "gray" }
  ];

  useEffect(() => {
    if (isOpen && userId) {
      loadSavedLocations();
    }
  }, [isOpen, userId]);

  const loadSavedLocations = async () => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/location/saved/${userId}`,
        { headers: { Authorization: `Bearer ${token}` }}
      );
      setSavedLocations(response.data.locations || []);
    } catch (error) {
      console.error('Error loading saved locations:', error);
    }
  };

  const getCurrentLocation = () => {
    setFetchingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setCurrentLocation({ latitude, longitude });
        
        // Get address name using reverse geocoding
        try {
          const address = await reverseGeocode(latitude, longitude);
          setAddressName(address);
        } catch (error) {
          console.error('Error getting address:', error);
          setAddressName(`Location: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
        }
        
        setFetchingLocation(false);
      },
      (error) => {
        console.error('Error getting location:', error);
        alert('Could not get your current location. Please enable location access.');
        setFetchingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const reverseGeocode = async (lat, lon) => {
    try {
      // Using OpenStreetMap Nominatim API (free, no API key needed)
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`,
        {
          headers: {
            'User-Agent': 'HealthMonitorApp/1.0'
          }
        }
      );
      
      const data = await response.json();
      
      if (data.address) {
        const parts = [];
        if (data.address.road) parts.push(data.address.road);
        if (data.address.suburb) parts.push(data.address.suburb);
        if (data.address.city || data.address.town) parts.push(data.address.city || data.address.town);
        if (data.address.state) parts.push(data.address.state);
        
        return parts.join(', ') || data.display_name;
      }
      
      return data.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    } catch (error) {
      console.error('Geocoding error:', error);
      return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    }
  };

  const saveLocation = async () => {
    if (!currentLocation) {
      alert('Please get your current location first');
      return;
    }

    if (!locationName.trim()) {
      alert('Please enter a name for this location');
      return;
    }

    // Use custom type if selected, otherwise use predefined type
    const finalLocationType = locationType === 'custom' && customType.trim() 
      ? customType.trim().toLowerCase()
      : locationType;

    if (locationType === 'custom' && !customType.trim()) {
      alert('Please enter a custom location type');
      return;
    }

    setLoading(true);
    try {
      // Log what we're sending
      console.log('📍 Saving location:', {
        user_id: userId,
        location_type: finalLocationType,
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
        location_name: locationName,
        radius_meters: 100
      });

      const response = await axios.post(
        `${API_BASE_URL}/api/location/save-place`,
        new URLSearchParams({
          user_id: userId,
          location_type: finalLocationType,
          latitude: currentLocation.latitude.toString(),
          longitude: currentLocation.longitude.toString(),
          location_name: locationName.trim(),
          radius_meters: '100'
        }),
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );

      console.log('✅ Save response:', response.data);
      alert(`✅ ${locationName} saved successfully!`);
      setLocationName("");
      setAddressName("");
      setCurrentLocation(null);
      setCustomType("");
      setShowCustomType(false);
      loadSavedLocations();
    } catch (error) {
      console.error('❌ Error saving location:', error);
      console.error('Error details:', error.response?.data);
      alert('Failed to save location. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const deleteLocation = async (locationId, locationName) => {
    // Better confirmation dialog
    const confirmed = window.confirm(
      `🗑️ Delete Location?\n\n` +
      `Are you sure you want to delete "${locationName}"?\n\n` +
      `This will remove:\n` +
      `• The saved location\n` +
      `• Auto-detection for this place\n` +
      `• Visit history\n\n` +
      `This action cannot be undone.`
    );
    
    if (!confirmed) {
      return;
    }

    setLoading(true);
    try {
      console.log('🗑️ Deleting location ID:', locationId);
      console.log('🗑️ Location name:', locationName);
      console.log('🗑️ API URL:', `${API_BASE_URL}/api/location/saved/${locationId}`);
      
      const response = await axios.delete(
        `${API_BASE_URL}/api/location/saved/${locationId}`,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log('✅ Delete response:', response.data);
      alert(`✅ "${locationName}" has been deleted successfully!`);
      loadSavedLocations();
    } catch (error) {
      console.error('❌ Error deleting location:', error);
      console.error('❌ Error response:', error.response?.data);
      console.error('❌ Error status:', error.response?.status);
      console.error('❌ Error message:', error.message);
      
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
      alert(`❌ Failed to delete "${locationName}".\n\nError: ${errorMessage}\n\nPlease check the console for details.`);
    } finally {
      setLoading(false);
    }
  };

  const deleteAllLocations = async () => {
    if (savedLocations.length === 0) {
      alert('No locations to delete!');
      return;
    }

    const confirmed = window.confirm(
      `⚠️ DELETE ALL LOCATIONS?\n\n` +
      `Are you sure you want to delete ALL ${savedLocations.length} saved location(s)?\n\n` +
      `This will permanently remove:\n` +
      `• All saved locations\n` +
      `• All auto-detection settings\n` +
      `• All visit history\n\n` +
      `⚠️ THIS ACTION CANNOT BE UNDONE! ⚠️\n\n` +
      `Type "DELETE ALL" in the next prompt to confirm.`
    );

    if (!confirmed) {
      return;
    }

    const confirmText = prompt('Type "DELETE ALL" to confirm (in capital letters):');
    if (confirmText !== 'DELETE ALL') {
      alert('❌ Deletion cancelled. Text did not match.');
      return;
    }

    setLoading(true);
    try {
      // Delete each location
      const deletePromises = savedLocations.map(loc =>
        axios.delete(
          `${API_BASE_URL}/api/location/saved/${loc.saved_location_id}`,
          { headers: { Authorization: `Bearer ${token}` }}
        )
      );

      await Promise.all(deletePromises);
      
      alert(`✅ All ${savedLocations.length} location(s) have been deleted successfully!`);
      loadSavedLocations();
    } catch (error) {
      console.error('Error deleting all locations:', error);
      alert('❌ Failed to delete some locations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-2xl">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold flex items-center">
              <span className="mr-3">📍</span>
              Manage Your Locations
            </h2>
            <button
              onClick={onClose}
              className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition-all"
            >
              <span className="text-2xl">✕</span>
            </button>
          </div>
          <p className="text-white text-opacity-90 mt-2">
            Label your frequent locations so we can give you better recommendations
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Add New Location */}
          <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-5 border-2 border-purple-200">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 flex items-center">
              <span className="mr-2">➕</span>
              Add New Location
            </h3>

            {/* Step 1: Get Current Location */}
            <div className="space-y-3">
              <button
                onClick={getCurrentLocation}
                disabled={fetchingLocation || currentLocation}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-xl font-medium hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {fetchingLocation ? (
                  <span className="flex items-center justify-center">
                    <span className="spinner w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                    Getting your location...
                  </span>
                ) : currentLocation ? (
                  <span className="flex items-center justify-center">
                    <span className="mr-2">✓</span>
                    Location captured
                  </span>
                ) : (
                  <span className="flex items-center justify-center">
                    <span className="mr-2">📍</span>
                    Get My Current Location
                  </span>
                )}
              </button>

              {/* Show address if location captured */}
              {addressName && (
                <div className="bg-white rounded-lg p-3 text-sm">
                  <p className="text-gray-600 mb-1">Detected Address:</p>
                  <p className="text-gray-900 font-medium">{addressName}</p>
                </div>
              )}

              {/* Step 2: Select Type and Name */}
              {currentLocation && (
                <div className="space-y-3 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Location Type
                    </label>
                    <select
                      value={locationType}
                      onChange={(e) => {
                        setLocationType(e.target.value);
                        setShowCustomType(e.target.value === 'custom');
                      }}
                      className="w-full border-2 border-gray-300 rounded-xl px-4 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    >
                      {locationTypes.map(type => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Custom Type Input */}
                  {showCustomType && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Custom Location Type
                      </label>
                      <input
                        type="text"
                        value={customType}
                        onChange={(e) => setCustomType(e.target.value)}
                        placeholder="e.g., dance studio, church, temple, mosque, salon, workshop"
                        className="w-full border-2 border-gray-300 rounded-xl px-4 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Enter any location type you want (e.g., music school, art studio, co-working space)
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Give it a name
                    </label>
                    <input
                      type="text"
                      value={locationName}
                      onChange={(e) => setLocationName(e.target.value)}
                      placeholder="e.g., My Home, ABC Office, Fitness First Gym"
                      className="w-full border-2 border-gray-300 rounded-xl px-4 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={saveLocation}
                      disabled={loading || !locationName.trim()}
                      className="flex-1 bg-green-600 text-white py-2 rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      {loading ? 'Saving...' : '💾 Save Location'}
                    </button>
                    <button
                      onClick={() => {
                        setCurrentLocation(null);
                        setAddressName("");
                        setLocationName("");
                        setCustomType("");
                        setShowCustomType(false);
                      }}
                      className="px-4 bg-gray-300 text-gray-700 py-2 rounded-xl font-medium hover:bg-gray-400 transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Saved Locations List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <span className="mr-2">📌</span>
                Your Saved Locations ({savedLocations.length})
              </h3>
              {savedLocations.length > 0 && (
                <button
                  onClick={deleteAllLocations}
                  disabled={loading}
                  className="px-3 py-1 bg-red-100 text-red-700 text-sm rounded-lg hover:bg-red-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <span>🗑️</span>
                  <span className="font-medium">Delete All</span>
                </button>
              )}
            </div>

            {savedLocations.length === 0 ? (
              <div className="bg-gray-50 rounded-xl p-8 text-center">
                <p className="text-gray-500 text-lg mb-2">📍</p>
                <p className="text-gray-600">No saved locations yet</p>
                <p className="text-gray-500 text-sm mt-1">Add your first location above!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {savedLocations.map((loc) => {
                  const typeInfo = locationTypes.find(t => t.value === loc.location_type);
                  const emoji = typeInfo ? typeInfo.label.split(' ')[0] : '📍';
                  const colorClass = typeInfo ? typeInfo.color : 'gray';
                  const displayType = loc.location_type.charAt(0).toUpperCase() + loc.location_type.slice(1);
                  
                  return (
                    <div
                      key={loc.saved_location_id}
                      className={`bg-${colorClass}-50 border-2 border-${colorClass}-200 rounded-xl p-4`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-lg">{emoji}</span>
                            <h4 className="font-semibold text-gray-900">{loc.location_name}</h4>
                            <span className={`text-xs px-2 py-1 bg-${colorClass}-100 text-${colorClass}-700 rounded-full`}>
                              {displayType}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">
                            📍 {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Saved on {new Date(loc.created_at).toLocaleDateString()}
                            {loc.visit_count > 0 && ` • Visited ${loc.visit_count} time${loc.visit_count > 1 ? 's' : ''}`}
                          </p>
                        </div>
                        <div className="flex flex-col gap-2">
                          <button
                            onClick={() => deleteLocation(loc.saved_location_id, loc.location_name)}
                            className="px-3 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 hover:shadow-lg transition-all flex items-center gap-2"
                            title="Delete this location"
                          >
                            <span>🗑️</span>
                            <span className="font-medium">Delete</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
            <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
              <span className="mr-2">💡</span>
              How This Works
            </h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• When you're within 100m of a saved location, it will be automatically recognized</li>
              <li>• Choose from 16+ predefined types or create your own custom type (e.g., dance studio, church, music school)</li>
              <li>• Location labels help us give you contextually relevant activity suggestions</li>
              <li>• For example: relaxing activities at home, energizing activities at gym, study tips at library</li>
              <li>• Your location data is private and only used for your personalized recommendations</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

