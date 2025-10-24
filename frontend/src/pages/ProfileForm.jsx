import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";

export default function ProfileForm({ user, isEditMode = false, onComplete }) {
  const [form, setForm] = useState({
    id: "",
    screetime_daily: "",
    job_description: "",
    free_hr_activities: "",
    travelling_hr: "",
    weekend_mood: "",
    week_day_mood: "",
    free_hr_mrg: "",
    free_hr_eve: "",
    sleep_time: "",
    preferred_exercise: "",
    social_preference: "",
    energy_level_rating: "",
    sleep_pattern: "",
    hobbies: "",
    work_schedule: "",
    meal_preferences: "",
    relaxation_methods: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(1);
  const [fetchingProfile, setFetchingProfile] = useState(isEditMode);
  const navigate = useNavigate();

  const token = localStorage.getItem("token");

  // Fetch existing profile data when in edit mode
  useEffect(() => {
    if (isEditMode && user?.id) {
      fetchProfileData(user.id);
    }
  }, [isEditMode, user]);

  const fetchProfileData = async (userId) => {
    try {
      setFetchingProfile(true);
      const response = await axios.get(`${API_BASE_URL}/api/habit/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data) {
        // Update form with existing data
        setForm(prevForm => ({
          ...prevForm,
          ...response.data
        }));
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
      setError("Could not load profile data");
    } finally {
      setFetchingProfile(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      // Create FormData to send profile data
      const formData = new FormData();
      
      // Add all form fields to FormData
      Object.keys(form).forEach(key => {
        formData.append(key, form[key]);
      });

      // Send to backend API
      const response = await axios.post(`${API_BASE_URL}/api/profile`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });
      
      if (isEditMode) {
        alert("✅ Profile updated successfully!");
      } else {
        alert("✅ Profile saved successfully! Generating your initial report...");
      }
      
      // Notify parent component
      if (onComplete) {
        onComplete();
      }
      
      // Navigate to mood entry
      navigate("/mood");
    } catch (err) {
      console.error("Error:", err);
      setError("Error saving profile: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => {
    setStep(step + 1);
  };

  const prevStep = () => {
    setStep(step - 1);
  };

  // Show loading state when fetching profile
  if (fetchingProfile) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 py-8 relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-96 h-96 bg-green-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-40 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="max-w-3xl mx-auto px-4 relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          {isEditMode && (
            <button
              onClick={() => navigate("/mood")}
              className="mb-4 px-4 py-2 bg-gray-500 text-white rounded-full hover:bg-gray-600 transition-all inline-flex items-center space-x-2"
            >
              <span>←</span>
              <span>Back to Mood Entry</span>
            </button>
          )}
          <div className="text-6xl mb-4 animate-bounce">
            {isEditMode ? "⚙️" : "📝"}
          </div>
          <h1 className="text-3xl font-bold gradient-text mb-2">
            {isEditMode ? "Edit Your Profile" : "Complete Your Profile"}
          </h1>
          <p className="text-gray-600">
            {isEditMode ? "Update your wellness preferences" : "Help us personalize your wellness journey"}
          </p>
          
          {/* Progress Bar */}
          <div className="mt-6 max-w-md mx-auto">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-green-400 via-blue-400 to-purple-400 transition-all duration-500 ease-out"
                style={{ width: `${(step / 3) * 100}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span className={step >= 1 ? 'text-purple-600 font-semibold' : ''}>Personal Info</span>
              <span className={step >= 2 ? 'text-purple-600 font-semibold' : ''}>Lifestyle</span>
              <span className={step >= 3 ? 'text-purple-600 font-semibold' : ''}>Preferences</span>
            </div>
          </div>
        </div>

        {/* Form Card */}
        <div className="pinterest-card bg-white p-8 shadow-2xl">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl animate-shake">
              <p className="text-red-600 text-sm text-center flex items-center justify-center">
                <span className="mr-2">⚠️</span>
                {error}
              </p>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Step 1: Personal Info */}
            {step === 1 && (
              <div className="space-y-6 animate-slideIn">
                <h3 className="text-xl font-semibold mb-4 flex items-center text-gray-900">
                  <span className="mr-2">👤</span>
                  Personal Information
                </h3>
                
                <div>
                  <label className="block text-sm font-medium mb-2">User ID</label>
                  <input
                    type="text"
                    name="id"
                    value={form.id}
                    onChange={handleChange}
                    className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                    placeholder="Enter your unique ID"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Job Description</label>
                  <input
                    type="text"
                    name="job_description"
                    value={form.job_description}
                    onChange={handleChange}
                    className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                    placeholder="e.g. Software Developer, Teacher, Student"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Energy Level (1-10)</label>
                    <input
                      type="number"
                      name="energy_level_rating"
                      value={form.energy_level_rating}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="1"
                      max="10"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Social Preference</label>
                    <select
                      name="social_preference"
                      value={form.social_preference}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      required
                    >
                      <option value="">Select</option>
                      <option value="solo">🧘 Solo Activities</option>
                      <option value="group">👥 Group Activities</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Lifestyle */}
            {step === 2 && (
              <div className="space-y-6 animate-slideIn">
                <h3 className="text-xl font-semibold mb-4 flex items-center text-gray-900">
                  <span className="mr-2">🏃</span>
                  Lifestyle & Schedule
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Daily Screen Time (hours)</label>
                    <input
                      type="number"
                      name="screetime_daily"
                      value={form.screetime_daily}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      step="0.1"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Travelling Time (min/day)</label>
                    <input
                      type="number"
                      name="travelling_hr"
                      value={form.travelling_hr}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Morning Free Time (minutes)</label>
                    <input
                      type="number"
                      name="free_hr_mrg"
                      value={form.free_hr_mrg}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Evening Free Time (minutes)</label>
                    <input
                      type="number"
                      name="free_hr_eve"
                      value={form.free_hr_eve}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Sleep Pattern (hours/day)</label>
                    <input
                      type="number"
                      name="sleep_pattern"
                      value={form.sleep_pattern}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      step="0.1"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Work Schedule (hours/day)</label>
                    <input
                      type="number"
                      name="work_schedule"
                      value={form.work_schedule}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      min="0"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Sleep Time</label>
                    <input
                      type="time"
                      name="sleep_time"
                      value={form.sleep_time}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Weekend Mood</label>
                    <select
                      name="weekend_mood"
                      value={form.weekend_mood}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      required
                    >
                      <option value="">Select</option>
                      <option value="happy">😊 Happy</option>
                      <option value="sad">😢 Sad</option>
                      <option value="stressed">😰 Stressed</option>
                      <option value="calm">😌 Calm</option>
                      <option value="neutral">😐 Neutral</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Weekday Mood</label>
                    <select
                      name="week_day_mood"
                      value={form.week_day_mood}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      required
                    >
                      <option value="">Select</option>
                      <option value="happy">😊 Happy</option>
                      <option value="sad">😢 Sad</option>
                      <option value="stressed">😰 Stressed</option>
                      <option value="calm">😌 Calm</option>
                      <option value="neutral">😐 Neutral</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Preferences */}
            {step === 3 && (
              <div className="space-y-6 animate-slideIn">
                <h3 className="text-xl font-semibold mb-4 flex items-center text-gray-900">
                  <span className="mr-2">🎯</span>
                  Your Preferences
                </h3>

                <div>
                  <label className="block text-sm font-medium mb-2">Free Hour Activities</label>
                  <textarea
                    name="free_hr_activities"
                    value={form.free_hr_activities}
                    onChange={handleChange}
                    className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"
                    placeholder="e.g. Reading, Music, Gardening, Walking"
                    rows="3"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Hobbies</label>
                  <textarea
                    name="hobbies"
                    value={form.hobbies}
                    onChange={handleChange}
                    className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"
                    placeholder="e.g. Painting, Cycling, Movies, Cooking"
                    rows="3"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Relaxation Methods</label>
                  <textarea
                    name="relaxation_methods"
                    value={form.relaxation_methods}
                    onChange={handleChange}
                    className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"
                    placeholder="e.g. Meditation, Deep breathing, Listening to music"
                    rows="3"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Preferred Exercise</label>
                    <input
                      type="text"
                      name="preferred_exercise"
                      value={form.preferred_exercise}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      placeholder="e.g. Yoga, Running, Gym, Swimming"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Meal Preferences</label>
                    <input
                      type="text"
                      name="meal_preferences"
                      value={form.meal_preferences}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                      placeholder="e.g. Vegetarian, Vegan, Non-Vegetarian"
                      required
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between items-center pt-6 border-t border-gray-200">
              {step > 1 && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-2xl font-semibold hover:bg-gray-300 transition-all transform hover:scale-105"
                >
                  ← Previous
                </button>
              )}
              
              {step < 3 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  className="animated-button ml-auto px-8 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-2xl font-semibold hover:shadow-2xl transition-all transform hover:scale-105"
                >
                  Next →
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={loading}
                  className="animated-button ml-auto px-8 py-3 bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-2xl font-bold hover:shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
                >
                  {loading ? (
                    <span className="flex items-center">
                      <span className="spinner w-5 h-5 border-3 border-white border-t-transparent rounded-full mr-3"></span>
                      Saving...
                    </span>
                  ) : (
                    <span className="flex items-center">
                      <span className="mr-2">✨</span>
                      Complete Profile
                    </span>
                  )}
                </button>
              )}
            </div>
          </form>
        </div>
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

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(30px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes shake {
          0%, 100% {
            transform: translateX(0);
          }
          10%, 30%, 50%, 70%, 90% {
            transform: translateX(-5px);
          }
          20%, 40%, 60%, 80% {
            transform: translateX(5px);
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

        .animate-slideIn {
          animation: slideIn 0.5s ease-out;
        }

        .animate-shake {
          animation: shake 0.5s;
        }

        .border-3 {
          border-width: 3px;
        }
      `}</style>
    </div>
  );
}
