import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, Sparkles } from 'lucide-react';
import { User, ChatMessage } from '../../types';
import { useWebSocket } from '../../hooks/useWebSocket';
import { MessageBubble } from './MessageBubble';

interface ChatProps {
  user: User;
}

const welcomeMessages = [
  "👋 Hi! I'm your AI fashion assistant. I can help you create amazing outfits!",
  "✨ Try asking me: 'What should I wear for a business meeting?' or 'Create a casual summer outfit'",
  "🎨 I can suggest outfits from your wardrobe and even create virtual try-ons!",
  "💡 Examples: 'Try on my blue shirt' or 'What goes well with my black dress?'"
];

export const Chat: React.FC<ChatProps> = ({ user }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Use user ID as stable session identifier - useMemo ensures it's truly stable
  const sessionId = useMemo(() => `chat-${user.userId}`, [user.userId]);
  
  // Debug: Log the sessionId to understand the issue
  console.log('DEBUG - Chat sessionId:', sessionId, 'user.userId:', user.userId, 'type:', typeof user.userId);

  const { isConnected, isThinking, sendMessage } = useWebSocket({
    userId: user.userId,
    onMessage: (message) => {
      setMessages(prev => {
        const existingIndex = prev.findIndex(m => m.id === message.id);
        if (existingIndex >= 0) {
          // Update existing streaming message
          const newMessages = [...prev];
          newMessages[existingIndex] = message;
          return newMessages;
        } else {
          // Add new message
          return [...prev, message];
        }
      });
    },
  });

  // Initialize welcome messages with stable session-based IDs
  useEffect(() => {
    if (messages.length === 0) {
      const initialMessages: ChatMessage[] = welcomeMessages.map((content, index) => ({
        id: `welcome-${index}-${sessionId}`, // Use stable session ID based on user ID only
        role: 'assistant',
        content,
        timestamp: new Date(),
      }));
      
      // Additional safety: ensure we don't have duplicates
      setMessages(prevMessages => {
        const hasWelcomeMessages = prevMessages.some(msg => msg.id.startsWith('welcome-'));
        if (hasWelcomeMessages) {
          return prevMessages; // Don't add if welcome messages already exist
        }
        return initialMessages;
      });
    }
  }, []); // Empty dependency - only run once per component instance

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = () => {
    if (!inputValue.trim() || !isConnected) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    sendMessage(inputValue);
    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { text: "Show me casual outfits from my wardrobe", icon: "👕" },
    { text: "What should I wear to work today?", icon: "💼" },
    { text: "Create a party outfit with my clothes", icon: "🎉" },
    { text: "Virtual try-on with my newest items", icon: "🪞" },
  ];

  return (
    <div className="wardrobe-mirror rounded-xl flex flex-col h-[600px]">
      {/* Header */}
      <div className="wood-panel p-4 rounded-t-xl border-b-2 border-amber-800">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-full" style={{
            background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
            boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
          }}>
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-white font-semibold">AI Fashion Assistant</h3>
            <p className="text-gray-300 text-sm">
              {isConnected ? '✨ Ready to style you!' : '🔄 Connecting...'}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-white/95 to-white/90">
        <AnimatePresence>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </AnimatePresence>

        {/* Thinking Indicator */}
        {isThinking && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center space-x-2 text-gray-500"
          >
            <div className="p-2 bg-gray-100 rounded-full">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-gray-100 rounded-2xl px-4 py-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length <= 3 && (
        <div className="px-4 py-2 border-t border-gray-100">
          <p className="text-sm text-gray-500 mb-2">Quick actions:</p>
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action, index) => (
              <motion.button
                key={index}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setInputValue(action.text)}
                className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full transition-colors"
              >
                <span className="mr-1">{action.icon}</span>
                {action.text}
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-100">
        <div className="flex space-x-3">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about your wardrobe..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            disabled={!isConnected}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSend}
            disabled={!inputValue.trim() || !isConnected}
            className="text-white p-3 rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
              boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
            }}
          >
            <Send className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
    </div>
  );
};