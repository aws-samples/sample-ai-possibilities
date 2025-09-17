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

// Parse SSE (Server-Sent Events) response format
const parseSSEResponse = (sseText, onChunk, onToolUse) => {
  const lines = sseText.split('\n');
  let fullText = '';
  let hasStreamed = false;
  
  console.log('Parsing SSE response, total lines:', lines.length);
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('data: ')) {
      const dataContent = line.slice(6); // Remove 'data: ' prefix
      console.log(`Line ${i}:`, dataContent.substring(0, 100));
      
      try {
        const parsed = JSON.parse(dataContent);
        
        // Handle different event types
        if (parsed.event?.contentBlockDelta?.delta?.text) {
          // This is a streaming text chunk
          const chunk = parsed.event.contentBlockDelta.delta.text;
          fullText += chunk;
          hasStreamed = true;
          console.log('Streaming chunk:', chunk);
          if (onChunk) {
            onChunk(chunk);
          }
        } else if (parsed.message?.content?.[0]?.text) {
          // This is the final complete message
          console.log('Final complete message received');
          fullText = parsed.message.content[0].text;
        }
        // Look for tool usage indicators in the data
        else if (dataContent.includes('tool_name') || dataContent.includes('function_name')) {
          console.log('Found tool usage indicator in JSON');
          const toolMatch = dataContent.match(/tool_name["']?\s*:\s*["']?(\w+)["']?/) || 
                           dataContent.match(/function_name["']?\s*:\s*["']?(\w+)["']?/);
          if (toolMatch && onToolUse) {
            console.log('Detected tool:', toolMatch[1]);
            onToolUse(toolMatch[1]);
          }
        }
      } catch (e) {
        // Not JSON, might be Python dict format - check for tool usage
        if (dataContent.includes('get_') || dataContent.includes('tool') || 
            dataContent.includes('function') || dataContent.includes('staff') || 
            dataContent.includes('roster')) {
          console.log('Checking non-JSON line for tools:', dataContent.substring(0, 100));
          
          // Look for common tool patterns
          const toolPatterns = [
            /get_staff_\w+/g,
            /get_roster_\w+/g, 
            /get_availability/g,
            /search_staff/g,
            /'(\w+_\w+)'/g,
            /"(\w+_\w+)"/g
          ];
          
          for (const pattern of toolPatterns) {
            const matches = dataContent.match(pattern);
            if (matches && onToolUse) {
              console.log('Found tool via pattern:', matches[0]);
              onToolUse(matches[0].replace(/['"]/g, ''));
              break;
            }
          }
        }
        // Skip non-parseable lines
      }
    }
  }
  
  console.log('Parsing complete. HasStreamed:', hasStreamed, 'FullText length:', fullText.length);
  return fullText;
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
    
    // Process the response
    if (response.response) {
      // Convert response to string
      const rawResponse = await response.response.transformToString();
      console.log('Raw response received, length:', rawResponse.length);
      console.log('Raw response preview:', rawResponse.substring(0, 500));
      
      // Parse the SSE format to extract text and detect tool usage
      const textResponse = parseSSEResponse(rawResponse, onStreamChunk, onToolUse);
      
      if (textResponse) {
        if (enableStreaming && onStreamComplete) {
          onStreamComplete(textResponse);
        }
        return textResponse;
      } else {
        // If parsing failed, try to return raw response
        console.warn('Could not parse SSE response, returning raw text');
        if (onStreamComplete) {
          onStreamComplete(rawResponse);
        }
        return rawResponse;
      }
    } else {
      throw new Error('No response received from agent');
    }
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