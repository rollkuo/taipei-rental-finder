import { getSupabaseServer } from "@/lib/supabase/server";
import type { Listing } from "@/lib/types";
import { ListingsView } from "./listings-view";

// Always fetch fresh from DB; Realtime keeps it up-to-date after first paint.
export const dynamic = "force-dynamic";

export default async function Home() {
  const supabase = await getSupabaseServer();
  const { data, error } = await supabase
    .from("listings")
    .select("*")
    .is("deleted_at", null)
    .order("posted_at", { ascending: false, nullsFirst: false })
    .limit(500);

  if (error) {
    return (
      <main className="p-8">
        <h1 className="text-2xl font-bold">載入失敗</h1>
        <pre className="mt-4 text-sm text-red-600">{error.message}</pre>
      </main>
    );
  }

  const { data: lastRun } = await supabase
    .from("crawl_runs")
    .select("source, status, started_at, finished_at, found_count, new_count")
    .eq("status", "success")
    .order("started_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return (
    <ListingsView
      initialListings={(data ?? []) as Listing[]}
      lastSuccessfulRun={lastRun}
    />
  );
}
