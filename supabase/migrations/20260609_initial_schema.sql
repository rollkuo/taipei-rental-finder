-- Initial schema for Taipei rental finder
-- listings: rental properties (auto-scraped + manual paste)
-- crawl_runs: scraper execution history (debug + last-success display)

create extension if not exists "pgcrypto";

create table public.listings (
  id              uuid primary key default gen_random_uuid(),
  source          text not null,
  source_id       text not null,
  url             text not null,
  title           text not null,
  price           int  not null,
  rooms           int  not null,
  bathrooms       int  not null,
  district        text not null,
  road            text,
  has_elevator    boolean not null default true,
  image_url       text,
  posted_at       timestamptz,
  first_seen_at   timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  scraped_payload jsonb,
  saved_at        timestamptz,
  deleted_at      timestamptz,
  unique (source, source_id)
);

create index listings_active_idx
  on public.listings (posted_at desc nulls last)
  where deleted_at is null;

create index listings_saved_idx
  on public.listings (saved_at desc nulls last)
  where deleted_at is null and saved_at is not null;

create index listings_district_idx
  on public.listings (district)
  where deleted_at is null;

create table public.crawl_runs (
  id           uuid primary key default gen_random_uuid(),
  source       text not null,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  status       text not null check (status in ('running','success','failed')),
  found_count  int,
  new_count    int,
  error        text
);

create index crawl_runs_recent_idx
  on public.crawl_runs (started_at desc);

-- Enable Realtime on listings (Postgres Changes broadcast)
alter publication supabase_realtime add table public.listings;

-- Row Level Security
alter table public.listings   enable row level security;
alter table public.crawl_runs enable row level security;

-- Public read access (no auth required - it's just us two)
create policy "anon can read listings"
  on public.listings for select
  to anon, authenticated
  using (true);

create policy "anon can read crawl_runs"
  on public.crawl_runs for select
  to anon, authenticated
  using (true);

-- Anon can only toggle saved_at and deleted_at — not modify scraped data
create policy "anon can toggle saved/deleted"
  on public.listings for update
  to anon, authenticated
  using (true)
  with check (true);

-- (Tighter column-level rule enforced in API layer via explicit column lists)

-- Service role bypasses RLS automatically for crawler writes
