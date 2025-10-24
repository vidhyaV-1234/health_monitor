# 🚂 Deploy Health Monitor to Railway.app

Railway.app is perfect for deploying ML models - it's similar to Render but with better support for heavy dependencies.

## 💰 Pricing

- **Free Tier:** $5 credit/month (enough for small projects)
- **After free credit:** ~$5-10/month depending on usage
- **Trial:** Get $5 credit immediately, no credit card required

## 📋 Prerequisites

1. Railway account: https://railway.app
2. GitHub account connected to Railway
3. Your code pushed to GitHub

---

## 🚀 Deployment Steps

### **Step 1: Sign Up for Railway**

1. Go to: https://railway.app
2. Click **"Start a New Project"**
3. Sign in with **GitHub**
4. Authorize Railway to access your repositories

---

### **Step 2: Create New Project**

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository: `health_monitor`
4. Railway will auto-detect it's a Python project

---

### **Step 3: Configure Service**

Railway will create a service automatically. Now configure it:

1. **Select the backend directory:**
   - Click on your service
   - Go to **Settings** → **Root Directory**
   - Set to: `health_monitor/backend`
   - Click **Save**

2. **Set Python version:**
   - In Settings → **Environment**
   - Add variable: `PYTHON_VERSION` = `3.10`

---

### **Step 4: Add Environment Variables**

Click **Variables** tab and add these:

```env
# Supabase
SUPABASE_URL=https://cswobvpopxypghwjolnb.supabase.co
SUPABASE_KEY=your-supabase-key

# JWT Authentication
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# AWS Bedrock Credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Optional: Supabase Media Bucket
SUPABASE_MEDIA_BUCKET=mood_media
```

**To add variables:**
1. Click **"New Variable"**
2. Enter `Key` and `Value`
3. Click **"Add"**
4. Repeat for all variables

---

### **Step 5: Deploy**

1. Click **"Deploy"** button
2. Railway will:
   - Install system dependencies (ffmpeg, libsndfile)
   - Install Python packages (~10-15 minutes for ML models)
   - Start your app

3. **Watch the logs** in real-time:
   - You should see:
     ```
     ✓ Preprocessor initialized (Whisper)
     ✓ Analyzer initialized (AWS Bedrock Claude 3.5 Sonnet)
     ✓ All ML models initialized successfully
     Uvicorn running on http://0.0.0.0:8000
     ```

---

### **Step 6: Get Your Railway URL**

1. Once deployed, go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Railway will give you a URL like: `https://health-monitor-production.up.railway.app`
4. **Copy this URL** - you'll need it for the frontend

---

### **Step 7: Update Frontend Config**

Update `frontend/src/config.js`:

```javascript
// API Configuration
// Backend URL points to Railway deployment
export const API_BASE_URL = 'https://health-monitor-production.up.railway.app';
```

Commit and push:
```bash
git add frontend/src/config.js
git commit -m "update: point frontend to Railway backend"
git push origin main
```

Vercel will auto-deploy the updated frontend.

---

### **Step 8: Test the Full Flow**

1. **Test Backend Directly:**
   ```bash
   curl https://your-railway-url.up.railway.app/
   ```
   
   Should return:
   ```json
   {
     "message": "Wellness Activity Recommender API",
     "version": "2.0.1"
   }
   ```

2. **Test Mood Endpoint:**
   ```bash
   curl -X POST https://your-railway-url.up.railway.app/api/mood \
     -H "Content-Type: application/json" \
     -d '{"id":"test","mood_text":"I am feeling stressed"}'
   ```

3. **Go to your Vercel frontend:**
   - https://health-monitor-tan.vercel.app
   - Login/Signup
   - Submit mood with text, audio, and image
   - Should get personalized recommendations!

---

## 📊 Expected Flow

```
User Input (Text + Audio + Image)
↓
Frontend (Vercel) → Upload to Supabase Storage
↓
Send URLs to Backend (Railway)
↓
Backend Downloads Files
↓
Preprocessor:
  ├─ Whisper transcribes audio
  ├─ DeepFace detects emotion from image
  └─ Combines with text
↓
Analyzer (AWS Bedrock):
  ├─ Fetches user history from Supabase
  ├─ Calls Claude 3.5 Sonnet
  └─ Generates personalized recommendations
↓
Report.py:
  ├─ Updates mood_entries table
  ├─ Updates user_reports table
  └─ Creates stress notifications
↓
Response to Frontend
↓
User sees recommendations
```

