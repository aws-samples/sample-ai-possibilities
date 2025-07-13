#!/bin/bash

# Video Ingestion Pipeline Deployment Script
# This script deploys the complete video processing pipeline with Twelve Labs SDK and OpenSearch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="video-ingestion-pipeline"
REGION="us-east-1"
BUCKET_NAME=""
OPENSEARCH_COLLECTION="video-insights-collection"
SECRET_NAME="twelve-labs-api-key"
DEPLOYMENT_BUCKET=""
ADDITIONAL_PRINCIPALS=""

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
    echo "  -r, --region REGION            AWS region (default: us-east-1)"
    echo "  -b, --bucket-name NAME         S3 bucket name for videos (required)"
    echo "  -d, --deployment-bucket NAME   S3 bucket for CloudFormation artifacts (required)"
    echo "  -o, --opensearch-collection NAME  OpenSearch collection name (default: video-insights-collection)"
    echo "  -k, --secret-name NAME         Secrets Manager secret name for API key (default: twelve-labs-api-key)"
    echo "  -a, --api-key KEY              Twelve Labs API key (will be stored in Secrets Manager)"
    echo "  -p, --principals ARN1,ARN2     Additional IAM principals for OpenSearch access (comma-separated)"
    echo "  --create-index                 Create OpenSearch index after deployment"
    echo "  --test                         Run end-to-end test after deployment"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -b my-videos-bucket -d my-deployment-bucket -a YOUR_API_KEY"
    echo "  $0 -s my-stack -b videos -d deploy --create-index --test"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
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
        -k|--secret-name)
            SECRET_NAME="$2"
            shift 2
            ;;
        -a|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -p|--principals)
            ADDITIONAL_PRINCIPALS="$2"
            shift 2
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

# Print configuration
print_message "=== Video Ingestion Pipeline Deployment ===" $BLUE
echo "Stack name: $STACK_NAME"
echo "Region: $REGION"
echo "Video bucket: $BUCKET_NAME"
echo "Deployment bucket: $DEPLOYMENT_BUCKET"
echo "OpenSearch collection: $OPENSEARCH_COLLECTION"
echo "Secret name: $SECRET_NAME"
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

print_message "AWS credentials verified ✓" $GREEN

# Store API key in Secrets Manager if provided
if [[ -n "$API_KEY" ]]; then
    print_message "Storing Twelve Labs API key in Secrets Manager..." $YELLOW
    
    # Check if secret already exists
    if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &> /dev/null; then
        print_message "Updating existing secret..." $YELLOW
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "{\"api_key\":\"$API_KEY\"}" \
            --region "$REGION"
    else
        print_message "Creating new secret..." $YELLOW
        aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --secret-string "{\"api_key\":\"$API_KEY\"}" \
            --description "Twelve Labs API key for video processing" \
            --region "$REGION"
    fi
    
    print_message "API key stored successfully ✓" $GREEN
fi

# Create deployment bucket if it doesn't exist
print_message "Checking deployment bucket..." $YELLOW
if ! aws s3 ls "s3://$DEPLOYMENT_BUCKET" &> /dev/null; then
    print_message "Creating deployment bucket..." $YELLOW
    if [[ "$REGION" == "us-east-1" ]]; then
        aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$REGION"
    else
        aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
    fi
fi
print_message "Deployment bucket ready ✓" $GREEN

# Build and package SAM application
print_message "Building SAM application..." $YELLOW
sam build --template infrastructure.yaml

print_message "Packaging CloudFormation template..." $YELLOW
sam package \
    --s3-bucket "$DEPLOYMENT_BUCKET" \
    --output-template-file packaged-template.yaml \
    --region "$REGION"

print_message "Template packaged successfully ✓" $GREEN

# Deploy CloudFormation stack
print_message "Deploying CloudFormation stack..." $YELLOW

# Build parameter overrides
PARAMS="VideoBucketName=$BUCKET_NAME OpenSearchCollectionName=$OPENSEARCH_COLLECTION TwelveLabsApiKeySecret=$SECRET_NAME"
if [[ -n "$ADDITIONAL_PRINCIPALS" ]]; then
    PARAMS="$PARAMS AdditionalOpenSearchPrincipals=$ADDITIONAL_PRINCIPALS"
fi

aws cloudformation deploy \
    --template-file packaged-template.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides $PARAMS \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset

if [[ $? -eq 0 ]]; then
    print_message "Stack deployed successfully ✓" $GREEN
else
    print_message "Stack deployment failed ✗" $RED
    exit 1
fi

# Get stack outputs
print_message "Retrieving stack outputs..." $YELLOW
OPENSEARCH_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`OpenSearchEndpoint`].OutputValue' \
    --output text)

SEARCH_FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`SearchFunctionArn`].OutputValue' \
    --output text)

STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
    --output text)

print_message "Stack outputs retrieved ✓" $GREEN

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
        
        # Run the index creation script
        python data_ingestion/1-create-opensearch-index.py \
            --endpoint "$OPENSEARCH_ENDPOINT" \
            --region "$REGION"
        
        # Store the exit code before deactivating
        INDEX_EXIT_CODE=$?
        
        # Deactivate virtual environment
        deactivate
        
        if [[ $INDEX_EXIT_CODE -eq 0 ]]; then
            print_message "OpenSearch index created successfully ✓" $GREEN
        else
            print_message "OpenSearch index creation failed ✗" $RED
        fi
    else
        print_message "OpenSearch index script not found" $YELLOW
    fi
fi

# Print deployment summary
print_message "=== Deployment Summary ===" $BLUE
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Video Bucket: $BUCKET_NAME"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "Search Function ARN: $SEARCH_FUNCTION_ARN"
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""

print_message "=== Next Steps ===" $BLUE
echo "1. Upload a video to s3://$BUCKET_NAME/videos/ to trigger processing"
echo "2. Monitor Step Functions execution in the AWS console"
echo "3. Use the Search Lambda function to query processed videos"
echo ""

if [[ -z "$API_KEY" ]]; then
    print_message "Note: Don't forget to store your Twelve Labs API key in Secrets Manager:" $YELLOW
    echo "  aws secretsmanager create-secret \\"
    echo "    --name '$SECRET_NAME' \\"
    echo "    --secret-string '{\"api_key\":\"YOUR_API_KEY\"}' \\"
    echo "    --region '$REGION'"
    echo ""
fi

print_message "🎉 Deployment completed successfully!" $GREEN

# Clean up temporary files
rm -f packaged-template.yaml

# Clean up virtual environment if created
if [[ -d ".venv-deploy" ]]; then
    print_message "Cleaning up virtual environment..." $YELLOW
    rm -rf ".venv-deploy"
fi

# Run test if requested
if [[ "$RUN_TEST" == "true" ]]; then
    print_message "Running end-to-end test..." $YELLOW
    print_message "Test functionality not yet implemented" $YELLOW
fi