---
title: "Video Keeper - AI-Powered Video Library with Multimodal Agentic Search via TwelveLabs API"
date: 2026-02-18
description: "Transform any video collection into an intelligent, searchable library using multi-modal AI and agentic conversation. This solution leverages Strands SDK (Agentic framework), Amazon Nova, Anthropic Claude, Twelve Labs models and Amazon Transcribe to retrieve rich insights from videos. This is a generic video search solution which works with any type of videos.

<img src="./images/UI.jpg" alt="Webserver UI" width="800" />"
layout: experiment
difficulty: medium
source_folder: "experiments/intelligent-video-search-ai-agent"

tags:
  - ai-agents
  - video-to-video-search
  - bedrock
  - python
  - demo
  - strands
  - mcp
technologies:
  - Python 3.11+
  - AWS SDK (boto3)
  - Amazon Bedrock
  - Amazon Nova
  - Amazon OpenSearch Serverless
  - AWS Step Functions
  - Strands Agents SDK
  - Model Context Protocol (MCP)
  - FastAPI
  - React
  - Tailwind CSS
  - TwelveLabs
---

# Video Keeper - AI-Powered Video Library with Multimodal Agentic Search via TwelveLabs API

## Overview

Transform any video collection into an intelligent, searchable library using multi-modal AI and agentic conversation. This solution leverages Strands SDK (Agentic framework), Amazon Nova, Anthropic Claude, Twelve Labs models and Amazon Transcribe to retrieve rich insights from videos. This is a generic video search solution which works with any type of videos.

<img src="./images/UI.jpg" alt="Webserver UI" width="800" />

## Tags

- ai-agents
- video-to-video-search
- bedrock
- python
- demo
- strands
- mcp

## Technologies

- Python 3.11+
- AWS SDK (boto3)
- Amazon Bedrock
- Amazon Nova
- Amazon OpenSearch Serverless
- AWS Step Functions
- Strands Agents SDK
- Model Context Protocol (MCP)
- FastAPI
- React
- Tailwind CSS
- TwelveLabs

## Difficulty

Medium

## 🎯 What is Video Keeper?

Video Keeper is an **agentic AI system** that automatically analyzes, indexes, and makes any video collection searchable through natural conversation. Whether you have training videos, personal memories, gaming recordings, educational content, or professional documentation, Video Keeper creates an intelligent search experience powered by AWS and advanced AI models.

### 🚀 Key Capabilities

**🎬 Universal Video Support**
- Personal memories, family videos, vacation recordings
- Educational content, lectures, tutorials, how-to guides  
- Gaming highlights, streams, gameplay recordings
- Professional content, meetings, presentations, training materials
- Entertainment videos, shows, documentaries

**🔍 Advanced Search Methods**
- **Conversational AI Search** - Chat naturally about your videos using AWS Strands SDK
- **Video-to-Video Similarity** - Upload a video to find visually similar content
- **Semantic Search** - "Find happy family moments" or "Show me Python tutorials"
- **Entity Search** - Find videos featuring specific people, brands, or objects
- **Keyword Search** - Traditional text-based search across all metadata

**🧠 Multi-Modal AI Analysis**
- Visual content understanding via Twelve Labs Marengo
- Speech-to-text transcription with Amazon Transcribe
- Entity extraction (people, brands, objects) using Amazon Nova
- Sentiment analysis and content insights via Twelve Labs Pegasus
- Smart thumbnails generated with FFmpeg

**🔧 Robust Architecture**
- Serverless AWS infrastructure (Step Functions, Lambda, OpenSearch)
- Real-time streaming responses via WebSocket
- Secure presigned URLs for video access
- Comprehensive error handling and monitoring

## 🏗️ Architecture Overview

