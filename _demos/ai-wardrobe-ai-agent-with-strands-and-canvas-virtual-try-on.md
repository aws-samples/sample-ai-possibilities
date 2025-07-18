---
title: "AI Unicorn Wardrobe: AI Agent with Strands SDK and Amazon Nova Canvas Virtual Try On"
date: 2025-07-18
description: "A sophisticated AI-powered virtual wardrobe and fashion assistant that combines cutting-edge Amazon Bedrock AI capabilities with an intuitive React interface. Users can build a digital wardrobe, receive personalized outfit recommendations, and visualize complete looks using advanced Amazon Nova Canvas virtual try-on technology."
layout: demo
difficulty: advanced
source_folder: "demos/ai-wardrobe-ai-agent-with-strands-and-canvas-virtual-try-on"

tags:
  - bedrock
  - claude-3.5-sonnet
  - nova-canvas
  - python
  - react
  - typescript
  - strands-sdk
  - mcp
  - virtual-try-on
  - fashion-tech
  - multi-modal-ai
  - computer-vision
  - conversational-ai
  - real-time-chat
  - image-generation
  - aws-ai-services
  - fastapi
  - websockets
  - tailwindcss
  - framer-motion
---

# AI Unicorn Wardrobe: AI Agent with Strands SDK and Amazon Nova Canvas Virtual Try On

A sophisticated AI-powered virtual wardrobe and fashion assistant that combines cutting-edge Amazon Bedrock AI capabilities with an intuitive React interface. Users can build a digital wardrobe, receive personalized outfit recommendations, and visualize complete looks using advanced Amazon Nova Canvas virtual try-on technology.

## Overview

This comprehensive demo showcases the integration of multiple cutting-edge AWS AI services to create a magical fashion assistant powered by unicorn technology. The application combines sophisticated image analysis, conversational AI, and virtual try-on technology to deliver a complete fashion management experience with a whimsical twist.

![AI Unicorn Wardrobe UI](images/ui.jpg)

### Key Capabilities

**🔍 Intelligent Wardrobe Management**
- Upload clothing photos with automatic AI categorization and attribute extraction
- Claude Vision analyzes 20+ clothing attributes (color, material, pattern, formality, seasonality)
- Smart filtering and search across your digital wardrobe
- Professional photo guidance for optimal virtual try-on results

**👗 Advanced Virtual Try-On**
- Nova Canvas integration for realistic garment visualization
- Multi-item outfit composition with layered clothing application
- Advanced styling options (sleeve styles, tucking preferences, outer layers)
- Support for complete outfit try-ons with multiple garments

**🤖 Conversational Fashion Assistant**
- Real-time chat with AI stylist using Claude 3.5 v2 Sonnet
- Context-aware outfit recommendations based on occasion, weather, and personal style
- Streaming responses with visual thinking indicators
- Maintains conversation history and user preferences

**📱 Modern User Experience**
- Responsive React interface with professional design system
- Smooth animations and interactive components using Framer Motion
- Adaptive grid layouts with builder mode for outfit creation
- Real-time WebSocket communication for instant AI responses

The architecture demonstrates how to build sophisticated multi-modal AI applications that seamlessly combine text understanding, computer vision, and generative AI in a production-ready interface.

## Tags

- bedrock
- claude-3.5-sonnet
- nova-canvas
- python
- react
- typescript
- strands-sdk
- mcp
- virtual-try-on
- fashion-tech
- multi-modal-ai
- computer-vision
- conversational-ai
- real-time-chat
- image-generation
- aws-ai-services
- fastapi
- websockets
- tailwindcss
- framer-motion

## Technologies

### Backend Stack
- **Python 3.11+** - Core runtime environment
- **FastAPI** - High-performance web framework with automatic OpenAPI documentation
- **WebSockets** - Real-time bidirectional communication for chat interface
- **Strands Agents SDK** - Advanced conversational AI agent framework
- **Model Context Protocol (MCP)** - Tool integration and function calling
- **AWS SDK (boto3)** - Native AWS service integration

