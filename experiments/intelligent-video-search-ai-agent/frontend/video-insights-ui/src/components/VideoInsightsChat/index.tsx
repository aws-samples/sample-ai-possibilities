import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Search, Filter, Download, Loader2, Sparkles, PlayCircle } from 'lucide-react';
import SearchFilters from './SearchFilters';
import VideoCard from './VideoCard';
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
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingMessageRef = useRef<string>('');
  const isStreamingRef = useRef<boolean>(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8090';
  const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

  const suggestions: string[] = [
    "Show me videos about Ring doorbell",
    "Find marketing videos with emotional appeal",
    "Search for videos discussing the Ring doorbell and tell me at what time ‘Ring’ is first mentioned in the video.",
    "Search for a brand name",
    "What videos mention Stephan?",
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
        
        const errorMsg = `Unable to connect to Nick at ${wsUrl}. Please ensure the backend is running.`;
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
        content: "👋 Hi! I'm Nick, your Video Insights Discovery Assistant. I can help you find videos, analyze marketing content, search for specific people or brands, and provide detailed insights. What would you like to explore?",
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
          errorMessage = `Cannot connect to Nick at ${API_URL}. Please ensure the backend server is running.`;
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

  const handleExport = (): void => {
    const exportData = {
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      messages: messages,
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `video-insights-${sessionId}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getToolMessage = (tool: string): string => {
    const toolMessages: Record<string, string> = {
      'search_videos_by_keywords': 'Searching by keywords...',
      'search_videos_by_semantic_query': 'Performing semantic search...',
      'search_videos_hybrid': 'Running hybrid search...',
      'get_video_details': 'Fetching video details...',
      'search_person_in_video': 'Finding person mentions...',
      'get_video_sentiment': 'Analyzing sentiment...',
      'get_video_summary': 'Getting summary...',
      'get_video_transcript': 'Retrieving transcript...'
    };
    return toolMessages[tool] || `Using ${tool}...`;
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-brand-600 to-brand-800 text-white shadow-lg backdrop-blur-lg bg-opacity-95">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <PlayCircle size={32} />
              <div>
                <h1 className="text-2xl font-bold">Video Insights Discovery</h1>
                <p className="text-sm opacity-90">Powered by Nick AI Assistant</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center space-x-2 px-3 py-1.5 bg-brand-700 rounded-lg hover:bg-brand-800 transition-colors"
              >
                <Filter size={18} />
                <span className="text-sm">Filters</span>
              </button>
              <button
                onClick={handleExport}
                className="flex items-center space-x-2 px-3 py-1.5 bg-brand-700 rounded-lg hover:bg-brand-800 transition-colors"
                disabled={messages.length <= 1}
              >
                <Download size={18} />
                <span className="text-sm">Export</span>
              </button>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-yellow-400'}`}></div>
                <span className="text-sm">{wsConnected ? 'Connected' : 'HTTP Mode'}</span>
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

      {/* Search Filters */}
      {showFilters && <SearchFilters activeFilter={activeFilter} setActiveFilter={setActiveFilter} />}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}
              animate-fade-in opacity-0 [animation-fill-mode:forwards]
              [animation-delay:${index * 0.1}s]`}
            >
              <div
                className={`max-w-3xl rounded-lg p-4 ${
                  message.role === 'user'
                  ? 'bg-gradient-to-r from-brand-600 to-brand-700 text-white ml-auto'
                  : 'bg-white border border-gray-100'
                }`}
              >
                {message.role === 'assistant' ? (
                  <MessageFormatter content={message.content} />
                ) : (
                  <p>{message.content}</p>
                )}
              </div>
            </div>
          ))}
          
          {/* Streaming message */}
          {isStreaming && streamingMessage && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-3xl bg-white shadow-md border border-gray-200 rounded-lg p-4">
                <MessageFormatter content={streamingMessage} />
                <span className="inline-block w-2 h-4 bg-brand-600 animate-pulse ml-1" />
              </div>
            </div>
          )}
          
          {/* Loading indicator */}
          {isLoading && !isStreaming && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-white shadow-md rounded-lg p-4 flex items-center space-x-2">
                <Loader2 className="animate-spin text-brand-600" size={20} />
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
              <Sparkles size={16} className="mr-1 text-brand-600" />
              Try these searches:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm hover:bg-gray-100 hover:border-brand-300 transition-all text-left"
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
                placeholder="Search videos, find people, analyze sentiment..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                disabled={isLoading || isStreaming}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={isLoading || isStreaming || !input.trim()}
              className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              <Send size={20} />
              <span>Search</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoInsightsChat;