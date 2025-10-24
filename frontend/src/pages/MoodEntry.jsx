import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import MasonryGrid from "../components/MasonryGrid";
import NotificationBanner from "../components/NotificationBanner";
import { isConfigured as supaConfigured, uploadFileAndGetUrl } from "../utils/supabase";

export default function MoodEntry({ user }) {
  const [form, setForm] = useState({
    id: "",
    mood_text: "",
    mood_audio: null,
    mood_image: null
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [audioFileName, setAudioFileName] = useState("");
  const [imageFileName, setImageFileName] = useState("");
  const [notificationHistory, setNotificationHistory] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  const token = localStorage.getItem("token");

  // Set user ID when component mounts
  useEffect(() => {
    if (user && user.id) {
      setForm(prevForm => ({ ...prevForm, id: user.id }));
      console.log("✓ User ID set:", user.id);
    }
  }, [user]);

  const loadNotificationHistory = async (userId) => {
    if (!userId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/stress-notifications/history/${userId}`);
      if (response.data.status === "success") {
        setNotificationHistory(response.data.data.notifications || []);
      }
    } catch (error) {
      console.error("Error loading notifications:", error);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const handleFileChange = (e) => {
    const { name, files } = e.target;
    if (files && files[0]) {
      setForm({ ...form, [name]: files[0] });
      if (name === "mood_audio") {
        setAudioFileName(files[0].name);
      } else if (name === "mood_image") {
        setImageFileName(files[0].name);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    // Validate required fields
    console.log("🔍 Validating form data:", { id: form.id, mood_text: form.mood_text, user: user });
    
    if (!form.id) {
      setError("User ID is missing. Please refresh the page and try again.");
      setLoading(false);
      return;
    }
    
    if (!form.mood_text || form.mood_text.trim() === "") {
      setError("Please enter your mood text.");
      setLoading(false);
      return;
    }

    try {
      let response;
      if (supaConfigured) {
        // 1) Upload media to Supabase Storage and get public URLs
        const bucket = import.meta.env.VITE_SUPABASE_MEDIA_BUCKET || "mood_media";
        const folder = form.id;

        console.log("📤 Uploading to Supabase:", { bucket, folder, supaConfigured });
        console.log("ENV CHECK:", {
          VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
          VITE_SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY ? 'SET' : 'MISSING',
          VITE_SUPABASE_MEDIA_BUCKET: import.meta.env.VITE_SUPABASE_MEDIA_BUCKET,
          VITE_API_URL: import.meta.env.VITE_API_URL
        });

        let audioUrl = null;
        let imageUrl = null;

        if (form.mood_audio) {
          console.log("🎤 Uploading audio...");
          try {
            const result = await uploadFileAndGetUrl({
              bucket,
              file: form.mood_audio,
              folder,
            });
            audioUrl = result.publicUrl;
            console.log("✓ Audio uploaded:", audioUrl);
          } catch (uploadErr) {
            console.error("Audio upload failed:", uploadErr);
            throw new Error(`Audio upload failed: ${uploadErr.message}`);
          }
        }

        if (form.mood_image) {
          console.log("📷 Uploading image...");
          try {
            const result = await uploadFileAndGetUrl({
              bucket,
              file: form.mood_image,
              folder,
            });
            imageUrl = result.publicUrl;
            console.log("✓ Image uploaded:", imageUrl);
          } catch (uploadErr) {
            console.error("Image upload failed:", uploadErr);
            throw new Error(`Image upload failed: ${uploadErr.message}`);
          }
        }

        // Send id, text, and URLs to backend
        const payload = {
          id: form.id,
          mood_text: form.mood_text,
          audio_url: audioUrl,
          image_url: imageUrl,
        };

        console.log("📤 Sending payload to backend:", payload);
        console.log("🌐 API URL:", API_BASE_URL);
        console.log("🔑 Token present:", !!token);

        response = await axios.post(`${API_BASE_URL}/api/mood`, payload, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        console.log("✅ Response received:", response.status);
      } else {
        // Fallback: send files directly to backend (legacy flow)
        const formData = new FormData();
        formData.append("id", form.id);
        formData.append("mood_text", form.mood_text);
        if (form.mood_audio) formData.append("mood_audio", form.mood_audio);
        if (form.mood_image) formData.append("mood_image", form.mood_image);

        response = await axios.post(`${API_BASE_URL}/api/mood`, formData, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        });
      }

      // 2) Continue handling response

      const newResult = {
        ...response.data.data,
        mood_text: form.mood_text,
        timestamp: new Date().toISOString()
      };
      
      setResult(newResult);
      
      // Reset form
      setForm({
        id: form.id,
        mood_text: "",
        mood_audio: null,
        mood_image: null
      });
      setAudioFileName("");
      setImageFileName("");
      
      console.log("Mood analysis result:", response.data.data);
    } catch (err) {
      console.error("Error:", err);
      console.error("Error response:", err.response);
      console.error("Error response data:", err.response?.data);
      console.error("Error response status:", err.response?.status);
      
      let errorMsg = "Error processing mood";
      
      // Handle 422 validation errors from FastAPI
      if (err.response?.status === 422 && err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // FastAPI validation error format
          const errors = err.response.data.detail.map(e => {
            const loc = e.loc ? e.loc.join('.') : 'unknown';
            return `${loc}: ${e.msg}`;
          });
          errorMsg += ": " + errors.join(", ");
        } else if (typeof err.response.data.detail === 'string') {
          errorMsg += ": " + err.response.data.detail;
        } else {
          errorMsg += ": " + JSON.stringify(err.response.data.detail);
        }
      } else if (err.message) {
        errorMsg += ": " + err.message;
      }
      
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-20 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-40 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10 bg-white bg-opacity-80 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">💭</span>
            <h1 className="text-2xl font-bold gradient-text">MoodFlow</h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-gray-600">Welcome, {user.username || 'User'}</span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-all hover:scale-105"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Notification Banner */}
        <NotificationBanner userId={form.id} />
        
        {/* Notification History Button */}
        {form.id && (
          <div className="mb-6 flex justify-end">
            <button
              onClick={() => {
                setShowNotifications(!showNotifications);
                if (!showNotifications && form.id) {
                  loadNotificationHistory(form.id);
                }
              }}
              className="px-6 py-2 bg-white rounded-full shadow-md hover:shadow-lg transition-all transform hover:scale-105 text-purple-600 font-semibold flex items-center space-x-2"
            >
              <span>🔔</span>
              <span>{showNotifications ? 'Hide' : 'View'} Notifications</span>
            </button>
          </div>
        )}

        {/* Notification History */}
        {showNotifications && (
          <div className="mb-8 bg-white rounded-2xl shadow-lg p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center">
              <span className="mr-2">📬</span>
              Your Notification History
            </h3>
            
            {notificationHistory.length > 0 ? (
              <div className="space-y-3">
                {notificationHistory.map((notif, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-xl border-2 ${
                      notif.notification_type === 'level_3' ? 'bg-red-50 border-red-300' :
                      notif.notification_type === 'level_2' ? 'bg-orange-50 border-orange-300' :
                      'bg-yellow-50 border-yellow-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="text-xl">
                            {notif.notification_type === 'level_3' ? '⚠️' :
                             notif.notification_type === 'level_2' ? '⚡' : '💡'}
                          </span>
                          <span className="font-semibold text-gray-800">
                            {notif.notification_type === 'level_3' ? 'Critical Alert' :
                             notif.notification_type === 'level_2' ? 'High Stress' : 'Wellness Reminder'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 mb-2">{notif.message}</p>
                        <div className="flex items-center space-x-4 text-xs text-gray-500">
                          <span>Stress Level: {notif.stress_day}/100</span>
                          <span>•</span>
                          <span>{new Date(notif.sent_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <span className="text-4xl mb-3 block">✅</span>
                <p>No notifications yet. Your stress level is normal!</p>
              </div>
            )}
          </div>
        )}
        
        {/* Mood Entry Form */}
        <div className="mood-form-card mb-8">
          <div className="text-center mb-6">
            <h2 className="text-3xl font-bold mb-2 flex items-center justify-center text-gray-900">
              <span className="mr-3">✨</span>
              How are you feeling today?
              <span className="ml-3">✨</span>
            </h2>
            <p className="text-gray-800">Share your thoughts and emotions with us</p>
          </div>
          
          {error && (
            <div className="mb-4 p-4 bg-red-500 bg-opacity-20 backdrop-blur-sm rounded-lg border border-white border-opacity-30">
              <p className="text-gray-900 text-sm text-center font-semibold">{error}</p>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900">User ID</label>
                <input
                  type="text"
                  name="id"
                  value={form.id}
                  onChange={handleChange}
                  className="w-full border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-white transition-all"
                  placeholder="Enter your ID"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium mb-2 text-gray-900">Your Thoughts & Feelings</label>
                <textarea
                  name="mood_text"
                  value={form.mood_text}
                  onChange={handleChange}
                  className="w-full border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-white transition-all resize-none"
                  placeholder="Express yourself freely... What's on your mind? How do you feel?"
                  rows="4"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 flex items-center">
                  <span className="mr-2">🎤</span>
                  Voice Recording (Optional)
                </label>
                <div className="relative">
                  <input
                    type="file"
                    name="mood_audio"
                    onChange={handleFileChange}
                    accept="audio/*"
                    className="hidden"
                    id="audio-upload"
                  />
                  <label
                    htmlFor="audio-upload"
                    className="w-full border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 cursor-pointer hover:bg-opacity-100 transition-all flex items-center justify-center"
                  >
                    {audioFileName || "Choose audio file..."}
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 flex items-center">
                  <span className="mr-2">📷</span>
                  Photo (Optional)
                </label>
                <div className="relative">
                  <input
                    type="file"
                    name="mood_image"
                    onChange={handleFileChange}
                    accept="image/*"
                    className="hidden"
                    id="image-upload"
                  />
                  <label
                    htmlFor="image-upload"
                    className="w-full border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 cursor-pointer hover:bg-opacity-100 transition-all flex items-center justify-center"
                  >
                    {imageFileName || "Choose image file..."}
                  </label>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="animated-button w-full bg-white text-purple-600 py-4 rounded-2xl font-bold text-lg hover:shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02] transition-all"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <span className="spinner w-6 h-6 border-3 border-purple-600 border-t-transparent rounded-full mr-3"></span>
                  Analyzing your mood...
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <span className="mr-2">🚀</span>
                  Analyze My Mood
                </span>
              )}
            </button>
          </form>
        </div>

        {/* Latest Result */}
        {result && (
          <div className="mb-8">
            <h3 className="text-2xl font-bold mb-4 text-center gradient-text flex items-center justify-center">
              <span className="mr-3">🎯</span>
              Your Latest Analysis
            </h3>
            <MasonryGrid items={[result]} onItemClick={null} />
          </div>
        )}


        {/* Empty State */}
        {!result && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🌟</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">Start Your Journey</h3>
            <p className="text-gray-500">Share your mood entry above to begin your emotional wellness analysis</p>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }

        .animate-blob {
          animation: blob 7s infinite;
        }

        .animation-delay-2000 {
          animation-delay: 2s;
        }

        .animation-delay-4000 {
          animation-delay: 4s;
        }

        .border-3 {
          border-width: 3px;
        }
      `}</style>
    </div>
  );
}
