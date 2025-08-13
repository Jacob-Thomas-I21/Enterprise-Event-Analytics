-- Database initialization script for Enterprise Event Analytics Platform
-- This script sets up the initial database schema and data

-- Create database if it doesn't exist
-- Note: This is handled by Docker environment variables

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'manager', 'analyst');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create users table (will be managed by SQLAlchemy, but we can create indexes)
-- The actual table creation is handled by the application

-- Create indexes for performance (these will be created after table creation)
-- Note: These are created by the application, but we can prepare the database

-- Create a function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create event processing status table for tracking
CREATE TABLE IF NOT EXISTS event_processing_status (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Create trigger for updated_at
CREATE TRIGGER update_event_processing_status_updated_at 
    BEFORE UPDATE ON event_processing_status 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for event processing status
CREATE INDEX IF NOT EXISTS idx_event_processing_status_event_type ON event_processing_status(event_type);
CREATE INDEX IF NOT EXISTS idx_event_processing_status_status ON event_processing_status(status);
CREATE INDEX IF NOT EXISTS idx_event_processing_status_created_at ON event_processing_status(created_at);

-- Create analytics summary table for caching
CREATE TABLE IF NOT EXISTS analytics_summary (
    id SERIAL PRIMARY KEY,
    summary_type VARCHAR(100) NOT NULL,
    summary_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE
);

-- Create trigger for analytics summary updated_at
CREATE TRIGGER update_analytics_summary_updated_at 
    BEFORE UPDATE ON analytics_summary 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for analytics summary
CREATE INDEX IF NOT EXISTS idx_analytics_summary_type ON analytics_summary(summary_type);
CREATE INDEX IF NOT EXISTS idx_analytics_summary_valid_until ON analytics_summary(valid_until);

-- Create audit log table for security
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit log
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for system metrics
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_created_at ON system_metrics(created_at);

-- Create notification queue table
CREATE TABLE IF NOT EXISTS notification_queue (
    id SERIAL PRIMARY KEY,
    recipient_id INTEGER,
    notification_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for notification queue
CREATE INDEX IF NOT EXISTS idx_notification_queue_recipient ON notification_queue(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notification_queue_status ON notification_queue(status);
CREATE INDEX IF NOT EXISTS idx_notification_queue_created_at ON notification_queue(created_at);

-- Insert initial system configuration
INSERT INTO analytics_summary (summary_type, summary_data, valid_until) 
VALUES (
    'system_config',
    '{"initialized": true, "version": "1.0.0", "setup_date": "' || CURRENT_TIMESTAMP || '"}',
    CURRENT_TIMESTAMP + INTERVAL '1 year'
) ON CONFLICT DO NOTHING;

-- Create a view for recent events (will be populated by the application)
CREATE OR REPLACE VIEW recent_events_summary AS
SELECT 
    'placeholder' as event_type,
    0 as count,
    CURRENT_TIMESTAMP as last_updated
WHERE FALSE; -- This will be replaced by actual data from Redis/Application

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO analytics_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO analytics_user;

-- Create a function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean old audit logs (keep 90 days)
    DELETE FROM audit_log WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    -- Clean old system metrics (keep 30 days)
    DELETE FROM system_metrics WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Clean old event processing status (keep 7 days for completed)
    DELETE FROM event_processing_status 
    WHERE status IN ('completed', 'failed') 
    AND updated_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    -- Clean expired analytics summaries
    DELETE FROM analytics_summary WHERE valid_until < CURRENT_TIMESTAMP;
    
    -- Clean sent notifications (keep 30 days)
    DELETE FROM notification_queue 
    WHERE status = 'sent' 
    AND sent_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
END;
$$ LANGUAGE plpgsql;

-- Log the initialization
INSERT INTO audit_log (user_id, action, resource, details, ip_address) 
VALUES (
    NULL, 
    'database_init', 
    'system', 
    '{"message": "Database initialized successfully", "timestamp": "' || CURRENT_TIMESTAMP || '"}',
    '127.0.0.1'::inet
);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Enterprise Event Analytics Database initialized successfully!';
    RAISE NOTICE 'Tables created: event_processing_status, analytics_summary, audit_log, system_metrics, notification_queue';
    RAISE NOTICE 'Functions created: update_updated_at_column, cleanup_old_data';
    RAISE NOTICE 'Ready for application startup.';
END $$;