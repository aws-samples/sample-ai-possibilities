import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';

// AWS Configuration - These should be configured via environment variables
const AWS_REGION = process.env.REACT_APP_AWS_REGION || 'us-west-2';
const AGENT_RUNTIME_ARN = process.env.REACT_APP_AGENT_RUNTIME_ARN || '';
const AGENT_QUALIFIER = process.env.REACT_APP_AGENT_QUALIFIER || 'DEFAULT';

// Optional: AWS credentials for local development
// In production, use IAM roles attached to your compute resources (EC2, ECS, Lambda, etc.)
const AWS_ACCESS_KEY_ID = process.env.REACT_APP_AWS_ACCESS_KEY_ID;
const AWS_SECRET_ACCESS_KEY = process.env.REACT_APP_AWS_SECRET_ACCESS_KEY;
const AWS_SESSION_TOKEN = process.env.REACT_APP_AWS_SESSION_TOKEN;

// Initialize AWS SDK client
const createAgentCoreClient = () => {
  // Configuration object
  const config = {
    region: AWS_REGION,
  };

  // Add explicit credentials if provided (for local development)
  // In production, rely on IAM roles
  if (AWS_ACCESS_KEY_ID && AWS_SECRET_ACCESS_KEY) {
    config.credentials = {
      accessKeyId: AWS_ACCESS_KEY_ID,
      secretAccessKey: AWS_SECRET_ACCESS_KEY,
      ...(AWS_SESSION_TOKEN && { sessionToken: AWS_SESSION_TOKEN })
    };
  }
  // Otherwise, the SDK will use the default credential provider chain:
  // 1. Environment variables
  // 2. Shared credentials file
  // 3. IAM roles (for EC2, ECS, Lambda, etc.)

  return new BedrockAgentCoreClient(config);
};

// Store runtime sessions to reuse them
const runtimeSessions = new Map();

// Generate or get a runtime session ID that's at least 33 characters
const getOrCreateRuntimeSessionId = (sessionId) => {
  // Check if we already have a runtime session for this sessionId
  if (runtimeSessions.has(sessionId)) {
    return runtimeSessions.get(sessionId);
  }
  
  // Create a new runtime session ID (must be 33+ characters)
  const timestamp = Date.now().toString();
  const random = Math.random().toString(36).substring(2, 15);
  const runtimeSessionId = `${sessionId}_${timestamp}_${random}`.padEnd(33, '0').substring(0, 100);
  
  // Store it for reuse
  runtimeSessions.set(sessionId, runtimeSessionId);
  console.log('Created new runtime session:', runtimeSessionId, 'for session:', sessionId);
  
  return runtimeSessionId;
};

