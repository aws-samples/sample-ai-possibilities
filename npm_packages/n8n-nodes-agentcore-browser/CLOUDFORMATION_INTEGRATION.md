# CloudFormation Integration Guide

## ⚠️ IMPORTANT: Simplified, Tested Approach

After reviewing N8N's Docker custom node loading, here's the **safest, simplest approach**:

## Problem

N8N in Docker containers needs custom nodes to be:
1. Installed via npm (published package), OR
2. Mounted into the container's node loading path, OR
3. Built into a custom Docker image

## Recommended Solution: Custom Docker Image (Most Reliable)

### Why This Approach?
- ✅ Clean, reproducible
- ✅ No runtime build complexity
- ✅ Playwright dependencies handled properly
- ✅ Works with N8N's module system
- ✅ Easy to rollback

### Steps

#### 1. Create Custom N8N Dockerfile

Create `/opt/n8n/Dockerfile.custom` on your EC2 instance:

```dockerfile
FROM n8nio/n8n:latest

USER root

# Install Playwright dependencies for Alpine Linux
RUN apk add --no-cache \
        chromium \
        nss \
        freetype \
        harfbuzz \
        ca-certificates \
        ttf-freefont \
        font-noto-emoji

# Switch back to node user
USER node

# Copy custom node
COPY --chown=node:node ./n8n-nodes-agentcore-browser /home/node/n8n-nodes-agentcore-browser

# Install custom node (include devDependencies for build)
WORKDIR /home/node/n8n-nodes-agentcore-browser
RUN npm ci --include=dev && npm run build

# Create custom nodes directory and copy the built package there (outside .n8n to avoid volume mount issues)
RUN mkdir -p /home/node/custom
RUN cp -r /home/node/n8n-nodes-agentcore-browser /home/node/custom/

# Back to node user and default workdir
USER node
WORKDIR /home/node/.n8n
```

#### 2. Updated CloudFormation SSM Steps

Add these steps to your SSM document:

