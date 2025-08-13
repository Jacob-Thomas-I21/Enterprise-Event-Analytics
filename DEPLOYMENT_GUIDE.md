# 🚀 **DEPLOYMENT GUIDE - Enterprise Event Analytics**

## Prerequisites

Before deploying, ensure you have:
- Docker and Docker Compose installed
- Git installed
- OpenSSL for generating secure keys
- Access to your server/cloud environment

## 📋 **Step-by-Step Deployment**

### **STEP 1: Clone and Setup**

```bash
# Clone the repository
git clone <your-repo-url>
cd enterprise-event-analytics

# Make sure you're in the project root directory
ls -la
# You should see: docker-compose.yml, .env.example, backend/, frontend/, etc.
```

### **STEP 2: Generate Secure Keys**

```bash
# Generate JWT Secret Key (32+ characters)
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" > .env.keys

# Generate Encryption Key (32+ characters)
echo "ENCRYPTION_KEY=$(openssl rand -base64 32)" >> .env.keys

# Generate secure database passwords
echo "DB_PASSWORD=$(openssl rand -base64 16)" >> .env.keys
echo "REDIS_PASSWORD=$(openssl rand -base64 16)" >> .env.keys
echo "NEO4J_PASSWORD=$(openssl rand -base64 16)" >> .env.keys

# View generated keys
cat .env.keys
```

### **STEP 3: Configure Environment**

```bash
# Copy the secure environment template
cp .env.secure .env

# Edit the environment file with your values
nano .env
# OR
vim .env
```

**Update these critical values in `.env`:**

```env
# Database - Replace with generated passwords
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@postgres:5432/event_analytics
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
REDIS_URL=redis://:YOUR_REDIS_PASSWORD@redis:6379

# Security - Use generated keys from .env.keys
JWT_SECRET_KEY=YOUR_GENERATED_JWT_SECRET
ENCRYPTION_KEY=YOUR_GENERATED_ENCRYPTION_KEY

# Your API Keys
OPENROUTER_API_KEY=your-actual-openrouter-key

# Your Domain (for production)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
REACT_APP_API_URL=https://api.yourdomain.com
```

### **STEP 4: Update Docker Compose for Production**

```bash
# Edit docker-compose.yml to use environment variables
nano docker-compose.yml
```

Update the environment sections to use your `.env` file:

```yaml
# In docker-compose.yml, update these sections:
backend:
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    - REDIS_URL=${REDIS_URL}
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}

redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}

neo4j:
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
```

### **STEP 5: Deploy the Application**

```bash
# Stop any existing containers
docker-compose down

# Remove old volumes (CAUTION: This deletes data)
docker-compose down -v

# Build and start all services
docker-compose up --build -d

# Check if all services are running
docker-compose ps
```

### **STEP 6: Verify Deployment**

```bash
# Check service health
docker-compose logs backend | tail -20
docker-compose logs frontend | tail -20

# Test the API health endpoint
curl http://localhost:8000/api/health

# Test the frontend
curl http://localhost:3000
```

### **STEP 7: Get Default User Credentials**

```bash
# Check backend logs for generated passwords
docker-compose logs backend | grep "Created default"

# You'll see output like:
# Created default admin user with password: Xy9#mK2$pL8@nR4!
# Created default manager user with password: Qw7&vB3*hN6%sT9@
# Created default analyst user with password: Zx5!cV8$jM1&fG4#
```

### **STEP 8: First Login and Security Setup**

1. **Access the application**: http://localhost:3000
2. **Login with admin credentials** from Step 7
3. **Immediately change the password**:
   - Go to Settings/Profile
   - Change password to your secure password
4. **Repeat for manager and analyst accounts**

## 🌐 **Production Deployment (with SSL)**

### **Option A: Using Nginx Reverse Proxy**

```bash
# Create nginx configuration
mkdir -p nginx
cat > nginx/nginx.conf << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        proxy_pass http://frontend:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Update docker-compose.yml to include nginx service
# (nginx service is already configured in your docker-compose.yml)
```

### **Option B: Using Cloud Providers**

#### **AWS Deployment**
```bash
# Install AWS CLI and configure
aws configure

# Create ECS cluster
aws ecs create-cluster --cluster-name enterprise-analytics

# Build and push to ECR
aws ecr create-repository --repository-name enterprise-analytics-backend
aws ecr create-repository --repository-name enterprise-analytics-frontend

# Tag and push images
docker tag enterprise-analytics-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/enterprise-analytics-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/enterprise-analytics-backend:latest
```

#### **Google Cloud Deployment**
```bash
# Install gcloud CLI
gcloud init

# Create GKE cluster
gcloud container clusters create enterprise-analytics --num-nodes=3

# Deploy using kubectl
kubectl apply -f k8s/
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Services won't start**:
   ```bash
   # Check logs
   docker-compose logs
   
   # Check if ports are available
   netstat -tulpn | grep :8000
   netstat -tulpn | grep :3000
   ```

2. **Database connection errors**:
   ```bash
   # Check PostgreSQL
   docker-compose exec postgres psql -U postgres -d event_analytics -c "SELECT 1;"
   
   # Check Redis
   docker-compose exec redis redis-cli ping
   
   # Check Neo4j
   docker-compose exec neo4j cypher-shell -u neo4j -p your_password "RETURN 1;"
   ```

3. **Authentication not working**:
   ```bash
   # Check if API routes are registered
   curl http://localhost:8000/api/auth/verify-token
   
   # Check environment variables
   docker-compose exec backend env | grep JWT
   ```

### **Performance Optimization**

```bash
# For production, optimize Docker images
docker-compose -f docker-compose.prod.yml up -d

# Monitor resource usage
docker stats

# Scale services if needed
docker-compose up --scale backend=3 -d
```

## 📊 **Monitoring Setup**

```bash
# Access monitoring dashboards
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3001 (admin/admin)"

# Check application metrics
curl http://localhost:8000/api/metrics
```

## 🔒 **Security Checklist**

- [ ] All default passwords changed
- [ ] SSL/TLS certificates installed
- [ ] Firewall configured (only ports 80, 443 open)
- [ ] Environment variables secured
- [ ] Database backups configured
- [ ] Log monitoring enabled
- [ ] Rate limiting tested
- [ ] CORS origins restricted to your domains

## 🆘 **Emergency Commands**

```bash
# Stop all services immediately
docker-compose down

# Backup database
docker-compose exec postgres pg_dump -U postgres event_analytics > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres event_analytics < backup.sql

# View real-time logs
docker-compose logs -f backend

# Restart specific service
docker-compose restart backend
```

## 📞 **Support**

If you encounter issues:
1. Check the logs: `docker-compose logs [service-name]`
2. Verify environment variables: `docker-compose config`
3. Test individual services: `docker-compose up [service-name]`
4. Check network connectivity: `docker network ls`

---

**🎉 Congratulations!** Your Enterprise Event Analytics platform is now deployed with enterprise-grade security!

**Next Steps:**
1. Set up SSL certificates for production
2. Configure monitoring and alerting
3. Set up automated backups
4. Create user accounts for your team