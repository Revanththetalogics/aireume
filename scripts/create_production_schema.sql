-- ============================================================================
-- ARIA Production Database - Complete Base Schema
-- Run this in pgAdmin to create all tables for fresh production DB
-- Database: aria_prod_db (user: aria)
--
-- This script creates ALL tables with exact columns as defined in models
-- and expected by Alembic migrations. Then migrations can add indexes, etc.
-- ============================================================================

-- ============================================================================
-- Drop existing tables (reverse dependency order)
-- ============================================================================
DROP TABLE IF EXISTS skill_templates CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS field_audit_logs CASCADE;
DROP TABLE IF EXISTS transcript_analyses CASCADE;
DROP TABLE IF EXISTS video_uploads CASCADE;
DROP TABLE IF EXISTS billing_events CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS dunning_records CASCADE;
DROP TABLE IF EXISTS usage_alerts CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS webhooks CASCADE;
DROP TABLE IF EXISTS revoked_tokens CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS jd_cache CASCADE;
DROP TABLE IF EXISTS job_metrics CASCADE;
DROP TABLE IF EXISTS analysis_artifacts CASCADE;
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS analysis_jobs CASCADE;
DROP TABLE IF EXISTS hiring_outcomes CASCADE;
DROP TABLE IF EXISTS sso_configs CASCADE;
DROP TABLE IF EXISTS tenant_email_configs CASCADE;
DROP TABLE IF EXISTS platform_configs CASCADE;
DROP TABLE IF EXISTS interview_evaluations CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS candidate_notes CASCADE;
DROP TABLE IF EXISTS plan_features CASCADE;
DROP TABLE IF EXISTS team_members CASCADE;
DROP TABLE IF EXISTS role_templates CASCADE;
DROP TABLE IF EXISTS skill_classification_templates CASCADE;
DROP TABLE IF EXISTS screening_results CASCADE;
DROP TABLE IF EXISTS candidates CASCADE;
DROP TABLE IF EXISTS usage_logs CASCADE;
DROP TABLE IF EXISTS "users" CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS subscription_plans CASCADE;

