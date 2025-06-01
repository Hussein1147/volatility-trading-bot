# Cloud Deployment Architecture

## Overview
This document outlines the cloud deployment strategy for the Volatility Trading Bot with monitoring dashboard.

## Architecture Components

### 1. Compute Infrastructure
**Option A: AWS**
- **EC2 Instance**: t3.micro (1 vCPU, 1GB RAM) - sufficient for the bot
- **EBS Storage**: 8GB GP3 for OS and logs
- **CloudWatch**: For monitoring and scheduling
- **RDS**: PostgreSQL micro instance for trade data

**Option B: GCP** 
- **Compute Engine**: e2-micro (1 vCPU, 1GB RAM)
- **Persistent Disk**: 10GB for storage
- **Cloud Scheduler**: For market hours automation
- **Cloud SQL**: PostgreSQL micro for trade data

### 2. Application Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Trading Bot   │───▶│    Database      │◀───│   Dashboard     │
│   (Container)   │    │   (PostgreSQL)   │    │   (Streamlit)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Alpaca API     │    │  Trade History   │    │  Web Interface  │
│  Claude API     │    │  Metrics Store   │    │  Real-time Data │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 3. Scheduling Strategy
- **Market Hours**: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
- **Weekend/Holiday**: Bot automatically detects and sleeps
- **Monitoring**: 24/7 dashboard availability

### 4. Security
- Environment variables stored in cloud secrets manager
- VPC with private subnets for database
- HTTPS for dashboard
- API key rotation capability

## Deployment Options

### Recommended: AWS Deployment
**Monthly Cost Estimate: ~$25-30**
- EC2 t3.micro: ~$8.50
- RDS db.t3.micro: ~$15
- EBS Storage: ~$1
- CloudWatch: ~$2
- Data Transfer: ~$1

### Alternative: GCP Deployment  
**Monthly Cost Estimate: ~$20-25**
- Compute Engine e2-micro: ~$6
- Cloud SQL micro: ~$12
- Storage: ~$1
- Other services: ~$3

## Dashboard Features
- Real-time trade monitoring
- P&L tracking and charts
- Position management
- IV rank/percentile graphs
- Trade history with filtering
- Performance metrics
- Alert management

## Deployment Steps
1. Create cloud resources (VM, database, networking)
2. Configure environment secrets
3. Deploy containerized bot
4. Set up monitoring dashboard
5. Configure scheduling and alerts
6. Test end-to-end functionality