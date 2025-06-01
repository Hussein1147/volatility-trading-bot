#!/bin/bash

# Local Development Setup Script for Volatility Trading Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}$1${NC}"
}

clear
echo "🚀 Volatility Trading Bot - Local Development Setup"
echo "=================================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker Desktop first."
    print_status "Download from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.template .env
        print_warning "Please edit .env file with your API keys before continuing."
        echo ""
        print_header "Required API Keys:"
        echo "1. Alpaca API Key & Secret (from alpaca.markets)"
        echo "2. Anthropic API Key (from console.anthropic.com)"
        echo ""
        read -p "Press Enter after updating .env file..."
    else
        print_error ".env.template file not found!"
        exit 1
    fi
fi

# Create logs directory
print_status "Creating logs directory..."
mkdir -p logs

# Start services
print_status "Starting PostgreSQL database..."
docker-compose up -d postgres

print_status "Waiting for database to be ready..."
sleep 10

# Check if database is ready
print_status "Checking database connection..."
until docker-compose exec postgres pg_isready -U bot_user -d trading_bot; do
    print_status "Waiting for database..."
    sleep 2
done

print_status "Database is ready!"

# Build and start all services
print_status "Building and starting all services..."
docker-compose up -d

print_status "Services started successfully!"

echo ""
print_header "🎉 Setup Complete!"
echo ""
print_status "Services Available:"
echo "  📊 Dashboard: http://localhost:8501"
echo "  🔍 Bot Health: http://localhost:8080/health"
echo "  🗄️  Database: localhost:5432"
echo ""
print_status "Useful Commands:"
echo "  📋 View logs: docker-compose logs -f"
echo "  📋 View bot logs: docker-compose logs -f trading-bot"
echo "  📋 View dashboard logs: docker-compose logs -f dashboard"
echo "  🛑 Stop services: docker-compose down"
echo "  🔄 Restart services: docker-compose restart"
echo ""
print_warning "The bot will only trade during market hours (9:30 AM - 4:00 PM ET)."
print_status "Monitor the dashboard for real-time updates and trade activity."

# Open dashboard in browser (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_status "Opening dashboard in browser..."
    sleep 3
    open http://localhost:8501
fi