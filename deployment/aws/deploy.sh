#!/bin/bash

# AWS Deployment Script for Volatility Trading Bot
# This script deploys the bot to an EC2 instance with RDS PostgreSQL

set -e

echo "🚀 Starting AWS deployment for Volatility Trading Bot"

# Configuration
REGION=${AWS_REGION:-us-east-1}
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.micro}
KEY_PAIR_NAME=${KEY_PAIR_NAME:-volatility-bot-key}
SECURITY_GROUP_NAME="volatility-bot-sg"
INSTANCE_NAME="volatility-trading-bot"
DB_INSTANCE_NAME="volatility-bot-db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in to AWS
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

print_status "AWS credentials verified"

# Create security group
print_status "Creating security group..."
aws ec2 create-security-group \
    --group-name $SECURITY_GROUP_NAME \
    --description "Security group for volatility trading bot" \
    --region $REGION || print_warning "Security group may already exist"

# Add security group rules
print_status "Configuring security group rules..."
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP_NAME \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region $REGION || print_warning "SSH rule may already exist"

aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP_NAME \
    --protocol tcp \
    --port 8501 \
    --cidr 0.0.0.0/0 \
    --region $REGION || print_warning "Dashboard rule may already exist"

aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP_NAME \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0 \
    --region $REGION || print_warning "Health check rule may already exist"

# Create RDS subnet group
print_status "Creating RDS subnet group..."
aws rds create-db-subnet-group \
    --db-subnet-group-name volatility-bot-subnet-group \
    --db-subnet-group-description "Subnet group for volatility bot database" \
    --subnet-ids $(aws ec2 describe-subnets --region $REGION --query 'Subnets[0:2].SubnetId' --output text) \
    --region $REGION || print_warning "Subnet group may already exist"

# Create RDS instance
print_status "Creating RDS PostgreSQL instance (this may take 5-10 minutes)..."
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_NAME \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username botuser \
    --master-user-password BotPassword123! \
    --allocated-storage 20 \
    --storage-type gp2 \
    --db-name trading_bot \
    --vpc-security-group-ids $(aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --region $REGION --query 'SecurityGroups[0].GroupId' --output text) \
    --db-subnet-group-name volatility-bot-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted \
    --region $REGION || print_warning "RDS instance may already exist"

# Wait for RDS to be available
print_status "Waiting for RDS instance to be available..."
aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_NAME --region $REGION

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_NAME \
    --region $REGION \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

print_status "RDS endpoint: $RDS_ENDPOINT"

# Create user data script
cat > user-data.sh << EOF
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /home/ec2-user
git clone https://github.com/Hussein1147/volatility-trading-bot.git
cd volatility-trading-bot

# Create .env file
cat > .env << ENVEOF
ALPACA_API_KEY=${ALPACA_API_KEY}
ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
DATABASE_URL=postgresql://botuser:BotPassword123!@${RDS_ENDPOINT}:5432/trading_bot
ENVIRONMENT=production
ENVEOF

# Create production docker-compose file
cat > docker-compose.prod.yml << PRODEOF
version: '3.8'

services:
  trading-bot:
    build: .
    environment:
      - ALPACA_API_KEY=\${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=\${ALPACA_SECRET_KEY}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
      - DATABASE_URL=\${DATABASE_URL}
      - ENVIRONMENT=production
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    command: python enhanced_volatility_bot.py

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    environment:
      - DATABASE_URL=\${DATABASE_URL}
    ports:
      - "8501:8501"
    restart: unless-stopped

volumes:
  logs:
PRODEOF

# Set permissions
chown -R ec2-user:ec2-user /home/ec2-user/volatility-trading-bot

# Start services
cd /home/ec2-user/volatility-trading-bot
docker-compose -f docker-compose.prod.yml up -d
EOF

# Launch EC2 instance
print_status "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_PAIR_NAME \
    --security-groups $SECURITY_GROUP_NAME \
    --user-data file://user-data.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

print_status "EC2 instance created: $INSTANCE_ID"

# Wait for instance to be running
print_status "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

# Cleanup
rm -f user-data.sh

print_status "🎉 Deployment completed successfully!"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo ""
echo "📊 Dashboard URL: http://$PUBLIC_IP:8501"
echo "🔍 Health Check: http://$PUBLIC_IP:8080/health"
echo ""
echo "📝 SSH Access: ssh -i ~/.ssh/${KEY_PAIR_NAME}.pem ec2-user@$PUBLIC_IP"
echo ""
print_warning "Please wait 5-10 minutes for the services to fully start up."
print_status "You can monitor the logs with: ssh -i ~/.ssh/${KEY_PAIR_NAME}.pem ec2-user@$PUBLIC_IP 'cd volatility-trading-bot && docker-compose logs -f'"
