# 🚀 PRODUCTION DEPLOYMENT GUIDE

## Overview

This guide will help you deploy ARIA to production alongside your existing staging environment.

**What you'll have after this:**
- ✅ **Staging**: `airesume-staging.thetalogics.com` (for testing)
- ✅ **Production**: `aira.thetalogics.com` (for real users)
- ✅ Both run on the same VPS, completely isolated
- ✅ Automatic deployments via GitHub → Docker Hub → Watchtower

---

## 📋 PART 1: Push Code to GitHub

### Step 1: Commit and Push Production Branch

Open PowerShell and run:

```powershell
cd "C:\Users\DELL\Projects\Resume AI by ThetaLogics"
git add .
git commit -m "feat: add production environment setup"
git push -u origin production
```

This creates the `production` branch on GitHub.

---

## 📦 PART 2: Deploy Production Stack in Portainer

### Step 2: Login to Portainer

1. Open your browser and go to your Portainer URL (usually `http://YOUR_VPS_IP:9000`)
2. Login with your credentials

### Step 3: Create Production Stack

1. Click on **"Stacks"** in the left menu
2. Click **"Add stack"** button
3. Fill in:
   - **Name**: `aria-production`
   - **Environment**: Select your Docker environment
   - **Build method**: Choose **"Web editor"** or **"Git Repository"**

#### Option A: Web Editor (Recommended for now)

1. Select **"Web editor"**
2. Open the file `docker-compose.production.yml` from your computer
3. Copy **ALL** the content
4. Paste it into the Portainer editor
5. Click **"Deploy the stack"**

#### Option B: Git Repository (Better for automation)

1. Select **"Git Repository"**
2. Fill in:
   - **Repository URL**: `https://github.com/YOUR_USERNAME/resume-ai` (replace with your repo)
   - **Git Reference**: `production`
   - **Compose path**: `docker-compose.production.yml`
3. Click **"Deploy the stack"**

### Step 4: Set Environment Variables in Portainer

After creating the stack, you need to set environment variables:

1. In Portainer, go to **Stacks** → Click on `aria-production`
2. Click on **"Editor"** tab
3. Add these environment variables:

```
POSTGRES_PASSWORD=Itslogical1.
JWT_SECRET_KEY=ecb77c4575f6d63fadf832346867c00fbd6888e9090b2d772ec44fe653abc3ad
OLLAMA_API_KEY=your_actual_ollama_api_key_here
CORS_ORIGINS=https://aira.thetalogics.com
```

4. Click **"Update the stack"**

> **Note**: If using Ollama Cloud (recommended), keep `OLLAMA_BASE_URL=https://ollama.com`  
> If using local Ollama, you'll need to connect to the staging Ollama container

### Step 5: Verify Deployment

1. In Portainer, go to **"Containers"**
2. You should see new containers with `-prod` suffix:
   - `aria-postgres-prod`
   - `aria-backend-prod`
   - `aria-frontend-prod`
   - `aria-nginx-prod`
   - `aria-watchtower-prod`

3. Click on each container and check **Logs** to ensure they started without errors

---

## 🌐 PART 3: Domain Setup (aira.thetalogics.com)

### Step 6: Configure DNS

You need to point `aira.thetalogics.com` to your VPS IP address.

#### If using a domain provider (GoDaddy, Namecheap, Cloudflare, etc.):

1. Login to your domain provider
2. Go to **DNS Management** or **DNS Settings**
3. Add a new **A Record**:
   - **Type**: `A`
   - **Name/Host**: `aira`
   - **Value/Points to**: `YOUR_VPS_IP_ADDRESS` (same IP as staging)
   - **TTL**: `3600` (or default)

4. Save the record

#### Example DNS Records:

```
Type    Name        Value               TTL
A       aira        123.45.67.89        3600
A       airesume-staging  123.45.67.89  3600
```

> Both subdomains point to the **same VPS IP**, but different ports internally

### Step 7: Wait for DNS Propagation

DNS changes can take **5 minutes to 48 hours** to propagate worldwide.

