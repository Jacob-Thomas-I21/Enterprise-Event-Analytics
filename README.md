# Enterprise Event-Driven Analytics Platform

A production-ready, enterprise-grade event analytics platform with JWT authentication, role-based access control, real-time dashboards, and comprehensive security features.

## 🏗️ Architecture

- **Backend**: FastAPI with JWT authentication and role-based access
- **Frontend**: React with modern dashboard and real-time updates
- **Database**: PostgreSQL + Neo4j for graph analytics
- **Queue**: Redis for event processing
- **Security**: Enterprise-grade encryption and validation
- **Deployment**: Docker containers ready for cloud deployment

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository>
cd enterprise-event-analytics

# Start with Docker
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Admin Dashboard: http://localhost:3000/admin
```

## 🔐 Default Credentials

- **Admin**: admin@company.com / admin123
- **Manager**: manager@company.com / manager123
- **Analyst**: analyst@company.com / analyst123

## 📊 Features

### Core Analytics
- Real-time event ingestion and processing
- 15+ built-in event processors (Lead Scoring, Blockchain, Chat, E-commerce, etc.)
- Advanced graph analytics with Neo4j
- Custom dashboard creation

### Enterprise Security
- JWT authentication with refresh tokens
- Role-based access control (Admin, Manager, Analyst)
- Data encryption at rest and in transit
- API rate limiting and security headers
- Audit logging and compliance features

### Modern UI/UX
- Responsive dashboard with real-time charts
- Dark/light theme support
- Interactive data visualization
- Mobile-friendly design
- Real-time notifications

## 🛠️ Development

See [DEVELOPMENT.md](./docs/DEVELOPMENT.md) for detailed development instructions.

## 📚 Documentation

- [API Documentation](./docs/API.md)
- [Security Guide](./docs/SECURITY.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [User Manual](./docs/USER_MANUAL.md)

## 🔧 Configuration

All configuration is handled via environment variables. See [.env.example](./.env.example) for all available options.

## 📈 Monitoring

- Health checks at `/api/health`
- Metrics endpoint at `/api/metrics`
- Real-time system status in admin dashboard
- Comprehensive logging with structured format

## 🚢 Deployment

The application is containerized and ready for deployment on:
- AWS ECS/EKS
- Google Cloud Run/GKE
- Azure Container Instances/AKS
- Any Docker-compatible platform

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.