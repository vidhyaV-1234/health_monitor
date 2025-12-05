import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL } from "../config";
import MasonryGrid from "../components/MasonryGrid";
import NotificationBanner from "../components/NotificationBanner";
import PermissionsManager from "../components/PermissionsManager";
import FCMTest from "../components/FCMTest";
import { isConfigured as supaConfigured, uploadFileAndGetUrl } from "../utils/supabase";

export default function MoodEntry({ user }) {
  const navigate = useNavigate();
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

  // Audio recording states
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState("");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Camera capture states
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

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

  // Audio Recording Functions
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);
        
        // Convert blob to file and set in form
        const audioFile = new File([audioBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
        setForm({ ...form, mood_audio: audioFile });
        setAudioFileName(audioFile.name);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setError("");
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Could not access microphone. Please grant permission and try again.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const clearAudio = () => {
    setAudioBlob(null);
    setAudioURL("");
    setForm({ ...form, mood_audio: null });
    setAudioFileName("");
  };

  // Camera Capture Functions
  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user' } 
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraOpen(true);
      setError("");
    } catch (err) {
      console.error('Error accessing camera:', err);
      setError('Could not access camera. Please grant permission and try again.');
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      canvas.toBlob((blob) => {
        const imageFile = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        setForm({ ...form, mood_image: imageFile });
        setImageFileName(imageFile.name);
        setCapturedImage(URL.createObjectURL(blob));
        closeCamera();
      }, 'image/jpeg', 0.95);
    }
  };

  const closeCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsCameraOpen(false);
  };

  const clearImage = () => {
    setCapturedImage(null);
    setForm({ ...form, mood_image: null });
    setImageFileName("");
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
      if (capturedImage) {
        URL.revokeObjectURL(capturedImage);
      }
    };
  }, []);

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
    
    // Check if at least one input is provided (text, audio, or image)
    const hasAnyInput = form.mood_text?.trim() || form.mood_audio || form.mood_image;
    if (!hasAnyInput) {
      setError("Please provide at least one input: text, audio, or image.");
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
        console.log("🔍 Payload details:", {
          id: payload.id,
          id_type: typeof payload.id,
          mood_text: payload.mood_text,
          mood_text_type: typeof payload.mood_text,
          audio_url: payload.audio_url,
          image_url: payload.image_url
        });
        console.log("🌐 API URL:", API_BASE_URL);
        console.log("🔑 Token present:", !!token);
        console.log("📋 Stringified payload:", JSON.stringify(payload));

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
            <img 
              src="/logo.jpeg" 
              alt="Mood Flow Logo" 
              className="w-12 h-12 rounded-full shadow-md object-cover"
            />
            <h1 className="text-2xl font-bold gradient-text">mood flow</h1>
          </div>
          <div className="flex items-center space-x-4">
            {user?.hasProfile ? (
              <button
                onClick={() => navigate("/profile/view")}
                className="px-4 py-2 bg-purple-500 text-white rounded-full hover:bg-purple-600 transition-all hover:scale-105 flex items-center space-x-2"
                title="View Profile"
              >
                <span>👤</span>
                <span>Profile</span>
              </button>
            ) : (
              <button
                onClick={() => navigate("/profile")}
                className="px-4 py-2 bg-green-500 text-white rounded-full hover:bg-green-600 transition-all hover:scale-105 flex items-center space-x-2"
                title="Complete Profile"
              >
                <span>📝</span>
                <span>Complete Profile</span>
              </button>
            )}
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
        {/* Permissions Manager */}
        {form.id && <PermissionsManager userId={form.id} />}
        
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
            <p className="text-sm text-gray-600 mt-2">✨ All inputs are optional - provide text, audio, image, or any combination!</p>
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
                <label className="block text-sm font-medium mb-2 text-gray-900">
                  Your Thoughts & Feelings (Optional)
                </label>
                <textarea
                  name="mood_text"
                  value={form.mood_text}
                  onChange={handleChange}
                  className="w-full border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-white transition-all resize-none"
                  placeholder="Express yourself freely... What's on your mind? How do you feel? (Optional - you can also just upload audio or image)"
                  rows="4"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 flex items-center">
                  <span className="mr-2">🎤</span>
                  Voice Recording (Optional)
                </label>
                
                {/* Audio Recording Controls */}
                <div className="space-y-3">
                  {!audioBlob && !audioFileName && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={isRecording ? stopRecording : startRecording}
                        className={`flex-1 border-0 rounded-2xl px-4 py-3 font-medium transition-all ${
                          isRecording 
                            ? 'bg-red-500 text-white animate-pulse' 
                            : 'bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 hover:bg-opacity-100'
                        }`}
                      >
                        {isRecording ? (
                          <span className="flex items-center justify-center">
                            <span className="w-3 h-3 bg-white rounded-full mr-2 animate-pulse"></span>
                            Stop Recording
                          </span>
                        ) : (
                          <span className="flex items-center justify-center">
                            <span className="mr-2">🎙️</span>
                            Record Audio
                          </span>
                        )}
                      </button>
                      
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
                        className="flex-1 border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 cursor-pointer hover:bg-opacity-100 transition-all flex items-center justify-center font-medium"
                      >
                        <span className="mr-2">📁</span>
                        Upload File
                      </label>
                    </div>
                  )}
                  
                  {/* Audio Preview */}
                  {(audioURL || audioFileName) && (
                    <div className="bg-white bg-opacity-90 backdrop-blur-sm rounded-2xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          {audioFileName || 'Recorded Audio'}
                        </span>
                        <button
                          type="button"
                          onClick={clearAudio}
                          className="text-red-500 hover:text-red-700 font-medium text-sm"
                        >
                          ✕ Remove
                        </button>
                      </div>
                      {audioURL && (
                        <audio controls className="w-full mt-2">
                          <source src={audioURL} type="audio/wav" />
                        </audio>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 flex items-center">
                  <span className="mr-2">📷</span>
                  Photo (Optional)
                </label>
                
                {/* Camera Controls */}
                <div className="space-y-3">
                  {!isCameraOpen && !capturedImage && !imageFileName && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={openCamera}
                        className="flex-1 border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 hover:bg-opacity-100 transition-all font-medium"
                      >
                        <span className="flex items-center justify-center">
                          <span className="mr-2">📸</span>
                          Open Camera
                        </span>
                      </button>
                      
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
                        className="flex-1 border-0 rounded-2xl px-4 py-3 bg-white bg-opacity-90 backdrop-blur-sm text-gray-700 cursor-pointer hover:bg-opacity-100 transition-all flex items-center justify-center font-medium"
                      >
                        <span className="mr-2">📁</span>
                        Upload File
                      </label>
                    </div>
                  )}
                  
                  {/* Camera View */}
                  {isCameraOpen && (
                    <div className="bg-white bg-opacity-90 backdrop-blur-sm rounded-2xl p-4">
                      <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        className="w-full rounded-lg mb-3"
                      />
                      <canvas ref={canvasRef} className="hidden" />
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={capturePhoto}
                          className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white py-2 rounded-xl font-medium hover:shadow-lg transition-all"
                        >
                          <span className="flex items-center justify-center">
                            <span className="mr-2">📸</span>
                            Capture Photo
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={closeCamera}
                          className="px-4 bg-gray-300 text-gray-700 py-2 rounded-xl font-medium hover:bg-gray-400 transition-all"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {/* Image Preview */}
                  {(capturedImage || imageFileName) && (
                    <div className="bg-white bg-opacity-90 backdrop-blur-sm rounded-2xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          {imageFileName || 'Captured Photo'}
                        </span>
                        <button
                          type="button"
                          onClick={clearImage}
                          className="text-red-500 hover:text-red-700 font-medium text-sm"
                        >
                          ✕ Remove
                        </button>
                      </div>
                      {capturedImage && (
                        <img 
                          src={capturedImage} 
                          alt="Captured" 
                          className="w-full rounded-lg mt-2"
                        />
                      )}
                      {imageFileName && !capturedImage && (
                        <div className="text-sm text-gray-600 mt-2">
                          ✓ {imageFileName}
                        </div>
                      )}
                    </div>
                  )}
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


        {/* FCM Debug Section */}
        <div className="mb-8">
          <details className="bg-white rounded-2xl shadow-lg overflow-hidden">
            <summary className="p-4 cursor-pointer hover:bg-gray-50 transition-colors font-semibold text-gray-700 flex items-center">
              <span className="mr-2">🔧</span>
              FCM Token Debug (Click to expand)
            </summary>
            <div className="border-t">
              <FCMTest />
            </div>
          </details>
        </div>

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
