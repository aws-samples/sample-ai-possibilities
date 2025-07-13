import React from 'react';
import { PlayCircle, Users, Hash, BarChart3, Clock, ChevronRight } from 'lucide-react';
import { VideoCardProps } from '../../types';

const VideoCard: React.FC<VideoCardProps> = ({ video, onClick }) => {
  const getSentimentColor = (sentiment?: string): string => {
    if (!sentiment) return 'text-gray-600';
    if (sentiment.toLowerCase().includes('positive')) return 'text-green-600 bg-green-50';
    if (sentiment.toLowerCase().includes('negative')) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'Unknown date';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Unknown date';
    }
  };

  return (
    <div 
      className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all cursor-pointer"
      onClick={() => onClick(video)}
    >
      <div className="flex">
        {/* Thumbnail */}
        {video.thumbnail_url && (
          <div className="w-48 h-28 flex-shrink-0">
            <img 
              src={video.thumbnail_url} 
              alt={video.video_title || 'Video thumbnail'}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to placeholder if image fails to load
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        )}
        
        {/* Content */}
        <div className="flex-1 p-4">
          <div className="flex items-center space-x-2 mb-2">
            <PlayCircle className="text-brand-600" size={20} />
            <h3 className="font-semibold text-gray-900">{video.video_title || 'Untitled Video'}</h3>
          </div>
          
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {video.summary}
          </p>
          
          <div className="flex flex-wrap gap-2 mb-2">
            {video.brands_mentioned && video.brands_mentioned.length > 0 && (
              <div className="flex items-center space-x-1 text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                <Hash size={12} />
                <span>{video.brands_mentioned.length} brands</span>
              </div>
            )}
            
            {video.people_mentioned && video.people_mentioned.length > 0 && (
              <div className="flex items-center space-x-1 text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded">
                <Users size={12} />
                <span>{video.people_mentioned.length} people</span>
              </div>
            )}
            
            {video.sentiment && (
              <div className={`flex items-center space-x-1 text-xs px-2 py-1 rounded ${getSentimentColor(video.sentiment)}`}>
                <BarChart3 size={12} />
                <span>Sentiment</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 flex items-center">
              <Clock size={12} className="mr-1" />
              {formatDate(video.processing_date)}
            </span>
            <ChevronRight className="text-gray-400" size={16} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoCard;