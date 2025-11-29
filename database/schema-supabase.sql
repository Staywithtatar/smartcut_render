-- ============================================================================
-- AutoCut Influencer - Supabase Optimized Database Schema
-- ============================================================================
-- Description: Production-ready schema following Supabase best practices
-- Database: PostgreSQL (Supabase)
-- Version: 2.0.0 (Supabase Optimized)
-- Created: 2025-11-29
-- ============================================================================

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable UUID generation (Supabase default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for additional crypto functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- CUSTOM TYPES
-- ============================================================================

-- Job status enumeration
CREATE TYPE job_status AS ENUM (
  'PENDING',      -- Job created, waiting to start
  'UPLOADING',    -- User uploading video
  'QUEUED',       -- In queue, waiting for worker
  'TRANSCRIBING', -- Whisper API processing
  'ANALYZING',    -- Gemini API analyzing
  'RENDERING',    -- FFmpeg rendering
  'COMPLETED',    -- Successfully completed
  'FAILED',       -- Processing failed
  'CANCELLED'     -- User cancelled
);

-- Credit transaction types
CREATE TYPE transaction_type AS ENUM (
  'PURCHASE',     -- User bought credits
  'USAGE',        -- Credits used for job
  'REFUND',       -- Credits refunded
  'BONUS',        -- Free credits (promo, referral)
  'ADJUSTMENT'    -- Manual admin adjustment
);

-- Payment status
CREATE TYPE payment_status AS ENUM (
  'PENDING',
  'COMPLETED',
  'FAILED',
  'REFUNDED',
  'CANCELLED'
);

-- Payment providers
CREATE TYPE payment_provider AS ENUM (
  'STRIPE',
  'PROMPTPAY',
  'TRUEMONEY',
  'MANUAL' -- For admin manual credits
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: profiles
-- Description: User profiles extending auth.users (Supabase pattern)
-- Note: This table uses auth.users.id as primary key
-- ----------------------------------------------------------------------------
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Profile Info
  full_name TEXT,
  avatar_url TEXT,
  
  -- Credit System
  credits INTEGER DEFAULT 0 NOT NULL CHECK (credits >= 0),
  total_credits_purchased INTEGER DEFAULT 0 NOT NULL,
  total_credits_used INTEGER DEFAULT 0 NOT NULL,
  
  -- Subscription (Future)
  subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'basic', 'pro', 'enterprise')),
  subscription_expires_at TIMESTAMPTZ,
  
  -- Metadata
  is_active BOOLEAN DEFAULT true,
  last_login_at TIMESTAMPTZ,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  deleted_at TIMESTAMPTZ
);

-- Indexes for profiles table
CREATE INDEX idx_profiles_subscription ON profiles(subscription_tier, subscription_expires_at) WHERE is_active = true;
CREATE INDEX idx_profiles_created_at ON profiles(created_at DESC);
CREATE INDEX idx_profiles_active ON profiles(is_active) WHERE deleted_at IS NULL;

COMMENT ON TABLE profiles IS 'User profiles extending auth.users with credit balance and subscription';
COMMENT ON COLUMN profiles.id IS 'References auth.users.id - managed by Supabase Auth';
COMMENT ON COLUMN profiles.credits IS 'Current available credits for video processing';
COMMENT ON COLUMN profiles.deleted_at IS 'Soft delete timestamp - NULL means active user';

-- ----------------------------------------------------------------------------
-- Table: jobs
-- Description: Video processing job queue and status tracking
-- ----------------------------------------------------------------------------
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Job Configuration
  job_name TEXT NOT NULL,
  priority INTEGER DEFAULT 0, -- Higher = more priority
  
  -- Status & Progress
  status job_status DEFAULT 'PENDING' NOT NULL,
  progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
  current_step TEXT, -- e.g., "Transcribing audio..."
  
  -- Video Files (Supabase Storage paths)
  input_video_path TEXT, -- e.g., "raw-videos/user-id/job-id/input.mp4"
  output_video_path TEXT, -- e.g., "final-videos/user-id/job-id/output.mp4"
  thumbnail_path TEXT,
  
  -- Video Metadata
  input_duration_seconds DECIMAL(10,2),
  output_duration_seconds DECIMAL(10,2),
  input_file_size_mb DECIMAL(10,2),
  output_file_size_mb DECIMAL(10,2),
  video_resolution TEXT, -- e.g., "1080x1920"
  
  -- AI Processing Data
  transcription_json JSONB, -- Whisper output
  analysis_json JSONB, -- Gemini editing script
  
  -- External Service IDs
  replicate_prediction_id TEXT, -- Replicate job ID
  
  -- Error Handling
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  
  -- Credits
  credits_cost INTEGER DEFAULT 1 NOT NULL,
  
  -- Timestamps
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for jobs table
CREATE INDEX idx_jobs_user_id ON jobs(user_id, created_at DESC);
CREATE INDEX idx_jobs_status ON jobs(status, priority DESC, created_at ASC) WHERE status IN ('QUEUED', 'PENDING');
CREATE INDEX idx_jobs_replicate_id ON jobs(replicate_prediction_id) WHERE replicate_prediction_id IS NOT NULL;
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_status_updated ON jobs(status, updated_at DESC);