const TOOL_NAME_PATTERNS = [
  /['"]?tool_name['"]?\s*:\s*['"]([^'"\s]+)['"]/,
  /['"]?function_name['"]?\s*:\s*['"]([^'"\s]+)['"]/,
  /calling\s+(\w+)/,
  /function\s+(\w+)/,
  /(get_\w+|search_\w+|create_\w+|update_\w+|delete_\w+)/
];

const createSSEState = ({ onChunk, onToolUse }) => ({
  fullText: '',
  finalText: '',
  hasStreamed: false,
  detectedTools: new Set(),
  onChunk,
  onToolUse
});

const recordToolUse = (toolName, state, debugSource) => {
  if (!toolName || !state.onToolUse || state.detectedTools.has(toolName)) {
    return;
  }
  console.log('AgentCore: Detected tool', toolName, 'via', debugSource);
  state.detectedTools.add(toolName);
  state.onToolUse(toolName);
};

const detectToolUsageFromText = (text, state) => {
  if (!state.onToolUse) {
    return;
  }

  if (!(text.includes('tool') || text.includes('function') || text.includes('get_') || text.includes('search_'))) {
    return;
  }

  console.log('AgentCore: Checking text for tools:', text.substring(0, 150));
  for (const pattern of TOOL_NAME_PATTERNS) {
    const match = text.match(pattern);
    if (match && match[1]) {
      recordToolUse(match[1], state, 'text pattern');
      break;
    }
  }
};

const detectToolUsageFromParsed = (parsed, state, rawContent) => {
  if (!state.onToolUse) {
    return;
  }

  const foundNames = new Set();

  const registerName = (name, source) => {
    if (name && !foundNames.has(name)) {
      foundNames.add(name);
      recordToolUse(name, state, source);
    }
  };

  const isToolUseObject = (value) => {
    return value && typeof value === 'object' && typeof value.name === 'string' && (
      'toolUseId' in value || 'tool_use_id' in value || 'type' in value || 'input' in value
    );
  };

  const walk = (node, sourcePath = '') => {
    if (!node || typeof node !== 'object') {
      return;
    }

    if (Array.isArray(node)) {
      node.forEach((item, index) => walk(item, `${sourcePath}[${index}]`));
      return;
    }

    if (isToolUseObject(node)) {
      registerName(node.name, sourcePath || 'toolUseObject');
    }

    for (const [key, value] of Object.entries(node)) {
      if (key === 'tool' && typeof value === 'string') {
        registerName(value, `${sourcePath}.${key}`);
      }

      if (key === 'name' && typeof value === 'string' && isToolUseObject(node)) {
        registerName(value, sourcePath || 'toolUseObject');
      }

      if (key === 'function_name' || key === 'tool_name') {
        if (typeof value === 'string') {
          registerName(value, `${sourcePath}.${key}`);
        }
      }

      walk(value, sourcePath ? `${sourcePath}.${key}` : key);
    }
  };

  walk(parsed.event || parsed, 'event');

  const toolName = parsed.function_name || parsed.tool_name;
  if (toolName) {
    registerName(toolName, 'root.function/tool name');
  }

  if (parsed.event?.metadata?.tool) {
    registerName(parsed.event.metadata.tool, 'event.metadata.tool');
  }

  if (foundNames.size === 0 && rawContent) {
    detectToolUsageFromText(rawContent, state);
  }
};

const handleSSEDataContent = (dataContent, state) => {
  console.log('Processing SSE data:', dataContent.substring(0, 100));

  try {
    const parsed = JSON.parse(dataContent);

    if (parsed.event?.contentBlockDelta?.delta?.text) {
      const chunk = parsed.event.contentBlockDelta.delta.text;
      state.fullText += chunk;
      state.hasStreamed = true;
      console.log('Streaming chunk:', chunk);
      if (state.onChunk) {
        state.onChunk(chunk);
      }
    } else if (parsed.message?.content?.[0]?.text) {
      console.log('Final complete message received');
      const finalMessage = parsed.message.content[0].text;
      state.finalText = finalMessage;
      if (!state.hasStreamed) {
        state.fullText = finalMessage;
      }
    }

    detectToolUsageFromParsed(parsed, state, dataContent);
  } catch (error) {
    detectToolUsageFromText(dataContent, state);
  }
};

const findEventDelimiter = (text) => {
  const lfIndex = text.indexOf('\n\n');
  const crlfIndex = text.indexOf('\r\n\r\n');

  if (lfIndex === -1 && crlfIndex === -1) {
    return { index: -1, length: 0 };
  }

  if (lfIndex === -1) {
    return { index: crlfIndex, length: 4 };
  }

  if (crlfIndex === -1) {
    return { index: lfIndex, length: 2 };
  }

  return lfIndex < crlfIndex
    ? { index: lfIndex, length: 2 }
    : { index: crlfIndex, length: 4 };
};

const processSSEEventBlock = (eventBlock, state) => {
  const lines = eventBlock.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('data: ')) {
      handleSSEDataContent(line.slice(6), state);
    }
  }
};

// Parse SSE (Server-Sent Events) response format
const parseSSEResponse = (sseText, onChunk, onToolUse) => {
  const state = createSSEState({ onChunk, onToolUse });
  const eventBlocks = sseText.split(/\r?\n\r?\n/);

  console.log('Parsing SSE response, total blocks:', eventBlocks.length);

  for (const eventBlock of eventBlocks) {
    if (eventBlock.trim().length === 0) {
      continue;
    }
    processSSEEventBlock(eventBlock, state);
  }

  console.log(
    'Parsing complete. HasStreamed:',
    state.hasStreamed,
    'FullText length:',
    state.fullText.length,
    'FinalText length:',
    state.finalText.length
  );

  return state.finalText || state.fullText;
};

// Main function to invoke the agent
export const invokeAgent = async ({
  message,
  sessionId,
  businessId,
  staffId = null,
  onStreamChunk = null,
  onStreamComplete = null,
  onStreamError = null,
  onToolUse = null,
  enableStreaming = true
}) => {
  console.log('[AgentCore] invokeAgent streaming rev 2');
  const client = createAgentCoreClient();
  
  // Get or create a runtime session ID for this session
  // This ensures the same runtime session is used for all messages in a conversation
  const runtimeSessionId = getOrCreateRuntimeSessionId(sessionId);
  
  // Encode the message as Uint8Array
  // The agent expects "prompt" not "message"
  const encoder = new TextEncoder();
  const payloadData = {
    prompt: message,  // Changed from 'message' to 'prompt'
    business_id: businessId,  // Using snake_case to match Python
    ...(staffId && { staff_id: staffId })  // Using snake_case
  };
  const payload = encoder.encode(JSON.stringify(payloadData));
  
  // Log what we're sending for debugging
  console.log('Sending payload:', payloadData);
  
  // Prepare the input for the agent
  const input = {
    runtimeSessionId: runtimeSessionId,
    agentRuntimeArn: AGENT_RUNTIME_ARN,
    qualifier: AGENT_QUALIFIER,
    payload: payload
  };

  console.log('Invoking agent with session:', runtimeSessionId);

  try {
    const command = new InvokeAgentRuntimeCommand(input);
    const response = await client.send(command);
    
    if (!response.response) {
      throw new Error('No response received from agent');
    }

    const agentResponse = response.response;
    const responseKeys = (() => {
      try {
        return Object.keys(agentResponse || {});
      } catch (error) {
        console.warn('Could not enumerate agent response keys:', error);
        return [];
      }
    })();

    console.log('Agent response capabilities:', {
      keys: responseKeys,
      hasGetReader: typeof agentResponse?.getReader === 'function',
      hasTransformToWebStream: typeof agentResponse?.transformToWebStream === 'function',
      hasStream: typeof agentResponse?.stream === 'function',
      hasTransformToString: typeof agentResponse?.transformToString === 'function'
    });

    const getReadableStreamReader = () => {
      if (!enableStreaming) {
        return null;
      }

      if (typeof agentResponse?.getReader === 'function') {
        return agentResponse.getReader();
      }

      if (typeof agentResponse?.transformToWebStream === 'function' && typeof ReadableStream !== 'undefined') {
        return agentResponse.transformToWebStream().getReader();
      }

      if (typeof agentResponse?.stream === 'function' && typeof ReadableStream !== 'undefined') {
        const webStream = agentResponse.stream();
        if (webStream && typeof webStream.getReader === 'function') {
          return webStream.getReader();
        }
      }

      return null;
    };

    const streamReader = getReadableStreamReader();

    if (streamReader) {
      console.log('Streaming agent response via ReadableStream reader');

      const state = createSSEState({ onChunk: onStreamChunk, onToolUse });
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { value, done } = await streamReader.read();
          if (done) {
            break;
          }

          const decoded = decoder.decode(value, { stream: true });
          buffer += decoded;

          let delimiter = findEventDelimiter(buffer);
          while (delimiter.index !== -1) {
            const eventBlock = buffer.slice(0, delimiter.index);
            buffer = buffer.slice(delimiter.index + delimiter.length);
            if (eventBlock.trim().length > 0) {
              processSSEEventBlock(eventBlock, state);
            }
            delimiter = findEventDelimiter(buffer);
          }
        }

        const remaining = decoder.decode();
        if (remaining) {
          buffer += remaining;
        }
      } finally {
        streamReader.releaseLock();
      }

      if (buffer.trim().length > 0) {
        processSSEEventBlock(buffer, state);
      }

      const finalText = state.finalText || state.fullText || '';

      if (enableStreaming && onStreamComplete) {
        onStreamComplete(finalText);
      }

      return finalText;
    }

    const rawResponse = await agentResponse.transformToString();
    console.log('Raw response received, length:', rawResponse.length);
    console.log('Raw response preview:', rawResponse.substring(0, 500));

    const textResponse = parseSSEResponse(rawResponse, onStreamChunk, onToolUse);

    if (textResponse) {
      if (enableStreaming && onStreamComplete) {
        onStreamComplete(textResponse);
      }
      return textResponse;
    }

    console.warn('Could not parse SSE response, returning raw text');
    if (onStreamComplete) {
      onStreamComplete(rawResponse);
    }
    return rawResponse;
  } catch (error) {
    console.error('Error invoking agent:', error);
    if (onStreamError) {
      onStreamError(error);
    }
    throw error;
  }
};

// Function to clear a session (useful for starting a new conversation)
export const clearSession = (sessionId) => {
  if (runtimeSessions.has(sessionId)) {
    console.log('Clearing runtime session for:', sessionId);
    runtimeSessions.delete(sessionId);
  }
};

// Function to validate AWS configuration
export const validateAWSConfig = () => {
  const missingConfigs = [];
  
  if (!AGENT_RUNTIME_ARN) missingConfigs.push('REACT_APP_AGENT_RUNTIME_ARN');
  if (!AWS_REGION) missingConfigs.push('REACT_APP_AWS_REGION');
  
  if (missingConfigs.length > 0) {
    console.warn('Missing AWS configuration:', missingConfigs.join(', '));
    console.warn('Please set these environment variables in your .env file');
    return false;
  }
  
  return true;
};

// Export configuration for debugging
export const getAWSConfig = () => ({
  region: AWS_REGION,
  agentRuntimeArn: AGENT_RUNTIME_ARN,
  qualifier: AGENT_QUALIFIER,
  hasCredentials: !!(AWS_ACCESS_KEY_ID && AWS_SECRET_ACCESS_KEY),
  configured: validateAWSConfig()
});
