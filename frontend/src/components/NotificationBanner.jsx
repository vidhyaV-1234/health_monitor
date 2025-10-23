import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";
import axios from "axios";

export default function NotificationBanner({ userId }) {
  const [notification, setNotification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (userId) {
      checkNotification();
    }
  }, [userId]);

  const checkNotification = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/check-stress/${userId}`);
      
      if (response.data.status === "success") {
        const result = response.data.data;
        
        if (result.status === "notification_sent") {
          setNotification(result);
        }
      }
    } catch (error) {
      console.error("Error checking notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !notification || dismissed) {
    return null;
  }

  const getPriorityColors = (priority) => {
    switch (priority) {
      case "critical":
        return {
          bg: "bg-red-500",
          border: "border-red-600",
          icon: "⚠️"
        };
      case "high":
        return {
          bg: "bg-orange-500",
          border: "border-orange-600",
          icon: "⚡"
        };
      case "moderate":
        return {
          bg: "bg-yellow-500",
          border: "border-yellow-600",
          icon: "💡"
        };
      default:
        return {
          bg: "bg-blue-500",
          border: "border-blue-600",
          icon: "ℹ️"
        };
    }
  };

  const colors = getPriorityColors(notification.priority);

  return (
    <div className={`${colors.bg} ${colors.border} border-2 rounded-2xl shadow-lg p-4 mb-6 animate-slideDown`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <span className="text-3xl">{colors.icon}</span>
          <div className="flex-1">
            <h3 className="text-white font-bold text-lg mb-1">
              {notification.priority === "critical" ? "Critical Alert" :
               notification.priority === "high" ? "High Stress Alert" :
               "Wellness Reminder"}
            </h3>
            <p className="text-white text-sm leading-relaxed">
              {notification.message}
            </p>
            <div className="mt-2 flex items-center space-x-4 text-xs text-white text-opacity-90">
              <span>Stress Level: {notification.stress_day}/100</span>
              <span>•</span>
              <span>{new Date(notification.sent_at).toLocaleTimeString()}</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-white hover:text-gray-200 text-2xl font-bold ml-4 transition-all"
          title="Dismiss"
        >
          ×
        </button>
      </div>

      <style jsx>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-slideDown {
          animation: slideDown 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}