COMMENT ON TABLE jobs IS 'Video processing job queue with comprehensive status tracking';
COMMENT ON COLUMN jobs.priority IS 'Job priority - higher values processed first';
COMMENT ON COLUMN jobs.transcription_json IS 'Full Whisper API transcription output with timestamps';
COMMENT ON COLUMN jobs.analysis_json IS 'Gemini API editing script (cut points, effects, etc.)';

-- ----------------------------------------------------------------------------
-- Table: payments
-- Description: Payment transaction records for credit purchases
-- ----------------------------------------------------------------------------
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Payment Details
  provider payment_provider NOT NULL,
  provider_transaction_id TEXT, -- External payment ID
  
  -- Amount
  amount_thb DECIMAL(10,2) NOT NULL, -- Amount in Thai Baht
  credits_purchased INTEGER NOT NULL,
  
  -- Status
  status payment_status DEFAULT 'PENDING' NOT NULL,
  
  -- Metadata
  payment_method TEXT, -- e.g., "credit_card", "qr_code"
  metadata JSONB, -- Provider-specific data
  
  -- Timestamps
  paid_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for payments table
CREATE INDEX idx_payments_user_id ON payments(user_id, created_at DESC);
CREATE INDEX idx_payments_status ON payments(status, created_at DESC);
CREATE INDEX idx_payments_provider_tx_id ON payments(provider_transaction_id) WHERE provider_transaction_id IS NOT NULL;
CREATE INDEX idx_payments_provider ON payments(provider, created_at DESC);

COMMENT ON TABLE payments IS 'Payment records for credit purchases';
COMMENT ON COLUMN payments.provider_transaction_id IS 'External payment gateway transaction ID';

