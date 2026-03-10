---
name: aws-setup
description: "Activate when the user needs help with AWS access, credentials, Workshop Studio login, or environment setup"
---

# AWS Setup & Environment Configuration

Guide for setting up AWS Workshop Studio access, extracting credentials, and launching SageMaker Studio for the Agentic Football World Cup workshop.

## Supported Regions

| Region | Code |
|--------|------|
| US East (N. Virginia) | `us-east-1` |
| US West (Oregon) | `us-west-2` |

Select the region as directed by your workshop support staff.

## Workshop Studio Login Flow

### Step 1: Enter Event Access Code

1. Go to [Workshop Studio](https://catalog.workshops.aws/join)
2. Enter the **12-digit event access code** provided by your AWS instructor
3. Click **Next**

### Step 2: Authenticate with OTP

1. Select **One Time Password (OTP)** (or use **Login with Amazon** if preferred)
2. Enter a valid email address and select **Send passcode**
3. Check your email for the one-time passcode:
   - **Subject:** "Your one-time passcode"
   - **Body:** A 9-digit number
4. Enter the 9-digit passcode and select **Sign in**

> If you cannot log in, contact your AWS instructor for assistance.

### Step 3: Review and Join Event

1. On the **Review and join** page, review the terms and conditions
2. Accept the terms and select **Join Event**

### Step 4: Access Workshop and AWS Console

1. Click **Get started** (right side) to access workshop content
2. Click **Open AWS console** (left menu) to access your AWS account
3. The **Outputs** section provides details needed throughout the competition
4. You should now be on the **AWS Management Console** home page

## Credential Extraction

To use the AWS CLI or SDK from your local environment, you need to extract credentials from Workshop Studio.

### Getting AWS CLI Credentials

1. In the Workshop Studio portal, navigate to **AWS Account Access**
2. Select **Get AWS CLI credentials**
3. Copy the provided credentials (Access Key ID, Secret Access Key, Session Token)
4. Configure your terminal using one of these methods:

**Option A: Environment Variables**

```bash
export AWS_ACCESS_KEY_ID="<your-access-key>"
export AWS_SECRET_ACCESS_KEY="<your-secret-key>"
export AWS_SESSION_TOKEN="<your-session-token>"
export AWS_DEFAULT_REGION="us-east-1"  # or us-west-2
```

**Option B: AWS CLI Configure**

```bash
aws configure
# Enter Access Key ID, Secret Access Key, and region when prompted
# For session token, set it separately:
export AWS_SESSION_TOKEN="<your-session-token>"
```

### Verifying Credentials

```bash
aws sts get-caller-identity
```

If successful, this returns your account ID, user ARN, and user ID. If it fails, re-extract credentials from Workshop Studio — session tokens expire periodically.

> **Note:** Workshop Studio credentials are temporary. If you get authentication errors during the workshop, return to the portal and re-extract fresh credentials.

## SageMaker Studio Access

For participants using the notebook-based workflow:

### Launching SageMaker Studio

1. In the AWS console, search for **SageMaker AI** in the top search bar
2. Navigate to the Amazon SageMaker AI console
3. In the left sidebar, under **Applications and IDEs**, select **Studio**
4. In the **Get started** box, ensure **user-profile-1** is selected
5. Select **Open studio** — SageMaker Studio opens in a new browser tab
6. Optionally take the quick tour or select **Skip Tour for now**
7. Accept or decline cookie preferences

### Using Notebooks in SageMaker Studio

Once in SageMaker Studio, you can:

- Open and run Jupyter notebooks for building your football agent
- Access pre-configured environments with required dependencies
- Use the integrated terminal for CLI operations

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot log in to Workshop Studio | Verify the 12-digit access code with your instructor |
| OTP email not received | Check spam folder; wait 1 minute; try resending |
| AWS console shows wrong region | Use the region selector in the top-right to switch to `us-east-1` or `us-west-2` |
| `aws sts get-caller-identity` fails | Re-extract credentials from Workshop Studio portal |
| Session token expired | Return to Workshop Studio and get fresh CLI credentials |
| SageMaker Studio won't open | Ensure you selected the correct user profile (`user-profile-1`) |

## Prerequisites

- AWS Workshop Studio access (provided by event staff)
- 12-digit event access code
- Valid email address (for OTP authentication)
- AWS CLI installed locally (for credential-based workflows)
- Python 3.x (for agent development)

## References

- Workshop Studio portal: https://catalog.workshops.aws/join
- Workshop content: https://catalog.workshops.aws/agentic-football
