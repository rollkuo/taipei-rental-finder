import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

import { TAIPEI_DISTRICTS } from "@/lib/constants";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface ManualBody {
  url?: string;
  price?: number;
  rooms?: number;
  bathrooms?: number;
  district?: string;
  road?: string | null;
}

const LISTING_ID_RE = /\/(\d+)(?:\.html)?(?:[?#]|$)/;
const OG_IMAGE_RE =
  /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i;
const OG_TITLE_RE =
  /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i;

function bad(msg: string, status = 400) {
  return NextResponse.json({ error: msg }, { status });
}

export async function POST(req: NextRequest) {
  let body: ManualBody;
  try {
    body = (await req.json()) as ManualBody;
  } catch {
    return bad("Invalid JSON body");
  }
  const { url, price, rooms, bathrooms, district, road } = body;

  if (!url || typeof url !== "string") return bad("url required");
  if (!url.startsWith("https://rent.591.com.tw/"))
    return bad("URL must be a rent.591.com.tw link");
  if (typeof price !== "number" || price <= 0 || price > 10_000_000)
    return bad("price must be a positive number");
  if (typeof rooms !== "number" || rooms < 1 || rooms > 9)
    return bad("rooms must be 1-9");
  if (typeof bathrooms !== "number" || bathrooms < 1 || bathrooms > 9)
    return bad("bathrooms must be 1-9");
  if (!district || !(TAIPEI_DISTRICTS as readonly string[]).includes(district))
    return bad("district must be a Taipei district");

  const idMatch = LISTING_ID_RE.exec(url);
  if (!idMatch) return bad("Could not extract listing ID from URL");
  const sourceId = idMatch[1];

  let imageUrl: string | null = null;
  let title = `[手動加入] ${district}${road ?? ""}`;
  try {
    const res = await fetch(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const html = await res.text();
      const ogImg = OG_IMAGE_RE.exec(html);
      const ogTitle = OG_TITLE_RE.exec(html);
      if (ogImg) imageUrl = ogImg[1];
      if (ogTitle) title = ogTitle[1].trim() || title;
    }
  } catch {
    // No-op; manual entry still proceeds without enrichment.
  }

  const supabaseUrl =
    process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) {
    return bad("Server misconfigured: Supabase env vars missing", 500);
  }
  const admin = createClient(supabaseUrl, serviceKey);

  const { data: existing } = await admin
    .from("listings")
    .select("id, deleted_at")
    .eq("source_id", sourceId)
    .limit(1)
    .maybeSingle();

  if (existing?.deleted_at) {
    return bad("This listing was previously deleted and will not be re-added", 409);
  }

  const row = {
    source: "591_manual",
    source_id: sourceId,
    url,
    title,
    price,
    rooms,
    bathrooms,
    district,
    road: road ?? null,
    has_elevator: true,
    image_url: imageUrl,
    posted_at: new Date().toISOString(),
  };

  if (existing) {
    const { error } = await admin
      .from("listings")
      .update({ ...row, last_seen_at: new Date().toISOString() })
      .eq("id", existing.id);
    if (error) return bad(error.message, 500);
    return NextResponse.json({ status: "updated", id: existing.id });
  }

  const { data: inserted, error } = await admin
    .from("listings")
    .insert(row)
    .select("id")
    .single();
  if (error) return bad(error.message, 500);
  return NextResponse.json({ status: "created", id: inserted.id });
}
