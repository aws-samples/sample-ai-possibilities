import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, User as UserIcon } from 'lucide-react';
import { User } from '../../types';
import ReactMarkdown from 'react-markdown';
import toast from 'react-hot-toast';

interface SimpleChatProps {
  user: User;
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any, source?: string) => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const SimpleChat: React.FC<SimpleChatProps> = ({ user, onTryOnResult }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello ${user.userName}! 🦄 I'm your AI fashion assistant. What would you like to try on today?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const currentResponseRef = useRef('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentResponse]);

  // Simple WebSocket connection
  useEffect(() => {
    const sessionId = `chat-${user.userId}`;
    const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}`);
    
    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      // Initialize session
      ws.send(JSON.stringify({
        type: 'init',
        userId: user.userId
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('📨 Received:', data.type, data);

      if (data.type === 'init_complete') {
        toast.success('🦄 Connected!');
      } else if (data.type === 'thinking_complete') {
        setIsThinking(false);
      } else if (data.type === 'virtual_tryon_loading') {
        setIsThinking(true);
      } else if (data.type === 'stream') {
        // Real-time streaming - append to current response
        setIsThinking(false);
        currentResponseRef.current += data.content;
        setCurrentResponse(currentResponseRef.current);
      } else if (data.type === 'complete') {
        // Response complete - move to messages
        setIsThinking(false);
        const finalContent = currentResponseRef.current.trim();
        if (finalContent) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: finalContent,
            timestamp: new Date()
          }]);
          setCurrentResponse('');
          currentResponseRef.current = '';
        }
      } else if (data.type === 'virtual_tryon_result') {
        if (data.tryOnImageUrl && onTryOnResult) {
          onTryOnResult(data.tryOnImageUrl, data.outfitData || {}, 'chat');
        }
      }
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [user.userId]);

  const sendMessage = () => {
    const content = input.trim();
    if (!content || !isConnected) return;

    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    }]);

    // Show thinking state immediately
    setIsThinking(true);

    // Send to server
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      message: content
    }));

    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-modern flex flex-col h-full min-h-[500px] max-h-[80vh]">
      {/* Header */}
      <div className="chat-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">AI Fashion Assistant</h3>
              <p className="text-xs text-white/70">Simple & Working</p>
            </div>
          </div>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 bg-gradient-to-br from-fashion-secondary to-fashion-accent rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            
            <div className={`max-w-[80%] ${
              message.role === 'user'
                ? 'bg-blue-800 text-white shadow-lg'
                : 'bg-fashion-light-gray text-fashion-charcoal'
            } rounded-2xl px-4 py-3`}>
              <div className="text-sm prose prose-sm max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              <p className="text-xs opacity-70 mt-1">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>

            {message.role === 'user' && (
              <div className="w-8 h-8 bg-blue-800 rounded-full flex items-center justify-center">
                <UserIcon className="w-5 h-5 text-white" />
              </div>
            )}
          </motion.div>
        ))}
        {/* Thinking indicator */}
        {isThinking && !currentResponse && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-fashion-secondary to-fashion-accent rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-fashion-light-gray rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-fashion-secondary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-fashion-secondary rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-fashion-secondary rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-sm text-fashion-medium-gray">Thinking...</span>
              </div>
            </div>
          </motion.div>
        )}
        
        {/* Current streaming response */}
        {currentResponse && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-fashion-secondary to-fashion-accent rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-fashion-light-gray rounded-2xl px-4 py-3 max-w-[80%]">
              <div className="text-sm prose prose-sm max-w-none">
                <ReactMarkdown>{currentResponse}</ReactMarkdown>
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-container">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConnected ? "Ask me about your wardrobe..." : "Connecting..."}
            disabled={!isConnected}
            className="flex-1 px-4 py-3 bg-fashion-light-gray rounded-full focus:outline-none focus:ring-2 focus:ring-fashion-secondary transition-all disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || !isConnected}
            className="btn-fashion-primary rounded-full w-12 h-12 flex items-center justify-center disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-fashion-medium-gray mt-2 text-center">
          Simple & Working Chat
        </p>
      </div>
    </div>
  );
};