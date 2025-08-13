# Deployment Guide

This guide covers deploying the Enterprise Event Analytics Platform to various environments.

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker and Docker Compose
- Git
- OpenRouter API key (sign up at [openrouter.ai](https://openrouter.ai))

### Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd enterprise-event-analytics
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start the application**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- Neo4j Browser: http://localhost:7474
- Grafana: http://localhost:3001

5. **Default Login Credentials**
- Admin: admin@company.com / admin123
- Manager: manager@company.com / manager123
- Analyst: analyst@company.com / analyst123

## 🌐 Production Deployment

### AWS ECS Deployment

1. **Create ECS Cluster**
```bash
aws ecs create-cluster --cluster-name enterprise-analytics
```

2. **Build and Push Images**
```bash
# Build backend image
docker build -t enterprise-backend ./backend
docker tag enterprise-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/enterprise-backend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/enterprise-backend:latest

# Build frontend image
docker build -t enterprise-frontend ./frontend
docker tag enterprise-frontend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/enterprise-frontend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/enterprise-frontend:latest
```

3. **Create Task Definitions**
```json
{
  "family": "enterprise-analytics",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/enterprise-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/enterprise-analytics",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run Deployment

1. **Enable APIs**
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sql-component.googleapis.com
```

2. **Deploy Backend**
```bash
gcloud run deploy enterprise-backend \
  --source ./backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL
```

3. **Deploy Frontend**
```bash
gcloud run deploy enterprise-frontend \
  --source ./frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars REACT_APP_API_URL=$BACKEND_URL
```

### Azure Container Instances

1. **Create Resource Group**
```bash
az group create --name enterprise-analytics --location eastus
```

2. **Deploy with Docker Compose**
```bash
az container create \
  --resource-group enterprise-analytics \
  --file docker-compose.yml \
  --name enterprise-analytics
```

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
NEO4J_URI=bolt://host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://host:6379

# Security
JWT_SECRET_KEY=your-32-character-secret-key
ENCRYPTION_KEY=your-32-character-encryption-key

# AI
OPENROUTER_API_KEY=your-openrouter-key
AI_MODEL=anthropic/claude-3-haiku

# Application
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
```

### Database Setup

1. **PostgreSQL**
```sql
CREATE DATABASE event_analytics;
CREATE USER analytics_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE event_analytics TO analytics_user;
```

2. **Neo4j**
```cypher
// Create indexes
CREATE INDEX user_email IF NOT EXISTS FOR (u:User) ON (u.email);
CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.type);
```

## 🔒 Security Configuration

### SSL/TLS Setup

1. **Generate SSL Certificates**
```bash
# Using Let's Encrypt
certbot certonly --standalone -d yourdomain.com
```

2. **Nginx Configuration**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw deny 5432   # PostgreSQL (internal only)
ufw deny 6379   # Redis (internal only)
ufw deny 7687   # Neo4j (internal only)
```

## 📊 Monitoring Setup

### Prometheus Configuration
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'enterprise-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/api/metrics'
```

### Grafana Dashboards

Import the provided dashboard configurations:
- System Metrics Dashboard
- Application Performance Dashboard
- Security Events Dashboard
- Business Analytics Dashboard

## 🔄 CI/CD Pipeline

### GitHub Actions
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and Deploy
        run: |
          docker build -t enterprise-backend ./backend
          docker build -t enterprise-frontend ./frontend
          # Deploy to your cloud provider
```

## 🧪 Health Checks

### Application Health
```bash
# Backend health
curl -f http://localhost:8000/api/health

# Database health
curl -f http://localhost:8000/api/health | jq '.databases'

# Frontend health
curl -f http://localhost:3000
```

### Monitoring Endpoints
- `/api/health` - Application health status
- `/api/metrics` - Prometheus metrics
- `/api/admin/system-status` - Detailed system information

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**
```bash
# Check database connectivity
docker exec -it postgres psql -U postgres -d event_analytics -c "SELECT 1;"
```

2. **Redis Connection Failed**
```bash
# Check Redis connectivity
docker exec -it redis redis-cli ping
```

3. **Neo4j Connection Failed**
```bash
# Check Neo4j connectivity
docker exec -it neo4j cypher-shell -u neo4j -p password "RETURN 1;"
```

### Log Analysis
```bash
# View application logs
docker logs enterprise-backend
docker logs enterprise-frontend

# View database logs
docker logs postgres
docker logs neo4j
docker logs redis
```

## 📈 Scaling

### Horizontal Scaling
- Use load balancers for multiple backend instances
- Scale workers independently based on queue depth
- Use database read replicas for analytics queries

### Vertical Scaling
- Increase container resources based on metrics
- Optimize database queries and indexing
- Implement caching strategies

## 🔐 Backup Strategy

### Database Backups
```bash
# PostgreSQL backup
pg_dump -h localhost -U postgres event_analytics > backup.sql

# Neo4j backup
neo4j-admin backup --backup-dir=/backups --name=graph.db-backup

# Redis backup
redis-cli --rdb dump.rdb
```

### Automated Backups
Set up automated backups using cloud provider tools or cron jobs.

## 📞 Support

For deployment issues:
1. Check the logs first
2. Verify environment variables
3. Test database connections
4. Review security configurations
5. Contact support with detailed error messages

---

This deployment guide ensures a secure, scalable, and maintainable production deployment of the Enterprise Event Analytics Platform.