### AI & Machine Learning
- **Amazon Bedrock Claude 3.5 Sonnet** - Advanced language understanding and generation
- **Amazon Nova Canvas** - Cutting-edge image generation and virtual try-on
- **Claude Vision** - Intelligent image analysis and clothing attribute extraction
- **Multi-modal AI Pipeline** - Seamless text and image processing

### Frontend Stack
- **React 19** with **TypeScript** - Modern type-safe UI framework
- **Tailwind CSS** - Utility-first styling with custom design system
- **Framer Motion** - Professional animations and micro-interactions
- **Lucide React** - Beautiful, customizable icon system
- **React Dropzone** - Drag-and-drop file upload with validation
- **React Hot Toast** - Elegant notification system
- **React Markdown** - Rich text rendering for AI responses

### Infrastructure & Data
- **Amazon DynamoDB** - NoSQL database with global secondary indexes
- **Amazon S3** - Scalable object storage with presigned URLs
- **AWS CloudFormation** - Infrastructure as Code deployment
- **IAM** - Fine-grained security and access control

## Difficulty

Advanced

## Prerequisites

- Python 3.11+
- AWS Account with appropriate permissions for:
  - Amazon Bedrock (Claude 3.5 Sonnet and Nova Canvas models)
  - DynamoDB
  - S3
  - CloudFormation
  - IAM
- AWS CLI configured with credentials
- Node.js 18+ (for frontend development)

## Setup

### 1. Deploy AWS Infrastructure

```bash
# Clone the repository
git clone https://github.com/aws-samples/sample-ai-possibilities.git
cd sample-ai-possibilities/demos/ai-wardrobe-ai-agent-with-strands-and-canvas-virtual-try-on

# Deploy the CloudFormation stack
aws cloudformation create-stack \
  --stack-name ai-unicorn-wardrobe \
  --template-body file://infrastructure.yaml \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for stack creation to complete (typically 2-3 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name ai-unicorn-wardrobe

# Get the outputs (save these for environment configuration)
aws cloudformation describe-stacks \
  --stack-name ai-unicorn-wardrobe \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
```

**Infrastructure Components Created:**
- **S3 Bucket**: `ai-unicorn-wardrobe-images-{account-id}` for storing clothing images and try-on results
- **DynamoDB Tables**: 
  - `ai-unicorn-wardrobe-users` - User profiles and preferences
  - `ai-unicorn-wardrobe-wardrobe-items` - Clothing item metadata with GSI for efficient querying
  - `ai-unicorn-wardrobe-outfits` - Saved outfit configurations and try-on results
- **IAM Roles**: Application role with least-privilege access to required services

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your CloudFormation outputs
vim .env  # or use your preferred editor
```

**Required Environment Variables:**
Due to security reasons it is recommended using IAM Role, however, if you prefer using local keys:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1 

# Resource Names (from CloudFormation outputs)
S3_BUCKET=ai-unicorn-wardrobe-images-{your-account-id}
USERS_TABLE=ai-unicorn-wardrobe-users
WARDROBE_ITEMS_TABLE=ai-unicorn-wardrobe-wardrobe-items
OUTFITS_TABLE=ai-unicorn-wardrobe-outfits

# API Configuration
MCP_SERVER_URL=http://localhost:8000
AGENT_API_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:3000
```

### 3. Install Dependencies and Run

#### Backend Setup
```bash
# Create and activate virtual environment
python --version # Make sure you have installed python 3.11
python -m venv venv # We are assuming your default python version is 3.11
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Verify AWS credentials and Bedrock access
python -c "import boto3; print('AWS credentials configured:', boto3.Session().get_credentials() is not None)"
```

#### Start Services (3 Terminal Windows)

**Terminal 1: MCP Server**
```bash
source venv/bin/activate
python MCP/wardrobe_mcp.py
# Server starts on http://localhost:8000 - if you need, you can change the port on .env
# Provides: User management, wardrobe operations, virtual try-on tools
# If you are using local credentials, make sure they are loaded here.
```

