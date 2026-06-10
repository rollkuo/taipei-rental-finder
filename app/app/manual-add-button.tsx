"use client";

import { useState } from "react";

import { TAIPEI_DISTRICTS } from "@/lib/constants";

export function ManualAddButton() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [price, setPrice] = useState("");
  const [rooms, setRooms] = useState("3");
  const [bathrooms, setBathrooms] = useState("2");
  const [district, setDistrict] = useState<string>("信義區");
  const [road, setRoad] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setUrl("");
    setPrice("");
    setRooms("3");
    setBathrooms("2");
    setDistrict("信義區");
    setRoad("");
    setError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch("/api/listings/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          price: Number(price),
          rooms: Number(rooms),
          bathrooms: Number(bathrooms),
          district,
          road: road.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "送出失敗");
        return;
      }
      reset();
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-2xl text-white shadow-lg transition-transform hover:scale-105 hover:bg-blue-700"
        aria-label="手動加入物件"
      >
        +
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
          onClick={() => !submitting && setOpen(false)}
        >
          <form
            onClick={(e) => e.stopPropagation()}
            onSubmit={submit}
            className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
          >
            <h2 className="mb-1 text-lg font-semibold">手動加入 591 物件</h2>
            <p className="mb-4 text-xs text-zinc-500">
              貼上 591 連結，填入基本資訊。圖片和標題會嘗試自動抓取。
            </p>

            <label className="mb-3 block text-sm">
              <span className="mb-1 block font-medium">591 連結 *</span>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://rent.591.com.tw/12345.html"
                className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
              />
            </label>

            <div className="mb-3 grid grid-cols-3 gap-2">
              <label className="block text-sm">
                <span className="mb-1 block font-medium">月租 *</span>
                <input
                  type="number"
                  required
                  min={1}
                  max={1_000_000}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full rounded border border-zinc-300 px-2 py-2 text-sm"
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">房</span>
                <select
                  value={rooms}
                  onChange={(e) => setRooms(e.target.value)}
                  className="w-full rounded border border-zinc-300 px-2 py-2 text-sm"
                >
                  {[3, 4, 5, 6].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium">衛</span>
                <select
                  value={bathrooms}
                  onChange={(e) => setBathrooms(e.target.value)}
                  className="w-full rounded border border-zinc-300 px-2 py-2 text-sm"
                >
                  {[2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="mb-3 block text-sm">
              <span className="mb-1 block font-medium">行政區 *</span>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
              >
                {TAIPEI_DISTRICTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>

            <label className="mb-4 block text-sm">
              <span className="mb-1 block font-medium">路段（選填）</span>
              <input
                type="text"
                value={road}
                onChange={(e) => setRoad(e.target.value)}
                placeholder="忠孝東路五段"
                className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
              />
            </label>

            {error && (
              <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                disabled={submitting}
                className="rounded px-3 py-2 text-sm hover:bg-zinc-100"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-blue-700"
              >
                {submitting ? "送出中..." : "加入物件"}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
