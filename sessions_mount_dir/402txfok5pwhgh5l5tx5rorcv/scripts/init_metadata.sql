-- Initialize metadata for dynamic member fields
-- This script inserts default metadata entries for common dynamic fields

-- Insert metadata for emergency contact
INSERT INTO member_metadata (member_id, metadata_key, metadata_value) 
SELECT 
    m.id,
    'emergency_contact',
    JSON_BUILD_OBJECT(
        'name', NULL,
        'phone', NULL,
        'relationship', NULL
    )::text
FROM members m
WHERE NOT EXISTS (
    SELECT 1 FROM member_metadata 
    WHERE member_id = m.id AND metadata_key = 'emergency_contact'
);

-- Insert metadata for member notes
INSERT INTO member_metadata (member_id, metadata_key, metadata_value) 
SELECT 
    m.id,
    'notes',
    ''
FROM members m
WHERE NOT EXISTS (
    SELECT 1 FROM member_metadata 
    WHERE member_id = m.id AND metadata_key = 'notes'
);

-- Insert metadata for medical information
INSERT INTO member_metadata (member_id, metadata_key, metadata_value) 
SELECT 
    m.id,
    'medical_info',
    JSON_BUILD_OBJECT(
        'allergies', NULL,
        'medications', NULL,
        'conditions', NULL
    )::text
FROM members m
WHERE NOT EXISTS (
    SELECT 1 FROM member_metadata 
    WHERE member_id = m.id AND metadata_key = 'medical_info'
);
