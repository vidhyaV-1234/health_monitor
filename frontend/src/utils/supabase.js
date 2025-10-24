import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const isConfigured = Boolean(supabaseUrl && supabaseAnonKey);
export const supabase = isConfigured ? createClient(supabaseUrl, supabaseAnonKey) : null;

export async function uploadToBucket({ bucket, path, file, contentType }) {
  if (!isConfigured || !supabase) {
    throw new Error('Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
  }
  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(path, file, { contentType, upsert: true });
  if (error) throw error;
  return data;
}

export async function ensureBucket(bucket) {
  // The public JS client cannot create buckets; ensure it exists via dashboard or backend.
  return true;
}

