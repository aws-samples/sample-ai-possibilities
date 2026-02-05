# Video Keeper - AI-Powered Video Library with Multimodal Agentic Search via Amazon Nova 2

## Overview

Transform any video collection into an intelligent, searchable library using multi-modal AI and agentic conversation. This solution leverages **Amazon Nova 2 models** through Amazon Bedrock, Strands SDK (Agentic framework), and Amazon OpenSearch to retrieve rich insights from videos - all without requiring external API keys or third-party SDKs. This is a generic video search solution which works with any type of videos.

**Key Innovation**: This implementation uses Amazon's cutting-edge Nova 2 models directly through Amazon Bedrock, providing enterprise-grade video AI capabilities with simplified deployment and billing through your AWS account. All models run in **us-east-1** for simplified architecture.

<img src="./images/UI.jpg" alt="Webserver UI" width="800" />

## Tags

- ai-agents
- video-to-video-search
- bedrock
- amazon-nova
- nova-omni
- nova-lite
- python
- demo
- strands
- mcp
- serverless

## Technologies

- Python 3.11+
- AWS SDK (boto3)
- Amazon Bedrock (Nova 2 models)
- Amazon Nova Omni (video understanding + transcription)
- Amazon Nova Lite 2.0 (entity extraction)
- Amazon Nova Multimodal Embeddings (video + text embeddings)
- Amazon OpenSearch Serverless
- AWS Step Functions
- Strands Agents SDK
- Model Context Protocol (MCP)
- FastAPI
- React
- Tailwind CSS

## Difficulty

Medium

## What is Video Keeper?

Video Keeper is an **agentic AI system** that automatically analyzes, indexes, and makes any video collection searchable through natural conversation. Whether you have training videos, personal memories, gaming recordings, educational content, or professional documentation, Video Keeper creates an intelligent search experience powered entirely by AWS services and Amazon Nova 2 models available through Amazon Bedrock.

### Key Capabilities

**Universal Video Support**
- Personal memories, family videos, vacation recordings
- Educational content, lectures, tutorials, how-to guides
- Gaming highlights, streams, gameplay recordings
- Professional content, meetings, presentations, training materials
- Entertainment videos, shows, documentaries

**Advanced Search Methods**
- **Conversational AI Search** - Chat naturally about your videos using AWS Strands SDK
- **Video-to-Video Similarity** - Upload a video to find visually similar content using Nova embeddings
- **Semantic Search** - "Find happy family moments" or "Show me Python tutorials"
- **Entity Search** - Find videos featuring specific people, brands, or objects
- **Keyword Search** - Traditional text-based search across all metadata

**Multi-Modal AI Analysis (Powered by Amazon Nova 2)**
- **Visual content understanding** via Nova Omni (video-only analysis)
- **Audio transcription** via Nova Omni (speech-to-text)
- **Video embeddings** via Nova Multimodal Embeddings (3072-dimensional vectors)
- **Entity extraction** (people, brands, companies) using Nova Lite 2.0
- **Text embeddings** for semantic search via Nova Multimodal Embeddings
- **Smart thumbnails** generated with FFmpeg

**Robust Architecture**
- **100% AWS-native** - No external dependencies or API keys required
- **Single region deployment** - All Nova 2 models in us-east-1
- **Serverless infrastructure** - Step Functions, Lambda, OpenSearch
- **Real-time streaming** responses via WebSocket
- **Secure presigned URLs** for video access
- **Comprehensive error handling** and monitoring

## Architecture Overview

