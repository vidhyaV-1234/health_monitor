import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL } from "../config";

export default function Login({ onLogin }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { data } = await axios.post(
        `${API_BASE_URL}/api/auth/login`,
        form
      );

      // Save JWT token
      localStorage.setItem("token", data.token);
      
      // Update user state
      if (onLogin) {
        onLogin(data.user);
      }

      // Redirect based on profile completion
      if (data.hasProfile) {
        navigate("/mood");
      } else {
        navigate("/profile");
      }
    } catch (err) {
      console.error("Login error:", err);
      setError(
        err.response?.data?.detail || err.response?.data?.message || "Login failed. Check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 flex items-center justify-center relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-40 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Login Card */}
      <div className="pinterest-card relative z-10 w-full max-w-md mx-4 p-8 bg-white shadow-2xl">
        <div className="text-center mb-8">
          <img 
            src="/logo.jpeg" 
            alt="Mood Flow Logo" 
            className="w-24 h-24 mx-auto mb-4 rounded-full shadow-lg object-cover"
          />
          <h1 className="text-3xl font-bold gradient-text mb-2">mood flow</h1>
          <h2 className="text-xl font-semibold text-gray-700">Welcome Back</h2>
          <p className="text-gray-500 text-sm mt-2">Sign in to continue your emotional journey</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl animate-shake">
            <p className="text-red-600 text-sm text-center flex items-center justify-center">
              <span className="mr-2">⚠️</span>
              {error}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">📧</span>
              <input
                type="email"
                name="email"
                placeholder="your.email@example.com"
                value={form.email}
                onChange={handleChange}
                className="w-full border-2 border-gray-200 rounded-2xl pl-12 pr-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">🔒</span>
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Enter your password (min 6 characters)"
                value={form.password}
                onChange={handleChange}
                className="w-full border-2 border-gray-200 rounded-2xl pl-12 pr-12 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                required
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
              >
                {showPassword ? "👁️" : "👁️‍🗨️"}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="animated-button w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-4 rounded-2xl font-bold text-lg hover:shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02] transition-all mt-6"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <span className="spinner w-5 h-5 border-3 border-white border-t-transparent rounded-full mr-3"></span>
                Logging in...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <span className="mr-2">✨</span>
                Login
              </span>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Don't have an account?{" "}
            <Link 
              to="/signup" 
              className="font-semibold text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 transition-all"
            >
              Sign Up
            </Link>
          </p>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-center space-x-4 text-xs text-gray-500">
            <span>🔒 Secure</span>
            <span>•</span>
            <span>🌈 Emotional Wellness</span>
            <span>•</span>
            <span>💖 Private</span>
          </div>
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
