-- ============================================================
-- 001_initial.sql — Brain Tumor Diagnostic Platform schema
-- ============================================================

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------
-- Patients
-- ---------------------------------------------------------
CREATE TABLE patients (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid  VARCHAR(128) NOT NULL UNIQUE,
    email         VARCHAR(255),
    display_name  VARCHAR(255),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_patients_firebase_uid ON patients (firebase_uid);

-- ---------------------------------------------------------
-- Scans
-- ---------------------------------------------------------
CREATE TABLE scans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id  UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    s3_key      VARCHAR(512) NOT NULL,
    s3_url      VARCHAR(1024) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_scans_patient_id   ON scans (patient_id);
CREATE INDEX ix_scans_patient_date ON scans (patient_id, uploaded_at);

-- ---------------------------------------------------------
-- Predictions
-- ---------------------------------------------------------
CREATE TABLE predictions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id           UUID NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    tumor_type        VARCHAR(50)  NOT NULL,
    confidence        DOUBLE PRECISION NOT NULL,
    location          VARCHAR(255),
    size_estimate     VARCHAR(100),
    gradcam_url       VARCHAR(1024),
    processing_time_ms DOUBLE PRECISION NOT NULL,
    predicted_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------
-- Reports
-- ---------------------------------------------------------
CREATE TABLE reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id      UUID NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    patient_id   UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recommendation TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_reports_patient_id ON reports (patient_id);

-- ---------------------------------------------------------
-- Audit logs
-- ---------------------------------------------------------
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  VARCHAR(50) NOT NULL,
    user_id     UUID,
    scan_id     UUID,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_audit_logs_user_event ON audit_logs (user_id, event_type);
CREATE INDEX ix_audit_logs_created    ON audit_logs (created_at);

-- ---------------------------------------------------------
-- updated_at trigger for patients
-- ---------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
