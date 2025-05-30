#!/bin/bash

# Code Deployment Script for Volatility Trading Bot
# This script deploys the application code to an existing EC2 instance using AWS Systems Manager

set -e

INSTANCE_ID=$1
if [ -z "$INSTANCE_ID" ]; then
    echo "Usage: $0 <instance-id>"
    echo "Example: $0 i-1234567890abcdef0"
    exit 1
fi

echo "=== Deploying Code to Instance: $INSTANCE_ID ==="

# Check if instance is running
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text)
if [ "$INSTANCE_STATE" != "running" ]; then
    echo "Error: Instance $INSTANCE_ID is not in running state (current state: $INSTANCE_STATE)"
    exit 1
fi

echo "✓ Instance is running"

# Create temporary deployment package
TEMP_DIR=$(mktemp -d)
echo "Creating deployment package..."

# Copy application files
cp -r /Users/djibrilkeita/Crisp/data_intergration/volatility-trading-bot/*.py "$TEMP_DIR/" 2>/dev/null || true
cp /Users/djibrilkeita/Crisp/data_intergration/volatility-trading-bot/requirements.txt "$TEMP_DIR/" 2>/dev/null || true

# Create deployment script
cat > "$TEMP_DIR/install.sh" << 'EOF'
#!/bin/bash
cd /opt/volatility-bot

# Install Python dependencies
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
fi

# Set proper permissions
chown -R ec2-user:ec2-user /opt/volatility-bot
chmod +x *.py

# Start the service
systemctl daemon-reload
systemctl start volatility-bot
systemctl status volatility-bot

echo "Application deployed and started successfully"
EOF

chmod +x "$TEMP_DIR/install.sh"

# Create a tarball
cd "$TEMP_DIR"
tar -czf deployment.tar.gz *

echo "✓ Deployment package created"

# Upload and execute via Systems Manager
echo "Uploading and deploying code..."

# Create S3 bucket for deployment if it doesn't exist
BUCKET_NAME="volatility-bot-deployments-$(date +%s)"
aws s3 mb s3://"$BUCKET_NAME" 2>/dev/null || true

# Upload deployment package
aws s3 cp deployment.tar.gz s3://"$BUCKET_NAME"/deployment.tar.gz

# Execute deployment via SSM
COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
        "cd /opt/volatility-bot",
        "aws s3 cp s3://'"$BUCKET_NAME"'/deployment.tar.gz .",
        "tar -xzf deployment.tar.gz",
        "bash install.sh"
    ]' \
    --query 'Command.CommandId' \
    --output text)

echo "✓ Deployment command sent: $COMMAND_ID"
echo "Waiting for deployment to complete..."

# Wait for command to complete
aws ssm wait command-executed --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID"

# Get command output
COMMAND_STATUS=$(aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query 'Status' \
    --output text)

if [ "$COMMAND_STATUS" = "Success" ]; then
    echo "✓ Deployment completed successfully"
    
    # Show service status
    echo ""
    echo "=== Service Status ==="
    aws ssm send-command \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=["systemctl status volatility-bot --no-pager"]' \
        --query 'Command.CommandId' \
        --output text > /dev/null
    
    sleep 3
    
    echo "Application has been deployed and started on instance $INSTANCE_ID"
    echo ""
    echo "To check logs:"
    echo "  aws ssm start-session --target $INSTANCE_ID"
    echo "  sudo journalctl -u volatility-bot -f"
else
    echo "✗ Deployment failed"
    # Show error output
    aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --query 'StandardErrorContent' \
        --output text
fi

# Cleanup
rm -rf "$TEMP_DIR"
aws s3 rm s3://"$BUCKET_NAME"/deployment.tar.gz 2>/dev/null || true
aws s3 rb s3://"$BUCKET_NAME" 2>/dev/null || true

echo "Cleanup completed"