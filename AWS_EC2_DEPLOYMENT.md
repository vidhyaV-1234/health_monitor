# Deploy Health Monitor to AWS EC2 (Free Tier)

## Prerequisites
- AWS Account with free tier eligibility
- Same AWS account where Bedrock is enabled

## Step 1: Launch EC2 Instance

1. **Go to AWS Console:** https://console.aws.amazon.com/ec2
2. **Click "Launch Instance"**
3. **Configure:**
   - **Name:** `health-monitor-backend`
   - **AMI:** Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance type:** `t2.micro` or `t3.micro` (1GB RAM, free tier)
   - **Key pair:** Create new or use existing (for SSH)
   - **Security Group:** 
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from anywhere
     - Allow Custom TCP (port 8000) from anywhere
   - **Storage:** 8GB (free tier includes 30GB)

4. **Click "Launch Instance"**

## Step 2: Connect to Instance

```bash
# Get your instance public IP from AWS console
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP
```

## Step 3: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install system dependencies for ML models
sudo apt install -y ffmpeg libsndfile1 libsm6 libxext6 libxrender-dev libgomp1

# Install git
sudo apt install -y git
```

## Step 4: Clone Repository

```bash
# Clone your repo
git clone https://github.com/vidhyaV-1234/health_monitor.git
cd health_monitor/health_monitor/backend
```

## Step 5: Setup Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies (this will take 10-15 minutes for ML packages)
pip install -r requirements.txt
```

## Step 6: Configure Environment Variables

```bash
# Create .env file
nano .env
```

Add these variables:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256

# AWS (usually auto-detected on EC2 with IAM role)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

Save and exit (`Ctrl+X`, `Y`, `Enter`)

## Step 7: Test Run

```bash
# Run backend
python backend_api.py
```

You should see:
```
✓ Preprocessor initialized (Whisper)
✓ Analyzer initialized (AWS Bedrock Claude 3.5 Sonnet)
✓ All ML models initialized successfully
Uvicorn running on http://0.0.0.0:8000
```

## Step 8: Setup as System Service (Run Forever)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/health-monitor.service
```

Add:
```ini
[Unit]
Description=Health Monitor Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/health_monitor/health_monitor/backend
Environment="PATH=/home/ubuntu/health_monitor/health_monitor/backend/venv/bin"
ExecStart=/home/ubuntu/health_monitor/health_monitor/backend/venv/bin/python backend_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable health-monitor
sudo systemctl start health-monitor
sudo systemctl status health-monitor
```

## Step 9: Setup Nginx (Optional - For Port 80)

```bash
sudo apt install -y nginx

sudo nano /etc/nginx/sites-available/health-monitor
```

Add:
```nginx
server {
    listen 80;
    server_name YOUR_INSTANCE_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/health-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 10: Update Frontend Config

Update `frontend/src/config.js`:
```javascript
export const API_BASE_URL = 'http://YOUR_EC2_PUBLIC_IP';
```

Or get a free domain from:
- Duck DNS: https://www.duckdns.org (free subdomain)
- No-IP: https://www.noip.com (free dynamic DNS)

## Cost Breakdown

**AWS EC2 Free Tier (12 months):**
- t2.micro instance: FREE (750 hours/month)
- 30GB storage: FREE
- Data transfer: 15GB/month FREE

**After 12 months:**
- t2.micro: ~$8/month
- Or switch to t3.micro: ~$7.50/month

**Total cost:** $0 for 12 months, then ~$8/month

## Monitoring

Check logs:
```bash
sudo journalctl -u health-monitor -f
```

Check status:
```bash
sudo systemctl status health-monitor
```

Restart if needed:
```bash
sudo systemctl restart health-monitor
```

## Updating Code

```bash
cd /home/ubuntu/health_monitor
git pull
sudo systemctl restart health-monitor
```

## Security Best Practices

1. **Use IAM Role** instead of hardcoded AWS keys:
   - Create EC2 IAM role with Bedrock permissions
   - Attach to instance
   - Remove AWS keys from .env

2. **Setup SSL/HTTPS:**
   - Use Let's Encrypt (free SSL)
   - Setup certbot for nginx

3. **Firewall:**
   - Only allow necessary ports in security group
   - Use AWS WAF if needed

4. **Backups:**
   - Take EBS snapshots weekly
   - Export env vars before updates

