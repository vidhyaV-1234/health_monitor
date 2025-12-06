import { useState } from 'react';
import { getFCMToken } from '../firebase-config';
import { simpleFCMTest } from '../utils/fcm-simple-test';

export default function FCMTest() {
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debugInfo, setDebugInfo] = useState([]);

  const testFCMToken = async () => {
    setLoading(true);
    setError(null);
    setToken(null);
    setDebugInfo([]);

    // Capture console logs
    const logs = [];
    const originalLog = console.log;
    const originalError = console.error;
    
    console.log = (...args) => {
      logs.push({ type: 'log', message: args.join(' ') });
      originalLog(...args);
    };
    
    console.error = (...args) => {
      logs.push({ type: 'error', message: args.join(' ') });
      originalError(...args);
    };

    try {
      console.log('🧪 Starting comprehensive FCM test...');
      
      // Run simple test first
      const result = await simpleFCMTest();
      
      if (result && typeof result === 'string') {
        setToken(result);
        console.log('✅ FCM Test successful!');
      } else {
        setError('FCM token generation failed. Check console for details.');
      }
    } catch (err) {
      console.error('❌ FCM Test failed:', err);
      setError(err.message);
    } finally {
      // Restore console
      console.log = originalLog;
      console.error = originalError;
      setDebugInfo(logs);
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 m-4">
      <h3 className="text-xl font-bold mb-4 flex items-center">
        <span className="mr-2">🧪</span>
        FCM Token Test
      </h3>
      
      <div className="space-y-4">
        <button
          onClick={testFCMToken}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Testing...' : 'Test FCM Token Generation'}
        </button>

        {loading && (
          <div className="flex items-center space-x-2 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>Generating FCM token...</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-semibold text-red-800 mb-1">❌ Error</h4>
            <p className="text-red-700 text-sm">{error}</p>
            <div className="mt-2 text-xs text-red-600">
              <p>Common solutions:</p>
              <ul className="list-disc list-inside ml-2">
                <li>Configure Firebase in firebase-config.js</li>
                <li>Set the correct VAPID key</li>
                <li>Ensure you're on HTTPS or localhost</li>
                <li>Grant notification permissions</li>
              </ul>
            </div>
          </div>
        )}

        {token && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-semibold text-green-800 mb-2">✅ Success!</h4>
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium text-green-700">Token Length:</span>
                <span className="ml-2 text-sm text-green-600">{token.length} characters</span>
              </div>
              <div>
                <span className="text-sm font-medium text-green-700">Token Preview:</span>
                <div className="mt-1 p-2 bg-white rounded border text-xs font-mono break-all">
                  {token.substring(0, 100)}...
                </div>
              </div>
              <div className="text-xs text-green-600">
                ✅ FCM token generated successfully! This token can be used to send push notifications.
              </div>
            </div>
          </div>
        )}

        {debugInfo.length > 0 && (
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <h4 className="font-semibold text-gray-800 mb-2">🔍 Debug Log</h4>
            <div className="max-h-60 overflow-y-auto space-y-1">
              {debugInfo.map((log, index) => (
                <div key={index} className={`text-xs font-mono p-1 rounded ${
                  log.type === 'error' ? 'bg-red-100 text-red-700' : 'bg-white text-gray-700'
                }`}>
                  {log.message}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-semibold text-blue-800 mb-2">💡 Debug Info</h4>
          <p className="text-sm text-blue-700 mb-2">
            Open browser console (F12) to see detailed debug information when testing.
          </p>
          <p className="text-xs text-blue-600">
            You can also run <code className="bg-white px-1 rounded">window.simpleFCMTest()</code> in the console anytime.
          </p>
        </div>
      </div>
    </div>
  );
}