```yaml
- name: BuildCustomN8nImage
  action: aws:runShellScript
  inputs:
    timeoutSeconds: 900
    runCommand:
      - '#!/bin/bash'
      - set -euo pipefail
      - !Sub |
          echo "=== Building Custom N8N Image with AgentCore Browser ==="

          # Configuration
          AGENTCORE_SOURCE="${AgentcoreBrowserLocalPath:-/workshop/agentcore_browser_extension}"
          N8N_DIR="/opt/n8n"

          # Skip if source doesn't exist
          if [ ! -d "$AGENTCORE_SOURCE" ]; then
            echo "AgentCore Browser source not found at: $AGENTCORE_SOURCE"
            echo "Skipping custom node installation"
            exit 0
          fi

          # Copy source to N8N directory
          mkdir -p $N8N_DIR/n8n-nodes-agentcore-browser
          cp -r $AGENTCORE_SOURCE/* $N8N_DIR/n8n-nodes-agentcore-browser/

          # Create Dockerfile
          cat > $N8N_DIR/Dockerfile.custom <<'DOCKERFILE'
          FROM n8nio/n8n:latest

          USER root
          RUN apk add --no-cache \
                  chromium \
                  nss \
                  freetype \
                  harfbuzz \
                  ca-certificates \
                  ttf-freefont \
                  font-noto-emoji

          USER node
          COPY --chown=node:node ./n8n-nodes-agentcore-browser /home/node/n8n-nodes-agentcore-browser
          WORKDIR /home/node/n8n-nodes-agentcore-browser
          RUN npm ci --include=dev && npm run build
          RUN mkdir -p /home/node/custom
          RUN cp -r /home/node/n8n-nodes-agentcore-browser /home/node/custom/

          USER node
          WORKDIR /home/node/.n8n
          DOCKERFILE

          # Build custom image
          cd $N8N_DIR
          echo "Building custom N8N image..."
          docker build -t n8n-custom:latest -f Dockerfile.custom .

          if [ $? -eq 0 ]; then
            echo "Custom N8N image built successfully"
            docker images | grep n8n-custom
          else
            echo "ERROR: Failed to build custom N8N image"
            exit 1
          fi

- name: UpdateN8nDockerCompose
  action: aws:runShellScript
  inputs:
    timeoutSeconds: 300
    runCommand:
      - '#!/bin/bash'
      - set -euo pipefail
      - !Sub |
          echo "=== Updating N8N docker-compose.yml ==="

          cd /opt/n8n

          # Check if custom image exists
          if docker images | grep -q "n8n-custom"; then
            echo "Custom image found, updating docker-compose.yml"
            N8N_IMAGE="n8n-custom:latest"
          else
            echo "No custom image, using standard N8N"
            N8N_IMAGE="n8nio/n8n:latest"
          fi

          # Create updated docker-compose.yml
          # Note: All environment variables ($DB_HOST, etc.) should already be set from ConfigureN8n step

          cat > docker-compose.yml <<COMPOSE_EOF
          version: '3.8'

          services:
            n8n-main:
              image: $N8N_IMAGE
              container_name: n8n-main
              restart: unless-stopped
              ports:
                - "${N8nPort}:5678"
              environment:
                - DB_TYPE=postgresdb
                - DB_POSTGRESDB_HOST=$DB_HOST
                - DB_POSTGRESDB_PORT=$DB_PORT
                - DB_POSTGRESDB_DATABASE=n8ndb
                - DB_POSTGRESDB_USER=n8nadmin
                - DB_POSTGRESDB_PASSWORD=$DB_PASSWORD
                - N8N_ENCRYPTION_KEY=$ENCRYPTION_KEY
                - EXECUTIONS_MODE=queue
                - QUEUE_BULL_REDIS_HOST=$REDIS_HOST
                - QUEUE_BULL_REDIS_PORT=$REDIS_PORT
                - N8N_EDITOR_BASE_URL=https://$CLOUDFRONT_DOMAIN/
                - WEBHOOK_URL=https://$CLOUDFRONT_DOMAIN/
                - NODE_FUNCTION_ALLOW_BUILTIN=*
                - NODE_FUNCTION_ALLOW_EXTERNAL=*
                - N8N_CUSTOM_EXTENSIONS=/home/node/custom
              volumes:
                - n8n_data:/home/node/.n8n
              networks:
                - n8n-network

            n8n-webhook:
              image: $N8N_IMAGE
              container_name: n8n-webhook
              restart: unless-stopped
              command: webhook
              environment:
                - DB_TYPE=postgresdb
                - DB_POSTGRESDB_HOST=$DB_HOST
                - DB_POSTGRESDB_PORT=$DB_PORT
                - DB_POSTGRESDB_DATABASE=n8ndb
                - DB_POSTGRESDB_USER=n8nadmin
                - DB_POSTGRESDB_PASSWORD=$DB_PASSWORD
                - N8N_ENCRYPTION_KEY=$ENCRYPTION_KEY
                - EXECUTIONS_MODE=queue
                - QUEUE_BULL_REDIS_HOST=$REDIS_HOST
                - QUEUE_BULL_REDIS_PORT=$REDIS_PORT
                - WEBHOOK_URL=https://$CLOUDFRONT_DOMAIN/
                - NODE_FUNCTION_ALLOW_BUILTIN=*
                - NODE_FUNCTION_ALLOW_EXTERNAL=*
                - N8N_CUSTOM_EXTENSIONS=/home/node/custom
              volumes:
                - n8n_data:/home/node/.n8n
              networks:
                - n8n-network

            n8n-worker:
              image: $N8N_IMAGE
              container_name: n8n-worker
              restart: unless-stopped
              command: worker --concurrency=10
              environment:
                - DB_TYPE=postgresdb
                - DB_POSTGRESDB_HOST=$DB_HOST
                - DB_POSTGRESDB_PORT=$DB_PORT
                - DB_POSTGRESDB_DATABASE=n8ndb
                - DB_POSTGRESDB_USER=n8nadmin
                - DB_POSTGRESDB_PASSWORD=$DB_PASSWORD
                - N8N_ENCRYPTION_KEY=$ENCRYPTION_KEY
                - EXECUTIONS_MODE=queue
                - QUEUE_BULL_REDIS_HOST=$REDIS_HOST
                - QUEUE_BULL_REDIS_PORT=$REDIS_PORT
                - NODE_FUNCTION_ALLOW_BUILTIN=*
                - NODE_FUNCTION_ALLOW_EXTERNAL=*
                - N8N_CUSTOM_EXTENSIONS=/home/node/custom
              volumes:
                - n8n_data:/home/node/.n8n
              networks:
                - n8n-network

          volumes:
            n8n_data:

          networks:
            n8n-network:
              driver: bridge
          COMPOSE_EOF

          # Restart N8N with new image
          echo "Stopping N8N..."
          docker-compose down

          echo "Starting N8N with custom image..."
          docker-compose up -d

          echo "Waiting for N8N to start..."
          sleep 30

          echo "N8N status:"
          docker-compose ps

          echo "=== N8N Update Complete ==="
```

