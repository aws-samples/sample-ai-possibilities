import React, { useState, useEffect, useRef, useReducer } from 'react';
import { flushSync } from 'react-dom';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Avatar,
  Fade,
  Grow,
} from '@mui/material';
import {
  Send,
  SmartToy,
  Person,
  CloudOff,
  Cloud,
  Build,
} from '@mui/icons-material';
import { invokeAgent, validateAWSConfig, getAWSConfig } from '../services/awsAgentCore';

const ChatPanel = ({ onPanelUpdate, staffInfo }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session_${Date.now()}`);
  const [businessId] = useState('cafe-001');
  const messagesEndRef = useRef(null);
  const [currentTool, setCurrentTool] = useState('');
  const [toolHistory, setToolHistory] = useState([]);
  const [messageTools, setMessageTools] = useState({});
  const [awsConfigValid, setAwsConfigValid] = useState(false);
  const [connectionError, setConnectionError] = useState('');
  
  // Direct React state approach - use flushSync to bypass batching
  const [streamingState, setStreamingState] = useState({
    isStreaming: false,
    message: '',
    counter: 0
  });
  
  // Use ref to track current state for callbacks to avoid stale closures
  const streamingStateRef = useRef(streamingState);
  streamingStateRef.current = streamingState;
  
  const updateStreamingState = (newState) => {
    console.log('updateStreamingState: Setting state from:', streamingStateRef.current, 'to:', newState);
    // Use React's flushSync to force immediate update
    flushSync(() => {
      setStreamingState(newState);
      streamingStateRef.current = newState; // Keep ref in sync
    });
    console.log('updateStreamingState: State updated synchronously');
  };

  // Staff-specific suggestions
  const [suggestions] = useState([
    "Show my upcoming shifts",
    "When do I work next?",
    "What's the sick leave policy?",
    "Request time off next week",
    "Check my availability settings",
    "View my recent payroll"
  ]);

  // AWS AgentCore configuration check

  // Use refs for values that change during streaming
  const panelUpdatedRef = useRef(false);

  const scrollToBottom = () => {
    // Use setTimeout to ensure DOM has updated before scrolling
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 100);
  };

  // Initialize AWS configuration
  useEffect(() => {
    const isValid = validateAWSConfig();
    setAwsConfigValid(isValid);
    
    if (isValid) {
      const config = getAWSConfig();
      console.log('AWS AgentCore configured for ChatPanel:', config);
    } else {
      setConnectionError('AWS AgentCore configuration is missing. Please check environment variables.');
      const config = getAWSConfig();
      console.error('Missing AWS configuration:', config);
    }
  }, []);

  // Detect panel context from AI response content
  const detectPanelContext = (content) => {
    const lowerContent = content.toLowerCase();
    
    // Check for more specific terms first to avoid false matches
    // Leave-related terms (check first as "sick leave" might contain "schedule")
    if (lowerContent.includes('leave') || 
        lowerContent.includes('holiday') || 
        lowerContent.includes('time off') || 
        lowerContent.includes('sick') || 
        lowerContent.includes('vacation') ||
        lowerContent.includes('absence')) {
      onPanelUpdate('leave');
    } 
    // Policy-related terms
    else if (lowerContent.includes('policy') || 
             lowerContent.includes('procedure') || 
             lowerContent.includes('rule') ||
             lowerContent.includes('entitle')) {
      onPanelUpdate('policy');
    }
    // Payroll-related terms
    else if (lowerContent.includes('payroll') || 
             lowerContent.includes('salary') || 
             lowerContent.includes('wage') ||
             lowerContent.includes('payment')) {
      onPanelUpdate('payroll');
    }
    // Availability-related terms
    else if (lowerContent.includes('availability') || 
             (lowerContent.includes('available') && !lowerContent.includes('leave available'))) {
      onPanelUpdate('availability');
    }
    // Roster/shift terms (check last as these are more general)
    else if (lowerContent.includes('shift') || 
             lowerContent.includes('roster') || 
             lowerContent.includes('schedule') ||
             lowerContent.includes('work')) {
      onPanelUpdate('roster');
    }
  };


  useEffect(() => {
    console.log('Messages updated:', messages.length, 'messages');
    messages.forEach((msg, idx) => {
      console.log(`Message ${idx}:`, msg.role, msg.content.substring(0, 50) + '...');
    });
    if (streamingState.message) {
      console.log('Streaming message:', streamingState.message.substring(0, 50) + '...');
    }
    scrollToBottom();
  }, [messages, streamingState]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading || streamingState.isStreaming || !awsConfigValid) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    updateStreamingState({ isStreaming: false, message: '', counter: 0 });
    panelUpdatedRef.current = false;
    const currentMessageTools = [];

    try {
      await invokeAgent({
        message: userMessage.content,
        sessionId: sessionId,
        businessId: businessId,
        staffId: staffInfo.staffId,
        enableStreaming: true,
        onStreamChunk: (chunk) => {
          // Handle streaming chunks
          console.log('onStreamChunk: Received chunk:', chunk);
          
          setIsLoading(false);
          // Use ref to get current state to avoid stale closure
          const currentState = streamingStateRef.current;
          const newMessage = currentState.message + chunk;
          const newState = {
            isStreaming: true,
            message: newMessage,
            counter: currentState.counter + 1
          };
          console.log('onStreamChunk: Setting streaming state from:', currentState, 'to:', newState);
          updateStreamingState(newState);
          
          // Auto-detect panel updates based on content
          if (!panelUpdatedRef.current && newMessage.length > 50) {
            console.log('onStreamChunk: Detecting panel context for:', newMessage.substring(0, 100));
            detectPanelContext(newMessage);
            panelUpdatedRef.current = true;
          }
        },
        onStreamComplete: (fullResponse) => {
          // Handle stream completion
          console.log('onStreamComplete: Full response received, length:', fullResponse.length);
          const assistantMessage = {
            role: 'assistant',
            content: fullResponse,
            timestamp: new Date().toISOString(),
            tools: currentMessageTools.length > 0 ? [...currentMessageTools] : undefined
          };
          setMessages(prev => [...prev, assistantMessage]);
          updateStreamingState({ isStreaming: false, message: '', counter: 0 });
          setIsLoading(false);
          console.log('onStreamComplete: Reset streaming state and added message to history');
          // Don't immediately clear the tool, let it fade out
          setTimeout(() => setCurrentTool(''), 2000);
        },
        onStreamError: (error) => {
          // Handle stream errors
          console.error('onStreamError:', error);
          setConnectionError(error.message || 'Failed to get response from AWS AgentCore');
          setIsLoading(false);
          updateStreamingState({ isStreaming: false, message: '', counter: 0 });
        },
        onToolUse: (toolName) => {
          // Handle tool usage indication
          console.log('onToolUse: Agent is using tool:', toolName);
          const displayName = toolName.replace(/_/g, ' ').replace(/^get /, '').charAt(0).toUpperCase() + 
                            toolName.replace(/_/g, ' ').replace(/^get /, '').slice(1);
          setCurrentTool(`Accessing ${displayName}`);
          setToolHistory(prev => [...prev, { tool: toolName, timestamp: Date.now() }]);
          // Track tools for this message
          if (!currentMessageTools.includes(toolName)) {
            currentMessageTools.push(toolName);
            console.log('onToolUse: Added tool to message tools:', toolName, 'Total tools:', currentMessageTools.length);
          }
        }
      });
    } catch (error) {
      console.error('Error sending message:', error);
      setConnectionError(error.message || 'Failed to send message. Please try again.');
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    if (!isLoading && !streamingState.isStreaming && awsConfigValid) {
      setInput(suggestion);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Connection Status */}
      <Box sx={{ px: 2, py: 1, backgroundColor: 'background.default' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {awsConfigValid ? (
            <>
              <Cloud sx={{ fontSize: 16, color: 'success.main' }} />
              <Typography variant="caption" sx={{ color: 'success.main' }}>
                AWS AgentCore Connected
              </Typography>
            </>
          ) : (
            <>
              <CloudOff sx={{ fontSize: 16, color: 'error.main' }} />
              <Typography variant="caption" sx={{ color: 'error.main' }}>
                AWS Not Configured
              </Typography>
            </>
          )}
        </Box>
      </Box>

      {/* Connection Error Alert */}
      {connectionError && (
        <Alert 
          severity="error" 
          variant="outlined"
          sx={{ mx: 2, mt: 1 }}
          onClose={() => setConnectionError('')}
        >
          {connectionError}
        </Alert>
      )}

      {/* Chat Messages */}
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        px: 2, 
        py: 1,
        minHeight: 0,
        maxHeight: 'calc(100vh - 200px)',
        scrollBehavior: 'smooth',
        '&::-webkit-scrollbar': {
          width: '6px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'rgba(0,0,0,0.2)',
          borderRadius: '3px',
        }
      }}>
        {messages.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <SmartToy sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>
              Hello {staffInfo.name}!
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              I'm here to help with your schedule, leave requests, and company policies.
              Try one of these suggestions to get started:
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center', mb: 2 }}>
              {suggestions.map((suggestion, index) => (
                <Grow in timeout={300 + index * 100} key={suggestion}>
                  <Chip
                    label={suggestion}
                    onClick={() => handleSuggestionClick(suggestion)}
                    clickable
                    variant="filled"
                    size="small"
                    sx={{ 
                      transition: 'all 0.2s',
                      backgroundColor: 'action.hover',
                      '&:hover': {
                        backgroundColor: 'primary.main',
                        color: 'white',
                        transform: 'scale(1.02)',
                        boxShadow: 1
                      }
                    }}
                  />
                </Grow>
              ))}
            </Box>
          </Box>
        )}

        {/* Message History */}
        {messages.map((message, index) => (
          <Fade in timeout={300} key={`${message.timestamp}-${index}`}>
            <Box sx={{ mb: 2, display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <Avatar
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
                  fontSize: '0.8rem'
                }}
              >
                {message.role === 'user' ? (
                  <Person fontSize="small" />
                ) : (
                  <SmartToy fontSize="small" />
                )}
              </Avatar>
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '80%',
                  backgroundColor: message.role === 'user' ? 'primary.light' : 'background.paper',
                  color: message.role === 'user' ? 'white' : 'text.primary'
                }}
              >
                {message.role === 'assistant' && message.tools && message.tools.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
                    {message.tools.map((tool, idx) => (
                      <Chip
                        key={idx}
                        icon={<Build sx={{ fontSize: 14 }} />}
                        label={tool.replace(/_/g, ' ')}
                        size="small"
                        sx={{ 
                          fontSize: '0.7rem',
                          height: 20,
                          backgroundColor: 'action.selected',
                          color: 'primary.main'
                        }}
                      />
                    ))}
                  </Box>
                )}
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {message.content}
                </Typography>
              </Paper>
            </Box>
          </Fade>
        ))}

        {/* Streaming Message */}
        {console.log('Render: Streaming state check:', streamingState)}
        {(streamingState.message || streamingState.isStreaming) && (
          <Box key={`streaming-${streamingState.counter}`} sx={{ mb: 2, display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: 'secondary.main',
                fontSize: '0.8rem'
              }}
            >
              <SmartToy fontSize="small" />
            </Avatar>
            <Paper
              elevation={1}
              sx={{
                p: 2,
                maxWidth: '80%',
                backgroundColor: 'background.paper',
                border: 1,
                borderColor: 'primary.light'
              }}
            >
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {streamingState.message || "..."}
                <Box 
                  component="span" 
                  sx={{ 
                    display: 'inline-block',
                    width: 2,
                    height: 16,
                    backgroundColor: 'primary.main',
                    ml: 0.5,
                    '@keyframes blink': {
                      '0%, 50%': { opacity: 1 },
                      '51%, 100%': { opacity: 0 },
                    },
                    animation: 'blink 1s infinite'
                  }} 
                />
              </Typography>
            </Paper>
          </Box>
        )}

        {/* Tool Usage Indicator */}
        {currentTool && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, justifyContent: 'center' }}>
            <Build sx={{ fontSize: 16, color: 'primary.main' }} />
            <Typography variant="caption" color="primary">
              {currentTool}
            </Typography>
            <CircularProgress size={12} />
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box sx={{ 
        p: 2, 
        flexShrink: 0,
        borderTop: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper'
      }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            multiline
            maxRows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={awsConfigValid ? "Ask me about your schedule, policies, or submit requests..." : "AWS not configured..."}
            disabled={!awsConfigValid || isLoading || streamingState.isStreaming}
            variant="outlined"
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />
          <IconButton
            onClick={sendMessage}
            disabled={!input.trim() || !awsConfigValid || isLoading || streamingState.isStreaming}
            color="primary"
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              '&:hover': {
                bgcolor: 'primary.dark'
              },
              '&:disabled': {
                bgcolor: 'action.disabled'
              }
            }}
          >
            {isLoading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <Send />
            )}
          </IconButton>
        </Box>
      </Box>

    </Box>
  );
};

export default ChatPanel;
