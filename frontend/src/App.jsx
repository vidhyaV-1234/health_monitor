import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ProfileForm from "./pages/ProfileForm";
import MoodEntry from "./pages/MoodEntry";
import axios from "axios";
import { API_BASE_URL } from "./config";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      // Verify token and get user info (quick timeout to avoid hanging during local dev)
      const response = await axios.get(`${API_BASE_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 7000,
      });
      setUser(response.data);
    } catch (error) {
      console.error("Auth check failed:", error);
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Routes>
          <Route 
            path="/" 
            element={
              user ? (
                user.hasProfile ? <Navigate to="/mood" /> : <Navigate to="/profile" />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
          <Route 
            path="/login" 
            element={
              user ? <Navigate to="/mood" replace /> : <Login onLogin={setUser} />
            } 
          />
          <Route 
            path="/signup" 
            element={
              user ? <Navigate to="/mood" replace /> : <Signup />
            } 
          />
          <Route 
            path="/profile" 
            element={
              user ? (
                <ProfileForm onComplete={() => setUser({...user, hasProfile: true})} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
          <Route 
            path="/profile/edit" 
            element={
              user ? (
                <ProfileForm 
                  user={user}
                  isEditMode={true} 
                  onComplete={() => setUser({...user, hasProfile: true})} 
                />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
          <Route 
            path="/mood" 
            element={
              user ? (
                <MoodEntry user={user} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;