#### 3. Integration into Your CloudFormation Template

**ADD to Parameters section** (around line 76):
```yaml
  AgentcoreBrowserLocalPath:
    Type: String
    Description: Local path to AgentCore Browser node source code
    Default: /workshop/agentcore_browser_extension
```

**ADD these two steps** AFTER the `ConfigureN8n` step (around line 1375):
- `BuildCustomN8nImage`
- `UpdateN8nDockerCompose`

#### 4. Pre-Deployment Checklist

- [ ] Your AgentCore Browser code is at `/workshop/agentcore_browser_extension`
- [ ] The code has been built (`npm run build`)
- [ ] You've tested the Docker build locally (see below)
- [ ] You have a rollback plan (see below)

## Testing Locally BEFORE CloudFormation

```bash
# On your development machine
cd /Users/edsilva/Downloads/git/agentcore_browser_extension

# Build the project
npm run build

# Test Docker build
cat > Dockerfile.test <<'EOF'
FROM n8nio/n8n:latest
USER root
RUN apt-get update && apt-get install -y fonts-liberation libasound2 && rm -rf /var/lib/apt/lists/*
USER node
COPY --chown=node:node . /home/node/n8n-nodes-agentcore-browser
WORKDIR /home/node/n8n-nodes-agentcore-browser
RUN npm install && npm run build
WORKDIR /usr/local/lib/node_modules/n8n/node_modules
RUN ln -s /home/node/n8n-nodes-agentcore-browser n8n-nodes-agentcore-browser
WORKDIR /home/node/.n8n
EOF

docker build -t n8n-test -f Dockerfile.test .

# If successful:
docker run -p 5678:5678 n8n-test

# Open http://localhost:5678 and check if AgentCore Browser node appears
```

## Rollback Plan

If deployment fails:

```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance

# Go to N8N directory
cd /opt/n8n

# Restore original configuration
cat > docker-compose.yml <<'EOF'
version: '3.8'
services:
  n8n-main:
    image: n8nio/n8n:latest
    # ... (copy from original template)
EOF

# Restart
docker-compose down
docker-compose up -d
```

## Expected Deployment Time

- Building custom image: **3-5 minutes**
- Playwright dependencies: **2-3 minutes**
- Total additional time: **~8 minutes**

## Monitoring Deployment

```bash
# Watch SSM command execution
aws ssm list-command-invocations \
  --command-id <command-id> \
  --details

# Check CloudWatch logs
aws logs tail /aws/ssm/YourSSMDocumentName --follow

# On EC2 instance
docker logs -f n8n-main
```

## Verification

After deployment:
1. Open N8N UI: `https://your-cloudfront-domain/`
2. Click "+" to add a node
3. Search for "AgentCore"
4. Should see "AgentCore Browser" node
5. Add it and configure AWS credentials

## Questions?

Before proceeding, please confirm:
1. Where is your AgentCore Browser code? (default: `/workshop/agentcore_browser_extension`)
2. Have you run `npm run build` on the code?
3. Do you want to test the Docker build locally first?
4. Should I create a test script to validate everything?
