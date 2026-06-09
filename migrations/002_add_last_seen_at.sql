-- Migration: Add last_seen_at and last_machine_id columns
-- Run this in the Supabase SQL Editor for project vuyhjbmvyimapabdcjjt
-- SQL Editor: https://supabase.com/dashboard/project/vuyhjbmvyimapabdcjjt/sql/new

ALTER TABLE IF EXISTS licenses
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_machine_id TEXT;
