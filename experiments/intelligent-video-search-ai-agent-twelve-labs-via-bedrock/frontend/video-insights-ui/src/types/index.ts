export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  video_context?: VideoContext;
  search_results?: VideoResult[];
}

export interface VideoContext {
  recent_videos: string[];
  all_mentioned_videos: Record<string, VideoMention>;
}

export interface VideoMention {
  first_mentioned: string;
  last_mentioned: string;
  mention_count: number;
}

export interface VideoResult {
  video_id: string;
  video_title: string;
  video_url?: string;
  thumbnail_url?: string;
  summary: string;
  score?: number;
  processing_date?: string;
  brands_mentioned?: string[];
  companies_mentioned?: string[];
  people_mentioned?: string[];
  sentiment?: string;
}

export interface WebSocketMessage {
  type: 'status' | 'tool_use' | 'stream' | 'complete' | 'error' | 'response';
  content?: string;
  message?: string;
  tool?: string;
  status?: string;
  timestamp?: string;
  metadata?: any;
}

export interface SearchFiltersProps {
  activeFilter: string;
  setActiveFilter: (filter: string) => void;
}

export interface VideoCardProps {
  video: VideoResult;
  onClick: (video: VideoResult) => void;
}

export interface MessageFormatterProps {
  content: string;
}