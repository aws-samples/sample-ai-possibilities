#!/usr/bin/env python3
"""
Delete OpenSearch Serverless vector index for StaffCast Knowledge Base

This script safely deletes the existing index to allow recreation with corrected mapping.

Usage:
    python delete_opensearch_index.py --region us-west-2 --stack-name staffcast-opensearch-dev
"""

import os
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from dotenv import load_dotenv
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenSearchIndexDeleter:
    def __init__(self, region='us-west-2', stack_name='staffcast-opensearch-dev'):
        self.region = region
        self.stack_name = stack_name
        self.session = boto3.Session(region_name=region)
        self.cloudformation = self.session.client('cloudformation')
        
        # Load environment variables
        load_dotenv()
        
        # Collection details (will be populated from CloudFormation)
        self.collection_endpoint = None
        self.collection_name = None
        
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
            self.collection_name = output_map.get('CollectionName')
            
            if not all([self.collection_endpoint, self.collection_name]):
                raise ValueError("Missing required collection details from CloudFormation outputs")
                
            logger.info(f"Collection details retrieved:")
            logger.info(f"  Name: {self.collection_name}")
            logger.info(f"  Endpoint: {self.collection_endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to retrieve collection details: {str(e)}")
            raise
    
    def delete_index(self):
        """Delete the vector index from OpenSearch Serverless"""
        logger.info(f"Deleting vector index: {self.index_name}")
        
        # Check if index exists first
        if not self.check_index_exists():
            logger.info(f"✅ Index {self.index_name} does not exist. Nothing to delete.")
            return True
        
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
        
        try:
            # Delete the index using the OpenSearch client
            response = client.indices.delete(index=self.index_name)
            
            logger.info(f"✅ Successfully deleted index: {self.index_name}")
            logger.info(f"Response: {response}")
            return True
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ Error deleting index: {error_str}")
            
            if "404" in error_str or "index_not_found" in error_str.lower():
                logger.info(f"✅ Index {self.index_name} was already deleted or doesn't exist!")
                return True
            else:
                logger.error(f"❌ Unexpected error: {error_str}")
                return False
    
    def check_index_exists(self):
        """Check if the index exists"""
        try:
            credentials = self.session.get_credentials()
            url = f"{self.collection_endpoint}/{self.index_name}"
            
            request = AWSRequest(method='HEAD', url=url)
            SigV4Auth(credentials, 'aoss', self.region).add_auth(request)
            
            response = requests.head(url, headers=dict(request.headers), timeout=30)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def run(self):
        """Execute the complete index deletion process"""
        try:
            logger.info("🗑️ Starting OpenSearch index deletion process...")
            logger.info("="*60)
            
            # Step 1: Get collection details from CloudFormation
            logger.info("📋 Step 1: Retrieving collection details...")
            self.get_collection_details()
            
            # Step 2: Delete the vector index
            logger.info("\n🗑️ Step 2: Deleting vector index...")
            if not self.delete_index():
                raise Exception("Failed to delete vector index")
            
            logger.info("\n" + "="*60)
            logger.info("🎉 SUCCESS! OpenSearch index deletion completed!")
            logger.info("You can now recreate the index with the corrected mapping.")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"\n❌ FAILED: Index deletion failed: {str(e)}")
            logger.error("Please check the error details above and try again.")
            raise

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Delete OpenSearch Serverless vector index for StaffCast Knowledge Base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python delete_opensearch_index.py --region us-west-2 --stack-name staffcast-opensearch-dev
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
    
    print(f"StaffCast OpenSearch Index Deleter")
    print(f"Region: {args.region}")
    print(f"Stack: {args.stack_name}")
    print("")
    
    # Create and run the index deleter
    deleter = OpenSearchIndexDeleter(region=args.region, stack_name=args.stack_name)
    deleter.run()

if __name__ == '__main__':
    main()