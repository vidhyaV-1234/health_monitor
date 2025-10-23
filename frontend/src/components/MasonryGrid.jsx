import { useState, useEffect } from "react";

export default function MasonryGrid({ items, onItemClick }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  const getFloatClass = (index) => {
    const classes = ['float-1', 'float-2', 'float-3'];
    return classes[index % classes.length];
  };

  const getGradient = (emotion) => {
    const gradients = {
      happy: 'from-yellow-400 via-orange-400 to-pink-400',
      sad: 'from-blue-400 via-indigo-400 to-purple-400',
      angry: 'from-red-400 via-orange-400 to-yellow-400',
      anxious: 'from-purple-400 via-pink-400 to-red-400',
      calm: 'from-green-400 via-teal-400 to-blue-400',
      excited: 'from-pink-400 via-purple-400 to-indigo-400',
      neutral: 'from-gray-400 via-gray-500 to-gray-600',
      default: 'from-indigo-400 via-purple-400 to-pink-400'
    };
    return gradients[emotion?.toLowerCase()] || gradients.default;
  };

  const getEmoji = (emotion) => {
    const emojis = {
      happy: '😊',
      sad: '😢',
      angry: '😠',
      anxious: '😰',
      calm: '😌',
      excited: '🤗',
      neutral: '😐',
      default: '💭'
    };
    return emojis[emotion?.toLowerCase()] || emojis.default;
  };

  const parseRecommendations = (recommendations) => {
    // Convert to string if it's an array
    let recText = Array.isArray(recommendations) 
      ? recommendations.join(' ') 
      : String(recommendations);

    console.log('Original recommendations:', recText);

    // Extract mood and stress level
    const moodMatch = recText.match(/Mood:\s*([^,]+),?\s*stress_level:\s*(\d+)/i);
    let moodInfo = null;
    if (moodMatch) {
      moodInfo = { 
        mood: moodMatch[1].trim(), 
        stressLevel: moodMatch[2] 
      };
      // Remove the mood info from the text
      recText = recText.replace(moodMatch[0], '').trim();
    }

    // Split by numbers followed by period and process each one
    const recommendations_list = [];
    
    // First, split by the pattern "number."
    const lines = recText.split(/(?=\d+\.\s)/);
    
    lines.forEach((line) => {
      line = line.trim();
      if (!line) return;
      
      // Match: number. followed by anything
      const match = line.match(/^(\d+)\.\s*(.+)$/s);
      if (!match) return;
      
      const number = match[1];
      let content = match[2].trim();
      
      // Try to split by " - " (dash with spaces)
      let title, description;
      const dashIndex = content.indexOf(' - ');
      
      if (dashIndex !== -1) {
        title = content.substring(0, dashIndex).trim();
        description = content.substring(dashIndex + 3).trim();
      } else {
        // Try to split by "-" (dash without spaces)
        const dashIndex2 = content.indexOf('-');
        if (dashIndex2 !== -1) {
          title = content.substring(0, dashIndex2).trim();
          description = content.substring(dashIndex2 + 1).trim();
        } else {
          // No dash found, use first few words as title
          const words = content.split(/\s+/);
          title = words.slice(0, 4).join(' ');
          description = words.slice(4).join(' ') || content;
        }
      }
      
      if (title && description && recommendations_list.length < 5) {
        recommendations_list.push({
          number: number,
          title: title,
          description: description
        });
      }
    });

    console.log('Parsed recommendations:', recommendations_list);

    return { moodInfo, recommendations: recommendations_list };
  };

  return (
    <div className="masonry-grid">
      {items.map((item, index) => (
        <div
          key={index}
          className={`masonry-item stagger-${(index % 5) + 1}`}
          onMouseEnter={() => setHoveredIndex(index)}
          onMouseLeave={() => setHoveredIndex(null)}
          onClick={() => onItemClick && onItemClick(item)}
        >
          <div className={`pinterest-card ${getFloatClass(index)} ${hoveredIndex === index ? 'glow' : ''}`}>
            {/* Emoji Outside */}
            <div className="flex justify-center -mb-8 relative z-10">
              <div className="text-7xl bg-white rounded-full p-2 shadow-lg">
                {getEmoji(item.emotion)}
              </div>
            </div>
            
            {/* Thin Emotion Bar */}
            <div className={`bg-gradient-to-r ${getGradient(item.emotion)} pt-10 pb-3 px-4 text-center`}>
              <div className="text-lg font-bold text-white capitalize">{item.emotion}</div>
              {item.emotion_confidence && (
                <div className="text-xs font-semibold text-white text-opacity-90 mt-1">
                  {Math.round(item.emotion_confidence * 100)}% confidence
                </div>
              )}
            </div>

            {/* Content */}
            <div className="p-6">
              {item.mood_text && (
                <div className="mb-4">
                  <p className="text-gray-700 text-sm leading-relaxed line-clamp-4">
                    {item.mood_text}
                  </p>
                </div>
              )}

              {item.audio_transcript && item.audio_transcript !== "Audio processing not available" && (
                <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
                  <div className="flex items-center mb-2">
                    <span className="text-purple-600 mr-2">🎤</span>
                    <span className="text-xs font-semibold text-purple-600">Audio Transcript</span>
                  </div>
                  <p className="text-xs text-gray-600 italic line-clamp-3">
                    "{item.audio_transcript}"
                  </p>
                </div>
              )}

              {item.recommendations && (() => {
                const { moodInfo, recommendations } = parseRecommendations(item.recommendations);
                
                return (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                      <span className="mr-2">💡</span>
                      Recommendations
                    </h4>
                    
                    {moodInfo && (
                      <div className="mb-3 p-3 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200">
                        <div className="flex items-center justify-between text-sm">
                          <div>
                            <span className="font-semibold text-indigo-700">Mood: </span>
                            <span className="text-indigo-900 font-bold capitalize">{moodInfo.mood}</span>
                          </div>
                          <div className="bg-purple-600 text-white px-3 py-1 rounded-full font-bold">
                            Stress: {moodInfo.stressLevel}/10
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div className="space-y-2">
                      {recommendations.length > 0 ? (
                        recommendations.slice(0, 5).map((rec, recIndex) => (
                          <div key={recIndex} className="recommendation-card group">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0 w-7 h-7 bg-gradient-to-br from-indigo-500 to-purple-500 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-md">
                                {rec.number}
                              </div>
                              <div className="flex-1 min-w-0">
                                <h5 className="text-xs font-bold text-gray-800 mb-1 leading-tight">{rec.title}</h5>
                                <p className="text-xs text-gray-600 leading-relaxed">{rec.description}</p>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="recommendation-card">
                          <p className="text-xs text-gray-700">{item.recommendations}</p>
                        </div>
                      )}
                      
                      {recommendations.length > 5 && (
                        <p className="text-xs text-gray-500 italic mt-2 text-center">
                          +{recommendations.length - 5} more recommendations
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}

              {item.timestamp && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-xs text-gray-500 flex items-center">
                    <span className="mr-2">📅</span>
                    {new Date(item.timestamp).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              )}
            </div>

            {/* Hover Overlay */}
            {hoveredIndex === index && (
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none rounded-3xl"></div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

