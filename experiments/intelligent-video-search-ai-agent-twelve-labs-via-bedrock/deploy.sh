#!/bin/bash

# Video Ingestion Pipeline Deployment Script
# This script deploys the complete video processing pipeline with TwelveLabs models via Amazon Bedrock and OpenSearch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="video-ingestion-pipeline"
PRIMARY_REGION="us-east-1"  # For Marengo and main resources
PEGASUS_REGION="us-west-2"  # For Pegasus model
REGION="$PRIMARY_REGION"  # Backward compatibility
BUCKET_NAME=""
BUCKET_WEST=""  # Required: S3 bucket in us-west-2
OPENSEARCH_COLLECTION="video-insights-collection"
DEPLOYMENT_BUCKET=""
ADDITIONAL_PRINCIPALS=""
MAREGO_MODEL_ID="twelvelabs.marengo-embed-2-7-v1:0"
PEGASUS_MODEL_ID="us.twelvelabs.pegasus-1-2-v1:0"

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
    echo "  -r, --region REGION            Primary AWS region (default: us-east-1)"
    echo "  -b, --bucket-name NAME         S3 bucket name for videos in primary region (required)"
    echo "  -w, --bucket-west NAME         S3 bucket name for videos in us-west-2 (required - create manually)"
    echo "  -d, --deployment-bucket NAME   S3 bucket for CloudFormation artifacts (required)"
    echo "  -o, --opensearch-collection NAME  OpenSearch collection name (default: video-insights-collection)"
    echo "  -p, --principals ARN1,ARN2     Additional IAM principals for OpenSearch access (comma-separated)"
    echo "  --create-index                 Create OpenSearch index after deployment"
    echo "  --test                         Run end-to-end test after deployment"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -b my-videos-bucket -w my-videos-bucket-west -d my-deployment-bucket --create-index"
    echo "  $0 -s my-stack -b videos -w videos-west -d deploy --test"
    echo ""
    echo "IMPORTANT: You must manually create the S3 bucket in us-west-2 before deployment:"
    echo "  aws s3 mb s3://YOUR-BUCKET-WEST --region us-west-2"
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
        -w|--bucket-west)
            BUCKET_WEST="$2"
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

if [[ -z "$BUCKET_WEST" ]]; then
    print_message "Error: Video bucket name for us-west-2 is required" $RED
    print_message "Please create an S3 bucket in us-west-2 manually first:" $YELLOW
    print_message "  aws s3 mb s3://YOUR-BUCKET-WEST --region us-west-2" $YELLOW
    show_usage
    exit 1
fi

if [[ -z "$DEPLOYMENT_BUCKET" ]]; then
    print_message "Error: Deployment bucket name is required" $RED
    show_usage
    exit 1
fi

# Verify us-west-2 bucket exists
print_message "Verifying us-west-2 bucket exists..." $YELLOW
if ! aws s3 ls "s3://$BUCKET_WEST" --region us-west-2 &> /dev/null; then
    print_message "Error: S3 bucket '$BUCKET_WEST' does not exist in us-west-2" $RED
    print_message "Please create it first: aws s3 mb s3://$BUCKET_WEST --region us-west-2" $YELLOW
    exit 1
fi
print_message "us-west-2 bucket verified ✓" $GREEN

# Print configuration
print_message "=== Video Ingestion Pipeline Deployment (Bedrock) ===" $BLUE
echo "Stack name: $STACK_NAME"
echo "Primary region: $PRIMARY_REGION (Marengo + main resources)"
echo "Pegasus region: $PEGASUS_REGION (Pegasus model)"
echo "Video bucket (primary): $BUCKET_NAME"
echo "Video bucket (us-west-2): $BUCKET_WEST"
echo "Deployment bucket: $DEPLOYMENT_BUCKET"
echo "OpenSearch collection: $OPENSEARCH_COLLECTION"
echo "Marengo model: $MAREGO_MODEL_ID"
echo "Pegasus model: $PEGASUS_MODEL_ID"
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

# Note: No API key storage needed for Bedrock deployment
print_message "Using TwelveLabs models via Amazon Bedrock - no API key required ✓" $GREEN

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
print_message "Deployment bucket ready ✓" $GREEN

# Build and package SAM application
print_message "Building SAM application..." $YELLOW
sam build --template infrastructure.yaml

print_message "Packaging CloudFormation template..." $YELLOW
sam package \
    --s3-bucket "$DEPLOYMENT_BUCKET" \
    --output-template-file packaged-template.yaml \
    --region "$PRIMARY_REGION"

print_message "Template packaged successfully ✓" $GREEN

# Deploy CloudFormation stack
print_message "Deploying CloudFormation stack..." $YELLOW

# Build parameter overrides for Bedrock deployment
PARAMS="VideoBucketName=$BUCKET_NAME VideoBucketWest=$BUCKET_WEST OpenSearchCollectionName=$OPENSEARCH_COLLECTION"
PARAMS="$PARAMS PrimaryRegion=$PRIMARY_REGION PegasusRegion=$PEGASUS_REGION"
PARAMS="$PARAMS MarengoModelId=$MAREGO_MODEL_ID PegasusModelId=$PEGASUS_MODEL_ID"
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
    print_message "Stack deployed successfully ✓" $GREEN
else
    print_message "Stack deployment failed ✗" $RED
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
            --region "$PRIMARY_REGION"
        
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
echo "Primary Region: $PRIMARY_REGION (Marengo + main resources)"
echo "Pegasus Region: $PEGASUS_REGION (Pegasus model)"
echo "Video Bucket (primary): $BUCKET_NAME"
echo "Video Bucket (us-west-2): $BUCKET_WEST"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""

print_message "=== Next Steps ===" $BLUE
echo "1. Upload a video to s3://$BUCKET_NAME/videos/ to trigger processing"
echo "2. Monitor Step Functions execution in the AWS console ($PRIMARY_REGION)"
echo "3. Videos will be processed using Marengo (us-east-1) and Pegasus (us-west-2)"
echo "4. Cross-region processing will copy videos to us-west-2 bucket as needed"
echo ""

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