<img src="./images/vid-architecture.png" alt="Architecture" width="800" />

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   S3 Video  │───▶│ EventBridge  │───▶│ Step Functions  │
│   Upload    │    │   Trigger    │    │   Workflow      │
└─────────────┘    └──────────────┘    └─────────────────┘
                                                │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             ▼                             │
                   │                    ┌─────────────────┐                    │
                   │                    │ Lambda: Initiate│                    │
                   │                    │   Processing    │                    │
                   │                    └─────────────────┘                    │
                   │                             │                             │
                   │                             ▼                             │
       ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
       │ Amazon Bedrock  │◀────────────▶│ Lambda: Extract │─────────────▶│ OpenSearch      │
       │ Nova 2 Models   │              │   Insights      │              │ Serverless      │
       │ (Omni + Lite +  │              └─────────────────┘              │ (Vector + Text) │
       │  Embeddings)    │                       │                       └─────────────────┘
       └─────────────────┘                       │                                   ▲
                                                 ▼                                   │
                                        ┌─────────────────┐                          │
                                        │ Nova Multimodal │──────────────────────────┘
                                        │ Embeddings      │
                                        │ (3072-dim)      │
                                        └─────────────────┘
                   │
       ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
       │ Frontend React  │◀────────────▶│ AI Agent        │◀────────────▶│ MCP Server      │
       │ (Port 3000)     │              │ (Strands SDK)   │              │ (Port 8008)     │
       │                 │              │ (Port 8090)     │              │                 │
       └─────────────────┘              └─────────────────┘              └─────────────────┘
                   │                             │                                  │
                   │                             ▼                                  ▼
                   │                    ┌─────────────────┐              ┌─────────────────┐
                   └───────────────────▶│ Video API       │              │ OpenSearch      │
                                        │ (Port 8091)     │─────────────▶│ Video Search    │
                                        └─────────────────┘              └─────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │ Amazon Bedrock  │
                                        │ (Nova Omni)     │
                                        └─────────────────┘
```

## Quick Start

### Prerequisites

- **AWS Account** with permissions for Bedrock, OpenSearch Serverless, Lambda, Step Functions, S3
- **AWS CLI** configured with appropriate credentials
- **Python 3.11+** and **Node.js 16+** installed
- **SAM CLI** installed ([installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- **Amazon Bedrock access** to Nova 2 models (all in us-east-1):
  - Amazon Nova Omni (`global.amazon.nova-2-omni-v1:0`)
  - Amazon Nova Lite 2.0 (`global.amazon.nova-2-lite-v1:0`)
  - Amazon Nova Multimodal Embeddings (`amazon.nova-2-multimodal-embeddings-v1:0`)
- **S3 deployment bucket** - Create an S3 bucket for SAM deployment artifacts before running deploy.sh

### 1. Deploy AWS Infrastructure

This deployment uses **Amazon Nova 2 models natively through Amazon Bedrock**:
- **Nova Omni** - Video understanding (visual) and transcription (audio)
- **Nova Lite 2.0** - Named entity recognition (NER)
- **Nova Multimodal Embeddings** - Video and text embeddings (3072 dimensions)

All models are available in **us-east-1** - no cross-region complexity.

> ⚠️ **IMPORTANT: OpenSearch Access**
>
> OpenSearch Serverless requires explicit IAM permissions. The deploy script **automatically adds your current IAM identity** to the OpenSearch data access policy. This is required to:
> - Run the MCP server locally
> - Run the video-api locally
> - Run the agent locally
> - Create the OpenSearch index
>
> **If you get 403 Forbidden errors**, your IAM identity is not in the access policy. Redeploy to fix this.

```bash
# Clone repository
git clone <repository-url>
cd intelligent-video-search-ai-agent-nova

# Create deployment bucket for SAM artifacts (one-time setup)
aws s3 mb s3://my-sam-deployment-bucket-$(date +%s) --region us-east-1

# Deploy using the deployment script
# The script will:
# - Detect your current IAM identity
# - Automatically add it to OpenSearch access policy
# - Show you which principals have access
#
# Options:
# -b: Video bucket - CloudFormation will CREATE this bucket (use a NEW unique name)
# -d: Deployment bucket - MUST already exist (stores CloudFormation artifacts)
# -p: Additional IAM principals for OpenSearch access (optional, comma-separated)
# --no-auto-principal: Don't auto-add current IAM user (not recommended)
# --create-index: Create OpenSearch index automatically

./deploy.sh -b video-bucket -d deployment-bucket --create-index

# Example with additional team member access:
./deploy.sh -b video-keeper-bucket -d videos-deployment \
    -p "arn:aws:iam::123456789012:user/teammate" --create-index

