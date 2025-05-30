# AWS Deployment for Volatility Trading Bot

This directory contains scripts for deploying the volatility trading bot to AWS EC2 without SSH key requirements.

## Prerequisites

1. AWS CLI installed and configured
2. Appropriate IAM permissions for EC2, S3, and Systems Manager
3. Default VPC available in your AWS region

## Deployment Process

### Step 1: Launch EC2 Instance

```bash
./deploy.sh
```

This script will:
- Create a security group if needed
- Launch an EC2 instance without SSH keys
- Configure the instance with necessary dependencies
- Set up a systemd service for the bot

### Step 2: Deploy Application Code

```bash
./deploy-code.sh <instance-id>
```

Replace `<instance-id>` with the instance ID returned from step 1.

This script will:
- Package your application code
- Upload it to the EC2 instance via AWS Systems Manager
- Install dependencies and start the service

## Security Features

- **No SSH Keys**: Instances are launched without SSH key pairs for enhanced security
- **Systems Manager Access**: Use AWS Systems Manager Session Manager for secure access
- **Minimal Security Group**: Only allows necessary outbound connections

## Connecting to Your Instance

To access the instance without SSH:

```bash
aws ssm start-session --target <instance-id>
```

## Monitoring and Management

### Check Service Status
```bash
aws ssm send-command \
    --instance-ids <instance-id> \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["systemctl status volatility-bot"]'
```

### View Logs
```bash
# Start session first
aws ssm start-session --target <instance-id>

# Then view logs
sudo journalctl -u volatility-bot -f
```

### Stop Instance
```bash
aws ec2 stop-instances --instance-ids <instance-id>
```

### Terminate Instance
```bash
aws ec2 terminate-instances --instance-ids <instance-id>
```

## Configuration

You can customize the deployment by setting environment variables:

- `INSTANCE_TYPE`: EC2 instance type (default: t3.micro)
- `AMI_ID`: Amazon Machine Image ID (default: Amazon Linux 2)

Example:
```bash
INSTANCE_TYPE=t3.small ./deploy.sh
```

## Troubleshooting

1. **AWS CLI not configured**: Run `aws configure` to set up credentials
2. **No default VPC**: Create a VPC in your AWS region
3. **Permission denied**: Ensure your IAM user/role has necessary permissions
4. **Instance not accessible**: Check security group rules and instance state

## Files

- `deploy.sh`: Main deployment script for launching EC2 instance
- `deploy-code.sh`: Script for deploying application code to existing instance
- `README.md`: This documentation file