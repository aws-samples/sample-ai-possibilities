import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Search, Loader2, Sparkles, PlayCircle, ChevronUp, ChevronDown, Video, Target } from 'lucide-react';
import VideoResults from './VideoResults';
import VideoCarousel from './VideoCarousel';
import VideoSimilaritySearch from './VideoSimilaritySearch';
import MessageFormatter from './MessageFormatter';
import { Message, WebSocketMessage, VideoResult } from '../../types';

const VideoInsightsChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [sessionId] = useState<string>(`session_${Date.now()}`);
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [currentTool, setCurrentTool] = useState<string>('');
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string>('');
  const [sampleVideos, setSampleVideos] = useState<VideoResult[]>([]);
  const [carouselExpanded, setCarouselExpanded] = useState<boolean>(true);
  const [currentVideo, setCurrentVideo] = useState<VideoResult | null>(null);
  const [showSimilaritySearch, setShowSimilaritySearch] = useState<boolean>(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingMessageRef = useRef<string>('');
  const isStreamingRef = useRef<boolean>(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8090';
  const VIDEO_API_URL = process.env.REACT_APP_VIDEO_API_URL || 'http://localhost:8091';
  const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

  const suggestions: string[] = [
    "Find training videos about Python programming",
    "Show me gameplay from last month",
    "Search for tutorial videos on machine learning",
    "Are there any videos that feature Adam?",
    "Find presentation recordings from meetings",
    "Find videos with positive sentiment"
  ];

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const connectWebSocket = useCallback((): void => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    const wsUrl = `${WS_URL}/ws/${sessionId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setWsConnected(true);
        setConnectionError('');
        reconnectAttemptsRef.current = 0;
      };

      wsRef.current.onmessage = (event: MessageEvent) => {
        const data: WebSocketMessage = JSON.parse(event.data);
        
        switch (data.type) {
          case 'status':
            console.log('Status:', data.message);
            setCurrentTool('');
            break;
            
          case 'tool_use':
            setCurrentTool(data.tool || '');
            console.log('Using tool:', data.tool);
            break;
            
          case 'stream':
            isStreamingRef.current = true;
            setIsStreaming(true);
            setIsLoading(false);
            streamingMessageRef.current += data.content || '';
            setStreamingMessage(streamingMessageRef.current);
            break;
            
          case 'complete':
            if (streamingMessageRef.current || isStreamingRef.current) {
              const assistantMessage: Message = {
                role: 'assistant',
                content: streamingMessageRef.current,
                timestamp: data.timestamp || new Date().toISOString(),
                metadata: data.metadata
              };
              setMessages(prev => [...prev, assistantMessage]);
              
              // Check if response contains video results and refresh library
              const { videos } = parseVideoResults(streamingMessageRef.current);
              if (videos.length > 0 && messages.length === 1) {
                // Refresh carousel if we're on the main page and got video results
                setTimeout(() => refreshVideoLibrary(), 1000);
              }
              
              streamingMessageRef.current = '';
              isStreamingRef.current = false;
              setStreamingMessage('');
              setIsStreaming(false);
              setCurrentTool('');
            }
            setIsLoading(false);
            break;
            
          case 'response':
            const assistantMessage: Message = {
              role: 'assistant',
              content: data.content || '',
              timestamp: data.timestamp || new Date().toISOString()
            };
            setMessages(prev => [...prev, assistantMessage]);
            setIsLoading(false);
            break;
            
          case 'error':
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: `❌ Error: ${data.message}`,
              timestamp: new Date().toISOString()
            }]);
            setIsLoading(false);
            setIsStreaming(false);
            setStreamingMessage('');
            streamingMessageRef.current = '';
            isStreamingRef.current = false;
            setCurrentTool('');
            break;
            
          default:
            console.warn('Unknown message type:', data.type);
            break;
        }
      };

      wsRef.current.onerror = (error: Event) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
        
        const errorMsg = `Unable to connect to Video Keeper at ${wsUrl}. Please ensure the backend is running.`;
        setConnectionError(errorMsg);
        
        if (reconnectAttemptsRef.current === 0) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `❌ ${errorMsg}\n\nUsing HTTP fallback mode. Real-time streaming will not be available.`,
            timestamp: new Date().toISOString()
          }]);
        }
      };

      wsRef.current.onclose = (event: CloseEvent) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setWsConnected(false);
        
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current++;
          
          console.log(`Reconnection attempt ${reconnectAttemptsRef.current} in ${delay}ms`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionError((error as Error).message);
      setWsConnected(false);
    }
  }, [WS_URL, sessionId]);

  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: "👋 **Hi! I'm your Video Keeper Assistant.** I help you organize and search through any video collection - whether it's personal memories, training materials, gaming content, tutorials, or professional recordings.\n\n🎬 **Your video library is loading above** - you can click on any video thumbnail to learn more about it.\n\n💬 **Two ways to search:**\n• **Type** keywords, questions, or descriptions in the chat box\n• **Upload a video** using the purple button to find visually similar content\n\n**What are you looking for?**",
        timestamp: new Date().toISOString()
      }]);
    }
    
    const timeoutId = setTimeout(() => {
      connectWebSocket();
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const sendMessage = async (): Promise<void> => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setStreamingMessage('');
    streamingMessageRef.current = '';
    isStreamingRef.current = false;
    setCurrentTool('');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message: userMessage.content
      }));
    } else {
      console.log('WebSocket not available, falling back to HTTP');
      
      try {
        const response = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            session_id: sessionId
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const data = await response.json();
        
        if (data.error) {
          throw new Error(data.error);
        }

        const assistantMessage: Message = {
          role: 'assistant',
          content: data.response,
          timestamp: data.timestamp,
          metadata: data.metadata
        };

        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Error:', error);
        let errorMessage = (error as Error).message;
        
        if (errorMessage.includes('Failed to fetch')) {
          errorMessage = `Cannot connect to Video Keeper at ${API_URL}. Please ensure the backend server is running.`;
        }
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ Error: ${errorMessage}`,
          timestamp: new Date().toISOString()
        }]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };


  const getToolMessage = (tool: string): string => {
    const toolMessages: Record<string, string> = {
      'search_videos_by_keywords': 'Searching by keywords...',
      'search_videos_by_semantic_query': 'Performing semantic search...',
      'search_videos_hybrid': 'Running hybrid search...',
      'get_video_details': 'Fetching video details...',
      'get_all_videos': 'Loading video library...',
      'search_person_in_video': 'Finding person mentions...',
      'get_video_sentiment': 'Analyzing sentiment...',
      'get_video_summary': 'Getting summary...',
      'get_video_transcript': 'Retrieving transcript...'
    };
    return toolMessages[tool] || `Using ${tool}...`;
  };

  const parseVideoResults = (content: string): { text: string; videos: VideoResult[] } => {
    // Look for video results in various formats
    const videos: VideoResult[] = [];
    let cleanedText = content;
    
    // Pattern 1: Individual video JSON objects
    const videoPattern = /\{[^{}]*"video_id"[^{}]*\}/g;
    const videoMatches = content.match(videoPattern);
    
    if (videoMatches) {
      videoMatches.forEach(match => {
        try {
          const video = JSON.parse(match);
          if (video.video_id) {
            videos.push(video);
            cleanedText = cleanedText.replace(match, '');
          }
        } catch (e) {
          // Not valid JSON, ignore
        }
      });
    }
    
    // Pattern 2: get_all_videos response format
    const allVideosPattern = /"videos":\s*\[([^\]]+)\]/;
    const allVideosMatch = content.match(allVideosPattern);
    
    if (allVideosMatch) {
      try {
        const videosArray = JSON.parse(`[${allVideosMatch[1]}]`);
        videosArray.forEach((video: any) => {
          if (video && video.video_id) {
            videos.push(video);
          }
        });
        // Remove the videos array from the text
        cleanedText = cleanedText.replace(allVideosMatch[0], '');
      } catch (e) {
        // Failed to parse videos array
      }
    }
    
    // Remove empty lines and clean up text
    cleanedText = cleanedText.replace(/\n\s*\n/g, '\n').trim();
    
    return { text: cleanedText, videos };
  };

  const handleVideoClick = (video: VideoResult): void => {
    // Set the current video for display in chat
    setCurrentVideo(video);
    // Add a message asking for more details about the video
    setInput(`Tell me more about video ${video.video_id}`);
  };

  const handleSimilaritySearchComplete = (results: VideoResult[]): void => {
    // Close the similarity search modal
    setShowSimilaritySearch(false);
    
    // Add a message to chat showing the results
    const resultsMessage: Message = {
      role: 'assistant',
      content: `🎯 **Video Similarity Search Complete**\n\nFound ${results.length} similar videos in your library based on visual content analysis.`,
      timestamp: new Date().toISOString(),
      metadata: {
        search_results: results
      }
    };
    
    setMessages(prev => [...prev, resultsMessage]);
  };

  const refreshVideoLibrary = useCallback(async () => {
    try {
      const response = await fetch(`${VIDEO_API_URL}/videos`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.videos && data.videos.length > 0) {
          setSampleVideos(data.videos);
        }
      }
    } catch (error) {
      console.error('Failed to refresh video library:', error);
    }
  }, [VIDEO_API_URL]);

  // Fetch real videos from standalone Video API
  useEffect(() => {
    const fetchVideos = async () => {
      console.log('🎬 Fetching videos for carousel from Video API...');
      try {
        const response = await fetch(`${VIDEO_API_URL}/videos`);
        console.log('📡 Video API response status:', response.status);

        if (response.ok) {
          const data = await response.json();
          console.log('📊 Video API data:', data);
          
          if (data.success && data.videos && data.videos.length > 0) {
            setSampleVideos(data.videos);
            console.log('✅ Set sample videos from Video API:', data.videos.length);
          } else {
            console.log('⚠️ No videos found in Video API:', data.error || 'No videos returned');
          }
        } else {
          console.error('❌ Video API response not OK:', response.status, response.statusText);
        }
      } catch (error) {
        console.error('💥 Failed to fetch videos from Video API:', error);
      }
    };

    // Add a small delay to ensure the backend is ready
    const timeoutId = setTimeout(fetchVideos, 1000);
    return () => clearTimeout(timeoutId);
  }, [VIDEO_API_URL]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Video className="text-white" size={20} />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Video Keeper</h1>
                <p className="text-sm text-gray-500">AI-Powered Video Library</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-amber-400'}`}></div>
                <span>{wsConnected ? 'Connected' : 'HTTP Mode'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Connection Error Banner */}
      {connectionError && (
        <div className="bg-yellow-100 border-b border-yellow-400 text-yellow-800 px-4 py-2 text-sm">
          <div className="max-w-6xl mx-auto">
            ⚠️ {connectionError}
          </div>
        </div>
      )}



      {/* Collapsible Video Carousel */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center space-x-2">
              <Video size={16} className="text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Video Library</span>
              <span className="text-xs text-gray-500">({sampleVideos.length} videos)</span>
            </div>
            <button
              onClick={() => setCarouselExpanded(!carouselExpanded)}
              className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              <span>{carouselExpanded ? 'Collapse' : 'Expand'}</span>
              {carouselExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
          {carouselExpanded && (
            <div className="pb-4">
              <VideoCarousel videos={sampleVideos} onVideoClick={handleVideoClick} />
            </div>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Current Video Context */}
          {currentVideo && (
            <div className="sticky top-0 z-10 bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  {currentVideo.thumbnail_url ? (
                    <img 
                      src={currentVideo.thumbnail_url} 
                      alt={currentVideo.video_title}
                      className="w-20 h-12 object-cover rounded-lg"
                    />
                  ) : (
                    <div className="w-20 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                      <PlayCircle className="text-gray-400" size={20} />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-900">{currentVideo.video_title}</h3>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{currentVideo.summary}</p>
                  <div className="flex items-center mt-2">
                    {currentVideo.brands_mentioned && currentVideo.brands_mentioned.length > 0 && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded mr-2">
                        {currentVideo.brands_mentioned[0]}
                      </span>
                    )}
                    {currentVideo.people_mentioned && currentVideo.people_mentioned.length > 0 && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                        {currentVideo.people_mentioned[0]}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setCurrentVideo(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  ×
                </button>
              </div>
            </div>
          )}
          {messages.map((message, index) => {
            if (message.role === 'user') {
              return (
                <div
                  key={index}
                  className={`flex justify-end animate-fade-in opacity-0 [animation-fill-mode:forwards] [animation-delay:${index * 0.1}s]`}
                >
                  <div className="max-w-3xl rounded-lg p-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white ml-auto shadow-sm">
                    <p>{message.content}</p>
                  </div>
                </div>
              );
            } else {
              // Parse video results from assistant messages
              const { text, videos } = parseVideoResults(message.content);
              
              // Check for similarity search results in metadata
              const similarityResults = message.metadata?.search_results || [];
              const allVideos = [...videos, ...similarityResults];
              
              return (
                <div
                  key={index}
                  className={`flex justify-start animate-fade-in opacity-0 [animation-fill-mode:forwards] [animation-delay:${index * 0.1}s]`}
                >
                  <div className="max-w-3xl space-y-3">
                    {text && (
                      <div className="bg-white border border-gray-100 rounded-lg p-4">
                        <MessageFormatter content={text} />
                      </div>
                    )}
                    {allVideos.length > 0 && (
                      <VideoResults 
                        videos={allVideos} 
                        onVideoClick={handleVideoClick}
                        showSimilarityScores={similarityResults.length > 0}
                      />
                    )}
                  </div>
                </div>
              );
            }
          })}
          
          {/* Streaming message */}
          {isStreaming && streamingMessage && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-3xl bg-white shadow-md border border-gray-200 rounded-lg p-4">
                <MessageFormatter content={streamingMessage} />
                <span className="inline-block w-2 h-4 bg-blue-600 animate-pulse ml-1" />
              </div>
            </div>
          )}
          
          {/* Loading indicator */}
          {isLoading && !isStreaming && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-white shadow-md border border-gray-100 rounded-lg p-4 flex items-center space-x-2">
                <Loader2 className="animate-spin text-blue-600" size={20} />
                <span className="text-gray-700">
                  {currentTool ? getToolMessage(currentTool) : 'Searching video database...'}
                </span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggestions */}
      {messages.length === 1 && (
        <div className="px-4 pb-4 border-t bg-white">
          <div className="max-w-4xl mx-auto pt-4">
            <p className="text-sm text-gray-600 mb-3 flex items-center">
              <Sparkles size={16} className="mr-1 text-blue-600" />
              Try these searches:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm hover:bg-gray-100 hover:border-blue-300 transition-all text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t bg-white p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Search your videos, find people, rediscover memories..."
                className="w-full pl-10 pr-4 py-3 border-2 border-purple-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white shadow-sm hover:border-purple-400 transition-colors"
                disabled={isLoading || isStreaming}
              />
            </div>
            <button
              onClick={() => setShowSimilaritySearch(true)}
              disabled={isLoading || isStreaming}
              className="px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 shadow-sm flex items-center space-x-2"
              title="Upload a video to find similar content"
            >
              <Target size={20} />
              <span className="hidden sm:inline">Search by Video</span>
            </button>
            <button
              onClick={sendMessage}
              disabled={isLoading || isStreaming || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center space-x-2"
            >
              <Send size={20} />
              <span>Search</span>
            </button>
          </div>
          
          {/* Search Options Helper Text */}
          <div className="mt-2 text-center">
            <p className="text-xs text-gray-500">
              💬 <span className="font-medium">Chat to search</span> with keywords, questions, or descriptions
              <span className="mx-2">•</span>
              🎬 <span className="font-medium">Upload video</span> to find visually similar content
            </p>
          </div>
        </div>
      </div>

      {/* Video Similarity Search Modal */}
      {showSimilaritySearch && (
        <VideoSimilaritySearch
          onSearchComplete={handleSimilaritySearchComplete}
          onClose={() => setShowSimilaritySearch(false)}
        />
      )}
    </div>
  );
};

export default VideoInsightsChat;