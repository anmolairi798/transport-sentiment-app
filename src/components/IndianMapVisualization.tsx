import React from 'react';
import { StateData } from '../types';
import { getSentimentColor, getSentimentEmoji } from '../utils/sentimentAnalysis';
import { INDIAN_STATES } from '../utils/indianStatesData';

interface IndianMapVisualizationProps {
  states: StateData[];
  selectedTransportType: string;
}

export const IndianMapVisualization: React.FC<IndianMapVisualizationProps> = ({ 
  states, 
  selectedTransportType 
}) => {
  const filteredStates = states.filter(state => 
    selectedTransportType === 'all' || 
    state.transportBreakdown[selectedTransportType as keyof typeof state.transportBreakdown] > 0
  );

  // Boundary of India (approximate)
  const MIN_LAT = 6;
  const MAX_LAT = 37;
  const MIN_LNG = 68;
  const MAX_LNG = 97;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">India Transport Sentiment Map</h2>
        <div className="text-sm text-gray-600">
          Real-time sentiment analysis across Indian states
        </div>
      </div>
      
      {/* Map Container */}
      <div className="relative bg-gradient-to-br from-blue-50 to-green-50 rounded-lg h-[500px] overflow-hidden">
        {/* Indian Map Image */}
        <div className="absolute inset-0 w-full h-full">
          <img 
            src="/MapChart_Map.png" 
            alt="Indian Map" 
            className="w-full h-full object-cover"  // 🔄 Stretch map to fill
            style={{ filter: 'brightness(1.1) contrast(1.05)' }}
            onError={(e) => {
              console.error('Map image failed to load:', e);
              e.currentTarget.style.display = 'none';
            }}
            onLoad={() => console.log('Map image loaded successfully')}
          />
        </div>

        {/* State Markers */}
        {filteredStates.map((state) => {
          const stateCoords = INDIAN_STATES[state.state];
          if (!stateCoords) return null;

          const score = Number(state.sentimentScore || 0);

          // 🔄 100% Scaled position mapping
          const x = ((stateCoords.lng - MIN_LNG) / (MAX_LNG - MIN_LNG)) * 100;
          const y = ((MAX_LAT - stateCoords.lat) / (MAX_LAT - MIN_LAT)) * 100;

          return (
            <div
              key={state.state}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
              style={{ left: `${x}%`, top: `${y}%` }}
            >
              {/* Heatmap Circle */}
              <div
                className="w-12 h-12 rounded-full opacity-60 animate-pulse"
                style={{
                  backgroundColor: getSentimentColor(score),
                  transform: `scale(${0.8 + Math.abs(score) * 0.8})`,
                }}
              />

              {/* Emoji Marker */}
              <div
                className="absolute inset-0 w-6 h-6 rounded-full border-2 border-white shadow-lg flex items-center justify-center text-xs font-bold text-white m-3"
                style={{ backgroundColor: getSentimentColor(score) }}
              >
                {getSentimentEmoji({
                  polarity: score,
                  subjectivity: 0.5,
                  label: 'neutral',
                  confidence: 0.8,
                })}
              </div>

              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                <div className="bg-gray-800 text-white px-4 py-3 rounded-lg text-sm whitespace-nowrap shadow-xl">
                  <div className="font-semibold text-yellow-300">{state.state}</div>
                  <div className="text-xs text-gray-300 mb-2">
                    Cities: {state.majorCities.slice(0, 2).join(', ')}
                  </div>
                  <div className="space-y-1">
                    <div>Sentiment: 
                      <span className="font-medium">
                        {typeof state.sentimentScore === 'number'
                          ? state.sentimentScore.toFixed(2)
                          : !isNaN(Number(state.sentimentScore))
                            ? Number(state.sentimentScore).toFixed(2)
                            : 'N/A'}
                      </span>
                    </div>
                    <div>Messages: 
                      <span className="font-medium">{state.totalMessages.toLocaleString()}</span>
                    </div>
                    <div>Trend: 
                      <span className={`font-medium ${
                        state.trend === 'improving' ? 'text-green-400' : 
                        state.trend === 'declining' ? 'text-red-400' : 'text-yellow-400'
                      }`}>{state.trend}</span>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-600">
                    <div className="text-xs">
                      <div>🚌 Bus: {state.transportBreakdown.bus}</div>
                      <div>🚇 Metro: {state.transportBreakdown.metro}</div>
                      <div>🚂 Train: {state.transportBreakdown.train}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Regional Labels */}
        <div className="absolute top-4 left-4 text-xs text-gray-600 bg-white/80 p-2 rounded">
          <div className="font-semibold mb-1">Regions</div>
          <div>🔵 North • 🟢 South • 🟡 East • 🟠 West • 🟣 Central</div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-green-500"></div>
            <span className="text-sm">Positive Sentiment</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
            <span className="text-sm">Neutral Sentiment</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-red-500"></div>
            <span className="text-sm">Negative Sentiment</span>
          </div>
        </div>
        <div className="text-sm text-gray-500">
          Total States: {filteredStates.length} | 
          Last Updated: {new Date().toLocaleTimeString('en-IN')}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="mt-4 grid grid-cols-5 gap-4 text-center">
        {['north', 'south', 'east', 'west', 'central'].map(region => (
          <div key={region} className={`bg-${region}-50 p-3 rounded-lg`}>
            <div className={`text-lg font-bold text-${region}-600`}>
              {filteredStates.filter(s => INDIAN_STATES[s.state]?.region === region).length}
            </div>
            <div className={`text-xs text-${region}-600 capitalize`}>{region}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
