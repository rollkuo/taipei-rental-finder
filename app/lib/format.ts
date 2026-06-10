export function formatPrice(price: number): string {
  return `NT$${price.toLocaleString("zh-TW")}`;
}

export function formatRelativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffMin = Math.round((now - then) / 60_000);
  if (diffMin < 1) return "剛剛";
  if (diffMin < 60) return `${diffMin} 分鐘前`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `${diffH} 小時前`;
  const diffD = Math.round(diffH / 24);
  if (diffD < 30) return `${diffD} 天前`;
  return new Date(iso).toLocaleDateString("zh-TW");
}
