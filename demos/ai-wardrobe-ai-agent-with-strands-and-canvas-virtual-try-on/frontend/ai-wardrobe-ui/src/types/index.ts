export interface User {
  userId: string;
  userName: string;
  createdAt: string;
  wardrobeItems: string[];
  profilePhoto?: string;
}

export interface WardrobeItem {
  itemId: string;
  userId: string;
  imageUrl: string;
  presignedUrl?: string;
  category: 'top' | 'bottom' | 'dress' | 'outerwear' | 'shoes' | 'accessory';
  attributes: {
    color: string;
    style: string;
    season: string;
    description?: string;
  };
  uploadedAt: string;
}

export interface Outfit {
  outfitId: string;
  userId: string;
  items: string[];
  occasion: string;
  tryOnImageUrl?: string;
  tryOnPresignedUrl?: string;
  createdAt: string;
  notes?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface WebSocketMessage {
  type: 'init' | 'init_complete' | 'message' | 'stream' | 'complete' | 'error' | 'thinking' | 'thinking_complete' | 'get_wardrobe' | 'wardrobe_data' | 'get_outfits' | 'outfits_data';
  content?: string;
  message?: string;
  data?: any;
  timestamp?: string;
}