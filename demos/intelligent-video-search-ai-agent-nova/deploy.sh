#!/bin/bash

# Video Ingestion Pipeline Deployment Script
# This script deploys the complete video processing pipeline with Nova 2 models via Amazon Bedrock and OpenSearch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="video-ingestion-pipeline"
PRIMARY_REGION="us-east-1"  # All Nova 2 models are in us-east-1
REGION="$PRIMARY_REGION"  # Backward compatibility
BUCKET_NAME=""
OPENSEARCH_COLLECTION="video-insights-collection"
DEPLOYMENT_BUCKET=""
ADDITIONAL_PRINCIPALS=""
AUTO_ADD_PRINCIPAL=true  # Auto-add current IAM user to OpenSearch access policy

# Nova 2 Model IDs (all in us-east-1)
NOVA_OMNI_MODEL_ID="global.amazon.nova-2-omni-v1:0"
NOVA_LITE_MODEL_ID="global.amazon.nova-2-lite-v1:0"
NOVA_EMBEDDING_MODEL_ID="amazon.nova-2-multimodal-embeddings-v1:0"
NOVA_EMBEDDING_DIMENSION="3072"

# Function to print colored output
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --stack-name NAME           CloudFormation stack name (default: video-ingestion-pipeline)"
    echo "  -r, --region REGION            AWS region (default: us-east-1 - required for Nova 2)"
    echo "  -b, --bucket-name NAME         S3 bucket name for videos (required)"
    echo "  -d, --deployment-bucket NAME   S3 bucket for CloudFormation artifacts (required)"
    echo "  -o, --opensearch-collection NAME  OpenSearch collection name (default: video-insights-collection)"
    echo "  -p, --principals ARN1,ARN2     Additional IAM principals for OpenSearch access (comma-separated)"
    echo "  --no-auto-principal            Don't auto-add current IAM user to OpenSearch access policy"
    echo "  --embedding-dimension DIM      Nova embedding dimension (default: 3072, options: 256, 384, 1024, 3072)"
    echo "  --create-index                 Create OpenSearch index after deployment"
    echo "  --test                         Run end-to-end test after deployment"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -b my-videos-bucket -d my-deployment-bucket --create-index"
    echo "  $0 -s my-stack -b videos -d deploy --test"
    echo ""
    echo "IMPORTANT: OpenSearch Access"
    echo "  Your current IAM identity is automatically added to the OpenSearch data access"
    echo "  policy so you can run local tools (MCP server, video-api, agent)."
    echo "  Use --no-auto-principal to disable this behavior."
    echo "  Use -p to add additional IAM principals (e.g., other team members)."
    echo ""
    echo "NOTE: All Nova 2 models are available in us-east-1 only."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            PRIMARY_REGION="$2"
            REGION="$2"  # Backward compatibility
            shift 2
            ;;
        -b|--bucket-name)
            BUCKET_NAME="$2"
            shift 2
            ;;
        -d|--deployment-bucket)
            DEPLOYMENT_BUCKET="$2"
            shift 2
            ;;
        -o|--opensearch-collection)
            OPENSEARCH_COLLECTION="$2"
            shift 2
            ;;
        -p|--principals)
            ADDITIONAL_PRINCIPALS="$2"
            shift 2
            ;;
        --embedding-dimension)
            NOVA_EMBEDDING_DIMENSION="$2"
            shift 2
            ;;
        --no-auto-principal)
            AUTO_ADD_PRINCIPAL=false
            shift
            ;;
        --create-index)
            CREATE_INDEX=true
            shift
            ;;
        --test)
            RUN_TEST=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$BUCKET_NAME" ]]; then
    print_message "Error: Video bucket name is required" $RED
    show_usage
    exit 1
fi

if [[ -z "$DEPLOYMENT_BUCKET" ]]; then
    print_message "Error: Deployment bucket name is required" $RED
    show_usage
    exit 1
fi

# Warn if not using us-east-1
if [[ "$PRIMARY_REGION" != "us-east-1" ]]; then
    print_message "WARNING: Nova 2 models are only available in us-east-1" $YELLOW
    print_message "The deployment will use us-east-1 for Bedrock API calls" $YELLOW
fi

