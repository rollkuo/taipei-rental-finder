/**
 * Test helpers — talk directly to Supabase via service role to seed/cleanup
 * data without involving the UI. Lets us assert UI behavior in isolation.
 */
import { createClient } from "@supabase/supabase-js";
import { config as dotenvConfig } from "@dotenvx/dotenvx";
import path from "node:path";

// Load root .env.local (has SUPABASE_SERVICE_ROLE_KEY) — not committed.
dotenvConfig({ path: path.resolve(__dirname, "../../.env.local"), ignore: ["MISSING_ENV_FILE"] });

const URL =
  process.env.SUPABASE_URL ??
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://wrcvdowpfvdbhqgeiveo.supabase.co";
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!KEY) {
  throw new Error("SUPABASE_SERVICE_ROLE_KEY missing — load .env.local before tests");
}

export const admin = createClient(URL, KEY);

export interface SeedListing {
  source: string;
  source_id: string;
  url: string;
  title: string;
  price: number;
  rooms: number;
  bathrooms: number;
  district: string;
  road?: string | null;
  image_url?: string | null;
}

export async function seedListing(
  partial: Partial<SeedListing> = {}
): Promise<{ id: string; source: string; source_id: string }> {
  const sourceId = `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const row: SeedListing = {
    source: "e2e",
    source_id: sourceId,
    url: `https://rent.591.com.tw/${sourceId}`,
    title: `[E2E測試] ${partial.district ?? "信義區"}三房`,
    price: partial.price ?? 88_000,
    rooms: partial.rooms ?? 3,
    bathrooms: partial.bathrooms ?? 2,
    district: partial.district ?? "信義區",
    road: partial.road ?? null,
    image_url: partial.image_url ?? null,
    ...partial,
  };
  const { data, error } = await admin
    .from("listings")
    .insert(row)
    .select("id, source, source_id")
    .single();
  if (error || !data) throw new Error(`seed failed: ${error?.message}`);
  return data;
}

export async function hardDelete(id: string): Promise<void> {
  await admin.from("listings").delete().eq("id", id);
}

export async function readListing(id: string) {
  const { data } = await admin.from("listings").select("*").eq("id", id).maybeSingle();
  return data;
}
