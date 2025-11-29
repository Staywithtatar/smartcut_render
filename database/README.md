# AutoCut Influencer - Database Schema

## Overview

This directory contains the complete database schema for the AutoCut Influencer platform.

## Files

- **`schema.sql`** - Complete PostgreSQL schema ready for Supabase deployment

## Database Structure

### Core Tables

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `users` | User management & credits | Credit balance, subscription tiers, soft deletes |
| `jobs` | Video processing queue | Status tracking, priority queue, retry mechanism |
| `credit_transactions` | Credit audit trail | Immutable log of all credit movements |
| `payments` | Payment records | Multi-provider support (Stripe, PromptPay, TrueMoney) |
| `credit_packages` | Pricing configuration | Flexible packages with discounts |
| `user_preferences` | User settings | Video defaults, notifications, UI preferences |
| `webhook_logs` | Webhook debugging | Complete audit trail for external services |
| `api_usage_logs` | Cost monitoring | Track API usage and costs |

### Entity Relationship Diagram

```
users (1) ──────< (N) jobs
  │                    │
  │                    └──< (N) api_usage_logs
  │
  ├──< (N) credit_transactions
  │         │
  │         └──< (1) payments
  │
  ├──< (N) payments
  │
  └──< (1) user_preferences

webhook_logs ──> jobs (optional)
webhook_logs ──> payments (optional)
```

## Key Features

### 1. Automatic Credit Management

The schema includes triggers that automatically:
- **Deduct credits** when a job starts (`QUEUED` status)
- **Refund credits** if a job fails
- **Sync user balance** with transaction log

### 2. Row Level Security (RLS)

All tables have RLS policies ensuring:
- Users can only access their own data
- Credit packages are publicly readable
- Webhook/API logs are service-only

### 3. Audit Trail

Complete tracking of:
- All credit movements (`credit_transactions`)
- Payment history (`payments`)
- Webhook events (`webhook_logs`)
- API usage and costs (`api_usage_logs`)

### 4. Job Queue System

The `jobs` table supports:
- **Priority queue** - Higher priority jobs processed first
- **Status tracking** - 9 different states from PENDING to COMPLETED
- **Retry mechanism** - Automatic retry with configurable limits
- **Progress tracking** - Real-time progress percentage

## Deployment to Supabase

### Option 1: SQL Editor (Recommended for first-time setup)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy the entire contents of `schema.sql`
5. Run the query

### Option 2: Migration (Recommended for production)

```bash
# Install Supabase CLI
npm install -g supabase

# Initialize Supabase in your project
supabase init

# Create a new migration
supabase migration new initial_schema

# Copy schema.sql content to the migration file
# Then push to Supabase
supabase db push
```

### Option 3: Using Supabase CLI directly

```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Apply the schema
supabase db push
```

## Initial Data

The schema automatically creates 6 credit packages:

| Package | Credits | Price (THB) | Discount |
|---------|---------|-------------|----------|
| Trial Pack | 1 | 0 | 0% |
| Starter Pack | 3 | 99 | 0% |
| Popular Pack | 10 | 299 | 10% |
| Pro Pack | 25 | 699 | 15% |
| Business Pack | 50 | 1,299 | 20% |
| Enterprise Pack | 100 | 2,399 | 25% |

## Views for Analytics

The schema includes two views:

### `user_stats`
Aggregated user statistics including:
- Total jobs, completed jobs, failed jobs
- Total credits spent
- Last login time

### `job_queue_status`
Real-time queue monitoring:
- Job count by status
- Average wait time

## Custom Types

The schema defines 4 ENUM types:

1. **`job_status`** - 9 states for job lifecycle
2. **`transaction_type`** - 5 types of credit transactions
3. **`payment_status`** - 5 payment states
4. **`payment_provider`** - Supported payment gateways

## Indexes

All tables have optimized indexes for:
- User lookups
- Job queue processing (status + priority)
- Transaction history
- Webhook processing
- API cost tracking

## Security Notes

### RLS Policies

- ✅ Users can only view/edit their own data
- ✅ Credit transactions are read-only for users
- ✅ Webhook logs are service-only
- ✅ Credit packages are publicly readable

### Triggers

- ✅ Automatic `updated_at` timestamp updates
- ✅ Credit deduction on job start
- ✅ Automatic refund on job failure
- ✅ User balance sync with transactions

## Testing the Schema

After deployment, verify the setup:

```sql
-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verify RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';

-- Check initial credit packages
SELECT * FROM credit_packages ORDER BY sort_order;

-- Test credit package view (as authenticated user)
SELECT * FROM credit_packages WHERE is_active = true;
```

## Next Steps

After deploying the schema:

1. **Configure Supabase Storage**
   - Create buckets: `raw-videos`, `final-videos`, `thumbnails`
   - Set up storage policies

2. **Setup Authentication**
   - Enable email/password auth
   - Configure OAuth providers (Google, Facebook)
   - Setup email templates

3. **Create API Keys**
   - Generate service role key for backend
   - Create anon key for frontend

4. **Configure Webhooks**
   - Setup webhook endpoints in Next.js
   - Configure Replicate webhook URL
   - Setup payment provider webhooks

## Maintenance

### Backup Strategy

```sql
-- Export schema
pg_dump -s your_database > schema_backup.sql

-- Export data
pg_dump -a your_database > data_backup.sql
```

### Performance Monitoring

```sql
-- Check slow queries
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Support

For issues or questions about the database schema, please refer to:
- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
