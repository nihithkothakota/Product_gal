-- PostgreSQL initialization script
-- Runs on first container startup

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable ltree for hierarchical category paths (optional future use)
CREATE EXTENSION IF NOT EXISTS ltree;
