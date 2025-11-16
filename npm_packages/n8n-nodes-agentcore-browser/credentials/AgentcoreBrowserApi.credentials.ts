import { IAuthenticateGeneric, ICredentialType, INodeProperties } from 'n8n-workflow';

export class AgentcoreBrowserApi implements ICredentialType {
	name = 'agentcoreBrowserApi';
	displayName = 'AgentCore Browser API';
	documentationUrl =
		'https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-browser.html';
	properties: INodeProperties[] = [
		{
			displayName: 'AWS Region',
			name: 'region',
			type: 'string',
			default: 'us-east-1',
			required: true,
			description: 'AWS region where AgentCore Browser is available',
			placeholder: 'us-east-1',
		},
		{
			displayName: 'Access Key ID',
			name: 'accessKeyId',
			type: 'string',
			default: '',
			required: true,
			description: 'AWS Access Key ID with permissions for AgentCore Browser',
		},
		{
			displayName: 'Secret Access Key',
			name: 'secretAccessKey',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			required: true,
			description: 'AWS Secret Access Key',
		},
		{
			displayName: 'Session Token',
			name: 'sessionToken',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			description:
				'Temporary session token (optional, for assumed roles or temporary credentials)',
		},
		{
			displayName: 'Custom Endpoint',
			name: 'customEndpoint',
			type: 'string',
			default: '',
			description:
				'Custom endpoint URL for AgentCore (optional, for VPC endpoints or testing)',
			placeholder: 'https://bedrock-agentcore.us-east-1.amazonaws.com',
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {},
	};

	// Note: AWS requires SigV4 signing for all API requests, which is complex to implement
	// in the credentials test. The node will validate credentials when actually used.
}
