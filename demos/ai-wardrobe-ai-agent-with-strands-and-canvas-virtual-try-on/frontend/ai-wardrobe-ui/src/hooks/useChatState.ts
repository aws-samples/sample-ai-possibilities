import { useReducer, useCallback } from 'react';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

export type LoadingState = 'idle' | 'thinking' | 'processing' | 'virtual-tryon' | 'error';

interface ChatState {
  messages: ChatMessage[];
  isConnected: boolean;
  isTyping: boolean;
  loadingState: LoadingState;
  error: string | null;
  currentAssistantMessage: string;
}

type ChatAction = 
  | { type: 'CONNECT' }
  | { type: 'DISCONNECT' }
  | { type: 'ADD_MESSAGE'; message: ChatMessage }
  | { type: 'UPDATE_MESSAGE'; id: string; updates: Partial<ChatMessage> }
  | { type: 'SET_TYPING'; isTyping: boolean }
  | { type: 'SET_LOADING_STATE'; state: LoadingState }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'START_ASSISTANT_MESSAGE' }
  | { type: 'APPEND_ASSISTANT_MESSAGE'; content: string }
  | { type: 'COMPLETE_ASSISTANT_MESSAGE' }
  | { type: 'RESET' };

const initialState: ChatState = {
  messages: [],
  isConnected: false,
  isTyping: false,
  loadingState: 'idle',
  error: null,
  currentAssistantMessage: '',
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'CONNECT':
      return { ...state, isConnected: true, error: null };
    
    case 'DISCONNECT':
      return { ...state, isConnected: false, loadingState: 'idle', isTyping: false };
    
    case 'ADD_MESSAGE':
      return { 
        ...state, 
        messages: [...state.messages, action.message],
        error: null 
      };
    
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map(msg => 
          msg.id === action.id ? { ...msg, ...action.updates } : msg
        )
      };
    
    case 'SET_TYPING':
      return { ...state, isTyping: action.isTyping };
    
    case 'SET_LOADING_STATE':
      return { ...state, loadingState: action.state };
    
    case 'SET_ERROR':
      return { ...state, error: action.error, loadingState: 'error' };
    
    case 'CLEAR_ERROR':
      return { ...state, error: null, loadingState: 'idle' };
    
    case 'START_ASSISTANT_MESSAGE':
      return { 
        ...state, 
        currentAssistantMessage: state.currentAssistantMessage || '',  // Don't reset if already has content
        isTyping: true,
        loadingState: 'processing'
      };
    
    case 'APPEND_ASSISTANT_MESSAGE':
      return { 
        ...state, 
        currentAssistantMessage: (state.currentAssistantMessage || '') + action.content 
      };
    
    case 'COMPLETE_ASSISTANT_MESSAGE':
      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: state.currentAssistantMessage,
        timestamp: new Date(),
        status: 'sent'
      };
      return {
        ...state,
        messages: [...state.messages, newMessage],
        currentAssistantMessage: '',
        isTyping: false,
        loadingState: 'idle'
      };
    
    case 'RESET':
      return initialState;
    
    default:
      return state;
  }
}

export function useChatState() {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const addUserMessage = useCallback((content: string) => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'sent'
    };
    dispatch({ type: 'ADD_MESSAGE', message });
    return message.id;
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content,
      timestamp: new Date(),
      status: 'sent'
    };
    dispatch({ type: 'ADD_MESSAGE', message });
  }, []);

  const setLoadingState = useCallback((loadingState: LoadingState) => {
    dispatch({ type: 'SET_LOADING_STATE', state: loadingState });
  }, []);

  const setError = useCallback((error: string) => {
    dispatch({ type: 'SET_ERROR', error });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const connect = useCallback(() => {
    dispatch({ type: 'CONNECT' });
  }, []);

  const disconnect = useCallback(() => {
    dispatch({ type: 'DISCONNECT' });
  }, []);

  const startAssistantMessage = useCallback(() => {
    dispatch({ type: 'START_ASSISTANT_MESSAGE' });
  }, []);

  const appendAssistantMessage = useCallback((content: string) => {
    dispatch({ type: 'APPEND_ASSISTANT_MESSAGE', content });
  }, []);

  const completeAssistantMessage = useCallback(() => {
    dispatch({ type: 'COMPLETE_ASSISTANT_MESSAGE' });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    actions: {
      addUserMessage,
      addSystemMessage,
      setLoadingState,
      setError,
      clearError,
      connect,
      disconnect,
      startAssistantMessage,
      appendAssistantMessage,
      completeAssistantMessage,
      reset
    }
  };
}