---

## 🔍 Monitoring & Debugging

### **View Logs:**
- Click on your service
- Go to **"Deployments"** → Click latest deployment
- Click **"View Logs"**
- Watch real-time logs

### **Check Metrics:**
- Go to **"Metrics"** tab
- See CPU, Memory, Network usage
- Railway shows if you're exceeding free tier

### **Restart Service:**
- Go to **Settings**
- Click **"Restart"**

---

## 💡 Tips & Best Practices

### **1. Optimize Memory Usage:**

If you run out of memory, reduce model sizes:

In `backend/preprocessor.py`:
```python
# Use smaller Whisper model
self.whisper_model = whisper.load_model("tiny")  # Instead of "base"
```

### **2. Monitor Costs:**

Railway shows your usage:
- Go to **"Usage"** tab
- See current spend
- Set spending limits if needed

### **3. Setup Alerts:**

Railway can send notifications:
- Go to **Settings** → **Notifications**
- Add Discord/Slack webhook
- Get notified of deploys/errors

### **4. Environment-Specific Configs:**

Use Railway's built-in env vars:
```python
# In backend_api.py
import os

# Railway provides these automatically
PORT = int(os.getenv("PORT", 8000))
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT")  # production/staging

if RAILWAY_ENVIRONMENT == "production":
    # Production-specific settings
    pass
```

---

## 🐛 Troubleshooting

### **Issue: Build Timeout**

If the build takes too long:
1. Railway free tier has build limits
2. Consider upgrading to Pro ($5/month for more build time)
3. Or pre-build Docker image

### **Issue: Out of Memory**

If app crashes with OOM:
1. Check **Metrics** → Memory usage
2. Upgrade to a plan with more RAM
3. Or optimize model sizes (use "tiny" Whisper instead of "base")

### **Issue: "Module not found"**

If Python packages fail to install:
1. Check **Logs** during build
2. Ensure `requirements.txt` is in root directory path
3. Try pinning specific versions

### **Issue: CORS Errors**

If frontend can't reach backend:
1. Check `backend_api.py` CORS config includes your Vercel URL
2. Verify Railway domain is correct in frontend config
3. Check Railway logs for incoming requests

---

## 🎯 After Deployment Checklist

- [ ] Backend is running on Railway
- [ ] All environment variables are set
- [ ] ML models initialized successfully (check logs)
- [ ] Frontend points to Railway URL
- [ ] Vercel redeployed with new config
- [ ] Test mood submission with text, audio, image
- [ ] Verify Supabase receives data
- [ ] Check AWS Bedrock is being called
- [ ] Test stress notification system

---

## 📈 Scaling Tips

As your app grows:

1. **Upgrade Railway Plan:** More RAM/CPU for better performance
2. **Add Redis:** Cache user data to reduce Supabase calls
3. **Use CDN:** Serve static assets faster
4. **Database Indexing:** Speed up Supabase queries
5. **Async Processing:** Queue heavy ML processing jobs

---

## 🆘 Support

- **Railway Discord:** https://discord.gg/railway
- **Railway Docs:** https://docs.railway.app
- **Railway Status:** https://status.railway.app

---

## 💰 Cost Optimization

To stay within free tier:

1. **Use smaller ML models:**
   - Whisper "tiny" instead of "base"
   - Reduces memory usage by 50%

2. **Implement caching:**
   - Cache frequent Bedrock responses
   - Reduce API calls

3. **Optimize startup:**
   - Lazy-load models only when needed
   - Faster cold starts

4. **Sleep inactive instances:**
   - Railway sleeps after inactivity (free tier)
   - First request after wake takes longer

---

## ✅ Success Criteria

Your deployment is successful when:

1. ✅ Railway logs show:
   ```
   ✓ Preprocessor initialized (Whisper)
   ✓ Analyzer initialized (AWS Bedrock)
   ✓ All ML models initialized successfully
   ```

2. ✅ Test endpoint returns:
   ```json
   {
     "message": "Mood processed successfully with full ML pipeline"
   }
   ```

3. ✅ Frontend shows personalized recommendations from Claude

4. ✅ Supabase tables are being updated

5. ✅ Audio transcription works

6. ✅ Image emotion detection works

---

**You're all set! 🎉**

Your Health Monitor app is now running on Railway with full ML capabilities!

