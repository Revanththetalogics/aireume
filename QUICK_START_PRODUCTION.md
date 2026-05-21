# 🎯 QUICK START - Production Deployment

## What I've Created For You:

### ✅ Files Created:
1. **`docker-compose.production.yml`** - Production stack configuration for Portainer
2. **`nginx/nginx.production.conf`** - Production nginx config for `aira.thetalogics.com`
3. **`.env.production.template`** - Environment variables template for production
4. **`PRODUCTION_DEPLOYMENT_GUIDE.md`** - Complete step-by-step deployment guide

### ✅ Files Modified:
1. **`docker-compose.prod.yml`** - Updated to use `:staging` tags
2. **`.github/workflows/cd.yml`** - Updated CI/CD for branch-based deployments
3. **`nginx/Dockerfile`** - Updated to support dynamic nginx config selection
4. **Renamed**: `nginx.prod.conf` → `nginx.staging.conf`

### ✅ Git Branch:
- Created **`production`** branch from `main`

---

## 🚀 What You Need To Do (Simple Steps):

### Step 1: Push Code to GitHub

Open PowerShell and run:

```powershell
cd "C:\Users\DELL\Projects\Resume AI by ThetaLogics"
git add .
git commit -m "feat: add production environment setup"
git push -u origin production
```

### Step 2: Setup Production Stack in Portainer

1. Login to Portainer
2. Go to **Stacks** → **Add stack**
3. Name it: `aria-production`
4. Use **Web editor** and paste content from `docker-compose.production.yml`
5. Click **Deploy the stack**

### Step 3: Setup DNS for aira.thetalogics.com

Login to your domain provider and add:

```
Type: A
Name: aira
Value: YOUR_VPS_IP_ADDRESS (same as staging)
TTL: 3600
```

### Step 4: Test

After DNS propagates (5 mins - 48 hours):

- **Staging**: `https://airesume-staging.thetalogics.com` (port 80)
- **Production**: `https://aira.thetalogics.com` (port 8080 internally)

---

## 📊 How It Works:

### Staging (main branch):
```
Push to main → Build :staging images → Watchtower updates staging → Test here first
```

### Production (production branch):
```
Merge to production → Build :latest images → Watchtower updates production → Live for users
```

---

## 🔑 Key Differences:

| Feature | Staging | Production |
|---------|---------|------------|
| **Branch** | `main` | `production` |
| **Domain** | `airesume-staging.thetalogics.com` | `aira.thetalogics.com` |
| **Port** | 80 | 8080 |
| **Database** | `aria_db` | `aria_prod_db` |
| **Docker Images** | `:staging` tag | `:latest` tag |
| **Containers** | `resume-screener-*` | `aria-*-prod` |
| **Purpose** | Testing & development | Live users |

---

## ⚠️ Important Notes:

1. **Ollama is SHARED** between staging and production (saves 8GB RAM)
2. **Databases are SEPARATE** (staging data won't mix with production)
3. **Same VPS** - both stacks run on your existing server
4. **Automatic deployments** - Watchtower updates containers within 60 seconds of new images

---

## 🆘 If Something Goes Wrong:

1. **Check Portainer** → Stacks → aria-production → Logs
2. **Verify DNS** → `ping aira.thetalogics.com` should show your VPS IP
3. **Test port 8080** → `http://YOUR_VPS_IP:8080/health` should return `{"status": "ok"}`
4. **Check firewall** → Ensure port 8080 is open on your VPS

---

## 📖 Full Documentation:

See `PRODUCTION_DEPLOYMENT_GUIDE.md` for detailed step-by-step instructions with screenshots and troubleshooting.

---

## 🎯 Next Steps After Deployment:

1. ✅ Test production with a few users
2. ✅ Setup SSL certificate for `aira.thetalogics.com`
3. ✅ Monitor both stacks in Portainer
4. ✅ Start using the staging → production workflow for new features

**That's it! You're ready to go live! 🚀**
