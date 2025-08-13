"""
Database configuration and connection management
Supports PostgreSQL and Neo4j
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from neo4j import GraphDatabase
import redis
from typing import Generator
import logging

from core.config import settings, get_database_url, get_redis_url, get_neo4j_config

logger = logging.getLogger(__name__)

# PostgreSQL Database with improved connection handling
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=10,  # Allow overflow connections
    pool_timeout=30,  # Timeout for getting connection from pool
    echo=settings.DEBUG,
    connect_args={
        "connect_timeout": 10,
        "application_name": "enterprise_event_analytics"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Get database session with error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Neo4j Database for Graph Analytics
class Neo4jDatabase:
    """Neo4j database connection manager"""
    
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        """Connect to Neo4j database"""
        try:
            neo4j_config = get_neo4j_config()
            self.driver = GraphDatabase.driver(
                neo4j_config["uri"],
                auth=(neo4j_config["user"], neo4j_config["password"])
            )
            logger.info("Connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def get_session(self):
        """Get Neo4j session"""
        if not self.driver:
            raise Exception("Neo4j driver not initialized")
        return self.driver.session()
    
    def execute_query(self, query: str, parameters: dict = None):
        """Execute a Cypher query"""
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]
    
    def create_indexes(self):
        """Create necessary indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.email)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.type)",
            "CREATE INDEX IF NOT EXISTS FOR (a:Analytics) ON (a.created_at)",
        ]
        
        for index in indexes:
            try:
                self.execute_query(index)
                logger.info(f"Created index: {index}")
            except Exception as e:
                logger.error(f"Failed to create index: {e}")

# Global Neo4j instance
neo4j_db = Neo4jDatabase()

def get_neo4j() -> Neo4jDatabase:
    """Get Neo4j database instance"""
    return neo4j_db

# Redis Database for Caching and Queues
class RedisDatabase:
    """Redis database connection manager"""
    
    def __init__(self):
        self.client = None
        self.connect()
    
    def connect(self):
        """Connect to Redis database"""
        try:
            self.client = redis.from_url(
                get_redis_url(),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.client.ping()
            logger.info("Connected to Redis database")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def get_client(self):
        """Get Redis client"""
        if not self.client:
            raise Exception("Redis client not initialized")
        return self.client
    
    def set_with_expiry(self, key: str, value: str, expiry: int):
        """Set key with expiry time"""
        return self.client.setex(key, expiry, value)
    
    def get(self, key: str):
        """Get value by key"""
        return self.client.get(key)
    
    def delete(self, key: str):
        """Delete key"""
        return self.client.delete(key)
    
    def exists(self, key: str):
        """Check if key exists"""
        return self.client.exists(key)

# Global Redis instance
redis_db = RedisDatabase()

def get_redis() -> RedisDatabase:
    """Get Redis database instance"""
    return redis_db

# Database initialization
def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def init_neo4j_schema():
    """Initialize Neo4j schema and constraints"""
    try:
        neo4j_db.create_indexes()
        
        # Create constraints
        constraints = [
            "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                neo4j_db.execute_query(constraint)
                logger.info(f"Created constraint: {constraint}")
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j schema: {e}")

# Health check functions
def check_postgresql_health() -> bool:
    """Check PostgreSQL database health"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False

def check_neo4j_health() -> bool:
    """Check Neo4j database health"""
    try:
        neo4j_db.execute_query("RETURN 1")
        return True
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return False

def check_redis_health() -> bool:
    """Check Redis database health"""
    try:
        redis_db.client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False

def get_database_health() -> dict:
    """Get health status of all databases"""
    return {
        "postgresql": check_postgresql_health(),
        "neo4j": check_neo4j_health(),
        "redis": check_redis_health()
    }

# Cleanup function
def close_db_connections():
    """Close all database connections"""
    try:
        engine.dispose()
        neo4j_db.close()
        logger.info("All database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")