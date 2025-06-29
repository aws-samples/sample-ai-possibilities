//./components/RecipeGenieChat
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, ChefHat, ShoppingCart, Loader2, Sparkles } from 'lucide-react';

const RecipeGenieChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(`session_${Date.now()}`);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [currentTool, setCurrentTool] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState('');
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  
  const [suggestions] = useState([
    "chicken, rice, vegetables",
    "pasta, tomatoes, cheese", 
    "eggs, bread, milk",
    "Find recipes under $10",
    "What's on special today?"
  ]);

  // Get API URL from environment or use default localhost
  // In development, this will use the proxy configured in package.json
  // In production, set REACT_APP_API_URL to your backend URL
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
  const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

  // Use refs for values that change during streaming
  const streamingMessageRef = useRef('');
  const isStreamingRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const connectWebSocket = useCallback(() => {
    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    const wsUrl = `${WS_URL}/ws/${sessionId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    console.log('API_URL:', API_URL);
    console.log('WS_URL:', WS_URL);
    
    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setWsConnected(true);
        setConnectionError('');
        reconnectAttemptsRef.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'status':
            // Status updates
            console.log('Status:', data.message);
            setCurrentTool('');
            break;
            
          case 'tool_use':
            // Show which tool is being used
            setCurrentTool(data.tool);
            console.log('Using tool:', data.tool);
            break;
            
          case 'stream':
            // Streaming content
            isStreamingRef.current = true;
            setIsStreaming(true);
            setIsLoading(false);
            streamingMessageRef.current += data.content;
            setStreamingMessage(streamingMessageRef.current);
            break;
            
          case 'complete':
            // Streaming complete
            if (streamingMessageRef.current || isStreamingRef.current) {
              const assistantMessage = {
                role: 'assistant',
                content: streamingMessageRef.current,
                timestamp: data.timestamp
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
            // Non-streaming response (fallback)
            const assistantMessage = {
              role: 'assistant',
              content: data.content,
              timestamp: data.timestamp
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

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        console.error('WebSocket readyState:', wsRef.current?.readyState);
        console.error('WebSocket URL was:', wsUrl);
        setWsConnected(false);
        
        const errorMsg = `Unable to connect to Recipe Genie backend at ${wsUrl}. Please ensure the backend is running.`;
        setConnectionError(errorMsg);
        
        // Don't show error message repeatedly
        if (reconnectAttemptsRef.current === 0) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `❌ ${errorMsg}\n\nUsing HTTP fallback mode. WebSocket features like real-time streaming will not be available.`,
            timestamp: new Date().toISOString()
          }]);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setWsConnected(false);
        
        // Attempt reconnection with exponential backoff
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
      setConnectionError(error.message);
      setWsConnected(false);
    }
  }, [WS_URL, sessionId, API_URL]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  useEffect(() => {
    // Add welcome message only on mount
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: "👋 Hi! I'm the Recipe Genie! Give me some ingredients and I'll create delicious recipes with real-time pricing from Coles. What ingredients do you have?",
        timestamp: new Date().toISOString()
      }]);
    }
    
    // Connect to WebSocket after a short delay to ensure component is mounted
    const timeoutId = setTimeout(() => {
      connectWebSocket();
    }, 100);

    // Cleanup on unmount
    return () => {
      clearTimeout(timeoutId);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const formatMessage = (content) => {
    const lines = content.split('\n');
    return lines.map((line, index) => {
      if (line.startsWith('### ')) {
        return <h3 key={index} className="text-lg font-bold mt-4 mb-2">{line.substring(4)}</h3>;
      }
      if (line.startsWith('## ')) {
        return <h2 key={index} className="text-xl font-bold mt-4 mb-2">{line.substring(3)}</h2>;
      }
      if (line.includes('🍽️') || line.includes('💰') || line.includes('📝') || line.includes('🛒') || line.includes('👨‍🍳')) {
        return <p key={index} className="font-semibold mt-3 mb-1">{line}</p>;
      }
      if (line.trim().startsWith('- ') || line.trim().startsWith('• ')) {
        return <li key={index} className="ml-6 mb-1">{line.substring(2)}</li>;
      }
      if (/^\d+\./.test(line.trim())) {
        return <li key={index} className="ml-6 mb-1">{line}</li>;
      }
      if (line.includes('🏷️')) {
        return <p key={index} className="text-green-600 font-semibold">{line}</p>;
      }
      if (line.includes('---') || line.includes('===')) {
        return <hr key={index} className="my-4 border-gray-300" />;
      }
      if (line.trim()) {
        return <p key={index} className="mb-2">{line}</p>;
      }
      return <br key={index} />;
    });
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
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

    // Try WebSocket first, fall back to HTTP if not connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send message through WebSocket
      wsRef.current.send(JSON.stringify({
        message: userMessage.content
      }));
    } else {
      // Fall back to HTTP endpoint
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

        const assistantMessage = {
          role: 'assistant',
          content: data.response,
          timestamp: data.timestamp
        };

        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Error:', error);
        let errorMessage = error.message;
        
        // Provide more helpful error messages
        if (error.message.includes('Failed to fetch')) {
          errorMessage = `Cannot connect to Recipe Genie backend at ${API_URL}. Please ensure the backend server is running.`;
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

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white p-4 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <ChefHat size={32} />
            <div>
              <h1 className="text-2xl font-bold">Recipe Genie</h1>
              <p className="text-sm opacity-90">Powered by real prices app</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <ShoppingCart size={20} />
            <span className="text-sm">
              {wsConnected ? (
                <span className="flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-1"></span>
                  Live prices
                </span>
              ) : (
                <span className="flex items-center">
                  <span className="w-2 h-2 bg-yellow-400 rounded-full mr-1"></span>
                  HTTP mode
                </span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Connection status banner */}
      {connectionError && (
        <div className="bg-yellow-100 border-b border-yellow-400 text-yellow-800 px-4 py-2 text-sm">
          <div className="max-w-4xl mx-auto">
            ⚠️ {connectionError}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white shadow-md'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    {formatMessage(message.content)}
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </div>
            </div>
          ))}
          
          {/* Streaming message */}
          {isStreaming && streamingMessage && (
            <div className="flex justify-start">
              <div className="max-w-3xl bg-white shadow-md rounded-lg p-4">
                <div className="prose prose-sm max-w-none">
                  {formatMessage(streamingMessage)}
                  <span className="inline-block w-2 h-4 bg-gray-500 animate-pulse ml-1" />
                </div>
              </div>
            </div>
          )}
          
          {/* Loading indicator with tool info */}
          {isLoading && !isStreaming && (
            <div className="flex justify-start">
              <div className="bg-white shadow-md rounded-lg p-4 flex items-center space-x-2">
                <Loader2 className="animate-spin" size={20} />
                <span>
                  {currentTool ? `Using ${currentTool}...` : 'Searching Coles for ingredients...'}
                </span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggestions */}
      {messages.length === 1 && (
        <div className="px-4 pb-2">
          <div className="max-w-4xl mx-auto">
            <p className="text-sm text-gray-600 mb-2 flex items-center">
              <Sparkles size={16} className="mr-1" />
              Try these suggestions:
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-3 py-1 bg-white border border-gray-300 rounded-full text-sm hover:bg-gray-50 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t bg-white p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter ingredients (e.g., chicken, rice, vegetables)"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              disabled={isLoading || isStreaming}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || isStreaming || !input.trim()}
              className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              <Send size={20} />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecipeGenieChat;