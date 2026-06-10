export const TAIPEI_DISTRICTS = [
  "中正區",
  "大同區",
  "中山區",
  "松山區",
  "大安區",
  "萬華區",
  "信義區",
  "士林區",
  "北投區",
  "內湖區",
  "南港區",
  "文山區",
] as const;

// Defaults the user wants visible on first load
export const DEFAULT_DISTRICTS: readonly string[] = ["信義區", "大安區"];