# Print configuration
print_message "=== Video Ingestion Pipeline Deployment (Nova 2) ===" $BLUE
echo "Stack name: $STACK_NAME"
echo "Region: $PRIMARY_REGION"
echo "Video bucket: $BUCKET_NAME"
echo "Deployment bucket: $DEPLOYMENT_BUCKET"
echo "OpenSearch collection: $OPENSEARCH_COLLECTION"
echo ""
echo "Nova 2 Models (all in us-east-1):"
echo "  - Nova Omni: $NOVA_OMNI_MODEL_ID (video understanding + transcription)"
echo "  - Nova Lite: $NOVA_LITE_MODEL_ID (NER/entity extraction)"
echo "  - Nova Embeddings: $NOVA_EMBEDDING_MODEL_ID (dimension: $NOVA_EMBEDDING_DIMENSION)"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_message "Error: AWS CLI is not installed" $RED
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    print_message "Error: AWS credentials not configured" $RED
    exit 1
fi

print_message "AWS credentials verified" $GREEN

# Get current IAM identity for OpenSearch access
CURRENT_IAM_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
print_message "Current IAM identity: $CURRENT_IAM_ARN" $BLUE

# Auto-add current IAM principal to OpenSearch access policy
if [[ "$AUTO_ADD_PRINCIPAL" == "true" ]]; then
    # Check if this is a user or role (not assumed-role session)
    if [[ "$CURRENT_IAM_ARN" == *":user/"* ]]; then
        # It's an IAM user - use as-is
        IAM_PRINCIPAL_TO_ADD="$CURRENT_IAM_ARN"
    elif [[ "$CURRENT_IAM_ARN" == *":assumed-role/"* ]]; then
        # It's an assumed role session - extract the role ARN
        # Format: arn:aws:sts::ACCOUNT:assumed-role/ROLE_NAME/SESSION_NAME
        ROLE_NAME=$(echo "$CURRENT_IAM_ARN" | sed 's/.*:assumed-role\/\([^/]*\)\/.*/\1/')
        ACCOUNT_ID=$(echo "$CURRENT_IAM_ARN" | sed 's/.*::\([0-9]*\):.*/\1/')
        IAM_PRINCIPAL_TO_ADD="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
        print_message "Detected assumed role, using role ARN: $IAM_PRINCIPAL_TO_ADD" $YELLOW
    elif [[ "$CURRENT_IAM_ARN" == *":role/"* ]]; then
        # It's a role - use as-is
        IAM_PRINCIPAL_TO_ADD="$CURRENT_IAM_ARN"
    else
        print_message "Warning: Could not determine IAM principal type from: $CURRENT_IAM_ARN" $YELLOW
        IAM_PRINCIPAL_TO_ADD=""
    fi

    # Add to ADDITIONAL_PRINCIPALS if not already present
    if [[ -n "$IAM_PRINCIPAL_TO_ADD" ]]; then
        if [[ -z "$ADDITIONAL_PRINCIPALS" ]]; then
            ADDITIONAL_PRINCIPALS="$IAM_PRINCIPAL_TO_ADD"
            print_message "Auto-adding your IAM identity to OpenSearch access policy" $GREEN
        elif [[ "$ADDITIONAL_PRINCIPALS" != *"$IAM_PRINCIPAL_TO_ADD"* ]]; then
            ADDITIONAL_PRINCIPALS="$ADDITIONAL_PRINCIPALS,$IAM_PRINCIPAL_TO_ADD"
            print_message "Adding your IAM identity to OpenSearch access policy" $GREEN
        else
            print_message "Your IAM identity is already in the access policy" $GREEN
        fi
    fi
else
    print_message "Skipping auto-add of IAM principal (--no-auto-principal specified)" $YELLOW
fi

# Display OpenSearch access policy principals and confirm
echo ""
print_message "=== OpenSearch Data Access Policy ===" $YELLOW
echo "The following IAM principals will have access to OpenSearch Serverless:"
echo "  - Lambda execution role (automatic, created by CloudFormation)"
if [[ -n "$ADDITIONAL_PRINCIPALS" ]]; then
    IFS=',' read -ra PRINCIPAL_ARRAY <<< "$ADDITIONAL_PRINCIPALS"
    for principal in "${PRINCIPAL_ARRAY[@]}"; do
        echo "  - $principal"
    done