-- ============================================================================
-- 1. subscription_plans
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    "limits" TEXT NOT NULL DEFAULT '{}',
    price_monthly INTEGER NOT NULL DEFAULT 0,
    price_yearly INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    features TEXT NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 2. tenants
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_id INTEGER REFERENCES subscription_plans(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    subscription_status VARCHAR(20) NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    analyses_count_this_month INTEGER NOT NULL DEFAULT 0,
    storage_used_bytes BIGINT NOT NULL DEFAULT 0,
    usage_reset_at TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_updated_at TIMESTAMP WITH TIME ZONE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    suspended_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    scoring_weights TEXT,
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    onboarding_completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 3. users
-- ============================================================================
CREATE TABLE IF NOT EXISTS "users" (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'recruiter',
    is_active BOOLEAN DEFAULT TRUE,
    is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE,
    platform_role VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 4. usage_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "users"(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 5. candidates
-- ============================================================================
CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resume_file_hash VARCHAR(64),
    resume_filename VARCHAR(255),
    resume_file_data BYTEA,
    resume_converted_pdf_data BYTEA,
    raw_resume_text TEXT,
    parsed_skills TEXT,
    parsed_education TEXT,
    parsed_work_exp TEXT,
    gap_analysis_json TEXT,
    "current_role" VARCHAR(255),
    current_company VARCHAR(255),
    total_years_exp REAL,
    profile_quality VARCHAR(20),
    profile_updated_at TIMESTAMP WITH TIME ZONE,
    parser_snapshot_json TEXT,
    ai_professional_summary TEXT
);

-- ============================================================================
-- 6. candidate_notes
-- ============================================================================
CREATE TABLE IF NOT EXISTS candidate_notes (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    note_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 7. screening_results
-- ============================================================================
CREATE TABLE IF NOT EXISTS screening_results (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    candidate_id INTEGER REFERENCES candidates(id),
    role_template_id INTEGER,
    resume_text TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    parsed_data TEXT NOT NULL,
    analysis_result TEXT NOT NULL,
    narrative_json TEXT,
    narrative_status VARCHAR(20) DEFAULT 'pending',
    narrative_error TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    is_active BOOLEAN DEFAULT TRUE,
    version_number INTEGER DEFAULT 1,
    role_category VARCHAR(50),
    weight_reasoning TEXT,
    suggested_weights_json TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deterministic_score INTEGER,
    domain_match_score REAL,
    core_skill_score REAL,
    eligibility_status BOOLEAN,
    eligibility_reason VARCHAR(100),
    status_updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 8. role_templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(200) NOT NULL,
    jd_text TEXT NOT NULL,
    scoring_weights TEXT,
    tags VARCHAR(500),
    required_skills_override TEXT,
    nice_to_have_skills_override TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 9. team_members
-- ============================================================================
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    invited_by INTEGER,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 10. plan_features
-- ============================================================================
CREATE TABLE IF NOT EXISTS plan_features (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    feature_key VARCHAR(100) NOT NULL,
    feature_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 11. comments
-- ============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    candidate_id INTEGER REFERENCES candidates(id),
    result_id INTEGER REFERENCES screening_results(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 12. tenant_email_configs
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_email_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id),
    smtp_host VARCHAR(255),
    smtp_port INTEGER,
    smtp_user VARCHAR(255),
    smtp_password TEXT,
    from_email VARCHAR(255),
    from_name VARCHAR(255),
    use_tls BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 13. sso_configs
-- ============================================================================
CREATE TABLE IF NOT EXISTS sso_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id),
    provider_type VARCHAR(20) NOT NULL DEFAULT 'saml2',
    idp_entity_id VARCHAR(500) NOT NULL,
    idp_sso_url VARCHAR(500) NOT NULL,
    idp_slo_url VARCHAR(500),
    idp_certificate TEXT NOT NULL,
    sp_entity_id VARCHAR(500),
    sp_acs_url VARCHAR(500),
    enforce_sso BOOLEAN NOT NULL DEFAULT FALSE,
    auto_provision BOOLEAN NOT NULL DEFAULT TRUE,
    default_role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 14. webhooks
-- ============================================================================
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    events TEXT NOT NULL,
    secret TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES "users"(id)
);

-- ============================================================================
-- 15. notifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER REFERENCES "users"(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 16. billing_events
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    provider VARCHAR(20) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    raw_payload TEXT,
    result VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_detail TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 17. video_uploads
-- ============================================================================
CREATE TABLE IF NOT EXISTS video_uploads (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    candidate_id INTEGER REFERENCES candidates(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 18. transcript_analyses
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcript_analyses (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    video_upload_id INTEGER REFERENCES video_uploads(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    job_description TEXT,
    transcript_text TEXT,
    analysis_result TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 19. audit_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER REFERENCES "users"(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 20. skill_templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    skills TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 21. jd_cache
-- ============================================================================
CREATE TABLE IF NOT EXISTS jd_cache (
    hash VARCHAR(64) PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 22. skills
-- ============================================================================
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    aliases TEXT,
    domain VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    source VARCHAR(20) NOT NULL DEFAULT 'seed',
    frequency INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 23. revoked_tokens
-- ============================================================================
CREATE TABLE IF NOT EXISTS revoked_tokens (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(64) NOT NULL UNIQUE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- ============================================================================
-- 24. field_audit_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS field_audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER NOT NULL REFERENCES "users"(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    change_reason VARCHAR(500)
);

-- ============================================================================
-- 25. invoices
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'paid',
    amount INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'usd',
    description VARCHAR(500),
    line_items JSONB,
    payment_provider VARCHAR(20),
    provider_invoice_id VARCHAR(255),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 26. dunning_records
-- ============================================================================
CREATE TABLE IF NOT EXISTS dunning_records (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 4,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_retry_at TIMESTAMP WITH TIME ZONE,
    failure_reason VARCHAR(500),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 27. usage_alerts
-- ============================================================================
CREATE TABLE IF NOT EXISTS usage_alerts (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    threshold_percent INTEGER NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    current_value INTEGER NOT NULL,
    limit_value INTEGER NOT NULL,
    notified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_key VARCHAR(10) NOT NULL
);

-- ============================================================================
-- 28. skill_classification_templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_classification_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    role_template_id INTEGER REFERENCES role_templates(id),
    required_skills TEXT NOT NULL DEFAULT '[]',
    nice_to_have_skills TEXT NOT NULL DEFAULT '[]',
    created_by INTEGER REFERENCES "users"(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 29. interview_evaluations
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_evaluations (
    id SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL REFERENCES screening_results(id),
    user_id INTEGER NOT NULL REFERENCES "users"(id),
    question_category VARCHAR(30) NOT NULL,
    question_index INTEGER NOT NULL,
    rating VARCHAR(10),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 30. platform_configs
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description VARCHAR(500)
);

-- ============================================================================
-- 31. hiring_outcomes
-- ============================================================================
CREATE TABLE IF NOT EXISTS hiring_outcomes (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    screening_result_id INTEGER NOT NULL UNIQUE REFERENCES screening_results(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    role_template_id INTEGER REFERENCES role_templates(id),
    decision VARCHAR(20) NOT NULL,
    decision_stage VARCHAR(50),
    decision_date TIMESTAMP,
    decision_by_user_id INTEGER REFERENCES "users"(id),
    feedback_rating INTEGER,
    feedback_notes TEXT,
    source VARCHAR(20) DEFAULT 'manual',
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Done!
-- ============================================================================
SELECT 'All tables created successfully!' AS result;