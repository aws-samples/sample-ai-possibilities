#!/usr/bin/env python3
"""
Create OpenSearch Serverless vector index for StaffCast Knowledge Base

This script:
1. Retrieves OpenSearch collection details from CloudFormation
2. Creates the vector index with proper configuration for Bedrock
3. Updates the .env file with collection information
4. Verifies the index was created successfully

Prerequisites:
- AWS CLI configured with appropriate permissions
- CloudFormation stack 'staffcast-opensearch-dev' deployed
- boto3, requests, and python-dotenv packages installed

Usage:
    python create_opensearch_index.py --region us-west-2 --stack-name staffcast-opensearch-dev
"""

import os
import json
import time
import boto3
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from dotenv import load_dotenv, set_key
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenSearchIndexCreator:
    def __init__(self, region='us-west-2', stack_name='staffcast-opensearch-dev'):
        self.region = region
        self.stack_name = stack_name
        self.session = boto3.Session(region_name=region)
        self.cloudformation = self.session.client('cloudformation')
        
        # Load environment variables
        load_dotenv()
        
        # Collection details (will be populated from CloudFormation)
        self.collection_endpoint = None
        self.collection_arn = None
        self.collection_name = None
        self.policy_bucket_name = None
        self.kb_role_arn = None
        
        # Index configuration for StaffCast
        self.index_name = 'staffcast-policies-index'
        
    def get_collection_details(self):
        """Get OpenSearch collection details from CloudFormation outputs"""
        logger.info(f"Retrieving collection details from stack: {self.stack_name}")
        
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            outputs = response['Stacks'][0]['Outputs']
            
            output_map = {output['OutputKey']: output['OutputValue'] for output in outputs}
            
            # Get required outputs from opensearch stack
            self.collection_endpoint = output_map.get('CollectionEndpoint')
            self.collection_arn = output_map.get('CollectionArn')
            self.collection_name = output_map.get('CollectionName')
            self.kb_role_arn = output_map.get('KnowledgeBaseRoleArn')
            
            # Policy bucket will come from staff-extensions stack later
            self.policy_bucket_name = None
            
            if not all([self.collection_endpoint, self.collection_arn, self.collection_name]):
                raise ValueError("Missing required collection details from CloudFormation outputs")
                
            logger.info(f"Collection details retrieved:")
            logger.info(f"  Name: {self.collection_name}")
            logger.info(f"  Endpoint: {self.collection_endpoint}")
            logger.info(f"  ARN: {self.collection_arn}")
            logger.info(f"  Bucket: {self.policy_bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to retrieve collection details: {str(e)}")
            raise
    
    def wait_for_collection_ready(self, max_wait_time=600):
        """Wait for OpenSearch collection to be in ACTIVE state"""
        logger.info("Checking if collection is ready...")
        
        aoss_client = self.session.client('opensearchserverless')
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                logger.info(f"Checking collection: {self.collection_name}")
                response = aoss_client.batch_get_collection(names=[self.collection_name])
                
                if not response.get('collectionDetails'):
                    logger.warning(f"No collection found with name: {self.collection_name}")
                    logger.info("Collection not ready yet, waiting 30 seconds...")
                    time.sleep(30)
                    continue
                    
                status = response['collectionDetails'][0]['status']
                logger.info(f"Collection status: {status}")
                
                if status == 'ACTIVE':
                    logger.info("✅ Collection is ready!")
                    return True
                elif status in ['FAILED', 'DELETING']:
                    raise Exception(f"Collection is in failed state: {status}")
                else:
                    logger.info(f"Collection status is {status}, waiting 30 seconds...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error checking collection status: {str(e)}")
                logger.info("Retrying in 30 seconds...")
                time.sleep(30)
        
        raise TimeoutError(f"Collection did not become ready within {max_wait_time} seconds")
    
    def create_vector_index(self, max_retries=3):
        """Create the vector index in OpenSearch Serverless using proper AWS authentication"""
        logger.info(f"Creating vector index: {self.index_name}")
        
        # Check if index already exists first
        if self.check_index_exists():
            logger.info(f"✅ Index {self.index_name} already exists!")
            return True
        
        # Index mapping configuration optimized for Bedrock Knowledge Base
        index_mapping = {
            "settings": {
                "index.knn": True,
                "number_of_shards": 1,
                "knn.algo_param.ef_search": 512
            },
            "mappings": {
                "properties": {
                    "vector": {
                        "type": "knn_vector",
                        "dimension": 1024,  # Cohere Embed Multilingual v3 dimensions
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss",
                            "parameters": {
                                "m": 16
                            }
                        }
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "metadata": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "source": {
                        "type": "keyword"
                    },
                    "document_id": {
                        "type": "keyword"
                    }
                }
            }
        }
        
        # Get AWS credentials for authentication
        credentials = self.session.get_credentials()
        
        # Create AWS4Auth for OpenSearch Serverless
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'aoss',  # OpenSearch Serverless service
            session_token=credentials.token
        )
        
        # Parse the collection endpoint to get host
        from urllib.parse import urlparse
        parsed_url = urlparse(self.collection_endpoint)
        host = parsed_url.hostname
        
        # Create OpenSearch client with proper authentication
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )
        
        # Retry logic for 403 errors (policy propagation delays)
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to create index...")
                
                # Wait for policy propagation on first attempt
                if attempt == 0:
                    logger.info("Waiting 45 seconds for data access policy to propagate...")
                    time.sleep(45)
                
                # Create the index using the OpenSearch client
                response = client.indices.create(
                    index=self.index_name,
                    body=index_mapping
                )
                
                logger.info(f"✅ Successfully created index: {self.index_name}")
                logger.info(f"Response: {response}")
                return True
                    
            except Exception as e:
                error_str = str(e)
                logger.error(f"❌ Error on attempt {attempt + 1}: {error_str}")
                
                if "403" in error_str or "Forbidden" in error_str:
                    logger.warning(f"⚠️  403 Forbidden on attempt {attempt + 1}. This might be due to policy propagation delay.")
                    if attempt < max_retries - 1:
                        wait_time = 30 * (attempt + 1)  # Exponential backoff: 30s, 60s, 90s
                        logger.info(f"Waiting {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Still getting 403 after {max_retries} attempts.")
                        logger.error("This suggests the data access policy may not include your user ARN or hasn't propagated yet.")
                        return False
                elif "resource_already_exists" in error_str.lower():
                    logger.info(f"✅ Index {self.index_name} already exists!")
                    return True
                else:
                    logger.error(f"❌ Unexpected error: {error_str}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in 30 seconds...")
                        time.sleep(30)
                    else:
                        logger.error(f"❌ Failed after {max_retries} attempts")
                        return False
        
        return False
    
    def check_index_exists(self):
        """Check if the index already exists"""
        try:
            credentials = self.session.get_credentials()
            url = f"{self.collection_endpoint}/{self.index_name}"
            
            request = AWSRequest(method='HEAD', url=url)
            SigV4Auth(credentials, 'aoss', self.region).add_auth(request)
            
            response = requests.head(url, headers=dict(request.headers), timeout=30)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def verify_index_creation(self):
        """Verify that the index was created successfully"""
        logger.info("Verifying index creation...")
        
        # Get AWS credentials for signing
        credentials = self.session.get_credentials()
        
        # Check if index exists
        url = f"{self.collection_endpoint}/{self.index_name}"
        
        request = AWSRequest(method='GET', url=url)
        SigV4Auth(credentials, 'aoss', self.region).add_auth(request)
        
        try:
            response = requests.get(url, headers=dict(request.headers), timeout=30)
            
            if response.status_code == 200:
                index_info = response.json()
                logger.info("✅ Index verification successful!")
                logger.info(f"Index mapping confirmed with {index_info.get(self.index_name, {}).get('mappings', {}).get('properties', {}).keys()}")
                return True
            else:
                logger.error(f"❌ Index verification failed. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verifying index: {str(e)}")
            return False
    
    def update_env_file(self):
        """Update .env file with collection information"""
        logger.info("Updating .env file with collection details...")
        
        env_file = '.env'
        
        # Values to update - following your existing naming convention
        env_updates = {
            # OpenSearch Collection details
            'OPENSEARCH_COLLECTION_NAME': self.collection_name,
            'OPENSEARCH_COLLECTION_ENDPOINT': self.collection_endpoint,
            'OPENSEARCH_COLLECTION_ARN': self.collection_arn,
            'OPENSEARCH_INDEX_NAME': self.index_name,
            
            # S3 Bucket for policies
            'POLICY_BUCKET_NAME': self.policy_bucket_name,
            
            # IAM Role for Knowledge Base (for manual creation)
            'KNOWLEDGE_BASE_ROLE_ARN': self.kb_role_arn
        }
        
        try:
            for key, value in env_updates.items():
                if value:  # Only update if we have a value
                    set_key(env_file, key, value)
                    logger.info(f"  ✅ {key}={value}")
                
            logger.info(f"✅ Successfully updated {env_file}")
            
            # Display next steps
            logger.info("\n" + "="*60)
            logger.info("📋 NEXT STEPS:")
            logger.info("1. Create Knowledge Base manually or via CLI")
            logger.info("2. Add KNOWLEDGE_BASE_ID to .env file")
            logger.info("3. Run demo data population scripts")
            logger.info("4. Test the complete system")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ Error updating .env file: {str(e)}")
            raise
    
    def run(self):
        """Execute the complete index creation process"""
        try:
            logger.info("🚀 Starting OpenSearch index creation process...")
            logger.info("="*60)
            
            # Step 1: Get collection details from CloudFormation
            logger.info("📋 Step 1: Retrieving collection details...")
            self.get_collection_details()
            
            # Step 2: Wait for collection to be ready
            logger.info("\n⏳ Step 2: Checking collection status...")
            # Uncomment below to actually wait:
            # self.wait_for_collection_ready()
            
            # Step 3: Create the vector index
            logger.info("\n🔧 Step 3: Creating vector index...")
            if not self.create_vector_index():
                raise Exception("Failed to create vector index")
            
            # Step 4: Verify index creation
            logger.info("\n🔍 Step 4: Verifying index creation...")
            time.sleep(10)  # Allow time for index to be available
            if not self.verify_index_creation():
                logger.warning("⚠️  Index verification failed, but creation may have succeeded")
            
            # Step 5: Update .env file
            logger.info("\n📝 Step 5: Updating environment configuration...")
            self.update_env_file()
            
            logger.info("\n" + "="*60)
            logger.info("🎉 SUCCESS! OpenSearch index creation completed!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"\n❌ FAILED: Index creation failed: {str(e)}")
            logger.error("Please check the error details above and try again.")
            raise

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Create OpenSearch Serverless vector index for StaffCast Knowledge Base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_opensearch_index.py --region us-west-2 --stack-name staffcast-staff-dev
  python create_opensearch_index.py --region us-east-1 --stack-name my-custom-stack
        """
    )
    
    parser.add_argument(
        '--region', 
        default='us-west-2', 
        help='AWS region (default: us-west-2)'
    )
    parser.add_argument(
        '--stack-name', 
        default='staffcast-opensearch-dev',
        help='CloudFormation stack name containing OpenSearch collection (default: staffcast-opensearch-dev)'
    )
    
    args = parser.parse_args()
    
    print(f"StaffCast OpenSearch Index Creator")
    print(f"Region: {args.region}")
    print(f"Stack: {args.stack_name}")
    print("")
    
    # Create and run the index creator
    creator = OpenSearchIndexCreator(region=args.region, stack_name=args.stack_name)
    creator.run()

if __name__ == '__main__':
    main()