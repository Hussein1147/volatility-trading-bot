#!/bin/bash

# AWS EC2 Deployment Script for Volatility Trading Bot
# This script deploys the volatility trading bot to AWS EC2 without SSH key requirements

set -e  # Exit on any error

# Configuration variables
INSTANCE_TYPE=${INSTANCE_TYPE:-"t3.micro"}
AMI_ID=${AMI_ID:-"ami-0c02fb55956c7d316"}  # Amazon Linux 2 AMI (us-east-1)
SECURITY_GROUP_NAME="volatility-bot-sg"
INSTANCE_NAME="volatility-trading-bot"

echo "=== Volatility Trading Bot AWS Deployment ==="
echo "Instance Type: $INSTANCE_TYPE"
echo "AMI ID: $AMI_ID"
echo ""

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✓ AWS CLI configured successfully"

# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "Error: No default VPC found. Please create a VPC first."
    exit 1
fi
echo "✓ Using VPC: $VPC_ID"

# Create security group if it doesn't exist
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [ "$SECURITY_GROUP_ID" = "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo "Creating security group: $SECURITY_GROUP_NAME"
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for volatility trading bot" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' \
        --output text)
    
    # Add rules for HTTP/HTTPS (if needed for APIs)
    aws ec2 authorize-security-group-egress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
    
    aws ec2 authorize-security-group-egress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
    
    echo "✓ Security group created: $SECURITY_GROUP_ID"
else
    echo "✓ Using existing security group: $SECURITY_GROUP_ID"
fi

# Create user data script for instance initialization
USER_DATA=$(cat << 'EOF'
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git

# Create application directory
mkdir -p /opt/volatility-bot
cd /opt/volatility-bot

# Create a simple systemd service for the bot
cat > /etc/systemd/system/volatility-bot.service << 'EOL'
[Unit]
Description=Volatility Trading Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/volatility-bot
ExecStart=/usr/bin/python3 /opt/volatility-bot/volatility_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Enable the service (will start after code is deployed)
systemctl enable volatility-bot

# Install CloudWatch agent for monitoring (optional)
yum install -y amazon-cloudwatch-agent

echo "Instance initialization completed" > /var/log/volatility-bot-init.log
EOF
)

echo "Launching EC2 instance..."

# Launch EC2 instance without SSH key
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --count 1 \
    --instance-type "$INSTANCE_TYPE" \
    --security-group-ids "$SECURITY_GROUP_ID" \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

if [ -z "$INSTANCE_ID" ]; then
    echo "Error: Failed to launch EC2 instance"
    exit 1
fi

echo "✓ EC2 instance launched: $INSTANCE_ID"
echo "Waiting for instance to be in running state..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get instance details
INSTANCE_INFO=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0]')
PUBLIC_IP=$(echo "$INSTANCE_INFO" | jq -r '.PublicIpAddress // "N/A"')
PRIVATE_IP=$(echo "$INSTANCE_INFO" | jq -r '.PrivateIpAddress // "N/A"')
AVAILABILITY_ZONE=$(echo "$INSTANCE_INFO" | jq -r '.Placement.AvailabilityZone // "N/A"')

echo ""
echo "=== Deployment Successful ==="
echo "Instance ID: $INSTANCE_ID"
echo "Instance Type: $INSTANCE_TYPE"
echo "Public IP: $PUBLIC_IP"
echo "Private IP: $PRIVATE_IP"
echo "Availability Zone: $AVAILABILITY_ZONE"
echo "Security Group: $SECURITY_GROUP_ID"
echo ""
echo "=== Next Steps ==="
echo "1. The instance is now running and will automatically install dependencies"
echo "2. Deploy your volatility bot code using AWS Systems Manager Session Manager or CodeDeploy"
echo "3. Monitor the instance using CloudWatch or AWS Systems Manager"
echo "4. To connect without SSH, use: aws ssm start-session --target $INSTANCE_ID"
echo ""
echo "=== Instance Management ==="
echo "To stop the instance:"
echo "  aws ec2 stop-instances --instance-ids $INSTANCE_ID"
echo ""
echo "To terminate the instance:"
echo "  aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
echo ""
echo "To check instance status:"
echo "  aws ec2 describe-instances --instance-ids $INSTANCE_ID"
echo ""
echo "Note: This instance was launched without SSH keys for enhanced security."
echo "Use AWS Systems Manager Session Manager for secure access if needed."