**Terminal 2: Strands Agent API**
```bash
source venv/bin/activate
python agent/wardrobe_agent_api.py
# Server starts on http://localhost:8080
# Provides: WebSocket chat, conversational AI, outfit recommendations
# If you are using local credentials, make sure they are loaded here.
```

**Terminal 3: React Frontend**
```bash
cd frontend/ai-wardrobe-ui
npm install  # First time only
npm start
# Frontend available at http://localhost:3000
```

**Service Endpoints:**
- **Frontend UI**: http://localhost:3000 (React development server)
- **Agent API**: http://localhost:8080 (FastAPI with WebSocket support)
- **WebSocket**: ws://localhost:8080/ws/{session_id} (Real-time chat)
- **MCP Server**: http://localhost:8000 (Tool integration server)
- **API Docs**: http://localhost:8080/docs (Interactive OpenAPI documentation)

### Cleanup Instructions

To delete all resources deployed as part of this solution (make sure you have loaded your credentials and you are using the same region used during the setup):

```bash
# Stop local services
1. Stop all 3 shells.

# Empty S3 bucket (required before CloudFormation deletion) - If you are using a different S3 bucket, update it accordingly
aws s3 rm s3://ai-unicorn-wardrobe-images-$(aws sts get-caller-identity --query Account --output text) --recursive

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name ai-unicorn-wardrobe

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name ai-unicorn-wardrobe

# Verify cleanup
aws cloudformation describe-stacks --stack-name ai-unicorn-wardrobe 2>/dev/null || echo "Stack successfully deleted"
```

**Note**: CloudFormation will fail to delete if the S3 bucket contains objects. The empty bucket command above ensures clean deletion.

## Architecture

```
┌─────────────────┐    WebSocket/HTTP    ┌──────────────────┐    MCP Protocol    ┌─────────────────┐
│   React UI      │◄────────────────────►│  Strands Agent   │◄──────────────────►│   MCP Server    │
│                 │                      │      API         │                    │                 │
│ • Wardrobe Mgmt │                      │ • Chat Interface │                    │ • Tool Functions│
│ • Outfit Builder│                      │ • Streaming AI   │                    │ • AWS Service   │
│ • Virtual Try-On│                      │ • Context Mgmt   │                    │   Integration   │
│ • Real-time Chat│                      │ • WebSocket Hub  │                    │ • State Mgmt    │
└─────────────────┘                      └──────────────────┘                    └─────────────────┘
                                         │                                        │
                                         │ Bedrock API                           │ boto3 SDK
                                         ▼                                        ▼
                               ┌─────────────────────────────────────────────────────────────┐
                               │                    AWS Services                             │
                               │                                                             │
                               │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │
                               │  │   Bedrock   │   │  DynamoDB   │   │       S3        │  │
                               │  │             │   │             │   │                 │  │
                               │  │• Claude 3.5 │   │• Users      │   │• Clothing       │  │
                               │  │  Sonnet     │   │• Wardrobe   │   │  Images         │  │
                               │  │• Nova Canvas│   │  Items      │   │• Try-on Results │  │
                               │  │• Vision     │   │• Outfits    │   │• Profile Photos │  │
                               │  │  Analysis   │   │             │   │                 │  │
                               │  └─────────────┘   └─────────────┘   └─────────────────┘  │
                               └─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Interaction** → React UI captures user actions (chat, upload, outfit building)
2. **Real-time Communication** → WebSocket maintains persistent connection for instant responses
3. **Agent Processing** → Strands Agent interprets requests and manages conversation context
4. **Tool Execution** → MCP Server executes specific functions (wardrobe management, AI analysis)
5. **AI Integration** → Bedrock provides language understanding and image generation
6. **Data Persistence** → DynamoDB stores structured data, S3 handles image assets
7. **Response Delivery** → Results stream back through the same path with visual updates

## Testing

Comprehensive test suite to verify all components:

### Prerequisites
```bash
# Activate virtual environment
source venv/bin/activate
```

### Core Functionality Tests
```bash
# Test AWS Bedrock and Nova Canvas access
python tests/test_nova_canvas.py
# Verifies: Model permissions, image generation, virtual try-on pipeline
```

### Frontend Testing
```bash
cd frontend/ai-wardrobe-ui

