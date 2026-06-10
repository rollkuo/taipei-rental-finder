export type Listing = {
  id: string;
  source: string;
  source_id: string;
  url: string;
  title: string;
  price: number;
  rooms: number;
  bathrooms: number;
  district: string;
  road: string | null;
  has_elevator: boolean;
  image_url: string | null;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  saved_at: string | null;
  deleted_at: string | null;
};

export type SortKey = "posted_at_desc" | "price_asc" | "price_desc";