-- ----------------------------------------------------------------------------
-- Table: credit_transactions
-- Description: Complete audit trail of all credit movements
-- ----------------------------------------------------------------------------
CREATE TABLE credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Transaction Details
  type transaction_type NOT NULL,
  amount INTEGER NOT NULL, -- Positive for add, negative for deduct
  balance_after INTEGER NOT NULL,
  
  -- References
  job_id UUID REFERENCES jobs(id) ON DELETE SET NULL, -- If related to a job
  payment_id UUID REFERENCES payments(id) ON DELETE SET NULL, -- If from payment
  
  -- Metadata
  description TEXT,
  metadata JSONB, -- Additional data (promo code, etc.)
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for credit_transactions table
CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id, created_at DESC);
CREATE INDEX idx_credit_transactions_type ON credit_transactions(type, created_at DESC);
CREATE INDEX idx_credit_transactions_job_id ON credit_transactions(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX idx_credit_transactions_payment_id ON credit_transactions(payment_id) WHERE payment_id IS NOT NULL;

COMMENT ON TABLE credit_transactions IS 'Immutable audit log of all credit transactions';
COMMENT ON COLUMN credit_transactions.balance_after IS 'User credit balance snapshot after this transaction';

-- ----------------------------------------------------------------------------
-- Table: credit_packages
-- Description: Available credit packages for purchase
-- ----------------------------------------------------------------------------
CREATE TABLE credit_packages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Package Details
  name TEXT NOT NULL, -- e.g., "Starter Pack", "Pro Bundle"
  description TEXT,
  credits INTEGER NOT NULL,
  price_thb DECIMAL(10,2) NOT NULL,
  
  -- Pricing
  discount_percentage INTEGER DEFAULT 0 CHECK (discount_percentage BETWEEN 0 AND 100),
  is_popular BOOLEAN DEFAULT false, -- Highlight in UI
  
  -- Availability
  is_active BOOLEAN DEFAULT true,
  sort_order INTEGER DEFAULT 0,
  
  -- Metadata
  metadata JSONB, -- Additional features, limits, etc.
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for credit_packages table
CREATE INDEX idx_credit_packages_active ON credit_packages(sort_order, price_thb) WHERE is_active = true;

COMMENT ON TABLE credit_packages IS 'Configurable credit packages for purchase';
COMMENT ON COLUMN credit_packages.is_popular IS 'Flag to highlight package in UI';

-- ----------------------------------------------------------------------------
-- Table: user_preferences
-- Description: User-specific settings and preferences
-- ----------------------------------------------------------------------------
CREATE TABLE user_preferences (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Video Preferences
  default_aspect_ratio TEXT DEFAULT '9:16' CHECK (default_aspect_ratio IN ('9:16', '16:9', '1:1', '4:5')),
  default_subtitle_style TEXT DEFAULT 'standard' CHECK (default_subtitle_style IN ('standard', 'highlight', 'animated')),
  enable_sound_fx BOOLEAN DEFAULT true,
  enable_jump_cuts BOOLEAN DEFAULT true,
  
  -- Notification Preferences
  email_on_job_complete BOOLEAN DEFAULT true,
  email_on_job_failed BOOLEAN DEFAULT true,
  email_marketing BOOLEAN DEFAULT false,
  
  -- UI Preferences
  theme TEXT DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'auto')),
  language TEXT DEFAULT 'th' CHECK (language IN ('th', 'en')),
  
  -- Metadata
  preferences_json JSONB, -- For future extensibility
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE user_preferences IS 'User-specific settings for video processing and UI';

-- ----------------------------------------------------------------------------
-- Table: webhook_logs
-- Description: Audit trail for incoming webhooks from external services
-- ----------------------------------------------------------------------------
CREATE TABLE webhook_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Source
  provider TEXT NOT NULL, -- e.g., "replicate", "stripe"
  event_type TEXT NOT NULL, -- e.g., "prediction.completed"
  
  -- Payload
  payload JSONB NOT NULL,
  headers JSONB,
  
  -- Processing
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMPTZ,
  error_message TEXT,
  
  -- References
  job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
  payment_id UUID REFERENCES payments(id) ON DELETE SET NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for webhook_logs table
CREATE INDEX idx_webhook_logs_provider ON webhook_logs(provider, created_at DESC);
CREATE INDEX idx_webhook_logs_processed ON webhook_logs(processed, created_at DESC) WHERE processed = false;
CREATE INDEX idx_webhook_logs_job_id ON webhook_logs(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX idx_webhook_logs_payment_id ON webhook_logs(payment_id) WHERE payment_id IS NOT NULL;

COMMENT ON TABLE webhook_logs IS 'Audit trail for debugging external service webhooks';

-- ----------------------------------------------------------------------------
-- Table: api_usage_logs
-- Description: Track external API usage for cost monitoring
-- ----------------------------------------------------------------------------
CREATE TABLE api_usage_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  
  -- API Details
  api_provider TEXT NOT NULL, -- e.g., "whisper", "gemini", "replicate"
  api_endpoint TEXT,
  
  -- Usage
  tokens_used INTEGER,
  processing_time_seconds DECIMAL(10,2),
  cost_usd DECIMAL(10,4),
  
  -- Metadata
  request_metadata JSONB,
  response_metadata JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for api_usage_logs table
CREATE INDEX idx_api_usage_logs_job_id ON api_usage_logs(job_id);
CREATE INDEX idx_api_usage_logs_provider ON api_usage_logs(api_provider, created_at DESC);
CREATE INDEX idx_api_usage_logs_created_at ON api_usage_logs(created_at DESC);

COMMENT ON TABLE api_usage_logs IS 'Track API usage and costs for budget monitoring';

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: handle_new_user
-- Description: Automatically create profile when new user signs up
-- This is the Supabase recommended pattern
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, full_name, avatar_url, created_at)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url',
    NOW()
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: Create profile on user signup
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

COMMENT ON FUNCTION handle_new_user IS 'Auto-create profile when user signs up via Supabase Auth';