# Run React component tests
npm test

# Run with coverage
npm test -- --coverage
```

## Usage Example

### Frontend Usage

1. **Access the Application**
   - Open http://localhost:3000
   - Create user profile with photo upload
   - Upload clothing items with automatic AI categorization

2. **Build Outfits**
   - Click "Outfit Builder" to enter builder mode
   - Select items from wardrobe to create complete looks
   - Preview combinations with virtual try-on

3. **Chat with AI Stylist**
   - Use the chat interface to ask for styling advice
   - Get personalized recommendations based on occasion, weather, style preferences
   - Receive real-time outfit suggestions with reasoning

4. **Browse Outfit Archive**
   - View previously created virtual try-on results
   - Save favorite outfit combinations
   - Re-create successful looks

## Advanced Features

### AI-Powered Clothing Analysis
- **Automatic Categorization**: Claude Vision identifies clothing type, material, color, and style
- **Attribute Extraction**: 20+ attributes including formality level, seasonality, versatility rating
- **Quality Assessment**: Image quality validation with improvement suggestions
- **Style Profiling**: Learns user preferences from wardrobe and interactions

### Multi-Item Virtual Try-On
- **Layered Application**: Applies clothing items in realistic order (base → outer layers)
- **Style Customization**: Advanced options for sleeve styles, tucking, fit preferences
- **Conflict Detection**: Prevents incompatible combinations (e.g., dress + separates)
- **Seasonal Adaptation**: Adjusts recommendations based on weather and season

### Conversational Intelligence
- **Context Awareness**: Maintains conversation history and user preferences
- **Streaming Responses**: Real-time AI responses with thinking indicators
- **Tool Integration**: Agent can browse wardrobe, create outfits, and run virtual try-ons during conversation
- **Personal Styling**: Provides reasoning for recommendations with style tips

### Professional UI/UX
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Animation System**: Smooth transitions and micro-interactions using Framer Motion
- **Professional Theme**: Modern design system with fashion-industry aesthetics
- **Real-time Updates**: WebSocket integration for instant feedback and updates

## Production Considerations
The code in this repo is not production ready, you may want to apply the following changes if you are handling multiple users.
### Security
- **IAM Roles**: Use least-privilege access principles
- **API Authentication**: Implement OAuth2 or JWT tokens for production
- **Data Encryption**: Enable encryption at rest and in transit
- **Input Validation**: Comprehensive validation for all user inputs

### Scalability
- **DynamoDB Auto-scaling**: Configure read/write capacity based on usage
- **S3 Lifecycle Policies**: Implement intelligent tiering for cost optimization
- **CloudFront CDN**: Add content delivery network for global image serving
- **API Rate Limiting**: Implement throttling to prevent abuse

### Monitoring
- **CloudWatch Metrics**: Monitor API performance and error rates
- **X-Ray Tracing**: Distributed tracing for debugging complex workflows
- **Cost Monitoring**: Set up billing alerts for Bedrock usage
- **Health Checks**: Implement comprehensive service health monitoring

### Compliance
- **Data Privacy**: Implement GDPR/CCPA compliance for user data
- **Image Rights**: Ensure proper handling of user-uploaded content
- **Model Usage**: Review Bedrock acceptable use policies
- **Audit Logging**: Comprehensive logging for security and compliance

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.

## Notes

- **Educational Purpose**: This project demonstrates AI integration patterns and is not production-ready
- **Model Access**: Ensure your AWS account has access to Claude 3.5 Sonnet and Nova Canvas in your region
- **Cost Management**: Monitor usage of Bedrock models and S3 storage - implement cost controls for production
- **Image Quality**: Virtual try-on results depend heavily on input image quality - provide clear guidance to users
- **Regional Availability**: Amazon Nova Canvas and Claude models may not be available in all AWS regions
- **Rate Limits**: Be aware of Amazon Bedrock model rate limits and implement appropriate retry logic



<div class='source-links'>
  <h3>Full Source Code</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/demos/ai-wardrobe-ai-agent-with-strands-and-canvas-virtual-try-on' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