fi
echo ""
print_message "IMPORTANT: To run local tools (MCP server, video-api, agent, UI)," $YELLOW
print_message "your IAM identity MUST be in this list or you will get 403 Forbidden errors." $YELLOW
echo ""

# Prompt for confirmation
read -p "Is this correct? (Y/n/add): " CONFIRM_RESPONSE
CONFIRM_RESPONSE=${CONFIRM_RESPONSE:-Y}  # Default to Yes

if [[ "$CONFIRM_RESPONSE" =~ ^[Nn] ]]; then
    echo ""
    print_message "Deployment cancelled." $RED
    echo "To specify a different IAM principal, use the -p flag:"
    echo "  ./deploy.sh -b $BUCKET_NAME -d $DEPLOYMENT_BUCKET -p \"arn:aws:iam::ACCOUNT:user/USERNAME\""
    exit 1
elif [[ "$CONFIRM_RESPONSE" =~ ^[Aa] ]]; then
    echo ""
    read -p "Enter additional IAM ARN(s) to add (comma-separated): " EXTRA_PRINCIPALS
    if [[ -n "$EXTRA_PRINCIPALS" ]]; then
        if [[ -n "$ADDITIONAL_PRINCIPALS" ]]; then
            ADDITIONAL_PRINCIPALS="$ADDITIONAL_PRINCIPALS,$EXTRA_PRINCIPALS"
        else
            ADDITIONAL_PRINCIPALS="$EXTRA_PRINCIPALS"
        fi
        print_message "Added: $EXTRA_PRINCIPALS" $GREEN
    fi
fi
echo ""

# Using Nova 2 models via Amazon Bedrock
print_message "Using Nova 2 models via Amazon Bedrock - no API key required" $GREEN

# Create deployment bucket if it doesn't exist
print_message "Checking deployment bucket..." $YELLOW
if ! aws s3 ls "s3://$DEPLOYMENT_BUCKET" &> /dev/null; then
    print_message "Creating deployment bucket..." $YELLOW
    if [[ "$PRIMARY_REGION" == "us-east-1" ]]; then
        aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$PRIMARY_REGION"
    else
        aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$PRIMARY_REGION" --create-bucket-configuration LocationConstraint="$PRIMARY_REGION"
    fi
fi
print_message "Deployment bucket ready" $GREEN

# Download ffmpeg static binary for Lambda
print_message "Setting up ffmpeg for Lambda..." $YELLOW
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/lambdas/ExtractInsightsFunction/setup-ffmpeg.sh" ]]; then
    bash "$SCRIPT_DIR/lambdas/ExtractInsightsFunction/setup-ffmpeg.sh"
    if [[ $? -ne 0 ]]; then
        print_message "Failed to setup ffmpeg" $RED
        exit 1
    fi
    print_message "ffmpeg ready" $GREEN
else
    print_message "Warning: setup-ffmpeg.sh not found, assuming ffmpeg is pre-installed" $YELLOW
fi

# Build and package SAM application
print_message "Building SAM application..." $YELLOW
sam build --template infrastructure.yaml

print_message "Packaging CloudFormation template..." $YELLOW
sam package \
    --s3-bucket "$DEPLOYMENT_BUCKET" \
    --output-template-file packaged-template.yaml \
    --region "$PRIMARY_REGION"

print_message "Template packaged successfully" $GREEN

# Deploy CloudFormation stack
print_message "Deploying CloudFormation stack..." $YELLOW

# Build parameter overrides for Nova 2 deployment
PARAMS="VideoBucketName=$BUCKET_NAME OpenSearchCollectionName=$OPENSEARCH_COLLECTION"
PARAMS="$PARAMS PrimaryRegion=$PRIMARY_REGION"
PARAMS="$PARAMS NovaOmniModelId=$NOVA_OMNI_MODEL_ID NovaLiteModelId=$NOVA_LITE_MODEL_ID"
PARAMS="$PARAMS NovaEmbeddingModelId=$NOVA_EMBEDDING_MODEL_ID NovaEmbeddingDimension=$NOVA_EMBEDDING_DIMENSION"
if [[ -n "$ADDITIONAL_PRINCIPALS" ]]; then
    PARAMS="$PARAMS AdditionalOpenSearchPrincipals=$ADDITIONAL_PRINCIPALS"
fi

aws cloudformation deploy \
    --template-file packaged-template.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides $PARAMS \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$PRIMARY_REGION" \
    --no-fail-on-empty-changeset

