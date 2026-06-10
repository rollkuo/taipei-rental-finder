"use client";

import { useEffect, useMemo, useState } from "react";
import type { RealtimePostgresChangesPayload } from "@supabase/supabase-js";

import { DEFAULT_DISTRICTS, TAIPEI_DISTRICTS } from "@/lib/constants";
import { formatPrice, formatRelativeTime } from "@/lib/format";
import { getSupabaseBrowser } from "@/lib/supabase/browser";
import type { Listing, SortKey } from "@/lib/types";
import { ManualAddButton } from "./manual-add-button";

interface LastRun {
  source: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  found_count: number | null;
  new_count: number | null;
}

interface Props {
  initialListings: Listing[];
  lastSuccessfulRun: LastRun | null;
}

export function ListingsView({ initialListings, lastSuccessfulRun }: Props) {
  const [listings, setListings] = useState<Listing[]>(initialListings);
  const [selectedDistricts, setSelectedDistricts] =
    useState<Set<string>>(new Set(DEFAULT_DISTRICTS));
  const [savedOnly, setSavedOnly] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("posted_at_desc");

  // Realtime: subscribe to listings INSERT/UPDATE so changes from the
  // crawler (new listings) or the other device (save/delete) propagate.
  useEffect(() => {
    const supabase = getSupabaseBrowser();
    const channel = supabase
      .channel("listings-changes")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "listings" },
        (payload: RealtimePostgresChangesPayload<Listing>) => {
          const next = payload.new as Listing;
          setListings((prev) => {
            if (prev.some((l) => l.id === next.id)) return prev;
            return [next, ...prev];
          });
        }
      )
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "listings" },
        (payload: RealtimePostgresChangesPayload<Listing>) => {
          const next = payload.new as Listing;
          setListings((prev) =>
            prev.map((l) => (l.id === next.id ? next : l))
          );
        }
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const visible = useMemo(() => {
    const filtered = listings.filter((l) => {
      if (l.deleted_at) return false;
      if (savedOnly && !l.saved_at) return false;
      if (selectedDistricts.size > 0 && !selectedDistricts.has(l.district))
        return false;
      return true;
    });
    return [...filtered].sort((a, b) => {
      switch (sortKey) {
        case "price_asc":
          return a.price - b.price;
        case "price_desc":
          return b.price - a.price;
        case "posted_at_desc":
        default: {
          const ax = a.posted_at ?? a.first_seen_at;
          const bx = b.posted_at ?? b.first_seen_at;
          return new Date(bx).getTime() - new Date(ax).getTime();
        }
      }
    });
  }, [listings, selectedDistricts, savedOnly, sortKey]);

  function toggleDistrict(d: string) {
    setSelectedDistricts((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d);
      else next.add(d);
      return next;
    });
  }

  async function toggleSaved(listing: Listing) {
    const supabase = getSupabaseBrowser();
    const newSavedAt = listing.saved_at ? null : new Date().toISOString();
    // Optimistic
    setListings((prev) =>
      prev.map((l) =>
        l.id === listing.id ? { ...l, saved_at: newSavedAt } : l
      )
    );
    const { error } = await supabase
      .from("listings")
      .update({ saved_at: newSavedAt })
      .eq("id", listing.id);
    if (error) {
      // Rollback
      setListings((prev) =>
        prev.map((l) =>
          l.id === listing.id ? { ...l, saved_at: listing.saved_at } : l
        )
      );
      alert(`儲存失敗：${error.message}`);
    }
  }

  async function softDelete(listing: Listing) {
    if (!confirm(`確定永久隱藏「${listing.title}」？\n（之後爬蟲遇到也不會再次出現）`))
      return;
    const supabase = getSupabaseBrowser();
    const now = new Date().toISOString();
    // Optimistic
    setListings((prev) => prev.map((l) => (l.id === listing.id ? { ...l, deleted_at: now } : l)));
    const { error } = await supabase
      .from("listings")
      .update({ deleted_at: now })
      .eq("id", listing.id);
    if (error) {
      setListings((prev) =>
        prev.map((l) =>
          l.id === listing.id ? { ...l, deleted_at: listing.deleted_at } : l
        )
      );
      alert(`刪除失敗：${error.message}`);
    }
  }

  const totalActive = listings.filter((l) => !l.deleted_at).length;
  const totalSaved = listings.filter((l) => l.saved_at && !l.deleted_at).length;

  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">台北租屋彙整</h1>
        <p className="mt-1 text-sm text-zinc-600">
          3 房以上 · 2 衛以上 · 月租 ≤ NT$120,000 · 有電梯
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          總共 {totalActive} 筆 · 已收藏 {totalSaved} 筆 · 上次抓取：
          {lastSuccessfulRun
            ? `${formatRelativeTime(lastSuccessfulRun.finished_at ?? lastSuccessfulRun.started_at)}（${
                lastSuccessfulRun.found_count ?? 0
              } 筆，新增 ${lastSuccessfulRun.new_count ?? 0}）`
            : "尚未成功"}
        </p>
      </header>

      <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={savedOnly}
              onChange={(e) => setSavedOnly(e.target.checked)}
              className="h-4 w-4"
            />
            只看已收藏
          </label>
          <label className="flex items-center gap-2 text-sm">
            排序：
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="rounded border border-zinc-300 bg-white px-2 py-1"
            >
              <option value="posted_at_desc">最新上架</option>
              <option value="price_asc">租金低 → 高</option>
              <option value="price_desc">租金高 → 低</option>
            </select>
          </label>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {TAIPEI_DISTRICTS.map((d) => {
            const on = selectedDistricts.has(d);
            return (
              <button
                key={d}
                onClick={() => toggleDistrict(d)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  on
                    ? "bg-blue-600 text-white"
                    : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                }`}
              >
                {d}
              </button>
            );
          })}
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-12 text-center text-zinc-500">
          沒有符合條件的物件。試試多選幾個行政區、或按右下角「+」手動加入。
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((l) => (
            <ListingCard
              key={l.id}
              listing={l}
              onToggleSave={() => toggleSaved(l)}
              onDelete={() => softDelete(l)}
            />
          ))}
        </ul>
      )}

      <ManualAddButton />
    </main>
  );
}

function ListingCard({
  listing,
  onToggleSave,
  onDelete,
}: {
  listing: Listing;
  onToggleSave: () => void;
  onDelete: () => void;
}) {
  const isSaved = !!listing.saved_at;
  return (
    <li
      className={`overflow-hidden rounded-lg border bg-white transition-shadow hover:shadow-md ${
        isSaved ? "border-amber-300 ring-1 ring-amber-200" : "border-zinc-200"
      }`}
    >
      <div className="relative aspect-[4/3] bg-zinc-100">
        {listing.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={listing.image_url}
            alt={listing.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-zinc-400">
            無圖
          </div>
        )}
        {isSaved && (
          <span className="absolute top-2 left-2 rounded bg-amber-500 px-2 py-0.5 text-xs font-medium text-white">
            ⭐ 已收藏
          </span>
        )}
      </div>
      <div className="p-3">
        <h3 className="line-clamp-2 text-sm font-medium leading-snug" title={listing.title}>
          {listing.title}
        </h3>
        <p className="mt-1.5 text-lg font-bold text-zinc-900">
          {formatPrice(listing.price)}
          <span className="ml-1 text-xs font-normal text-zinc-500">/月</span>
        </p>
        <p className="mt-1 text-xs text-zinc-600">
          {listing.rooms} 房 · {listing.bathrooms} 衛 · {listing.district}
          {listing.road ? ` · ${listing.road}` : ""}
        </p>
        <div className="mt-3 flex gap-2">
          <button
            onClick={onToggleSave}
            className={`flex-1 rounded px-2 py-1.5 text-xs font-medium transition-colors ${
              isSaved
                ? "bg-amber-100 text-amber-800 hover:bg-amber-200"
                : "bg-zinc-100 text-zinc-800 hover:bg-zinc-200"
            }`}
          >
            {isSaved ? "取消收藏" : "★ 收藏"}
          </button>
          <button
            onClick={onDelete}
            className="rounded px-2 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            刪除
          </button>
          <a
            href={listing.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded bg-blue-600 px-2 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            原始 ↗
          </a>
        </div>
      </div>
    </li>
  );
}
