import {
	BedrockAgentCoreClient,
	StartBrowserSessionCommand,
	StopBrowserSessionCommand,
} from '@aws-sdk/client-bedrock-agentcore';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';
import { HttpRequest } from '@smithy/protocol-http';
import { chromium, Browser, BrowserContext, Page } from 'playwright';

export interface AgentcoreCredentials {
	region: string;
	accessKeyId: string;
	secretAccessKey: string;
	sessionToken?: string;
	customEndpoint?: string;
}

export interface BrowserSessionConfig {
	browserToolArn: string;
	startUrl?: string;
	timeoutMs?: number;
}

export interface BrowserSessionInfo {
	browserId: string;
	sessionId: string;
	wsUrl: string;
	headers: Record<string, string>;
}

export class AgentcoreBrowserSession {
	private credentials: AgentcoreCredentials;
	private client: BedrockAgentCoreClient;
	private browser: Browser | null = null;
	private context: BrowserContext | null = null;
	private page: Page | null = null;
	private sessionInfo: BrowserSessionInfo | null = null;

	constructor(credentials: AgentcoreCredentials) {
		this.credentials = credentials;

		// Initialize AWS SDK client for AgentCore
		this.client = new BedrockAgentCoreClient({
			region: credentials.region,
			credentials: {
				accessKeyId: credentials.accessKeyId,
				secretAccessKey: credentials.secretAccessKey,
				...(credentials.sessionToken && { sessionToken: credentials.sessionToken }),
			},
			...(credentials.customEndpoint && { endpoint: credentials.customEndpoint }),
		});
	}

	/**
	 * Start a new AgentCore Browser session
	 * This calls the actual AWS AgentCore API to start a browser session
	 */
	async startSession(config: BrowserSessionConfig): Promise<BrowserSessionInfo> {
		try {
			// Extract browser ID from ARN
			// ARN format: arn:aws:bedrock-agentcore:us-east-1:aws:browser/aws.browser.v1
			const browserIdMatch = config.browserToolArn.match(/browser\/(.+)$/);
			const browserId = browserIdMatch ? browserIdMatch[1] : config.browserToolArn;

			// Start browser session via AWS AgentCore API
			const command = new StartBrowserSessionCommand({
				browserIdentifier: browserId,
				name: `n8n-session-${Date.now()}`,
				sessionTimeoutSeconds: Math.floor((config.timeoutMs || 300000) / 1000), // Convert ms to seconds
				viewPort: {
					height: 1080,
					width: 1920,
				},
			});

			const response = await this.client.send(command);

			if (!response.sessionId) {
				throw new Error('No session ID returned from AWS AgentCore');
			}

			const sessionId = response.sessionId;

			// Generate the CDP WebSocket URL
			const wsUrl = this.generateCDPWebSocketUrl(browserId, sessionId);

			// Generate signed headers for WebSocket connection
			const headers = await this.generateSignedHeaders(wsUrl);

			this.sessionInfo = {
				browserId,
				sessionId,
				wsUrl,
				headers,
			};

			return this.sessionInfo;
		} catch (error) {
			throw new Error(
				`Failed to start AgentCore Browser session: ${
					error instanceof Error ? error.message : String(error)
				}`,
			);
		}
	}

	/**
	 * Connect to the browser session via CDP using Playwright
	 * This is the simple part you showed in your code!
	 */
	async connectBrowser(): Promise<Page> {
		if (!this.sessionInfo) {
			throw new Error('No active session. Call startSession() first.');
		}

		try {
			// This is your code! Connect Playwright to the remote browser via CDP
			this.browser = await chromium.connectOverCDP(this.sessionInfo.wsUrl, {
				headers: this.sessionInfo.headers,
				timeout: 30000,
			});

			// Get or create context
			const contexts = this.browser.contexts();
			this.context = contexts.length > 0 ? contexts[0] : await this.browser.newContext();

			// Create a new page
			this.page = await this.context.newPage();

			return this.page;
		} catch (error) {
			throw new Error(
				`Failed to connect to browser: ${error instanceof Error ? error.message : String(error)}`,
			);
		}
	}

	/**
	 * Execute a user script on the page
	 */
	async executeScript(script: string, page: Page): Promise<any> {
		try {
			// Execute the user's script with the page object available
			const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
			const fn = new AsyncFunction('page', script);
			return await fn(page);
		} catch (error) {
			throw new Error(
				`Script execution failed: ${error instanceof Error ? error.message : String(error)}`,
			);
		}
	}

	/**
	 * Take a screenshot of the current page
	 */
	async takeScreenshot(page: Page, fullPage: boolean = false): Promise<Buffer> {
		try {
			return await page.screenshot({ fullPage, type: 'png' });
		} catch (error) {
			throw new Error(
				`Screenshot failed: ${error instanceof Error ? error.message : String(error)}`,
			);
		}
	}

	/**
	 * Close the browser session and stop the AWS session
	 */
	async close(): Promise<void> {
		try {
			// Close Playwright connections
			if (this.page && !this.page.isClosed()) {
				await this.page.close();
			}
			if (this.context) {
				await this.context.close();
			}
			if (this.browser) {
				await this.browser.close();
			}

			// Stop the AWS AgentCore browser session
			if (this.sessionInfo) {
				try {
					const command = new StopBrowserSessionCommand({
						browserIdentifier: this.sessionInfo.browserId,
						sessionId: this.sessionInfo.sessionId,
					});
					await this.client.send(command);
				} catch (error) {
					console.error('Error stopping AWS browser session:', error);
				}
			}

			this.sessionInfo = null;
		} catch (error) {
			// Log but don't throw on cleanup errors
			console.error('Error during session cleanup:', error);
		}
	}

	/**
	 * Generate the CDP WebSocket URL
	 * Format from AWS docs: wss://bedrock-agentcore.{region}.amazonaws.com/browser-streams/{browserId}/sessions/{sessionId}/automation
	 */
	private generateCDPWebSocketUrl(browserId: string, sessionId: string): string {
		const baseHost = this.credentials.customEndpoint
			? new URL(this.credentials.customEndpoint).hostname
			: `bedrock-agentcore.${this.credentials.region}.amazonaws.com`;

		return `wss://${baseHost}/browser-streams/${browserId}/sessions/${sessionId}/automation`;
	}

	/**
	 * Generate AWS SigV4 signed headers for WebSocket connection
	 */
	private async generateSignedHeaders(wsUrl: string): Promise<Record<string, string>> {
		try {
			const signer = new SignatureV4({
				service: 'bedrock-agentcore',
				region: this.credentials.region,
				credentials: {
					accessKeyId: this.credentials.accessKeyId,
					secretAccessKey: this.credentials.secretAccessKey,
					...(this.credentials.sessionToken && {
						sessionToken: this.credentials.sessionToken,
					}),
				},
				sha256: Sha256,
			});

			const url = new URL(wsUrl.replace('wss://', 'https://'));

			const request = new HttpRequest({
				method: 'GET',
				protocol: 'https:',
				hostname: url.hostname,
				path: url.pathname,
				headers: {
					host: url.hostname,
				},
			});

			const signedRequest = await signer.sign(request);

			return signedRequest.headers as Record<string, string>;
		} catch (error) {
			throw new Error(
				`Failed to generate signed headers: ${error instanceof Error ? error.message : String(error)}`,
			);
		}
	}

	/**
	 * Get session info for debugging/logging
	 */
	getSessionInfo(): BrowserSessionInfo | null {
		return this.sessionInfo;
	}
}
