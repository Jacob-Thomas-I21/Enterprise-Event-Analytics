#!/bin/bash

# 🚀 Enterprise Event Analytics - Quick Deploy Script
# This script automates the deployment process

set -e  # Exit on any error

echo "🚀 Starting Enterprise Event Analytics Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose found ✓"

# Step 1: Generate secure keys
print_status "Generating secure keys..."

if [ ! -f .env.keys ]; then
    echo "# Generated secure keys - $(date)" > .env.keys
    echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env.keys
    echo "ENCRYPTION_KEY=$(openssl rand -base64 32)" >> .env.keys
    echo "DB_PASSWORD=$(openssl rand -base64 16)" >> .env.keys
    echo "REDIS_PASSWORD=$(openssl rand -base64 16)" >> .env.keys
    echo "NEO4J_PASSWORD=$(openssl rand -base64 16)" >> .env.keys
    print_success "Secure keys generated in .env.keys"
else
    print_warning ".env.keys already exists, skipping key generation"
fi

# Step 2: Setup environment file
print_status "Setting up environment configuration..."

if [ ! -f .env ]; then
    if [ -f .env.secure ]; then
        cp .env.secure .env
        print_success "Environment file created from .env.secure template"
        
        # Source the generated keys
        source .env.keys
        
        # Replace placeholders in .env file
        sed -i "s/CHANGE_THIS_PASSWORD/${DB_PASSWORD}/g" .env
        sed -i "s/GENERATE_A_SECURE_32_CHAR_SECRET_KEY_HERE_12345/${JWT_SECRET_KEY}/g" .env
        sed -i "s/GENERATE_A_SECURE_32_CHAR_ENCRYPTION_KEY_HERE/${ENCRYPTION_KEY}/g" .env
        
        print_success "Environment variables updated with secure values"
    else
        print_error ".env.secure template not found!"
        exit 1
    fi
else
    print_warning ".env already exists, skipping environment setup"
fi

# Step 3: Stop existing containers
print_status "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Step 4: Build and start services
print_status "Building and starting services..."
docker-compose up --build -d

# Step 5: Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Step 6: Check service health
print_status "Checking service health..."

# Check if backend is responding
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    print_success "Backend API is healthy ✓"
else
    print_warning "Backend API health check failed, checking logs..."
    docker-compose logs backend | tail -10
fi

# Check if frontend is responding
if curl -f http://localhost:3000 >/dev/null 2>&1; then
    print_success "Frontend is healthy ✓"
else
    print_warning "Frontend health check failed, checking logs..."
    docker-compose logs frontend | tail -10
fi

# Step 7: Display default credentials
print_status "Extracting default user credentials..."
sleep 5  # Give time for user creation

echo ""
echo "🔐 DEFAULT USER CREDENTIALS:"
echo "=================================="
docker-compose logs backend | grep -A1 -B1 "Created default.*user with password" | grep -E "(admin|manager|analyst)" || {
    print_warning "Default credentials not found in logs yet. Check logs manually:"
    echo "docker-compose logs backend | grep 'Created default'"
}

# Step 8: Display access information
echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo "Frontend URL: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Health: http://localhost:8000/api/health"
echo "API Docs: http://localhost:8000/api/docs"
echo ""
echo "Monitoring:"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3001 (admin/admin)"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Access the frontend at http://localhost:3000"
echo "2. Login with the admin credentials shown above"
echo "3. IMMEDIATELY change all default passwords"
echo "4. Configure your domain settings for production"
echo ""
echo "📊 USEFUL COMMANDS:"
echo "- View logs: docker-compose logs [service-name]"
echo "- Stop services: docker-compose down"
echo "- Restart: docker-compose restart [service-name]"
echo ""

# Step 9: Final security reminder
print_warning "🚨 SECURITY REMINDER:"
echo "- Change all default passwords immediately"
echo "- Update .env with your actual API keys"
echo "- Configure SSL/TLS for production"
echo "- Restrict CORS origins to your domains"

print_success "Deployment completed successfully! 🎉"