-- ----------------------------------------------------------------------------
-- Function: update_updated_at_column
-- Description: Automatically update updated_at timestamp on row updates
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_profiles_updated_at 
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at 
  BEFORE UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at 
  BEFORE UPDATE ON payments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_credit_packages_updated_at 
  BEFORE UPDATE ON credit_packages
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
  BEFORE UPDATE ON user_preferences
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- Function: sync_user_credits
-- Description: Sync user credits in profiles table with credit_transactions
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sync_user_credits()
RETURNS TRIGGER AS $$
BEGIN
  -- Update profile credits based on transaction
  UPDATE profiles
  SET 
    credits = NEW.balance_after,
    total_credits_purchased = total_credits_purchased + CASE WHEN NEW.type = 'PURCHASE' THEN NEW.amount ELSE 0 END,
    total_credits_used = total_credits_used + CASE WHEN NEW.type = 'USAGE' THEN ABS(NEW.amount) ELSE 0 END,
    updated_at = NOW()
  WHERE id = NEW.user_id;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER sync_credits_on_transaction 
  AFTER INSERT ON credit_transactions
  FOR EACH ROW EXECUTE FUNCTION sync_user_credits();

-- ----------------------------------------------------------------------------
-- Function: deduct_credits_for_job
-- Description: Deduct credits when job starts processing
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION deduct_credits_for_job()
RETURNS TRIGGER AS $$
DECLARE
  user_current_credits INTEGER;
  new_balance INTEGER;
