-- PostgreSQL database schema
-- Auto-generated from: pg_dump spreadsheet_intelligence --schema-only --no-owner --no-acl --no-comments
-- Regenerate with: /opt/homebrew/opt/postgresql@17/bin/pg_dump spreadsheet_intelligence --schema-only --no-owner --no-acl --no-comments > db/schema.sql

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

CREATE TABLE public.workbooks (
    id integer NOT NULL,
    filename character varying(255) NOT NULL,
    original_name character varying(255) NOT NULL,
    upload_path character varying(500) NOT NULL,
    sheet_count integer NOT NULL,
    schema_json json,
    relationships_json json,
    has_formulas boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);

CREATE TABLE public.query_logs (
    id integer NOT NULL,
    workbook_id integer NOT NULL,
    question text NOT NULL,
    generated_sql text,
    answer_raw text,
    attribution_json json,
    error text,
    created_at timestamp without time zone NOT NULL
);

CREATE TABLE public.sheet_embeddings (
    id integer NOT NULL,
    workbook_id integer NOT NULL,
    sheet_name character varying(255) NOT NULL,
    table_name character varying(255) NOT NULL,
    description text NOT NULL,
    embedding public.vector(1536) NOT NULL,
    created_at timestamp without time zone NOT NULL
);

-- Sequences
CREATE SEQUENCE public.workbooks_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.workbooks_id_seq OWNED BY public.workbooks.id;
ALTER TABLE ONLY public.workbooks ALTER COLUMN id SET DEFAULT nextval('public.workbooks_id_seq'::regclass);

CREATE SEQUENCE public.query_logs_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.query_logs_id_seq OWNED BY public.query_logs.id;
ALTER TABLE ONLY public.query_logs ALTER COLUMN id SET DEFAULT nextval('public.query_logs_id_seq'::regclass);

CREATE SEQUENCE public.sheet_embeddings_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.sheet_embeddings_id_seq OWNED BY public.sheet_embeddings.id;
ALTER TABLE ONLY public.sheet_embeddings ALTER COLUMN id SET DEFAULT nextval('public.sheet_embeddings_id_seq'::regclass);

-- Primary keys
ALTER TABLE ONLY public.alembic_version ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);
ALTER TABLE ONLY public.workbooks ADD CONSTRAINT workbooks_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.query_logs ADD CONSTRAINT query_logs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.sheet_embeddings ADD CONSTRAINT sheet_embeddings_pkey PRIMARY KEY (id);

-- Indexes
CREATE INDEX ix_sheet_embeddings_workbook_id ON public.sheet_embeddings USING btree (workbook_id);

-- Foreign keys
ALTER TABLE ONLY public.query_logs ADD CONSTRAINT query_logs_workbook_id_fkey FOREIGN KEY (workbook_id) REFERENCES public.workbooks(id);
ALTER TABLE ONLY public.sheet_embeddings ADD CONSTRAINT sheet_embeddings_workbook_id_fkey FOREIGN KEY (workbook_id) REFERENCES public.workbooks(id);
