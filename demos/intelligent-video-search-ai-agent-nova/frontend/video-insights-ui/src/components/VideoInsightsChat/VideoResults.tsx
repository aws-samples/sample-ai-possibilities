import React from 'react';
import { VideoResult } from '../../types';
import { PlayCircle, Users, Hash, BarChart3, Clock, Target } from 'lucide-react';

interface VideoResultsProps {
  videos: VideoResult[];
  onVideoClick?: (video: VideoResult) => void;
  showSimilarityScores?: boolean;
}

const VideoResults: React.FC<VideoResultsProps> = ({ videos, onVideoClick, showSimilarityScores = false }) => {
  const getSentimentColor = (sentiment?: string): string => {
    if (!sentiment) return 'text-gray-600';
    if (sentiment.toLowerCase().includes('positive')) return 'text-green-600';
    if (sentiment.toLowerCase().includes('negative')) return 'text-red-600';
    return 'text-gray-600';
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'Unknown date';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Unknown date';
    }
  };

  const getSimilarityColor = (score: number): string => {
    if (score >= 0.9) return 'bg-gradient-to-r from-green-500 to-emerald-600';
    if (score >= 0.8) return 'bg-gradient-to-r from-blue-500 to-cyan-600';
    if (score >= 0.7) return 'bg-gradient-to-r from-yellow-500 to-orange-600';
    return 'bg-gradient-to-r from-gray-400 to-gray-500';
  };

  const getSimilarityLabel = (score: number): string => {
    if (score >= 0.9) return 'Very Similar';
    if (score >= 0.8) return 'Similar';
    if (score >= 0.7) return 'Somewhat Similar';
    return 'Low Similarity';
  };

  return (
    <div className="space-y-3">
      {showSimilarityScores && (
        <div className="flex items-center space-x-2 mb-4 p-3 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg">
          <Target className="text-purple-600" size={20} />
          <h3 className="text-md font-semibold text-purple-900">
            Similar Videos Found ({videos.length})
          </h3>
          <span className="text-sm text-purple-700">
            Ranked by visual similarity
          </span>
        </div>
      )}
      {videos.map((video, index) => (
        <div 
          key={video.video_id || index}
          className="bg-gray-50 rounded-lg overflow-hidden hover:shadow-md transition-all cursor-pointer border border-gray-200"
          onClick={() => onVideoClick?.(video)}
        >
          <div className="flex">
            {/* Thumbnail */}
            <div className="w-40 h-24 flex-shrink-0 bg-gray-200 relative">
              {video.thumbnail_url ? (
                <img 
                  src={video.thumbnail_url} 
                  alt={video.video_title || 'Video thumbnail'}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Hide broken image and show placeholder
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <PlayCircle className="text-gray-400" size={32} />
                </div>
              )}
              {/* Play overlay */}
              <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 hover:bg-opacity-30 transition-all">
                <PlayCircle className="text-white opacity-0 hover:opacity-100 transition-opacity" size={24} />
              </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 p-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900 text-sm mb-1 line-clamp-1">
                    {video.video_title || 'Untitled Video'}
                  </h4>
                  
                  <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                    {video.summary}
                  </p>
                  
                  {/* Tags */}
                  <div className="flex flex-wrap gap-1.5">
                    {video.brands_mentioned && video.brands_mentioned.length > 0 && (
                      <div className="flex items-center space-x-0.5 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                        <Hash size={10} />
                        <span>{video.brands_mentioned.length} brands</span>
                      </div>
                    )}
                    
                    {video.people_mentioned && video.people_mentioned.length > 0 && (
                      <div className="flex items-center space-x-0.5 text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                        <Users size={10} />
                        <span>{video.people_mentioned.length} people</span>
                      </div>
                    )}
                    
                    {video.sentiment && (
                      <div className={`flex items-center space-x-0.5 text-xs px-1.5 py-0.5 rounded ${getSentimentColor(video.sentiment)} ${video.sentiment.toLowerCase().includes('positive') ? 'bg-green-100' : video.sentiment.toLowerCase().includes('negative') ? 'bg-red-100' : 'bg-gray-100'}`}>
                        <BarChart3 size={10} />
                        <span>Sentiment</span>
                      </div>
                    )}
                    
                    {/* Similarity Progress Bar */}
                    {showSimilarityScores && video.score && (
                      <div className="w-full mt-2">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-500">Similarity</span>
                          <span className="font-medium text-gray-700">
                            {getSimilarityLabel(video.score)}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-1000 ease-out ${getSimilarityColor(video.score)}`}
                            style={{ 
                              width: `${video.score * 100}%`,
                              animationDelay: `${index * 200 + 500}ms`
                            }}
                          />
                        </div>
                      </div>
                    )}
                    
                    <span className="text-xs text-gray-500 flex items-center ml-auto">
                      <Clock size={10} className="mr-0.5" />
                      {formatDate(video.processing_date)}
                    </span>
                  </div>
                </div>
                
                {video.score && showSimilarityScores && (
                  <div className="ml-2">
                    <div className={`px-2 py-1 rounded-full text-xs font-medium text-white ${getSimilarityColor(video.score)}`}>
                      {(video.score * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
                {video.score && !showSimilarityScores && (
                  <div className="ml-2 text-xs text-gray-500">
                    Score: {video.score.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default VideoResults;