# Note outputs: OpenSearch endpoint, State Machine ARN, S3 bucket name
```

> **WARNING: Video Bucket (-b)**
> - The video bucket will be **created** by CloudFormation - do NOT use an existing bucket name
> - S3 bucket names are globally unique - if the name exists anywhere in AWS, deployment will fail
> - If redeploying an existing stack, use the SAME bucket name from the original deployment
> - To find the current bucket: `aws cloudformation describe-stacks --stack-name video-ingestion-pipeline --query 'Stacks[0].Parameters[?ParameterKey==\`VideoBucketName\`].ParameterValue' --output text --region us-east-1`

### 2. Set Up Environment Variables

Copy and configure the `.env.example` file:

```bash
cp MCP/.env.example MCP/.env
cp agent/.env.example agent/.env
```

Then configure with your deployment outputs:

```bash
# ======================
# AWS Configuration
# ======================
AWS_REGION=us-east-1
PRIMARY_REGION=us-east-1  # All Nova 2 models in us-east-1

# ======================
# OpenSearch Configuration
# ======================
OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
INDEX_NAME=video-insights-rag

# ======================
# S3 Bucket
# ======================
VIDEO_BUCKET=your-video-bucket
S3_BUCKET=your-video-bucket

# ======================
# Nova 2 Models Configuration
# ======================
# Nova Omni - Video understanding and transcription
NOVA_OMNI_MODEL_ID=global.amazon.nova-2-omni-v1:0

# Nova Lite 2.0 - Entity extraction (NER)
NOVA_LITE_MODEL_ID=global.amazon.nova-2-lite-v1:0
NOVA_MAX_CHARS=350000

# Nova Multimodal Embeddings - Video and text embeddings
NOVA_EMBEDDING_MODEL_ID=amazon.nova-2-multimodal-embeddings-v1:0
NOVA_EMBEDDING_DIMENSION=3072

# AI Agent model (Nova Omni)
BEDROCK_MODEL_ID=global.amazon.nova-2-omni-v1:0
MODEL_TEMPERATURE=0.3

# ======================
# Service Ports
# ======================
MCP_HOST=localhost
MCP_PORT=8008
API_HOST=localhost
API_PORT=8090
VIDEO_API_HOST=localhost
VIDEO_API_PORT=8091

# ======================
# Frontend Configuration
# ======================
REACT_APP_API_URL=http://localhost:8090
REACT_APP_VIDEO_API_URL=http://localhost:8091
```

**Key Advantage**: No external API keys required - authentication is handled through your AWS credentials!

### 4. Start All Services

**Start services in order (MCP Server must be running before AI Agent):**

**Terminal 1 - MCP Server:**
```bash
pip install -r requirements.txt
cd MCP/
python 1-video-search-mcp.py
```

**Terminal 2 - AI Agent:**
```bash
cd agent/
python 1-ai-agent-video-search-strands-sdk.py
```

**Terminal 3 - Video API:**
```bash
cd video-api/
python 1-video-api.py
```

**Terminal 4 - Frontend:**
```bash
cd frontend/video-insights-ui/
npm install
npm start
```

### 5. Test the System

```bash
# Upload a test video
aws s3 cp test-video.mp4 s3://your-video-bucket/videos/

# The system will automatically:
# 1. Generate thumbnail using FFmpeg
# 2. Transcribe audio using Nova Omni
# 3. Analyze visual content using Nova Omni (video-only)
# 4. Extract entities using Nova Lite 2.0
# 5. Generate video embeddings using Nova Multimodal Embeddings
# 6. Generate text embeddings for semantic search
# 7. Index everything in OpenSearch

# Access the UI
open http://localhost:3000

