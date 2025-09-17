import React, { useState, useEffect, useRef } from 'react';
import { Send, Users, Calendar, Clock, Loader2, Sparkles, AlertCircle, CheckCircle, Bot, User } from 'lucide-react';
import { invokeAgent, validateAWSConfig, getAWSConfig } from '../services/awsAgentCore';

const StaffCastChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(`session_${Date.now()}`);
  const [businessId] = useState('cafe-001'); // Default to demo business
  const messagesEndRef = useRef(null);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [currentTool, setCurrentTool] = useState('');
  const [connectionError, setConnectionError] = useState('');
  
  const [suggestions] = useState([
    "Show today's roster status",
    "Generate tomorrow's schedule",
    "Check weekend availability",
    "View staff roster for next week"
  ]);

  // AWS AgentCore configuration
  const [awsConfigValid, setAwsConfigValid] = useState(false);
  const [configCheckComplete, setConfigCheckComplete] = useState(false);
  
  // Use refs for values that change during streaming
  const streamingMessageRef = useRef('');
  const isStreamingRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Initialize AWS configuration
  useEffect(() => {
    const isValid = validateAWSConfig();
    setAwsConfigValid(isValid);
    setConfigCheckComplete(true);
    
    if (isValid) {
      const config = getAWSConfig();
      console.log('AWS AgentCore configured for Recipe Genie:', config);
    } else {
      setConnectionError('AWS AgentCore configuration is missing. Please check environment variables.');
      const config = getAWSConfig();
      console.error('Missing AWS configuration:', config);
    }
  }, []);

  // Removed deprecated WebSocket code

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  useEffect(() => {
    // Add welcome message only after config check is complete
    if (messages.length === 0 && configCheckComplete) {
      setMessages([{
        role: 'assistant',
        content: awsConfigValid 
          ? `System ready. How can I assist with your staffing needs today?`
          : `System is not properly configured. Please check AWS AgentCore settings.`,
        timestamp: new Date().toISOString()
      }]);
    }
  }, [awsConfigValid, configCheckComplete, messages.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const formatMessage = (content) => {
    const lines = content.split('\n');
    const elements = [];
    let currentList = null;
    let listType = null;
    let currentTable = null;
    let inCodeBlock = false;
    let codeBlockContent = [];
    
    // Helper function to process inline formatting
    const processInlineFormatting = (text) => {
      // Handle bold text with **text** or __text__
      const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`)/g);
      return parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={idx} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>;
        } else if (part.startsWith('__') && part.endsWith('__')) {
          return <strong key={idx} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>;
        } else if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={idx} className="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm font-mono">{part.slice(1, -1)}</code>;
        }
        return part;
      });
    };
    
    lines.forEach((line, index) => {
      // Handle code blocks
      if (line.trim().startsWith('```')) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeBlockContent = [];
        } else {
          elements.push(
            <pre key={`code-${index}`} className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto mb-3">
              <code className="text-sm font-mono">{codeBlockContent.join('\n')}</code>
            </pre>
          );
          inCodeBlock = false;
        }
        return;
      }
      
      if (inCodeBlock) {
        codeBlockContent.push(line);
        return;
      }
      
      // Check if this is a table row
      const isTableRow = line.includes('|') && (line.match(/\|/g) || []).length >= 2;
      const isTableSeparator = /^\|[\s:-]+\|/.test(line.trim());
      
      if (isTableRow && !isTableSeparator) {
        if (!currentTable) {
          currentTable = { headers: null, rows: [] };
        }
        
        const cells = line.split('|').filter(cell => cell.trim() !== '');
        
        if (!currentTable.headers) {
          currentTable.headers = cells.map(cell => cell.trim());
        } else {
          currentTable.rows.push(cells.map(cell => cell.trim()));
        }
        
        // Check if next line is not a table row to close the table
        if (index === lines.length - 1 || (!lines[index + 1].includes('|') || lines[index + 1].trim() === '')) {
          if (currentTable && currentTable.headers) {
            elements.push(
              <div key={`table-${elements.length}`} className="overflow-x-auto mb-4">
                <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                  <thead className="bg-gray-50">
                    <tr>
                      {currentTable.headers.map((header, hIdx) => (
                        <th key={hIdx} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-r last:border-r-0">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {currentTable.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-gray-50 transition-colors">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="px-4 py-3 text-sm text-gray-900 border-r last:border-r-0">
                            {processInlineFormatting(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
            currentTable = null;
          }
        }
      } else if (isTableSeparator) {
        // Skip table separator lines
        return;
      } else {
        // Check if this line is a list item
        const isNumberedList = /^\d+\./.test(line.trim());
        const isBulletList = line.trim().startsWith('- ') || line.trim().startsWith('• ');
        
        // If we have a list item
        if (isNumberedList || isBulletList) {
          const newListType = isNumberedList ? 'ordered' : 'bullet';
          
          // If list type changed or no current list, flush current and start new
          if (listType !== newListType) {
            if (currentList) {
              elements.push(
                listType === 'ordered' ? 
                  <ol key={`list-${elements.length}`} className="ml-6 mb-3 list-decimal space-y-1">{currentList}</ol> :
                  <ul key={`list-${elements.length}`} className="ml-6 mb-3 list-disc space-y-1">{currentList}</ul>
              );
            }
            currentList = [];
            listType = newListType;
          }
          
          // Add item to current list
          if (isNumberedList) {
            const cleanedLine = line.trim().replace(/^\d+\.\s*/, '');
            currentList.push(
              <li key={`item-${index}`} className="text-gray-700">
                {processInlineFormatting(cleanedLine)}
              </li>
            );
          } else {
            currentList.push(
              <li key={`item-${index}`} className="text-gray-700">
                {processInlineFormatting(line.trim().substring(2))}
              </li>
            );
          }
        } else {
          // Not a list item - flush any current list
          if (currentList) {
            elements.push(
              listType === 'ordered' ? 
                <ol key={`list-${elements.length}`} className="ml-6 mb-3 list-decimal space-y-1">{currentList}</ol> :
                <ul key={`list-${elements.length}`} className="ml-6 mb-3 list-disc space-y-1">{currentList}</ul>
            );
            currentList = null;
            listType = null;
          }
          
          // Process non-list elements
          if (line.startsWith('### ')) {
            elements.push(
              <h3 key={index} className="text-lg font-bold mt-4 mb-2 text-blue-800 border-b border-blue-200 pb-1">
                {line.substring(4)}
              </h3>
            );
          } else if (line.startsWith('## ')) {
            elements.push(
              <h2 key={index} className="text-xl font-bold mt-4 mb-3 text-blue-900 border-b-2 border-blue-300 pb-2">
                {line.substring(3)}
              </h2>
            );
          } else if (line.startsWith('# ')) {
            elements.push(
              <h1 key={index} className="text-2xl font-bold mt-4 mb-3 text-gray-900">
                {line.substring(2)}
              </h1>
            );
          } else if (line.includes('✅')) {
            const cleanLine = line.replace(/✅/g, '').trim();
            elements.push(
              <div key={index} className="flex items-center text-green-700 font-medium bg-green-50 px-3 py-2 rounded-md mb-2">
                <CheckCircle size={16} className="mr-2 flex-shrink-0" />
                {processInlineFormatting(cleanLine)}
              </div>
            );
          } else if (line.includes('⚠️') || line.includes('❌')) {
            const cleanLine = line.replace(/⚠️|❌/g, '').trim();
            elements.push(
              <div key={index} className="flex items-center text-amber-700 font-medium bg-amber-50 px-3 py-2 rounded-md mb-2">
                <AlertCircle size={16} className="mr-2 flex-shrink-0" />
                {processInlineFormatting(cleanLine)}
              </div>
            );
          } else if (line.includes('---') || line.includes('===')) {
            elements.push(<hr key={index} className="my-4 border-gray-200" />);
          } else if (line.trim().startsWith('>')) {
            elements.push(
              <blockquote key={index} className="border-l-4 border-blue-300 pl-4 py-2 my-2 bg-blue-50 rounded-r">
                <p className="text-gray-700 italic">{processInlineFormatting(line.trim().substring(1).trim())}</p>
              </blockquote>
            );
          } else if (line.trim()) {
            // Check for special highlighting patterns
            if (line.includes('Staff:') || line.includes('Position:') || line.includes('Time:') || 
                line.includes('Cost:') || line.includes('Total:') || line.includes('Date:')) {
              elements.push(
                <p key={index} className="mb-2 text-gray-800">
                  {processInlineFormatting(line)}
                </p>
              );
            } else {
              elements.push(
                <p key={index} className="mb-2 text-gray-700">
                  {processInlineFormatting(line)}
                </p>
              );
            }
          } else if (!line.trim() && index > 0 && index < lines.length - 1) {
            // Only add spacing between content sections
            elements.push(<div key={index} className="h-2" />);
          }
        }
      }
    });
    
    // Flush any remaining list
    if (currentList) {
      elements.push(
        listType === 'ordered' ? 
          <ol key={`list-${elements.length}`} className="ml-6 mb-3 list-decimal space-y-1">{currentList}</ol> :
          <ul key={`list-${elements.length}`} className="ml-6 mb-3 list-disc space-y-1">{currentList}</ul>
      );
    }
    
    return elements;
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

    if (!awsConfigValid) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'AWS AgentCore is not properly configured. Please check your environment variables.',
        timestamp: new Date().toISOString()
      }]);
      setIsLoading(false);
      return;
    }

    try {
      // Use AWS AgentCore SDK
      await invokeAgent({
        message: userMessage.content,
        sessionId: sessionId,
        businessId: businessId,
        enableStreaming: true,
        onStreamChunk: (chunk) => {
          // Handle streaming chunks
          isStreamingRef.current = true;
          setIsStreaming(true);
          setIsLoading(false);
          streamingMessageRef.current += chunk;
          setStreamingMessage(streamingMessageRef.current);
        },
        onStreamComplete: (fullResponse) => {
          // Handle stream completion
          const assistantMessage = {
            role: 'assistant',
            content: fullResponse,
            timestamp: new Date().toISOString()
          };
          setMessages(prev => [...prev, assistantMessage]);
          streamingMessageRef.current = '';
          isStreamingRef.current = false;
          setStreamingMessage('');
          setIsStreaming(false);
          setIsLoading(false);
        },
        onStreamError: (error) => {
          // Handle stream errors
          console.error('Stream error:', error);
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `Error: ${error.message || 'Failed to get response from AWS AgentCore'}`,
            timestamp: new Date().toISOString()
          }]);
          setIsLoading(false);
          setIsStreaming(false);
          setStreamingMessage('');
          streamingMessageRef.current = '';
          isStreamingRef.current = false;
        },
        onToolUse: (toolName) => {
          // Handle tool usage indication
          console.log('Agent is using tool:', toolName);
          setCurrentTool(toolName);
        }
      });
    } catch (error) {
      console.error('Error invoking agent:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to connect to AWS AgentCore'}`,
        timestamp: new Date().toISOString()
      }]);
      setIsLoading(false);
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

  const getToolIcon = (toolName) => {
    if (toolName.includes('staff')) return <Users size={16} />;
    if (toolName.includes('roster')) return <Calendar size={16} />;
    if (toolName.includes('availability')) return <Clock size={16} />;
    return <Sparkles size={16} />;
  };

  const getToolDisplayName = (toolName) => {
    const toolMap = {
      'get_staff': 'Getting staff members',
      'get_roster_context': 'Analyzing roster context',
      'suggest_roster': 'Generating roster suggestions',
      'get_availability': 'Checking availability',
      'get_staff_with_availability': 'Checking staff & availability',
      'search_staff': 'Searching staff database'
    };
    return toolMap[toolName] || `Using ${toolName}`;
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Users size={32} />
            <div>
              <h1 className="text-2xl font-bold">StaffCast</h1>
              <p className="text-sm opacity-90">AI-powered staff scheduling</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Calendar size={24} className="text-amber-300" />
              <span className="text-lg font-semibold text-amber-100">The Daily Grind Cafe</span>
            </div>
            <div className="flex items-center space-x-2">
              {awsConfigValid ? (
                <span className="flex items-center text-sm">
                  <CheckCircle size={16} className="text-green-400 mr-1" />
                  AWS Connected
                </span>
              ) : (
                <span className="flex items-center text-sm">
                  <AlertCircle size={16} className="text-yellow-400 mr-1" />
                  Not Configured
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Connection status banner */}
      {connectionError && (
        <div className="bg-amber-50 border-b border-amber-200 text-amber-800 px-4 py-3 text-sm">
          <div className="max-w-4xl mx-auto flex items-center">
            <AlertCircle size={16} className="mr-2 flex-shrink-0" />
            {connectionError}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
            >
              <div
                className={`max-w-3xl rounded-lg shadow-md transition-all hover:shadow-lg ${
                  message.role === 'user'
                    ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white p-4'
                    : 'bg-white border border-gray-200 overflow-hidden'
                }`}
              >
                {message.role === 'assistant' ? (
                  <>
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Bot size={16} className="text-blue-600" />
                        <span className="text-sm font-semibold text-gray-700">StaffCast</span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="p-4">
                      <div className="prose prose-sm max-w-none text-gray-800">
                        {formatMessage(message.content)}
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <User size={16} className="text-white opacity-90" />
                        <span className="text-sm font-semibold">You</span>
                      </div>
                      <span className="text-xs text-white opacity-75">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-white">{message.content}</p>
                  </>
                )}
              </div>
            </div>
          ))}
          
          {/* Streaming message */}
          {isStreaming && streamingMessage && (
            <div className="flex justify-start animate-fadeIn">
              <div className="max-w-3xl bg-white border border-gray-200 shadow-md rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot size={16} className="text-blue-600 animate-pulse" />
                    <span className="text-sm font-semibold text-gray-700">StaffCast</span>
                  </div>
                  <span className="text-xs text-gray-500">Typing...</span>
                </div>
                <div className="p-4">
                  <div className="prose prose-sm max-w-none text-gray-800">
                    {formatMessage(streamingMessage)}
                    <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1 rounded" />
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Loading indicator with tool info */}
          {isLoading && !isStreaming && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-4 flex items-center space-x-3">
                <Loader2 className="animate-spin text-blue-500" size={20} />
                <div className="flex items-center space-x-2">
                  {currentTool && getToolIcon(currentTool)}
                  <span className="text-gray-700">
                    {currentTool ? getToolDisplayName(currentTool) : 'Processing your request...'}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggestions */}
      {messages.length === 1 && (
        <div className="px-4 pb-4">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-2 gap-3">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-4 py-3 bg-white border border-gray-200 rounded-md text-sm hover:bg-gray-50 hover:border-gray-300 transition-colors text-left shadow-sm"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t bg-white p-4 shadow-lg">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about staff schedules, availability, or roster planning..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading || isStreaming}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || isStreaming || !input.trim()}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2 shadow-md"
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

export default StaffCastChat;