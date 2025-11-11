-- Initialize athena user with proper password authentication
-- This runs after the main init script

-- Ensure the athena user has MD5 or SCRAM password auth
ALTER USER athena WITH PASSWORD 'athena_dev';

-- Grant necessary permissions
GRANT CREATE ON DATABASE athena TO athena;
GRANT USAGE ON SCHEMA public TO athena;
GRANT CREATE ON SCHEMA public TO athena;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO athena;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO athena;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO athena;