# Try searches like:
# - "Find videos with people laughing"
# - "Show me tutorial content"
# - "What videos mention Python?"
# - Upload a video to find similar content
```

## Enhanced Features

### Amazon Nova 2 Integration

The system uses Amazon's Nova 2 models directly through Amazon Bedrock:

- **Nova Omni** (`global.amazon.nova-2-omni-v1:0`)
  - Video understanding (visual analysis only, ignores audio)
  - Audio transcription (speech-to-text)
  - Multi-turn conversation for the AI agent

- **Nova Lite 2.0** (`global.amazon.nova-2-lite-v1:0`)
  - Named Entity Recognition (NER)
  - Extracts brands, companies, and person names from transcripts
  - Tool use support for structured output

- **Nova Multimodal Embeddings** (`amazon.nova-2-multimodal-embeddings-v1:0`)
  - 3072-dimensional embeddings (configurable: 256, 384, 1024, 3072)
  - Video embeddings for similarity search
  - Text embeddings for semantic search
  - Async processing for video embeddings

### Benefits of Nova 2

- **No API Keys Required**: Authentication through AWS IAM roles
- **Unified Billing**: All AI usage billed through your AWS account
- **Enterprise Support**: Full AWS support and SLAs
- **Single Region**: All models in us-east-1 (no cross-region complexity)
- **High Quality**: State-of-the-art video understanding and embeddings
- **Async Processing**: Efficient handling of long-running video analysis

### Video Understanding Insights

Nova Omni generates comprehensive insights including:

1. **Summary** - Detailed visual content analysis (300-500 words)
2. **Chapters** - Scene-by-scene breakdown with timestamps
3. **Highlights** - Key visual moments with impact analysis
4. **Topics** - Primary, secondary topics and keywords
5. **Hashtags** - Social media optimized tags
6. **Sentiment** - Visual emotion and mood analysis
7. **Content Analytics** - Production quality, scene composition
8. **Visual Objects** - Detected objects, people, actions

### OpenSearch Access Control

OpenSearch Serverless uses **data access policies** that require explicit IAM principal permissions. The deployment script handles this automatically:

**Automatic Detection (Default Behavior)**:
- The script auto-detects your current IAM identity via `aws sts get-caller-identity`
- Converts assumed-role ARNs to role ARNs for OpenSearch compatibility
- Prompts for confirmation before deployment with options to add more principals

**Manual Principal Addition**:
- Use `-p` flag to add additional IAM principals: `-p "arn:aws:iam::123456789012:user/teammate"`
- Use `--no-auto-principal` to disable auto-detection (not recommended)

**Troubleshooting 403 Forbidden Errors**:
```bash
# 1. Check your current IAM identity
aws sts get-caller-identity

# 2. Redeploy to add your identity to the policy
./deploy.sh -b your-video-bucket -d your-deployment-bucket

