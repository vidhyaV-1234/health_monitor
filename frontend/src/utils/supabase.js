import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export async function uploadToBucket({ bucket, path, file, contentType }) {
  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(path, file, { contentType, upsert: true });
  if (error) throw error;
  return data;
}

export async function ensureBucket(bucket) {
  try {
    // The public JS client cannot create buckets; ensure it exists via dashboard or backend.
    return true;
  } catch {
    return true;
  }
}

