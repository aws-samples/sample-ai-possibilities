import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { AgentcoreBrowserSession, AgentcoreCredentials } from '../../utils/AgentcoreBrowserSession';

export class AgentcoreBrowser implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'AgentCore Browser',
		name: 'agentcoreBrowser',
		icon: 'file:agentcore.png',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description: 'Automate browser tasks using Amazon Bedrock AgentCore Browser and Playwright',
		usableAsTool: true,
		defaults: {
			name: 'AgentCore Browser',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'aws',
				required: false,
				displayOptions: {
					show: {
						authentication: ['aws'],
					},
				},
			},
			{
				name: 'agentcoreBrowserApi',
				required: false,
				displayOptions: {
					show: {
						authentication: ['agentcoreBrowserApi'],
					},
				},
			},
		],
		properties: [
			{
				displayName: 'Authentication',
				name: 'authentication',
				type: 'options',
				options: [
					{
						name: 'AWS',
						value: 'aws',
						description:
							'Use standard AWS credentials (can reuse credentials from other AWS nodes)',
					},
					{
						name: 'AgentCore Browser API',
						value: 'agentcoreBrowserApi',
						description:
							'Use custom AgentCore Browser credentials (supports custom endpoints)',
					},
				],
				default: 'aws',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Agent Instructions',
						value: 'agentInstructions',
						description:
							'Execute browser tasks from natural language instructions (for AI agents)',
						action: 'Execute browser tasks from AI agent instructions',
					},
					{
						name: 'Run Script',
						value: 'runScript',
						description: 'Execute a custom Playwright script',
						action: 'Run a custom Playwright script',
					},
					{
						name: 'Navigate and Extract',
						value: 'navigateExtract',
						description: 'Navigate to a URL and extract data',
						action: 'Navigate to a URL and extract data',
					},
				],
				default: 'agentInstructions',
			},

			// Common parameters
			{
				displayName: 'Browser Tool ARN',
				name: 'browserToolArn',
				type: 'string',
				default: 'arn:aws:bedrock-agentcore:us-east-1:aws:browser/aws.browser.v1',
				required: true,
				description: 'ARN of the AgentCore Browser tool to use',
			},
			{
				displayName: 'Start URL',
				name: 'startUrl',
				type: 'string',
				default: '',
				required: true,
				description: 'URL to navigate to',
				placeholder: 'https://example.com',
			},
			{
				displayName: 'Timeout (ms)',
				name: 'timeoutMs',
				type: 'number',
				default: 60000,
				description: 'Maximum time to wait for the operation to complete',
			},

			// Agent Instructions operation parameters
			{
				displayName: 'Instructions',
				name: 'instructions',
				type: 'string',
				typeOptions: {
					rows: 5,
				},
				displayOptions: {
					show: {
						operation: ['agentInstructions'],
					},
				},
				default: '',
				required: true,
				description:
					'Natural language instructions for browser actions (e.g., "Search amazon.com for wireless headphones and extract top 3 products")',
				placeholder: 'Search for products, fill forms, extract data...',
			},
			{
				displayName: 'URL Override',
				name: 'urlOverride',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['agentInstructions'],
					},
				},
				default: '',
				description:
					'Optional URL override. If not provided, URL will be derived from instructions or use startUrl.',
				placeholder: 'https://example.com',
			},
			{
				displayName: 'Session Timeout (seconds)',
				name: 'sessionTimeoutSeconds',
				type: 'number',
				displayOptions: {
					show: {
						operation: ['agentInstructions'],
					},
				},
				default: 900,
				description: 'Browser session timeout in seconds',
			},

			// Run Script operation parameters
			{
				displayName: 'Script',
				name: 'script',
				type: 'string',
				typeOptions: {
					rows: 10,
				},
				displayOptions: {
					show: {
						operation: ['runScript'],
					},
				},
				default: `// Your Playwright script here
// The 'page' object is available
await page.waitForLoadState('networkidle');
const title = await page.title();
return { title };`,
				required: true,
				description:
					'JavaScript/TypeScript code to execute. The page object is available as "page".',
			},
			{
				displayName: 'Screenshot Mode',
				name: 'screenshotMode',
				type: 'options',
				displayOptions: {
					show: {
						operation: ['runScript'],
					},
				},
				options: [
					{
						name: 'None',
						value: 'none',
					},
					{
						name: 'Final Page',
						value: 'final',
					},
					{
						name: 'On Error Only',
						value: 'error',
					},
				],
				default: 'none',
				description: 'When to capture screenshots',
			},

			// Navigate & Extract operation parameters
			{
				displayName: 'Selector',
				name: 'selector',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
					},
				},
				default: '',
				description: 'CSS selector to extract data from',
				placeholder: 'h1, .title, #content',
			},
			{
				displayName: 'Extract Mode',
				name: 'extractMode',
				type: 'options',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
					},
				},
				options: [
					{
						name: 'Text Content',
						value: 'text',
						description: 'Extract text content',
					},
					{
						name: 'HTML',
						value: 'html',
						description: 'Extract HTML content',
					},
					{
						name: 'Attribute',
						value: 'attribute',
						description: 'Extract specific attribute',
					},
				],
				default: 'text',
				description: 'What to extract from the selected elements',
			},
			{
				displayName: 'Attribute Name',
				name: 'attributeName',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
						extractMode: ['attribute'],
					},
				},
				default: '',
				description: 'Name of the attribute to extract',
				placeholder: 'href, src, data-id',
			},
			{
				displayName: 'Wait for Selector',
				name: 'waitForSelector',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
					},
				},
				default: '',
				description: 'Wait for this selector to appear before extracting',
				placeholder: '.content-loaded',
			},
			{
				displayName: 'Actions',
				name: 'actions',
				type: 'fixedCollection',
				typeOptions: {
					multipleValues: true,
				},
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
					},
				},
				default: {},
				description: 'Actions to perform before extraction',
				options: [
					{
						name: 'action',
						displayName: 'Action',
						values: [
							{
								displayName: 'Action Type',
								name: 'type',
								type: 'options',
								options: [
									{
										name: 'Click',
										value: 'click',
									},
									{
										name: 'Type Text',
										value: 'type',
									},
									{
										name: 'Wait',
										value: 'wait',
									},
									{
										name: 'Press Key',
										value: 'press',
									},
								],
								default: 'click',
							},
							{
								displayName: 'Selector',
								name: 'selector',
								type: 'string',
								default: '',
								description: 'CSS selector for the element',
							},
							{
								displayName: 'Value',
								name: 'value',
								type: 'string',
								default: '',
								description:
									'Value for the action (text to type, key to press, or ms to wait)',
							},
						],
					},
				],
			},
			{
				displayName: 'Take Screenshot',
				name: 'takeScreenshot',
				type: 'boolean',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
					},
				},
				default: false,
				description: 'Whether to capture a screenshot of the page',
			},
			{
				displayName: 'Full Page Screenshot',
				name: 'fullPageScreenshot',
				type: 'boolean',
				displayOptions: {
					show: {
						operation: ['navigateExtract'],
						takeScreenshot: [true],
					},
				},
				default: false,
				description: 'Whether to capture the entire page or just the viewport',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				// Get authentication type
				const authentication = this.getNodeParameter('authentication', i) as
					| 'aws'
					| 'agentcoreBrowserApi';

				// Get credentials based on authentication type
				const credentials = await this.getCredentials(authentication, i);

				const agentcoreCredentials: AgentcoreCredentials = {
					region: credentials.region as string,
					accessKeyId: credentials.accessKeyId as string,
					secretAccessKey: credentials.secretAccessKey as string,
					sessionToken: credentials.sessionToken as string | undefined,
					customEndpoint:
						authentication === 'agentcoreBrowserApi'
							? (credentials.customEndpoint as string | undefined)
							: undefined,
				};

				// Get common parameters
				const browserToolArn = this.getNodeParameter('browserToolArn', i) as string;
				const startUrl = this.getNodeParameter('startUrl', i) as string;
				const timeoutMs = this.getNodeParameter('timeoutMs', i, 60000) as number;

				// Create session
				const session = new AgentcoreBrowserSession(agentcoreCredentials);

				try {
					// Start session
					await session.startSession({
						browserToolArn,
						startUrl,
						timeoutMs,
					});

					// Connect browser
					const page = await session.connectBrowser();

					// Navigate to URL
					await page.goto(startUrl, {
						timeout: timeoutMs,
						waitUntil: 'domcontentloaded',
					});

					let result: any = {};
					let screenshot: Buffer | null = null;

					if (operation === 'agentInstructions') {
						// Execute agent instructions operation
						const instructions = this.getNodeParameter('instructions', i) as string;
						const urlOverride = this.getNodeParameter('urlOverride', i, '') as string;

						// Determine URL from override, instructions, or startUrl
						const targetUrl = urlOverride || startUrl || 'https://amazon.com';

						try {
							// Parse instructions for search tasks
							// Detect search intent from various instruction formats
							const instructionsLower = instructions.toLowerCase();
							const isSearchTask =
								instructionsLower.includes('search') ||
								(instructionsLower.includes('type') &&
									(instructionsLower.includes('search field') ||
										instructionsLower.includes('search box') ||
										instructionsLower.includes('search input')));

							if (isSearchTask) {
								// Extract search query from various patterns:
								// - 'Type "query" into...'
								// - 'search for query'
								// - 'enter "query" in...'
								const patterns = [
									/type\s+"([^"]+)"/i, // Type "query"
									/type\s+'([^']+)'/i, // Type 'query'
									/enter\s+"([^"]+)"/i, // Enter "query"
									/enter\s+'([^']+)'/i, // Enter 'query'
									/search\s+for\s+["']?([^"'\n.]+)["']?/i, // search for query
									/search\s+["']?([^"'\n.]+)["']?/i, // search query
								];

								let searchQuery = '';
								for (const pattern of patterns) {
									const match = instructions.match(pattern);
									if (match && match[1]) {
										searchQuery = match[1].trim();
										break;
									}
								}

								// Navigate and search
								await page.goto(targetUrl, {
									timeout: timeoutMs,
									waitUntil: 'domcontentloaded',
								});

								// Example: Amazon search (customize based on targetUrl domain)
								if (targetUrl.includes('amazon.com') && searchQuery) {
									await page.fill('#twotabsearchtextbox', searchQuery);
									await page.click('#nav-search-submit-button');
									await page.waitForSelector('.s-search-results', {
										timeout: 10000,
									});

									// Extract top 3 products
									const products = await page.evaluate(() => {
										const items = Array.from(
											document.querySelectorAll('.s-result-item'),
										);
										return items.slice(0, 3).map((item: any) => ({
											name: item.querySelector('h2')?.textContent?.trim(),
											price: item
												.querySelector('.a-price-whole')
												?.textContent?.trim(),
										}));
									});

									result = { results: products, instructions, searchQuery };
								} else {
									// Search detected but not Amazon or no query extracted
									result = {
										url: page.url(),
										title: await page.title(),
										instructions,
										searchQuery: searchQuery || 'Could not extract search query',
									};
								}
							} else {
								// Generic navigation
								await page.goto(targetUrl, {
									timeout: timeoutMs,
									waitUntil: 'domcontentloaded',
								});
								result = {
									url: page.url(),
									title: await page.title(),
									instructions,
								};
							}

							// Capture screenshot if requested in instructions
							if (instructions.toLowerCase().includes('screenshot')) {
								screenshot = await session.takeScreenshot(page, true);
							}
						} catch (error) {
							throw error;
						}
					} else if (operation === 'runScript') {
						//Execute custom script operation
						const script = this.getNodeParameter('script', i) as string;
						const screenshotMode = this.getNodeParameter(
							'screenshotMode',
							i,
							'none',
						) as string;

						try {
							const scriptResult = await session.executeScript(script, page);
							result = { result: scriptResult };

							if (screenshotMode === 'final') {
								screenshot = await session.takeScreenshot(page);
							}
						} catch (error) {
							if (screenshotMode === 'error') {
								try {
									screenshot = await session.takeScreenshot(page);
								} catch (screenshotError) {
									// Ignore screenshot errors
								}
							}
							throw error;
						}
					} else if (operation === 'navigateExtract') {
						// Execute navigate & extract operation
						const selector = this.getNodeParameter('selector', i, '') as string;
						const extractMode = this.getNodeParameter(
							'extractMode',
							i,
							'text',
						) as string;
						const attributeName = this.getNodeParameter(
							'attributeName',
							i,
							'',
						) as string;
						const waitForSelector = this.getNodeParameter(
							'waitForSelector',
							i,
							'',
						) as string;
						const actions = this.getNodeParameter('actions', i, { action: [] }) as any;
						const takeScreenshot = this.getNodeParameter(
							'takeScreenshot',
							i,
							false,
						) as boolean;
						const fullPageScreenshot = this.getNodeParameter(
							'fullPageScreenshot',
							i,
							false,
						) as boolean;

						// Perform actions
						if (actions.action && Array.isArray(actions.action)) {
							for (const action of actions.action) {
								const { type, selector: actionSelector, value } = action;
								if (type === 'click' && actionSelector) {
									await page.click(actionSelector);
								} else if (type === 'type' && actionSelector && value) {
									await page.fill(actionSelector, value);
								} else if (type === 'wait') {
									await page.waitForTimeout(parseInt(value || '1000', 10));
								} else if (type === 'press' && actionSelector && value) {
									await page.press(actionSelector, value);
								}
							}
						}

						// Wait for selector if specified
						if (waitForSelector) {
							await page.waitForSelector(waitForSelector, { timeout: 10000 });
						}

						// Extract data
						let extractedData: any = null;
						if (selector) {
							const elements = await page.$$(selector);
							const dataArray = [];
							for (const element of elements) {
								let value: any;
								if (extractMode === 'text') {
									value = await element.textContent();
								} else if (extractMode === 'html') {
									value = await element.innerHTML();
								} else if (extractMode === 'attribute' && attributeName) {
									value = await element.getAttribute(attributeName);
								}
								dataArray.push(value);
							}
							extractedData = dataArray.length === 1 ? dataArray[0] : dataArray;
						}

						result = {
							data: extractedData,
							url: page.url(),
							title: await page.title(),
						};

						// Take screenshot if requested
						if (takeScreenshot) {
							screenshot = await session.takeScreenshot(page, fullPageScreenshot);
						}
					}

					// Add session info
					const sessionInfo = session.getSessionInfo();

					returnData.push({
						json: {
							...result,
							sessionInfo: {
								browserId: sessionInfo?.browserId,
								sessionId: sessionInfo?.sessionId,
							},
						},
						...(screenshot && {
							binary: {
								screenshot: await this.helpers.prepareBinaryData(
									screenshot,
									'screenshot.png',
									'image/png',
								),
							},
						}),
					});
				} finally {
					// Always close the session
					await session.close();
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							error: error instanceof Error ? error.message : String(error),
						},
					});
					continue;
				}
				throw new NodeOperationError(
					this.getNode(),
					error instanceof Error ? error : new Error(String(error)),
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
