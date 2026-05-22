BEGIN;

ALTER TABLE support_tickets
ADD COLUMN IF NOT EXISTS resolution_comment TEXT;

CREATE TABLE IF NOT EXISTS request_status_history (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('consultation', 'support')),
    entity_id BIGINT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consultation_reminder_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL UNIQUE REFERENCES consultation_requests(id) ON DELETE CASCADE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE consultation_requests
DROP CONSTRAINT IF EXISTS consultation_requests_consultation_slot_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_consultation_slot
ON consultation_requests(consultation_slot_id)
WHERE status IN ('new', 'approved');

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_normalized_phone ON users (
    regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g')
) WHERE phone IS NOT NULL AND regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g') <> '';

CREATE INDEX IF NOT EXISTS idx_request_status_history_entity
ON request_status_history(entity_type, entity_id, created_at);

COMMIT;
