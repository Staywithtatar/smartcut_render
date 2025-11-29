-- Create test user for development (without authentication)
-- Run this in Supabase SQL Editor

-- Step 1: Insert into auth.users (Supabase Auth table)
INSERT INTO auth.users (
  id,
  instance_id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at,
  confirmation_token,
  email_change,
  email_change_token_new,
  recovery_token
) VALUES (
  '00000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000000',
  'authenticated',
  'authenticated',
  'test@autocut.local',
  crypt('test123456', gen_salt('bf')),
  NOW(),
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Test User"}',
  NOW(),
  NOW(),
  '',
  '',
  '',
  ''
)
ON CONFLICT (id) DO NOTHING;

-- Step 2: Profile will be created automatically by trigger
-- But if trigger doesn't work, manually insert:
INSERT INTO profiles (id, full_name, credits, created_at)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Test User',
  1000,
  NOW()
)
ON CONFLICT (id) DO NOTHING;
