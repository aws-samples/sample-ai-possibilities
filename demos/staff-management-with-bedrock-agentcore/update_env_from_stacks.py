#!/usr/bin/env python3

import boto3
import os
from typing import Dict, List

def get_stack_outputs(stack_name: str, region: str) -> Dict[str, str]:
    """Get outputs from a CloudFormation stack."""
    cf = boto3.client('cloudformation', region_name=region)
    try:
        response = cf.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0].get('Outputs', [])
        return {output['OutputKey']: output['OutputValue'] for output in outputs}
    except Exception as e:
        print(f"Warning: Could not get outputs from {stack_name}: {e}")
        return {}

def update_env_file(env_vars: Dict[str, str], env_file: str = '.env'):
    """Update .env file with new variables."""
    existing_vars = {}
    
    # Read existing .env file if it exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Strip quotes from values
                    value = value.strip("'\"")
                    existing_vars[key] = value
    
    # Map CloudFormation outputs to expected .env variable names
    output_mapping = {
        'StaffTableName': 'STAFF_TABLE_NAME',
        'RosterTableName': 'ROSTER_TABLE_NAME', 
        'AvailabilityTableName': 'AVAILABILITY_TABLE_NAME',
        'BusinessTableName': 'BUSINESS_TABLE_NAME',
        'HolidaysTableName': 'HOLIDAYS_TABLE_NAME',
        'CertificationsTableName': 'CERTIFICATIONS_TABLE_NAME',
        'PayrollTableName': 'PAYROLL_TABLE_NAME',
        'TrainingTableName': 'TRAINING_TABLE_NAME',
        'CollectionName': 'OPENSEARCH_COLLECTION_NAME',
        'CollectionEndpoint': 'OPENSEARCH_COLLECTION_ENDPOINT',
        'CollectionArn': 'OPENSEARCH_COLLECTION_ARN',
        'KnowledgeBaseId': 'KNOWLEDGE_BASE_ID',
        'PolicyBucketName': 'POLICY_BUCKET_NAME'
    }
    
    # Apply mapping and update existing vars
    for cf_key, env_key in output_mapping.items():
        if cf_key in env_vars:
            existing_vars[env_key] = env_vars[cf_key]
    
    # Add other direct mappings
    for key, value in env_vars.items():
        if key not in output_mapping:
            existing_vars[key] = value
    # Add missing required variables with defaults
    existing_vars.setdefault('OPENSEARCH_INDEX_NAME', 'staffcast-policies-index')
    existing_vars.setdefault('MCP_SERVER_URL', 'http://localhost:8008/sse')
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.write("# AWS Configuration\n")
        f.write(f"AWS_REGION={existing_vars.get('AWS_REGION', 'us-west-2')}\n\n")
        
        f.write("# Core DynamoDB Tables\n")
        for key in ['STAFF_TABLE_NAME', 'ROSTER_TABLE_NAME', 'AVAILABILITY_TABLE_NAME', 'BUSINESS_TABLE_NAME', 'HOLIDAYS_TABLE_NAME']:
            if key in existing_vars:
                f.write(f"{key}={existing_vars[key]}\n")
        f.write("\n")
        
        f.write("# Extension Tables\n")
        for key in ['CERTIFICATIONS_TABLE_NAME', 'PAYROLL_TABLE_NAME', 'TRAINING_TABLE_NAME']:
            if key in existing_vars:
                f.write(f"{key}={existing_vars[key]}\n")
        f.write("\n")
        
        f.write("# OpenSearch Configuration\n")
        for key in ['OPENSEARCH_COLLECTION_NAME', 'OPENSEARCH_COLLECTION_ENDPOINT', 'OPENSEARCH_COLLECTION_ARN', 'OPENSEARCH_INDEX_NAME']:
            if key in existing_vars:
                f.write(f"{key}={existing_vars[key]}\n")
        f.write("\n")
        
        f.write("# Knowledge Base Configuration\n")
        for key in ['KNOWLEDGE_BASE_ID', 'POLICY_BUCKET_NAME']:
            if key in existing_vars:
                f.write(f"{key}={existing_vars[key]}\n")
        f.write("\n")
        
        f.write("# MCP and API Configuration\n")
        f.write(f"MCP_HOST={existing_vars.get('MCP_HOST', 'localhost')}\n")
        f.write(f"MCP_PORT={existing_vars.get('MCP_PORT', '8008')}\n")
        f.write(f"MCP_SERVER_URL={existing_vars.get('MCP_SERVER_URL', 'http://localhost:8008/sse')}\n")
        f.write(f"API_HOST={existing_vars.get('API_HOST', '0.0.0.0')}\n")
        f.write(f"API_PORT={existing_vars.get('API_PORT', '8080')}\n")
        f.write(f"STAFF_API_PORT={existing_vars.get('STAFF_API_PORT', '8081')}\n\n")
        
        f.write("# Bedrock Model Configuration\n")
        f.write(f"BEDROCK_MODEL_ID={existing_vars.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')}\n\n")
        
        f.write("# Demo Configuration\n")
        f.write(f"DEMO_STAFF_ID={existing_vars.get('DEMO_STAFF_ID', 'emma_davis')}\n")
        f.write(f"DEMO_BUSINESS_ID={existing_vars.get('DEMO_BUSINESS_ID', 'cafe-001')}\n")

def main():
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
    
    # Stack names
    stacks = {
        'core': 'staffcast-core-dev',
        'opensearch': 'staffcast-opensearch-dev', 
        'staff': 'staffcast-staff-dev'
    }
    
    # Collect all outputs
    all_outputs = {}
    all_outputs['AWS_REGION'] = region
    
    for stack_type, stack_name in stacks.items():
        print(f"Getting outputs from {stack_name}...")
        outputs = get_stack_outputs(stack_name, region)
        all_outputs.update(outputs)
    
    # Update .env file
    update_env_file(all_outputs)
    print(f"✅ Updated .env file with {len(all_outputs)} variables")
    
    # Display what was added
    print("\n📋 Environment variables updated:")
    for key, value in sorted(all_outputs.items()):
        print(f"  {key}={value}")

if __name__ == "__main__":
    main()
