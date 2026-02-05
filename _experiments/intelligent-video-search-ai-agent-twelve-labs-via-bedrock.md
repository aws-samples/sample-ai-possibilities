---
title: "Video Keeper - AI-Powered Video Library with Multimodal Agentic Search via Amazon Bedrock"
date: 2026-02-05
description: "Transform any video collection into an intelligent, searchable library using multi-modal AI and agentic conversation. This solution leverages **Amazon Bedrock's serverless native TwelveLabs models**, Strands SDK (Agentic framework), Amazon Nova, Cohere embedding, Anthropic Claude, and Amazon Transcribe to retrieve rich insights from videos - all without requiring external API keys or third-party SDKs. This is a generic video search solution which works with any type of videos.

**🎯 Key Innovation**: This implementation uses TwelveLabs' cutting-edge video understanding models (Marengo and Pegasus) directly through Amazon Bedrock, providing enterprise-grade video AI capabilities with simplified deployment and billing through your AWS account.

<img src="./images/UI.jpg" alt="Webserver UI" width="800" />"
layout: experiment
difficulty: medium
source_folder: "experiments/intelligent-video-search-ai-agent-twelve-labs-via-bedrock"

tags:
  - ai-agents
  - video-to-video-search
  - bedrock
  - bedrock-twelvelabs
  - python
  - demo
  - strands
  - mcp
  - serverless
technologies:
  - Python 3.11+
  - AWS SDK (boto3)
  - Amazon Bedrock (with TwelveLabs models)
  - Amazon Nova
  - Amazon OpenSearch Serverless
  - AWS Step Functions
  - Strands Agents SDK
  - Model Context Protocol (MCP)
  - FastAPI
  - React
  - Tailwind CSS
---

# Video Keeper - AI-Powered Video Library with Multimodal Agentic Search via Amazon Bedrock

## Overview

Transform any video collection into an intelligent, searchable library using multi-modal AI and agentic conversation. This solution leverages **Amazon Bedrock's serverless native TwelveLabs models**, Strands SDK (Agentic framework), Amazon Nova, Cohere embedding, Anthropic Claude, and Amazon Transcribe to retrieve rich insights from videos - all without requiring external API keys or third-party SDKs. This is a generic video search solution which works with any type of videos.

**🎯 Key Innovation**: This implementation uses TwelveLabs' cutting-edge video understanding models (Marengo and Pegasus) directly through Amazon Bedrock, providing enterprise-grade video AI capabilities with simplified deployment and billing through your AWS account.

<img src="./images/UI.jpg" alt="Webserver UI" width="800" />

## Tags

- ai-agents
- video-to-video-search
- bedrock
- bedrock-twelvelabs
- python
- demo
- strands
- mcp
- serverless

## Technologies

- Python 3.11+
- AWS SDK (boto3)
- Amazon Bedrock (with TwelveLabs models)
- Amazon Nova
- Amazon OpenSearch Serverless
- AWS Step Functions
- Strands Agents SDK
- Model Context Protocol (MCP)
- FastAPI
- React
- Tailwind CSS

## Difficulty

Medium

## 🎯 What is Video Keeper?

Video Keeper is an **agentic AI system** that automatically analyzes, indexes, and makes any video collection searchable through natural conversation. Whether you have training videos, personal memories, gaming recordings, educational content, or professional documentation, Video Keeper creates an intelligent search experience powered entirely by AWS services and advanced AI models available through Amazon Bedrock.

### 🚀 Key Capabilities

**🎬 Universal Video Support**
- Personal memories, family videos, vacation recordings
- Educational content, lectures, tutorials, how-to guides  
- Gaming highlights, streams, gameplay recordings
- Professional content, meetings, presentations, training materials
- Entertainment videos, shows, documentaries

**🔍 Advanced Search Methods**
- **Conversational AI Search** - Chat naturally about your videos using AWS Strands SDK
- **Video-to-Video Similarity** - Upload a video to find visually similar content using Marengo embeddings
- **Semantic Search** - "Find happy family moments" or "Show me Python tutorials"
- **Entity Search** - Find videos featuring specific people, brands, or objects
- **Keyword Search** - Traditional text-based search across all metadata

**🧠 Multi-Modal AI Analysis (Powered by Amazon Bedrock)**
- **Visual content understanding** via TwelveLabs Marengo (1024-dimensional embeddings)
- **Video comprehension** via TwelveLabs Pegasus (summaries, chapters, topics)
- **Speech-to-text transcription** with Amazon Transcribe
- **Entity extraction** (people, brands, objects) using Amazon Nova
- **Text embeddings** for semantic search via Cohere
- **Smart thumbnails** generated with FFmpeg