# 3. The script will show which principals have access and prompt for confirmation
```

**Common causes of 403 errors**:
- Using a different IAM user/role than during deployment
- Running from a different AWS profile
- IAM credentials have changed or expired

### Robust Video Processing Pipeline

The Step Functions workflow includes:

- **Early Validation**: Checks OpenSearch index exists before processing
- **Error Handling**: Comprehensive error states with detailed logging
- **Progress Tracking**: Real-time status updates during processing
- **Automatic Retries**: Built-in retry logic for transient failures

### Video-to-Video Similarity Search

Upload any video to find similar content using Nova embeddings:

```python
# The system:
# 1. Uploads your video to S3
# 2. Generates embeddings using Nova Multimodal Embeddings
# 3. Searches OpenSearch for similar video embeddings
# 4. Returns ranked results with similarity scores
```

## Search Capabilities

### 1. **Conversational AI Search**
Chat naturally with the AI agent powered by AWS Strands SDK and Nova Omni:
- *"Find videos where people are celebrating"*
- *"Show me all Python programming tutorials"*
- *"What videos feature John from the marketing team?"*

### 2. **Video-to-Video Similarity Search**
Upload any video to find visually similar content using Nova embeddings:
- Compare visual composition, colors, scenes
- Find different angles of the same event
- Locate similar content types or styles
- Configurable similarity threshold (default: 0.8)

### 3. **Advanced Search Methods**
- **Semantic Search**: Natural language understanding using Nova embeddings
- **Keyword Search**: Traditional text search across titles, descriptions, transcripts
- **Hybrid Search**: Combines semantic and keyword for best results
- **Entity Search**: Find specific people, brands, objects extracted by Nova Lite

### 4. **Smart Filtering**
- Sentiment analysis (positive, negative, neutral content)
- Temporal searches (date ranges, recent content)
- Content categorization via Nova Omni insights
- Speaker/person identification with timestamps

## Detailed Setup

### Environment Configuration

The `.env.example` files in MCP/ and agent/ directories contain all required variables with detailed descriptions.

### AWS Permissions Required

Your AWS user/role needs access to:
- **Amazon Bedrock**:
  - Nova Omni
  - Nova Lite 2.0
  - Nova Multimodal Embeddings
- **Amazon OpenSearch Serverless**: Collection creation, read/write access
- **AWS Lambda**: Function creation and execution
- **AWS Step Functions**: State machine creation and execution
- **Amazon S3**: Bucket access
- **Amazon EventBridge**: Rule creation for S3 events

### Video Requirements

- **Size**: Up to 1GB per video
- **Resolution**: Videos are internally resized to 672×672
- **Duration**: Any duration (with 1GB limit)

## Testing & Validation

### Agent Tests

```bash
# Test all agent endpoints and functionality
cd agent/
python 2-test_agent.py
```

The test suite validates:
- All API endpoints responding correctly
- MCP server connectivity and search functions
- WebSocket streaming for real-time responses
- Session management and context tracking
- Bedrock model integrations

### Manual Testing Workflow

1. **Upload Test Videos**: Use diverse content types (tutorials, personal videos, presentations)
2. **Monitor Processing**: Check Step Functions console for processing status
3. **Test Search Variety**: Try different search methods and query types
4. **Validate Results**: Ensure embeddings and insights are properly indexed
5. **Test Video Upload Search**: Upload new videos to find similar existing content

## Cost Considerations

### AWS Usage Charges
- **Amazon Bedrock**:
  - Nova Omni: Check current Bedrock pricing
  - Nova Lite 2.0: Check current Bedrock pricing
  - Nova Multimodal Embeddings: Check current Bedrock pricing
- **Amazon OpenSearch Serverless**: ~$100+/month minimum (main cost driver)
- **AWS Lambda**: Pay per execution, typically $1-10/month
- **Amazon S3**: Storage costs
- **AWS Step Functions**: Pay per state transition

### Cost Optimization Tips
- **Delete OpenSearch collection** when not in use (biggest cost saver)
- Implement video compression before upload
- Use lifecycle policies to archive old videos
- Monitor Bedrock usage via CloudWatch
- Consider processing only video segments instead of full videos
- Use smaller embedding dimensions (256 or 384) if accuracy allows

## Important Disclaimers

### Educational Purpose
This project is designed for **educational and demonstration purposes**. For production use:
- Implement proper authentication and authorization
- Add API rate limiting and throttling
- Deploy APIs properly (not as Python scripts)
- Add data encryption at rest and in transit
- Set up comprehensive monitoring and alerting
- Review and implement security best practices
- Consider compliance requirements (GDPR, CCPA, etc.)

### Data Privacy
- Videos and metadata are stored in your AWS account
- All AI processing happens within AWS infrastructure
- Implement appropriate data retention and deletion policies
- Consider geographic data residency requirements

### Scalability Considerations
- Current configuration suitable for personal to small team use
- For large-scale deployment, review:
  - OpenSearch collection sizing
  - Bedrock service quotas
  - Lambda concurrency limits
  - S3 request rate limits

## Cleanup & Cost Management

### Complete Resource Cleanup
```bash
# Empty and delete S3 bucket
aws s3 rm s3://your-video-bucket --recursive
aws s3 rb s3://your-video-bucket

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name YOUR_STACK_NAME

# Delete OpenSearch collection (if not deleted by stack)
# This is the main cost driver - ensure it's deleted!
aws opensearchserverless delete-collection --id YOUR_COLLECTION_ID
```

### Cost Monitoring
- Monitor your [AWS Billing Dashboard](https://console.aws.amazon.com/billing/)
- Set up billing alerts for unexpected charges
- Review Bedrock usage in CloudWatch
- **OpenSearch Serverless is the primary cost** - delete when not in use

## Project Structure

```
intelligent-video-search-ai-agent-nova/
├── MCP/                      # Model Context Protocol server
├── agent/                    # AI agent (Strands SDK + Nova Omni)
├── frontend/                 # React web interface
├── video-api/                # Video metadata API service
├── lambdas/                  # AWS Lambda functions
│   ├── InitiateVideoProcessing/ # Video processing setup
│   └── ExtractInsightsFunction/ # Nova model orchestration
├── data_ingestion/           # OpenSearch index setup
├── tests/                    # Nova 2 client tests
├── data/                     # Sample datasets
├── infrastructure.yaml       # CloudFormation template
├── deploy.sh                 # Deployment script
├── .env.example             # Environment configuration template
└── README.md                # This file
```

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.