<img src="./images/architecture.png" alt="Architecture" width="800" />

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
       │ Twelve Labs     │◀────────────▶│ Lambda: Extract │─────────────▶│ OpenSearch      │
       │ (Marengo +      │              │   Insights      │              │ Serverless      │
       │  Pegasus)       │              └─────────────────┘              │ (Vector + Text) │
       └─────────────────┘                       │                       └─────────────────┘
                                       ▼                                   ▲   ▲
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
       │                 │              │ (Port 8080)     │              │                 │
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
- **Twelve Labs API key** ([subscribe and test TwelveLab models using their daily free quota](https://twelvelabs.io))
- **S3 deployment bucket** - Create an S3 bucket for SAM deployment artifacts before running deploy.sh

### 1. Deploy AWS Infrastructure

```bash
# Clone repository
git clone <repository-url>
cd intelligent-video-search-ai-agent

# Create deployment bucket for SAM artifacts (one-time setup)
aws s3 mb s3://my-sam-deployment-bucket-$(date +%s)

# Deploy using the deployment script
# IMPORTANT: 
# -b: Deployment bucket (MUST already exist) - stores CloudFormation artifacts
# -d: Data bucket name (will be CREATED) - stores your videos
# -a: Your Twelve Labs API key - SAM will store your key on AWS Secrets-Manager (encrypted)
# -p: Your IAM user/role ARN - grants OpenSearch access for local development
# --create-index: Create Opensearch index using data_ingestion/1-create-opensearch-index.py script.
./deploy.sh -b existing-deployment-bucket -d new-video-data-bucket -a your-twelve-labs-api-key -p your-iam-arn --create-index

# Example:
# ./deploy.sh -b my-sam-deployment-bucket-1736281200 -d my-unique-video-bucket-name -a tlk_XXXXXXXXXXXXXX -p "$(aws sts get-caller-identity --query Arn --output text)" --create-index

# Note outputs: OpenSearch endpoint, S3 bucket names
```

### (Optional) 2. Configure Twelve Labs API Key
This step is only required if you did not provide your Twelve Labs API key with the deploy.sh script (-a)
```bash
# Store Twelve Labs API key in AWS Secrets Manager
aws secretsmanager create-secret \
  --name twelve-labs-api-key \
  --secret-string '{"api_key":"your_twelve_labs_api_key_here"}'
```

### 3. Set Up Environment Variables

Copy and configure environment files for each component:

```bash
# Copy environment files in each directory
cp MCP/.env.example MCP/.env
cp agent/.env.example agent/.env
cp video-api/.env.example video-api/.env
```

Then configure the main `.env` file:

```bash
# Core AWS Configuration
AWS_REGION=us-east-1
OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
INDEX_NAME=video-insights-rag

# Twelve Labs Configuration  
TWELVE_LABS_API_KEY_SECRET=twelve-labs-api-key
# Note: TWELVE_LABS_INDEX_ID is automatically managed by the system
# The video processing pipeline creates the index and stores the ID in AWS Secrets Manager

# AI Models
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
COHERE_MODEL_ID=cohere.embed-english-v3
NOVA_MODEL_ID=amazon.nova-lite-v1:0

# Service Ports
MCP_PORT=8008
API_PORT=8080
VIDEO_API_PORT=8091
```

**Important**: Edit each component's `.env` file with your specific AWS endpoints. The Twelve Labs index ID is now automatically managed - you only need to configure the API key and OpenSearch endpoint. Check all env files for more details about the required variables.

### 4. Start All Services

**Start services in order (MCP Server must be running before AI Agent):**

**Terminal 1 - MCP Server:**
```bash
pip install -r requirements.txt
cd MCP/
python 1-video-search-mcp.py
```
Note: The requirements.txt above contains the requirements for the Agent and MCP server.

**Terminal 2 - AI Agent:**
```bash
cd agent/
python 1-ai-agent-video-search-strands-sdk.py
```

**Terminal 3 - Video API:**
```bash
cd video-api/
pip install -r requirements.txt
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
# Upload a test video (use the data bucket name from -d parameter)
aws s3 cp test-video.mp4 s3://your-data-bucket-name/videos/

# Access the UI
open http://localhost:3000

# Try searches like:
# - "Find videos with people laughing"
# - "Show me tutorial content"  
# - "What videos mention Python?"
```

## 🔧 Enhanced Features

### OpenSearch Access Control
The deployment now supports adding your IAM user/role to OpenSearch permissions for local development:

- **Use `-p` flag** to grant your IAM principal access to OpenSearch
- **Prevents 403 errors** when running local APIs (video-api, MCP server)
- **Get your ARN**: `aws sts get-caller-identity --query Arn --output text`

### Early Validation
Video processing now includes early validation:

- **OpenSearch index check**: Verifies index exists before using Twelve Labs API
- **Prevents wasted API calls**: Stops processing early if infrastructure isn't ready
- **Clear error messages**: Helpful debugging information for deployment issues

### Automatic Index Management
The system now handles Twelve Labs index creation and management automatically:

- **Auto-Creation**: First video upload automatically creates the Twelve Labs index
- **Secure Storage**: Index ID is stored in AWS Secrets Manager for sharing between components
- **Zero Configuration**: No manual index ID management required
- **Automatic Sync**: All components (MCP server, Lambda functions) automatically retrieve the correct index ID


#### Option B: Use Sample Dataset
If you need sample videos for testing, use the provided dataset downloader:

```bash
# Navigate to data directory
cd data/

# Install requirements and authenticate with HuggingFace
pip install huggingface_hub
huggingface-cli login  # Enter your HF token

# Download sample videos (requires dataset access approval)
python download.py
```

**Note**: The sample dataset (`HuggingFaceFV/finevideo`) requires:
- HuggingFace account and access token
- Dataset access approval from the source
- Sufficient storage space (downloads 25 videos by default)

See `data/README.md` for complete licensing and usage information.

## 🔍 Search Capabilities

### 1. **Conversational AI Search**
Chat naturally with the AI agent powered by AWS Strands SDK and Claude 3.5 Sonnet:
- *"Find videos where people are celebrating"*
- *"Show me all Python programming tutorials"*
- *"What videos are featuring Nick?"*

### 2. **Video-to-Video Similarity Search**
Upload any video to find visually similar content in your library (`MCP/.env` defines the required similarity score):
- Compare visual composition, colors, scenes
- Find different angles of the same event
- Locate similar content types or styles

### 3. **Advanced Search Methods**
- **Semantic Search**: Natural language understanding using Cohere embeddings
- **Keyword Search**: Traditional text search across titles, descriptions, transcripts
- **Hybrid Search**: Combines semantic and keyword for best results
- **Entity Search**: Find specific people, brands, objects, or locations

### 4. **Smart Filtering**
- Sentiment analysis (positive, negative, neutral content)
- Temporal searches (date ranges, recent content)
- Content type classification
- Speaker/person identification with timestamps

## 📋 Detailed Setup

### Environment Configuration

Each component has its own `.env.example` file with required variables:

- **Main `.env.example`** - Core AWS and service configuration
- **`MCP/.env.example`** - OpenSearch and Twelve Labs settings
- **`agent/.env.example`** - AI agent and Bedrock configuration  
- **`frontend/.env.example`** - React app API endpoints

### AWS Permissions Required

Your AWS user/role needs access to:
- **Amazon Bedrock**: Claude 3.5 Sonnet, Cohere Embed, Nova Lite models
- **Amazon OpenSearch Serverless**: Collection creation, read/write access
- **AWS Lambda**: Function creation and execution
- **AWS Step Functions**: State machine creation and execution
- **Amazon S3**: Bucket access for video storage
- **Amazon EventBridge**: Rule creation for S3 events
- **AWS Secrets Manager**: Secret creation and access
- **Amazon Transcribe**: Video transcription services

### Video Requirements

- **Formats**: Your video files must be encoded in the video and audio formats listed on the [FFmpeg Formats Documentation](https://ffmpeg.org/ffmpeg-formats.html)
- **Size**: Up to 2GB per video
- **Resolution**: Must be at least 360x360 and must not exceed 3840x2160.
- **Duration**: For Twelve Labs Marengo (Embedding), it must be between 4 seconds and 2 hours (7,200s). For Pegasus, it must be between 4 seconds and 60 minutes (3600s). In a future release, the maximum duration for Pegasus will be 2 hours (7,200 seconds).

## 🧪 Testing & Validation

### Automated Test Suite

This script helps you to evaluate and troubleshoot agent issues.
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
- ✅ Error handling for edge cases

### Manual Testing Workflow

1. **Upload Test Videos**: Use diverse content types (tutorials, personal videos, presentations)
2. **Test Search Variety**: Try different search methods and query types
3. **Validate Results**: Check that returned videos match search intent
4. **Test Video Upload Search**: Upload new videos to find similar existing content

## 💰 Cost Considerations

### AWS Usage Charges
- **Amazon OpenSearch Serverless**: Major costs of this solution will be here, **make sure you delete your Collection if you are not using to avoid charges ($100+/month)**
- **AWS Lambda**: Pay per execution, typically $1-10/month for moderate use
- **Amazon Bedrock**: Pay per API call, varies by model and usage
- **Amazn S3**: Storage costs based on video collection size
- **AWS Step Functions**: Pay per state transition, minimal cost

### Third-Party Services
- **Twelve Labs**: Usage-based pricing for video analysis
- Free tier available, then pay per minute of video processed

### Cost Optimization Tips
- Implement video compression before upload to reduce storage costs
- Monitor Bedrock usage via Cost Explorer and implement caching for repeated queries

## 🚨 Important Disclaimers

### Educational Purpose
This project is designed for **educational and demonstration purposes**. In order to improve the security of this application, you may want to implement:
- Implement proper authentication and authorization
- Implement API rate control
- APIs are currently running as python scripts to make it simple for you to test, in production you need a proper hosting for the APIs
- Add data encryption at rest and in transit
- Set up comprehensive monitoring and alerting
- Review and implement security best practices
- Consider compliance requirements (GDPR, CCPA, etc.)

### Data Privacy
- Videos and metadata are stored in your AWS account
- Twelve Labs processes videos according to their privacy policy
- Implement appropriate data retention and deletion policies
- Consider geographic data residency requirements

### Scalability Considerations
- Current configuration suitable for personal to small team use
- For large-scale deployment, review OpenSearch sizing, Bedrock quotas and Lambda limits
- Consider implementing video preprocessing pipelines for very large collections

## 🧹 Cleanup & Cost Management

### Complete Resource Cleanup
```bash
# Empty and delete S3 buckets if required (you may need to do this before deleting the stack)
aws s3 rm s3://your-video-bucket --recursive
aws s3 rb s3://your-video-bucket

# Delete CloudFormation stack (removes most resources)
aws cloudformation delete-stack --stack-name YOUR_STACK_NAME

# (Optional) Delete OpenSearch collection manually if required
aws opensearchserverless delete-collection --id YOUR_COLLECTION_NAME

# (Optional) Delete secrets
aws secretsmanager delete-secret --secret-id twelve-labs-api-key --force-delete-without-recovery
```

### Cost Monitoring
- Monitor your [AWS Billing Dashboard](https://console.aws.amazon.com/billing/)
- Set up billing alerts for unexpected charges
- Review OpenSearch Serverless usage regularly (primary cost driver)

## 📚 Project Structure

```
intelligent-video-search-ai-agent/
├── 📁 MCP/                      # Model Context Protocol server
├── 📁 agent/                    # AI agent (Strands SDK + Claude)
├── 📁 frontend/                 # React web interface
├── 📁 video-api/                # Video metadata API service
├── 📁 lambdas/                  # AWS Lambda functions
├── 📁 data_ingestion/           # OpenSearch index setup
├── 📁 data/                     # Sample datasets
├── 📄 infrastructure.yaml       # CloudFormation template
├── 📄 step-functions-definition.json # Step Functions workflow
└── 📄 .env.example             # Environment configuration template
```

Each directory contains its own README.md with component-specific setup instructions.

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.


<div class='source-links'>
  <h3>View Source</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/experiments/intelligent-video-search-ai-agent' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