**🔧 Robust Architecture**
- **100% AWS-native** - No external dependencies or API keys required
- **Cross-region support** - Automatic handling of model availability (us-east-1 and us-west-2)
- **Serverless infrastructure** - Step Functions, Lambda, OpenSearch
- **Real-time streaming** responses via WebSocket
- **Secure presigned URLs** for video access
- **Comprehensive error handling** and monitoring

## 🏗️ Architecture Overview

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
       │ TwelveLabs      │              │   Insights      │              │ Serverless      │
       │ (Marengo +      │              └─────────────────┘              │ (Vector + Text) │
       │  Pegasus)       │                       │                       └─────────────────┘
       └─────────────────┘                       ▼                                   ▲   ▲
                              ┌─────────────────┐                          │   │
                              │ Cohere Embed    │──────────────────────────┘   │
                              │ (Semantic Vec.) │                              │
                              └─────────────────┘                              │
                                       │                                       │
                                       ▼                                       │
                              ┌─────────────────┐                              │
                              │ Amazon Nova     │──────────────────────────────┘
                              │ (Entity Extract)│                              
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
                              │ (Claude 3.5v2)  │
                              └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **AWS Account** with permissions for Bedrock, OpenSearch Serverless, Lambda, Step Functions, S3
- **AWS CLI** configured with appropriate credentials
- **Python 3.11+** and **Node.js 16+** installed
- **SAM CLI** installed ([installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- **Amazon Bedrock access** to:
  - TwelveLabs Marengo model (us-east-1)
  - TwelveLabs Pegasus model (us-west-2)
  - Anthropic Claude 3.5 Sonnet v2
  - Amazon Nova Lite
  - Cohere Embed v3
- **S3 deployment bucket** - Create an S3 bucket for SAM deployment artifacts before running deploy.sh

### 1. Deploy AWS Infrastructure

This deployment uses **TwelveLabs models natively through Amazon Bedrock** with automatic cross-region handling:
- **Marengo model** (video embeddings) - available only in `us-east-1`
- **Pegasus model** (video understanding) - available only in `us-west-2`
- **Automatic cross-region replication** - Videos are automatically copied between regions as needed

**Prerequisites:**
- Create S3 bucket in `us-west-2` manually (CloudFormation limitation)
- Get your IAM ARN for OpenSearch access

```bash
# Clone repository
git clone <repository-url>
cd intelligent-video-search-ai-agent-twelve-labs-via-bedrock

# Create deployment bucket for SAM artifacts (one-time setup)
aws s3 mb s3://my-sam-deployment-bucket-$(date +%s) --region us-east-1

# REQUIRED: Create S3 bucket in us-west-2 for Pegasus processing
aws s3 mb s3://my-videos-pegasus-bucket --region us-west-2

# Get your IAM ARN (REQUIRED for OpenSearch access)
aws sts get-caller-identity --query 'Arn' --output text

# Deploy using the deployment script
# IMPORTANT: 
# -b: Primary video bucket (will be CREATED in us-east-1)
# -d: Deployment bucket (MUST already exist) - stores CloudFormation artifacts
# -w: us-west-2 video bucket (MUST already exist) - for Pegasus processing
# -p: Your IAM user/role ARN (REQUIRED) - grants OpenSearch access
# --create-index: Create OpenSearch index automatically
./deploy.sh -b primary-video-bucket -d deployment-bucket -w pegasus-video-bucket -p your-iam-arn --create-index

# Example:
./deploy.sh -b video-ue1-bucket -d videos-deployment-ue1 -w videos-pegasus-uw2 -p arn:aws:iam::123456789012:user/admin --create-index

# Note outputs: OpenSearch endpoint, State Machine ARN, both S3 bucket names
```

**⚠️ CRITICAL: If you don't provide the `-p` parameter with your IAM ARN, OpenSearch index creation will fail with a 403 authorization error.**

### 2. Set Up Environment Variables

Copy and configure the `.env.example` file:

```bash
cp .env.example .env
```

Then configure the `.env` file with your deployment outputs:

```bash
# ======================
# AWS Configuration
# ======================
AWS_REGION=us-east-1
PRIMARY_REGION=us-east-1  # For Marengo model and main resources
PEGASUS_REGION=us-west-2  # For Pegasus model

# ======================
# OpenSearch Configuration
# ======================
OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
INDEX_NAME=video-insights-rag

# ======================
# S3 Buckets
# ======================
VIDEO_BUCKET=your-video-bucket-east      # Primary bucket from -b parameter
S3_BUCKET=your-video-bucket-east         # Alias for VIDEO_BUCKET
VIDEO_BUCKET_WEST=your-video-bucket-west # Secondary bucket from -w parameter

# ======================
# Bedrock Models Configuration
# ======================
# TwelveLabs models via Bedrock (no API key required!)
MARENGO_MODEL_ID=twelvelabs.marengo-embed-2-7-v1:0  # Video embeddings
PEGASUS_MODEL_ID=us.twelvelabs.pegasus-1-2-v1:0     # Video understanding

# Text and entity extraction models
COHERE_MODEL_ID=cohere.embed-english-v3    # Text embeddings
NOVA_MODEL_ID=amazon.nova-lite-v1:0        # Entity extraction
NOVA_MAX_CHARS=350000

# AI Agent model
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
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

**💡 Key Advantage**: Unlike the SDK version, this Bedrock-native implementation requires **no external API keys** - authentication is handled through your AWS credentials!

### 3. Start All Services

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

### 4. Test the System

```bash
# Upload a test video (use the primary bucket name from -b parameter)
aws s3 cp test-video.mp4 s3://your-primary-bucket-name/videos/

# The system will automatically:
# 1. Process with Marengo (us-east-1) for visual embeddings
# 2. Copy to us-west-2 bucket for Pegasus processing
# 3. Extract comprehensive insights using both models
# 4. Generate transcription with Amazon Transcribe
# 5. Extract entities with Amazon Nova
# 6. Index everything in OpenSearch

# Access the UI
open http://localhost:3000

# Try searches like:
# - "Find videos with people laughing"
# - "Show me tutorial content"  
# - "What videos mention Python?"
# - Upload a video to find similar content
```

## 🔧 Enhanced Features

### Native Amazon Bedrock Integration
The system now uses TwelveLabs models directly through Amazon Bedrock:

- **No API Keys Required**: Authentication through AWS IAM roles
- **Unified Billing**: All AI usage billed through your AWS account
- **Enterprise Support**: Full AWS support and SLAs
- **Cross-Region Handling**: Automatic video replication between regions
- **Async Processing**: Efficient handling of long-running video analysis

### OpenSearch Access Control
The deployment supports adding your IAM user/role to OpenSearch permissions:

- **Use `-p` flag** to grant your IAM principal access to OpenSearch
- **Prevents 403 errors** when running local APIs (video-api, MCP server)
- **Get your ARN**: `aws sts get-caller-identity --query Arn --output text`

### Robust Video Processing Pipeline
The Step Functions workflow now includes:

- **Early Validation**: Checks OpenSearch index exists before processing
- **Error Handling**: Comprehensive error states with detailed logging
- **Progress Tracking**: Real-time status updates during processing
- **Automatic Retries**: Built-in retry logic for transient failures

### Video-to-Video Similarity Search
Upload any video to find similar content using Marengo embeddings:

```python
# The system:
# 1. Uploads your video to S3
# 2. Generates embeddings using Bedrock Marengo
# 3. Searches OpenSearch for similar video embeddings
# 4. Returns ranked results with similarity scores
```

## 🔍 Search Capabilities

### 1. **Conversational AI Search**
Chat naturally with the AI agent powered by AWS Strands SDK and Claude 3.5 Sonnet:
- *"Find videos where people are celebrating"*
- *"Show me all Python programming tutorials"*
- *"What videos feature John from the marketing team?"*

### 2. **Video-to-Video Similarity Search**
Upload any video to find visually similar content using Marengo embeddings:
- Compare visual composition, colors, scenes
- Find different angles of the same event
- Locate similar content types or styles
- Configurable similarity threshold (default: 0.8)

### 3. **Advanced Search Methods**
- **Semantic Search**: Natural language understanding using Cohere embeddings
- **Keyword Search**: Traditional text search across titles, descriptions, transcripts
- **Hybrid Search**: Combines semantic and keyword for best results
- **Entity Search**: Find specific people, brands, objects extracted by Nova

### 4. **Smart Filtering**
- Sentiment analysis (positive, negative, neutral content)
- Temporal searches (date ranges, recent content)
- Content categorization via Pegasus insights
- Speaker/person identification with timestamps

## 📋 Detailed Setup

### Environment Configuration

The main `.env.example` file contains all required variables with detailed descriptions.

### AWS Permissions Required

Your AWS user/role needs access to:
- **Amazon Bedrock**: 
  - TwelveLabs Marengo (us-east-1)
  - TwelveLabs Pegasus (us-west-2)
  - Claude 3.5 Sonnet v2
  - Cohere Embed v3
  - Amazon Nova Lite
- **Amazon OpenSearch Serverless**: Collection creation, read/write access
- **AWS Lambda**: Function creation and execution
- **AWS Step Functions**: State machine creation and execution
- **Amazon S3**: Bucket access in both regions
- **Amazon EventBridge**: Rule creation for S3 events
- **Amazon Transcribe**: Video transcription services

### Video Requirements

- **Formats**: Your video files must be encoded in the video and audio formats listed on the [FFmpeg Formats Documentation](https://ffmpeg.org/ffmpeg-formats.html)
- **Size**: Up to 2GB per video
- **Resolution**: Must be at least 360x360 and must not exceed 3840x2160
- **Duration**: 
  - Marengo (Embeddings): 4 seconds to 2 hours (7,200s)
  - Pegasus (Understanding): 4 seconds to 60 minutes (3,600s)
  - Future release will support 2 hours for Pegasus

## 🧪 Testing & Validation

### Automated Test Suite

```bash
# Test all agent endpoints and functionality
cd agent/
python 2-test_agent.py
```

The test suite validates:
- ✅ All API endpoints responding correctly
- ✅ MCP server connectivity and search functions
- ✅ WebSocket streaming for real-time responses
- ✅ Session management and context tracking
- ✅ Bedrock model integrations
- ✅ Cross-region video processing

### Manual Testing Workflow

1. **Upload Test Videos**: Use diverse content types (tutorials, personal videos, presentations)
2. **Monitor Processing**: Check Step Functions console for processing status
3. **Test Search Variety**: Try different search methods and query types
4. **Validate Results**: Ensure embeddings and insights are properly indexed
5. **Test Video Upload Search**: Upload new videos to find similar existing content

## 💰 Cost Considerations

### AWS Usage Charges
- **Amazon Bedrock**:
  - TwelveLabs Marengo: ~$0.00024 per second of video
  - TwelveLabs Pegasus: ~$0.0008 per second of video
  - Claude 3.5 Sonnet: $3/$15 per million tokens (input/output)
  - Cohere Embed: $0.10 per million tokens
  - Nova Lite: $0.30/$0.60 per million tokens (input/output)
- **Amazon OpenSearch Serverless**: ~$100+/month minimum (main cost driver)
- **AWS Lambda**: Pay per execution, typically $1-10/month
- **Amazon S3**: Storage costs in both regions
- **AWS Step Functions**: Pay per state transition

### Cost Optimization Tips
- **Delete OpenSearch collection** when not in use (biggest cost saver)
- Implement video compression before upload
- Use lifecycle policies to archive old videos
- Monitor Bedrock usage via CloudWatch
- Consider processing only video segments instead of full videos

## 🚨 Important Disclaimers

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

## 🧹 Cleanup & Cost Management

### Complete Resource Cleanup
```bash
# Empty and delete S3 buckets (both regions)
aws s3 rm s3://your-video-bucket-east --recursive
aws s3 rb s3://your-video-bucket-east
aws s3 rm s3://your-video-bucket-west --recursive
aws s3 rb s3://your-video-bucket-west

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

## 📚 Project Structure

```
intelligent-video-search-ai-agent/
├── 📁 MCP/                      # Model Context Protocol server
├── 📁 agent/                    # AI agent (Strands SDK + Claude)
├── 📁 frontend/                 # React web interface
├── 📁 video-api/                # Video metadata API service
├── 📁 lambdas/                  # AWS Lambda functions
│   ├── InitiateVideoProcessing/ # Cross-region video setup
│   └── ExtractInsightsFunction/ # Bedrock model orchestration
├── 📁 data_ingestion/           # OpenSearch index setup
├── 📁 data/                     # Sample datasets
├── 📄 infrastructure.yaml       # CloudFormation template
├── 📄 .env.example             # Environment configuration template
└── 📄 README.md                # This file
```

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.

<div class='source-links'>
  <h3>View Source</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/experiments/intelligent-video-search-ai-agent-twelve-labs-via-bedrock' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
