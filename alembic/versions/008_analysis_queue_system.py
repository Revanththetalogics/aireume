"""Analysis Queue System

Revision ID: 008
Revises: 007
Create Date: 2026-04-13

Creates a scalable queue-based architecture for resume analysis processing.

This migration introduces:
- analysis_jobs: Main queue table for tracking analysis tasks
- analysis_results: Immutable storage for completed analyses
- analysis_artifacts: Store intermediate processing artifacts (parsed resume, JD, etc.)
- job_metrics: Performance and quality metrics for monitoring
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid


# Alembic revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # 1. ANALYSIS_JOBS - Main queue table
    # ============================================================================
    op.create_table(
        'analysis_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('candidate_id', sa.Integer, sa.ForeignKey('candidates.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Job identification and deduplication
        sa.Column('job_type', sa.String(50), nullable=False, default='resume_screening', index=True),
        sa.Column('resume_hash', sa.String(64), nullable=False, index=True),  # SHA-256 of resume content
        sa.Column('jd_hash', sa.String(64), nullable=False, index=True),      # SHA-256 of JD content
        sa.Column('input_hash', sa.String(64), nullable=False, unique=True),  # Combined hash for deduplication
        
        # Job status and lifecycle
        sa.Column('status', sa.String(20), nullable=False, default='queued', index=True),
        # Status values: 'queued', 'processing', 'completed', 'failed', 'cancelled', 'retrying'
        sa.Column('priority', sa.Integer, nullable=False, default=5, index=True),  # 1=highest, 10=lowest
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retries', sa.Integer, nullable=False, default=3),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True, index=True),
        
        # Worker assignment
        sa.Column('worker_id', sa.String(100), nullable=True, index=True),  # Which worker is processing this
        sa.Column('worker_heartbeat', sa.DateTime(timezone=True), nullable=True),  # Last heartbeat from worker
        
        # Input data references
        sa.Column('artifact_id', UUID(as_uuid=True), sa.ForeignKey('analysis_artifacts.id', ondelete='SET NULL'), nullable=True),
        
        # Processing metadata
        sa.Column('processing_stage', sa.String(50), nullable=True),  # Current pipeline stage
        sa.Column('progress_percent', sa.Integer, nullable=False, default=0),
        sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True),
        
        # Error tracking
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_stack_trace', sa.Text, nullable=True),
        sa.Column('error_context', JSONB, nullable=True),  # Additional error context
        
        # Result reference (populated when completed)
        sa.Column('result_id', UUID(as_uuid=True), sa.ForeignKey('analysis_results.id', ondelete='SET NULL'), nullable=True),
        
        # Configuration and options
        sa.Column('job_config', JSONB, nullable=True),  # Pipeline options, model selection, etc.
        
        # Indexes for queue operations
        sa.Index('idx_jobs_queue_processing', 'status', 'priority', 'queued_at'),
        sa.Index('idx_jobs_retry', 'status', 'next_retry_at'),
        sa.Index('idx_jobs_worker_heartbeat', 'worker_id', 'worker_heartbeat'),
        sa.Index('idx_jobs_tenant_status', 'tenant_id', 'status', 'created_at'),
    )

    # ============================================================================
    # 2. ANALYSIS_RESULTS - Immutable completed analyses
    # ============================================================================
    op.create_table(
        'analysis_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('analysis_jobs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('candidate_id', sa.Integer, sa.ForeignKey('candidates.id', ondelete='SET NULL'), nullable=True, index=True),
        
        # Core analysis data (ALWAYS complete and validated)
        sa.Column('fit_score', sa.Integer, nullable=False),  # NOT NULL - must have score
        sa.Column('final_recommendation', sa.String(50), nullable=False),  # NOT NULL
        sa.Column('risk_level', sa.String(20), nullable=True),
        
        # Full analysis JSON (validated before insert)
        sa.Column('analysis_data', JSONB, nullable=False),  # Complete analysis result
        sa.Column('parsed_resume', JSONB, nullable=False),  # Parsed resume structure
        sa.Column('parsed_jd', JSONB, nullable=False),      # Parsed JD structure
        
        # AI Enhancement (narrative)
        sa.Column('narrative_status', sa.String(20), nullable=False, default='pending'),
        sa.Column('narrative_data', JSONB, nullable=True),
        sa.Column('narrative_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ai_enhanced', sa.Boolean, nullable=False, default=False),
        
        # Metadata
        sa.Column('analysis_version', sa.String(20), nullable=False, default='1.0'),  # Pipeline version
        sa.Column('model_used', sa.String(100), nullable=True),  # LLM model name
        sa.Column('processing_time_ms', sa.Integer, nullable=True),  # Total processing time
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        
        # Quality and confidence
        sa.Column('analysis_quality', sa.String(20), nullable=False, default='medium'),
        sa.Column('confidence_score', sa.Float, nullable=True),  # 0.0 - 1.0
        
        # Artifact reference
        sa.Column('artifact_id', UUID(as_uuid=True), sa.ForeignKey('analysis_artifacts.id', ondelete='SET NULL'), nullable=True),
        
        # Indexes
        sa.Index('idx_results_tenant_created', 'tenant_id', 'created_at'),
        sa.Index('idx_results_candidate', 'candidate_id', 'created_at'),
        sa.Index('idx_results_fit_score', 'fit_score'),
        
        # Constraints to ensure data quality
        sa.CheckConstraint('fit_score >= 0 AND fit_score <= 100', name='valid_fit_score'),
        sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)', name='valid_confidence'),
    )

    # ============================================================================
    # 3. ANALYSIS_ARTIFACTS - Store input files and intermediate data
    # ============================================================================
    op.create_table(
        'analysis_artifacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # File metadata
        sa.Column('resume_filename', sa.String(255), nullable=False),
        sa.Column('resume_size_bytes', sa.Integer, nullable=False),
        sa.Column('resume_hash', sa.String(64), nullable=False, index=True),
        sa.Column('resume_mime_type', sa.String(100), nullable=True),
        
        sa.Column('jd_filename', sa.String(255), nullable=True),
        sa.Column('jd_size_bytes', sa.Integer, nullable=True),
        sa.Column('jd_hash', sa.String(64), nullable=False, index=True),
        sa.Column('jd_text', sa.Text, nullable=False),  # Store JD text directly
        
        # Storage location (if using object storage like S3)
        sa.Column('resume_storage_path', sa.String(500), nullable=True),
        sa.Column('resume_storage_bucket', sa.String(100), nullable=True),
        
        # Extracted text (for quick access)
        sa.Column('resume_text', sa.Text, nullable=False),
        sa.Column('resume_text_length', sa.Integer, nullable=False),
        
        # Parsed data cache
        sa.Column('parsed_resume_cache', JSONB, nullable=True),
        sa.Column('parsed_jd_cache', JSONB, nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),  # For cleanup
        sa.Column('access_count', sa.Integer, nullable=False, default=0),  # Track reuse
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Indexes
        sa.Index('idx_artifacts_hashes', 'resume_hash', 'jd_hash'),
        sa.Index('idx_artifacts_expires', 'expires_at'),
    )

    # ============================================================================
    # 4. JOB_METRICS - Performance and quality tracking
    # ============================================================================
    op.create_table(
        'job_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('analysis_jobs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Timing metrics (all in milliseconds)
        sa.Column('queue_wait_time_ms', sa.Integer, nullable=True),      # Time in queue before processing
        sa.Column('parsing_time_ms', sa.Integer, nullable=True),         # Resume + JD parsing
        sa.Column('llm_time_ms', sa.Integer, nullable=True),             # LLM inference time
        sa.Column('narrative_time_ms', sa.Integer, nullable=True),       # AI enhancement time
        sa.Column('total_time_ms', sa.Integer, nullable=False),          # End-to-end time
        
        # Resource usage
        sa.Column('llm_tokens_input', sa.Integer, nullable=True),
        sa.Column('llm_tokens_output', sa.Integer, nullable=True),
        sa.Column('llm_calls_count', sa.Integer, nullable=True),
        sa.Column('memory_peak_mb', sa.Integer, nullable=True),
        
        # Quality metrics
        sa.Column('parsing_confidence', sa.Float, nullable=True),
        sa.Column('analysis_confidence', sa.Float, nullable=True),
        sa.Column('json_parse_retries', sa.Integer, nullable=False, default=0),
        
        # Pipeline stages timing
        sa.Column('stage_timings', JSONB, nullable=True),  # {"parse": 150, "analyze": 3000, ...}
        
        # Error metrics (if job failed)
        sa.Column('error_stage', sa.String(50), nullable=True),
        sa.Column('retry_attempts', sa.Integer, nullable=False, default=0),
        
        # Worker info
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('worker_version', sa.String(50), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes for analytics
        sa.Index('idx_metrics_tenant_created', 'tenant_id', 'created_at'),
        sa.Index('idx_metrics_timing', 'total_time_ms'),
    )

    # ============================================================================
    # 5. Create views for common queries
    # ============================================================================
    
    # View: Active queue (jobs ready to process)
    op.execute("""
        CREATE VIEW active_queue AS
        SELECT 
            j.id,
            j.tenant_id,
            j.candidate_id,
            j.priority,
            j.status,
            j.retry_count,
            j.created_at,
            j.queued_at,
            EXTRACT(EPOCH FROM (NOW() - j.queued_at)) as wait_time_seconds,
            a.resume_filename,
            a.resume_size_bytes
        FROM analysis_jobs j
        LEFT JOIN analysis_artifacts a ON j.artifact_id = a.id
        WHERE j.status IN ('queued', 'retrying')
          AND (j.next_retry_at IS NULL OR j.next_retry_at <= NOW())
        ORDER BY j.priority ASC, j.queued_at ASC;
    """)
    
    # View: Job statistics by tenant
    op.execute("""
        CREATE VIEW job_stats_by_tenant AS
        SELECT 
            tenant_id,
            COUNT(*) as total_jobs,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status IN ('queued', 'processing')) as in_progress,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) FILTER (WHERE status = 'completed') as avg_completion_time_seconds,
            MAX(created_at) as last_job_at
        FROM analysis_jobs
        GROUP BY tenant_id;
    """)

    # ============================================================================
    # 6. Add triggers for automatic updates
    # ============================================================================
    
    # Trigger: Update artifact access tracking
    op.execute("""
        CREATE OR REPLACE FUNCTION update_artifact_access()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE analysis_artifacts
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
            WHERE id = NEW.artifact_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trigger_artifact_access
        AFTER INSERT ON analysis_jobs
        FOR EACH ROW
        WHEN (NEW.artifact_id IS NOT NULL)
        EXECUTE FUNCTION update_artifact_access();
    """)
    
    # Trigger: Validate analysis_results data before insert
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_analysis_result()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Ensure critical fields exist in analysis_data
            IF NOT (NEW.analysis_data ? 'strengths' AND 
                    NEW.analysis_data ? 'weaknesses' AND
                    NEW.analysis_data ? 'matched_skills') THEN
                RAISE EXCEPTION 'analysis_data missing required fields';
            END IF;
            
            -- Ensure fit_score matches analysis_data
            IF (NEW.analysis_data->>'fit_score')::int != NEW.fit_score THEN
                RAISE EXCEPTION 'fit_score mismatch between column and JSON';
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trigger_validate_result
        BEFORE INSERT ON analysis_results
        FOR EACH ROW
        EXECUTE FUNCTION validate_analysis_result();
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_artifact_access ON analysis_jobs;")
    op.execute("DROP TRIGGER IF EXISTS trigger_validate_result ON analysis_results;")
    op.execute("DROP FUNCTION IF EXISTS update_artifact_access();")
    op.execute("DROP FUNCTION IF EXISTS validate_analysis_result();")
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS active_queue;")
    op.execute("DROP VIEW IF EXISTS job_stats_by_tenant;")
    
    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('job_metrics')
    op.drop_table('analysis_results')
    op.drop_table('analysis_jobs')
    op.drop_table('analysis_artifacts')
