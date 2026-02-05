import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, X, Video, Search, Loader2, AlertCircle, Target, Zap, ChevronRight } from 'lucide-react';
import { VideoResult } from '../../types';

interface VideoSimilaritySearchProps {
  onSearchComplete?: (results: VideoResult[]) => void;
  onClose?: () => void;
}

interface UploadProgress {
  progress: number;
  stage: 'uploading' | 'processing' | 'searching' | 'complete';
  message: string;
}

const VideoSimilaritySearch: React.FC<VideoSimilaritySearchProps> = ({ 
  onSearchComplete,
  onClose 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null);
  const [uploadedVideoPreview, setUploadedVideoPreview] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [similarVideos, setSimilarVideos] = useState<VideoResult[]>([]);
  const [error, setError] = useState<string>('');
  const [isSearching, setIsSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8090';

  // Cleanup video preview URL on unmount
  useEffect(() => {
    return () => {
      if (uploadedVideoPreview) {
        URL.revokeObjectURL(uploadedVideoPreview);
      }
    };
  }, [uploadedVideoPreview]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const validateVideoFile = (file: File): boolean => {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = ['video/mp4', 'video/webm', 'video/ogg', 'video/avi', 'video/mov'];
    
    if (file.size > maxSize) {
      setError('File size must be less than 100MB');
      return false;
    }
    
    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a valid video file (MP4, WebM, OGG, AVI, MOV)');
      return false;
    }
    
    return true;
  };

  const uploadVideo = async (file: File): Promise<void> => {
    setError('');
    setIsSearching(true);
    setUploadProgress({
      progress: 10,
      stage: 'uploading',
      message: 'Uploading video...'
    });

    try {
      setUploadProgress({
        progress: 30,
        stage: 'processing',
        message: 'Processing video for similarity analysis...'
      });

      // Create FormData for file upload
      const formData = new FormData();
      formData.append('file', file);
      formData.append('use_visual_similarity', 'true');
      formData.append('max_results', '8');

      // Upload and search for similar videos
      const response = await fetch(`${API_URL}/search/video`, {
        method: 'POST',
        body: formData, // Send as multipart/form-data
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      setUploadProgress({
        progress: 70,
        stage: 'searching',
        message: 'Finding similar videos...'
      });

      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      setUploadProgress({
        progress: 100,
        stage: 'complete',
        message: 'Search complete!'
      });

      // Parse results
      const results = data.similar_videos || [];
      setSimilarVideos(results);
      onSearchComplete?.(results);

      // Clear progress after a short delay
      setTimeout(() => {
        setUploadProgress(null);
      }, 1500);

    } catch (error) {
      console.error('Upload error:', error);
      setError(error instanceof Error ? error.message : 'Upload failed');
      setUploadProgress(null);
    } finally {
      setIsSearching(false);
    }
  };

  const createVideoPreview = (file: File): void => {
    const url = URL.createObjectURL(file);
    setUploadedVideoPreview(url);
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find(file => file.type.startsWith('video/'));
    
    if (videoFile && validateVideoFile(videoFile)) {
      setUploadedVideo(videoFile);
      createVideoPreview(videoFile);
      await uploadVideo(videoFile);
    }
  }, []);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && validateVideoFile(file)) {
      setUploadedVideo(file);
      createVideoPreview(file);
      await uploadVideo(file);
    }
  }, []);

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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
                <Target className="text-white" size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Video Similarity Search</h2>
                <p className="text-sm text-gray-500">Upload a video to find similar content in your library</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Upload Area */}
        <div className="p-6">
          {!uploadedVideo && !uploadProgress && (
            <div
              className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                isDragging
                  ? 'border-purple-400 bg-purple-50 scale-105'
                  : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              
              <div className="flex flex-col items-center space-y-4">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isDragging ? 'bg-purple-100 scale-110' : 'bg-gray-100'
                }`}>
                  <Upload className={`transition-colors duration-300 ${
                    isDragging ? 'text-purple-600' : 'text-gray-600'
                  }`} size={24} />
                </div>
                
                <div>
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    {isDragging ? 'Drop your video here' : 'Upload a video to search'}
                  </p>
                  <p className="text-sm text-gray-500 mb-4">
                    Drag and drop a video file or click to browse
                  </p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-200 transform hover:scale-105"
                  >
                    <Video size={20} />
                    <span>Choose Video</span>
                  </button>
                </div>
                
                <p className="text-xs text-gray-400">
                  Supports MP4, WebM, OGG, AVI, MOV • Max 100MB
                </p>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploadProgress && (
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-6 border border-purple-200">
              <div className="flex items-center space-x-3 mb-4">
                <Loader2 className="animate-spin text-purple-600" size={20} />
                <span className="font-medium text-gray-900">{uploadProgress.message}</span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500 ease-out"
                  style={{ width: `${uploadProgress.progress}%` }}
                />
              </div>
              
              <div className="flex justify-between text-sm text-gray-600 mt-2">
                <span className="capitalize">{uploadProgress.stage}</span>
                <span>{uploadProgress.progress}%</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center space-x-3">
              <AlertCircle className="text-red-500" size={20} />
              <span className="text-red-700">{error}</span>
            </div>
          )}

          {/* Uploaded Video Info */}
          {uploadedVideo && !uploadProgress && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-green-900">Uploaded Video</h3>
                <button
                  onClick={() => {
                    setUploadedVideo(null);
                    setUploadedVideoPreview(null);
                    setSimilarVideos([]);
                    setError('');
                    if (uploadedVideoPreview) {
                      URL.revokeObjectURL(uploadedVideoPreview);
                    }
                  }}
                  className="text-green-600 hover:text-green-800 transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="flex items-center space-x-4">
                {/* Video Preview */}
                <div className="w-32 h-20 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                  {uploadedVideoPreview ? (
                    <video
                      src={uploadedVideoPreview}
                      className="w-full h-full object-cover"
                      muted
                      playsInline
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Video className="text-gray-400" size={24} />
                    </div>
                  )}
                </div>
                {/* Video Info */}
                <div className="flex-1">
                  <p className="font-medium text-green-900 text-sm">{uploadedVideo.name}</p>
                  <p className="text-sm text-green-700">
                    {(uploadedVideo.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    Ready to find similar videos
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Similar Videos Results */}
        {similarVideos.length > 0 && (
          <div className="px-6 pb-6">
            <div className="flex items-center space-x-2 mb-4">
              <Zap className="text-purple-600" size={20} />
              <h3 className="text-lg font-semibold text-gray-900">
                Similar Videos Found ({similarVideos.length})
              </h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {similarVideos.map((video, index) => {
                const score = video.score || 0;
                return (
                  <div
                    key={video.video_id}
                    className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1 opacity-0 animate-fade-in"
                    style={{
                      animationDelay: `${index * 100}ms`,
                      animationFillMode: 'forwards'
                    }}
                  >
                    <div className="flex">
                      {/* Thumbnail */}
                      <div className="w-32 h-20 flex-shrink-0 bg-gray-100 relative">
                        {video.thumbnail_url ? (
                          <img
                            src={video.thumbnail_url}
                            alt={video.video_title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Video className="text-gray-400" size={24} />
                          </div>
                        )}
                        
                        {/* Similarity Badge */}
                        <div className="absolute top-2 right-2">
                          <div className={`px-2 py-1 rounded-full text-xs font-medium text-white ${getSimilarityColor(score)}`}>
                            {(score * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 p-3">
                        <h4 className="font-medium text-gray-900 text-sm mb-1 line-clamp-1">
                          {video.video_title || 'Untitled Video'}
                        </h4>
                        
                        <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                          {video.summary}
                        </p>
                        
                        {/* Similarity Progress Bar */}
                        <div className="mb-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-500">Similarity</span>
                            <span className="font-medium text-gray-700">
                              {getSimilarityLabel(score)}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full transition-all duration-1000 ease-out ${getSimilarityColor(score)}`}
                              style={{ 
                                width: `${score * 100}%`,
                                animationDelay: `${index * 200 + 500}ms`
                              }}
                            />
                          </div>
                        </div>
                        
                        {/* Tags */}
                        <div className="flex flex-wrap gap-1">
                          {video.brands_mentioned?.slice(0, 2).map((brand, i) => (
                            <span
                              key={i}
                              className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                            >
                              {brand}
                            </span>
                          ))}
                          {video.people_mentioned?.slice(0, 1).map((person, i) => (
                            <span
                              key={i}
                              className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded"
                            >
                              {person}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="flex items-center pr-3">
                        <ChevronRight className="text-gray-400" size={16} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* No Results */}
        {uploadedVideo && !isSearching && !uploadProgress && similarVideos.length === 0 && !error && (
          <div className="px-6 pb-6">
            <div className="text-center py-8">
              <Search className="mx-auto text-gray-300 mb-3" size={48} />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Similar Videos Found</h3>
              <p className="text-gray-500">
                We couldn't find any similar videos in your library. Try uploading a different video.
              </p>
            </div>
          </div>
        )}
      </div>
      
    </div>
  );
};

export default VideoSimilaritySearch;