BEGIN
  -- Only deduct credits when job moves to QUEUED status
  IF NEW.status = 'QUEUED' AND (OLD IS NULL OR OLD.status != 'QUEUED') THEN
    -- Get current user credits
    SELECT credits INTO user_current_credits
    FROM profiles
    WHERE id = NEW.user_id;
    
    -- Check if user has enough credits
    IF user_current_credits < NEW.credits_cost THEN
      RAISE EXCEPTION 'Insufficient credits. Required: %, Available: %', NEW.credits_cost, user_current_credits;
    END IF;
    
    -- Calculate new balance
    new_balance := user_current_credits - NEW.credits_cost;
    
    -- Create credit transaction
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, job_id, description)
    VALUES (
      NEW.user_id,
      'USAGE',
      -NEW.credits_cost,
      new_balance,
      NEW.id,
      'Video processing: ' || NEW.job_name
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER deduct_credits_on_job_start
  AFTER INSERT OR UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION deduct_credits_for_job();

-- ----------------------------------------------------------------------------
-- Function: refund_credits_on_job_failure
-- Description: Refund credits if job fails
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION refund_credits_on_job_failure()
RETURNS TRIGGER AS $$
DECLARE
  user_current_credits INTEGER;
  new_balance INTEGER;
  already_refunded BOOLEAN;
BEGIN
  -- Only refund if job moves to FAILED status and hasn't been refunded
  IF NEW.status = 'FAILED' AND OLD.status != 'FAILED' THEN
    -- Check if already refunded
    SELECT EXISTS(
      SELECT 1 FROM credit_transactions
      WHERE job_id = NEW.id AND type = 'REFUND'
    ) INTO already_refunded;
    
    IF NOT already_refunded THEN
      -- Get current user credits
      SELECT credits INTO user_current_credits
      FROM profiles
      WHERE id = NEW.user_id;
      
      -- Calculate new balance
      new_balance := user_current_credits + NEW.credits_cost;
      
      -- Create refund transaction
      INSERT INTO credit_transactions (user_id, type, amount, balance_after, job_id, description)
      VALUES (
        NEW.user_id,
        'REFUND',
        NEW.credits_cost,
        new_balance,
        NEW.id,
        'Refund for failed job: ' || NEW.job_name
      );
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER refund_credits_on_failure
  AFTER UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION refund_credits_on_job_failure();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_packages ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- RLS Policies: profiles
-- ----------------------------------------------------------------------------

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

-- Users can update their own profile (except credits - managed by triggers)
CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Service role can do anything (for admin operations)
CREATE POLICY "Service role has full access to profiles"
  ON profiles FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- RLS Policies: jobs
-- ----------------------------------------------------------------------------

-- Users can view their own jobs
CREATE POLICY "Users can view own jobs"
  ON jobs FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can create jobs
CREATE POLICY "Users can create jobs"
  ON jobs FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own jobs (for cancellation)
CREATE POLICY "Users can update own jobs"
  ON jobs FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own jobs
CREATE POLICY "Users can delete own jobs"
  ON jobs FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Service role has full access
CREATE POLICY "Service role has full access to jobs"
  ON jobs FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- RLS Policies: credit_transactions
-- ----------------------------------------------------------------------------

-- Users can view their own transactions (read-only)
CREATE POLICY "Users can view own transactions"
  ON credit_transactions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Service role can manage transactions
CREATE POLICY "Service role has full access to transactions"
  ON credit_transactions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- RLS Policies: payments
-- ----------------------------------------------------------------------------

-- Users can view their own payments
CREATE POLICY "Users can view own payments"
  ON payments FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can create payments
CREATE POLICY "Users can create payments"
  ON payments FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Service role has full access
CREATE POLICY "Service role has full access to payments"
  ON payments FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- RLS Policies: user_preferences
-- ----------------------------------------------------------------------------

-- Users can manage their own preferences
CREATE POLICY "Users can manage own preferences"
  ON user_preferences FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- RLS Policies: credit_packages
-- ----------------------------------------------------------------------------

-- All authenticated users can view active packages
CREATE POLICY "Authenticated users can view active packages"
  ON credit_packages FOR SELECT
  TO authenticated
  USING (is_active = true);

-- Service role can manage packages
CREATE POLICY "Service role has full access to packages"
  ON credit_packages FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- RLS Policies: webhook_logs & api_usage_logs
-- ----------------------------------------------------------------------------

-- Only service role can access these tables
CREATE POLICY "Service role has full access to webhook_logs"
  ON webhook_logs FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role has full access to api_usage_logs"
  ON api_usage_logs FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default credit packages
INSERT INTO credit_packages (name, description, credits, price_thb, discount_percentage, is_popular, sort_order) VALUES
  ('Trial Pack', 'ทดลองใช้งาน - 1 คลิป', 1, 0, 0, false, 1),
  ('Starter Pack', 'เหมาะสำหรับผู้เริ่มต้น', 3, 99, 0, false, 2),
  ('Popular Pack', 'ยอดนิยม! คุ้มค่าที่สุด', 10, 299, 10, true, 3),
  ('Pro Pack', 'สำหรับครีเอเตอร์มืออาชีพ', 25, 699, 15, false, 4),
  ('Business Pack', 'สำหรับธุรกิจขนาดเล็ก', 50, 1299, 20, false, 5),
  ('Enterprise Pack', 'สำหรับองค์กรขนาดใหญ่', 100, 2399, 25, false, 6);

-- ============================================================================
-- VIEWS (Optional - for analytics)
-- ============================================================================

-- View: User statistics
CREATE OR REPLACE VIEW user_stats AS
SELECT 
  p.id,
  au.email,
  p.full_name,
  p.credits,
  p.total_credits_purchased,
  p.total_credits_used,
  p.subscription_tier,
  COUNT(DISTINCT j.id) as total_jobs,
  COUNT(DISTINCT j.id) FILTER (WHERE j.status = 'COMPLETED') as completed_jobs,
  COUNT(DISTINCT j.id) FILTER (WHERE j.status = 'FAILED') as failed_jobs,
  SUM(j.credits_cost) FILTER (WHERE j.status = 'COMPLETED') as total_credits_spent,
  p.created_at,
  p.last_login_at
FROM profiles p
LEFT JOIN auth.users au ON p.id = au.id
LEFT JOIN jobs j ON p.id = j.user_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, au.email;

COMMENT ON VIEW user_stats IS 'User statistics for analytics dashboard';

-- View: Job queue status
CREATE OR REPLACE VIEW job_queue_status AS
SELECT 
  status,
  COUNT(*) as count,
  AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_wait_time_seconds
FROM jobs
WHERE status IN ('PENDING', 'QUEUED', 'TRANSCRIBING', 'ANALYZING', 'RENDERING')
GROUP BY status;

COMMENT ON VIEW job_queue_status IS 'Real-time job queue status for monitoring';

-- ============================================================================
-- REALTIME SUBSCRIPTIONS (Supabase Feature)
-- ============================================================================

-- Enable realtime for jobs table (so users can see live progress)
ALTER PUBLICATION supabase_realtime ADD TABLE jobs;

-- Enable realtime for profiles (for credit updates)
ALTER PUBLICATION supabase_realtime ADD TABLE profiles;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
