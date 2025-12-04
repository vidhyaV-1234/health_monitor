# Supabase Storage Setup Guide

## Overview
This guide explains how to set up Supabase Storage for handling audio and image uploads in the Health Monitor application.

## Flow Diagram
```
User uploads file → Frontend uploads to Supabase Storage → Gets public URL → 
Sends URL to Backend → Backend downloads from URL → Processes with ML models
```

## Setup Steps

### 1. Create Supabase Storage Bucket

1. Go to your Supabase project dashboard: https://supabase.com/dashboard
2. Navigate to **Storage** in the left sidebar
3. Click **Create a new bucket**
4. Configure the bucket:
   - **Name**: `mood_media`
   - **Public bucket**: ✅ **Enable** (Required for backend to download files)
   - **File size limit**: Set based on your needs (e.g., 10MB)
   - **Allowed MIME types**: Leave empty to allow all types

5. Click **Create bucket**

### 2. Configure Bucket Policies (IMPORTANT!)

For the backend to download files, the bucket must be publicly accessible. Set up the following RLS policies:

#### Policy 1: Allow Public Read Access
```sql
-- Go to Storage > Policies > mood_media bucket > New Policy
-- Name: Public read access
-- Policy: SELECT
-- SQL:
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'mood_media');
```

#### Policy 2: Allow Authenticated Users to Upload
```sql
-- Name: Authenticated users can upload
-- Policy: INSERT
-- SQL:
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'mood_media' 
  AND auth.role() = 'authenticated'
);
```

#### Policy 3: Allow Users to Delete Their Own Files
```sql
-- Name: Users can delete their own files
-- Policy: DELETE
-- SQL:
CREATE POLICY "Users can delete their own files"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'mood_media' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

### 3. Configure Frontend Environment Variables

Create `.env.local` in the `frontend/` directory:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
VITE_SUPABASE_MEDIA_BUCKET=mood_media
```

**Where to find these values:**
- `VITE_SUPABASE_URL`: Project Settings > API > Project URL
- `VITE_SUPABASE_ANON_KEY`: Project Settings > API > anon/public key

### 4. Configure Vercel Environment Variables (Production)

In your Vercel project dashboard:

1. Go to **Settings** > **Environment Variables**
2. Add the following:
   - `VITE_API_URL`: `https://your-backend.onrender.com`
   - `VITE_SUPABASE_URL`: `https://your-project-id.supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: `your-anon-key-here`
   - `VITE_SUPABASE_MEDIA_BUCKET`: `mood_media`

3. Click **Save** and redeploy

## How It Works

### Frontend Upload Process
```javascript
// 1. User selects file
<input type="file" onChange={handleFileChange} />

// 2. File is stored in state
setForm({ ...form, mood_audio: file });

// 3. On submit, upload to Supabase
const result = await uploadFileAndGetUrl({
  bucket: 'mood_media',
  file: form.mood_audio,
  folder: user.id,  // Organizes files by user ID
});

// 4. Get public URL
const audioUrl = result.publicUrl;
// Example: https://your-project.supabase.co/storage/v1/object/public/mood_media/user123/1698765432_audio.wav

// 5. Send URL to backend
await axios.post('/api/mood', {
  id: user.id,
  mood_text: "feeling good",
  audio_url: audioUrl,
  image_url: imageUrl
});
```

### Backend Download Process
```python
# 1. Receive URL from frontend
audio_url = data.get("audio_url")

# 2. Download file from Supabase
if audio_url:
    resp = requests.get(audio_url)
    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".audio").name
    with open(audio_path, "wb") as f:
        f.write(resp.content)

# 3. Process with ML models
preprocessed_data = preprocessor.preprocess(
    audio_path=audio_path,
    image_path=image_path,
    text_input=mood_text,
    user_id=user_id,
    analyze=True
)

# 4. Clean up temp files
os.unlink(audio_path)
```

## File Organization

Files are organized in Supabase Storage by user ID:
```
mood_media/
├── user_123/
│   ├── 1698765432_recording.wav
│   ├── 1698765432_photo.jpg
│   └── 1698765500_recording.wav
├── user_456/
│   ├── 1698766000_recording.wav
│   └── 1698766000_photo.jpg
```

Each file is named with a timestamp to ensure uniqueness.

## Troubleshooting

### Issue: "Upload error: new row violates row-level security policy"
**Solution**: Make sure the bucket is public and RLS policies are correctly configured.

### Issue: "Error 403: Forbidden" when backend downloads
**Solution**: Ensure the bucket has public read access policy enabled.

### Issue: Files upload but backend can't process them
**Solution**: Check that the public URL is accessible by testing it in a browser. The URL should download the file.

### Issue: "Supabase is not configured" error
**Solution**: Verify that `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set in your `.env.local` (local) or Vercel environment variables (production).

## Testing

### Test Frontend Upload
1. Open browser DevTools console
2. Upload an audio/image file
3. Look for logs:
   ```
   📤 Uploading to Supabase: {bucket: "mood_media", folder: "user123", ...}
   🎤 Uploading audio...
   ✓ Audio uploaded: https://...
   📤 Sending payload to backend: {id: "user123", audio_url: "https://...", ...}
   ```

### Test Backend Download
1. Check backend logs on Render
2. Look for:
   ```
   Audio URL: https://your-project.supabase.co/storage/v1/object/public/mood_media/...
   Downloaded audio to: /tmp/...
   Using ML models with downloaded files
   ```

### Test Public URL Access
Copy a public URL from the logs and paste it in your browser. The file should download immediately.

## Security Considerations

1. **Public Read Access**: Files are publicly readable via URL. Don't store sensitive personal information.
2. **Authenticated Upload**: Only authenticated users can upload files.
3. **User Isolation**: Files are organized by user ID, making it easy to implement per-user deletion policies.
4. **Anon Key**: The `VITE_SUPABASE_ANON_KEY` is safe to expose in frontend code - it only provides limited access controlled by RLS policies.

## Cost Considerations

- **Supabase Free Tier**: 1GB storage, 2GB transfer
- **Files are not automatically deleted**: Consider implementing a cleanup policy to delete old files
- **Bandwidth**: Each mood entry requires: upload (frontend→Supabase) + download (Supabase→backend)

## Future Improvements

1. **Direct Backend Upload**: For better bandwidth efficiency, consider uploading directly to backend
2. **File Cleanup**: Implement automatic deletion of files after processing
3. **Compression**: Compress audio/images before upload to reduce storage costs
4. **CDN**: Use Supabase CDN for faster downloads