if [[ $? -eq 0 ]]; then
    print_message "Stack deployed successfully" $GREEN
else
    print_message "Stack deployment failed" $RED
    exit 1
fi

# Get stack outputs
print_message "Retrieving stack outputs..." $YELLOW
OPENSEARCH_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$PRIMARY_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`OpenSearchEndpoint`].OutputValue' \
    --output text)

SEARCH_FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$PRIMARY_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`SearchFunctionArn`].OutputValue' \
    --output text)

STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$PRIMARY_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
    --output text)

print_message "Stack outputs retrieved" $GREEN

# Create OpenSearch index if requested
if [[ "$CREATE_INDEX" == "true" ]]; then
    print_message "Creating OpenSearch index..." $YELLOW

    if [[ -f "data_ingestion/1-create-opensearch-index.py" ]]; then
        # Create and activate virtual environment
        print_message "Setting up Python virtual environment..." $YELLOW
        VENV_DIR=".venv-deploy"

        if [[ ! -d "$VENV_DIR" ]]; then
            python3 -m venv "$VENV_DIR"
        fi

        source "$VENV_DIR/bin/activate"

        # Install dependencies in virtual environment
        print_message "Installing dependencies..." $YELLOW
        if command -v uv &> /dev/null; then
            uv pip install opensearch-py boto3
        else
            pip install opensearch-py boto3
        fi

        # Run the index creation script with Nova embedding dimension
        NOVA_EMBEDDING_DIMENSION=$NOVA_EMBEDDING_DIMENSION python data_ingestion/1-create-opensearch-index.py \
            --endpoint "$OPENSEARCH_ENDPOINT" \
            --region "$PRIMARY_REGION"

        # Store the exit code before deactivating
        INDEX_EXIT_CODE=$?

        # Deactivate virtual environment
        deactivate

        if [[ $INDEX_EXIT_CODE -eq 0 ]]; then
            print_message "OpenSearch index created successfully" $GREEN
        else
            print_message "OpenSearch index creation failed" $RED
        fi
    else
        print_message "OpenSearch index script not found" $YELLOW
    fi
fi

# Print deployment summary
print_message "=== Deployment Summary ===" $BLUE
echo "Stack Name: $STACK_NAME"
echo "Region: $PRIMARY_REGION"
echo "Video Bucket: $BUCKET_NAME"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""
echo "Nova 2 Models:"
echo "  - Nova Omni: $NOVA_OMNI_MODEL_ID"
echo "  - Nova Lite: $NOVA_LITE_MODEL_ID"
echo "  - Nova Embeddings: $NOVA_EMBEDDING_MODEL_ID (dim: $NOVA_EMBEDDING_DIMENSION)"
echo ""

print_message "=== Next Steps ===" $BLUE
echo "1. Upload a video to s3://$BUCKET_NAME/videos/ to trigger processing"
echo "2. Monitor Step Functions execution in the AWS console ($PRIMARY_REGION)"
echo "3. Videos will be processed using Nova 2 models (all in us-east-1)"
echo ""

print_message "=== Local Development Setup (Optional) ===" $BLUE
echo "To run MCP server, agent, or video-api locally, configure .env files:"
echo ""
echo "  # Copy example files"
echo "  cp MCP/.env.example MCP/.env"
echo "  cp agent/.env.example agent/.env"
echo "  cp video-api/.env.example video-api/.env"
echo ""
echo "  # Update these values in each .env file:"
echo "  OPENSEARCH_ENDPOINT=$OPENSEARCH_ENDPOINT"
echo "  VIDEO_BUCKET=$BUCKET_NAME"
echo ""

print_message "Deployment completed successfully!" $GREEN

# Clean up temporary files
rm -f packaged-template.yaml

# Clean up virtual environment if created
if [[ -d ".venv-deploy" ]]; then
    print_message "Cleaning up virtual environment..." $YELLOW
    rm -rf ".venv-deploy"
fi

# Run test if requested
if [[ "$RUN_TEST" == "true" ]]; then
    print_message "Running Nova 2 client tests..." $YELLOW
    if [[ -f "tests/test_nova_clients.py" ]]; then
        python tests/test_nova_clients.py
    else
        print_message "Test script not found" $YELLOW
    fi
fi
