-- Create member table
CREATE TABLE IF NOT EXISTS member (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(100) NOT NULL,
    level VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'FROZEN', 'EXPIRED')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create member_metadata table
CREATE TABLE IF NOT EXISTS member_metadata (
    id BIGSERIAL PRIMARY KEY,
    member_id BIGINT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    metadata_key VARCHAR(100) NOT NULL,
    metadata_value TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(member_id, metadata_key)
);

-- Create member_dynamic_data table
CREATE TABLE IF NOT EXISTS member_dynamic_data (
    id BIGSERIAL PRIMARY KEY,
    member_id BIGINT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    field_key VARCHAR(100) NOT NULL,
    field_value TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create entry_records table
CREATE TABLE IF NOT EXISTS entry_records (
    id BIGSERIAL PRIMARY KEY,
    member_id BIGINT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_member_status ON member(status);
CREATE INDEX IF NOT EXISTS idx_member_level ON member(level);
CREATE INDEX IF NOT EXISTS idx_member_metadata_member_id ON member_metadata(member_id);
CREATE INDEX IF NOT EXISTS idx_member_dynamic_data_member_id ON member_dynamic_data(member_id);
CREATE INDEX IF NOT EXISTS idx_member_dynamic_data_key ON member_dynamic_data(field_key);
CREATE INDEX IF NOT EXISTS idx_entry_records_member_id ON entry_records(member_id);
CREATE INDEX IF NOT EXISTS idx_entry_records_entry_time ON entry_records(entry_time);

-- Create trigger to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_member_updated_at BEFORE UPDATE ON member
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_member_metadata_updated_at BEFORE UPDATE ON member_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_member_dynamic_data_updated_at BEFORE UPDATE ON member_dynamic_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();