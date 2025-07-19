import React, { useEffect, useState } from 'react';
import { VideoResult } from '../../types';
import { PlayCircle } from 'lucide-react';

interface VideoCarouselProps {
  videos: VideoResult[];
  onVideoClick?: (video: VideoResult) => void;
}

const VideoCarousel: React.FC<VideoCarouselProps> = ({ videos, onVideoClick }) => {
  const [offset, setOffset] = useState(0);
  
  useEffect(() => {
    if (videos.length === 0) return;
    
    // Auto-scroll effect
    const interval = setInterval(() => {
      setOffset((prev) => (prev + 1) % (videos.length * 200));
    }, 30); // Smooth scrolling
    
    return () => clearInterval(interval);
  }, [videos.length]);
  
  // Show message if no videos
  if (videos.length === 0) {
    return (
      <div className="py-8 px-6">
        <div className="text-center text-gray-500">
          <PlayCircle size={32} className="mx-auto mb-3 text-gray-300" />
          <p className="text-sm font-medium">No videos in your library yet</p>
          <p className="text-xs text-gray-400 mt-1">Upload videos to S3 to get started!</p>
        </div>
      </div>
    );
  }
  
  // Duplicate videos for seamless loop
  const displayVideos = [...videos, ...videos, ...videos];
  
  return (
    <div className="relative overflow-hidden py-4">
      <div className="absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-white to-transparent z-10" />
      <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-white to-transparent z-10" />
      
      <div 
        className="flex space-x-3 transition-transform px-6"
        style={{ transform: `translateX(-${offset}px)` }}
      >
        {displayVideos.map((video, index) => (
          <div
            key={`${video.video_id}-${index}`}
            className="flex-shrink-0 w-44 cursor-pointer group"
            onClick={() => onVideoClick?.(video)}
          >
            <div className="relative overflow-hidden rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-100">
              {/* Thumbnail */}
              <div className="w-44 h-24 bg-gray-100 relative">
                {video.thumbnail_url ? (
                  <img 
                    src={video.thumbnail_url} 
                    alt={video.video_title || 'Video thumbnail'}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gray-100">
                    <PlayCircle className="text-gray-400" size={32} />
                  </div>
                )}
                
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all flex items-center justify-center">
                  <PlayCircle className="text-white opacity-0 group-hover:opacity-100 transition-opacity" size={24} />
                </div>
                
                {/* Fade effect for rolling appearance */}
                <div 
                  className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-50"
                  style={{
                    opacity: Math.max(0, 1 - Math.abs((index * 200 - offset + 600) / 600))
                  }}
                />
              </div>
              
              {/* Title */}
              <div className="p-3 bg-white">
                <p className="text-xs font-medium text-gray-900 line-clamp-1">
                  {video.video_title || 'Untitled Video'}
                </p>
                <p className="text-xs text-gray-500 line-clamp-1 mt-1">
                  {video.brands_mentioned?.join(', ') || video.people_mentioned?.join(', ') || 'No tags'}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
      
    </div>
  );
};

export default VideoCarousel;