Check if it's working:
```powershell
ping aira.thetalogics.com
```

You should see your VPS IP address.

---

## 🔒 PART 4: SSL Certificate (HTTPS)

### Step 8: Setup SSL for Production

Your production nginx is configured to work with Certbot for SSL.

#### Option A: Using Portainer (Manual)

1. SSH into your VPS
2. Run this command to generate SSL certificate:

```bash
docker exec aria-certbot-prod certbot certonly --standalone -d aira.thetalogics.com --email your-email@thetalogics.com --agree-tos --non-interactive
```

3. Update nginx config to use SSL (you'll need to modify `nginx.production.conf`)

#### Option B: Using External Reverse Proxy (Easier)

If you have an existing nginx on your VPS that handles SSL:

1. Configure it to:
   - Listen on port 443 (HTTPS) for `aira.thetalogics.com`
   - Proxy pass to `http://localhost:8080` (your production nginx)
   
2. Example config:

```nginx
server {
    listen 443 ssl;
    server_name aira.thetalogics.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

> **Recommendation**: If you're not comfortable with SSL setup, ask a developer to help with this step

---

## ✅ PART 5: Test Everything

### Step 9: Verify Production is Working

1. **Check Portainer**:
   - All production containers should be running (green status)
   - Check logs for any errors

2. **Test Backend**:
   ```
   http://YOUR_VPS_IP:8080/health
   ```
   Should return: `{"status": "ok"}`

3. **Test Frontend**:
   ```
   http://YOUR_VPS_IP:8080
   ```
   Should show the ARIA login page

4. **Test Domain** (after DNS propagates):
   ```
   https://aira.thetalogics.com
   ```
   Should show the production app

---

## 🔄 How Automatic Deployments Work

### Staging (main branch):
1. You push code to `main` branch
2. GitHub Actions builds Docker images with `:staging` tag
3. Staging Watchtower detects new `:staging` images
4. Watchtower automatically updates staging containers
5. **Result**: `airesume-staging.thetalogics.com` is updated

### Production (production branch):
1. You merge tested code to `production` branch
2. GitHub Actions builds Docker images with `:latest` tag
3. Production Watchtower detects new `:latest` images
4. Watchtower automatically updates production containers
5. **Result**: `aira.thetalogics.com` is updated

---

## 🎯 Deployment Workflow

### When developing new features:
```
1. Work on feature branch
2. Merge to main → auto-deploys to staging
3. Test on staging
4. If everything works, merge to production → auto-deploys to production
```

### When fixing bugs:
```
1. Fix bug on main branch
2. Test on staging
3. Merge to production
```

---

## 🆘 Troubleshooting

### Production containers not starting?
1. Check Portainer → Stacks → aria-production → Logs
2. Common issues:
   - Wrong environment variables
   - Port 8080 already in use
   - Database connection failed

### Can't access via domain?
1. Check DNS propagation: `ping aira.thetalogics.com`
2. Check if port 8080 is open on your VPS firewall
3. Check nginx logs in Portainer

### Database issues?
1. Production uses separate database: `aria_prod_db`
2. Run migrations: `docker exec aria-backend-prod alembic upgrade head`

### Ollama connection issues?
1. If using Ollama Cloud: Check API key is correct
2. If using local Ollama: Ensure production backend can access staging Ollama container

---

## 📞 Need Help?

If you encounter issues:
1. Check container logs in Portainer
2. Verify environment variables are set correctly
3. Ensure DNS is pointing to correct IP
4. Check VPS firewall allows ports 80, 443, and 8080

---

## 🎉 Success Checklist

- [ ] Code pushed to `production` branch on GitHub
- [ ] Production stack created in Portainer
- [ ] All production containers running (green status)
- [ ] DNS record created for `aira.thetalogics.com`
- [ ] SSL certificate installed (or using external proxy)
- [ ] Can access production via `http://YOUR_VPS_IP:8080`
- [ ] Can access production via `https://aira.thetalogics.com`
- [ ] Database migrations run on production
- [ ] Test user can login and use the app

**Congratulations! You now have a production-ready deployment! 🚀**
