# Staging Split Deploy Guide (Simple Steps)

Use this guide to run ARIA staging on **two servers**:

| Server | Name | IP address | What runs here |
|--------|------|------------|----------------|
| Main | AI Software Factory | **66.70.191.79** | Website, database, resume analysis |
| Voice | Theta Insight - Staging | **158.69.223.111** | Phone calls, LiveKit, speech AI |

**Time needed:** about 45–60 minutes  
**Downtime:** a few minutes when updating the main server stack

---

## Before you start

You need:

1. Login access to **Portainer** on both servers (or ask whoever manages the servers)
2. Login access to **Twilio** (for phone/SIP settings)
3. The **environment variable** text blocks (provided by your tech lead — do not share publicly)
4. This guide open on a second screen

**Important rule:** When Portainer asks to delete volumes, always choose **NO**. That keeps your database safe.

---

## Part A — Wait for new software images (automatic)

After code is pushed to GitHub, wait **10–20 minutes** for the automatic build to finish.

Ask your developer to confirm these images were rebuilt:

- `revanth2245/resume-speech-service:staging`
- `revanth2245/resume-voice-agent:staging`

You can continue with Part B while waiting.

---

## Part B — Deploy the VOICE server first (`158.69.223.111`)

Do this **before** changing the main server. The main app keeps working during this step.

### Step B1 — Open Portainer on the voice server

1. Open Portainer in your browser for **Theta Insight - Staging**
2. Click **Stacks** in the left menu
3. Click **Add stack**

### Step B2 — Create the voice stack

1. **Name:** `aria-staging-voice`
2. **Build method:** Web editor
3. Open the file `docker-compose.voice.staging.yml` from the project (GitHub or copy from developer)
4. Paste the **entire file** into the editor box

### Step B3 — Add environment variables

1. Scroll to **Environment variables**
2. Click **Advanced mode** (if available) and paste the **VOICE server env block** your developer gave you
3. Double-check:
   - `STAGING_LIVEKIT_NODE_IP=158.69.223.111`
   - `ARIA_BACKEND_URL=https://airesume-staging.thetalogics.com`

### Step B4 — Deploy

1. Click **Deploy the stack**
2. Wait until all containers show **running** (green)
3. If something is red, click the container name → **Logs** and send logs to your developer

### Step B5 — Quick check (voice server)

Open this link in your browser:

`http://158.69.223.111:8002/health`

You should see text mentioning `"status"` and `"max_concurrent_calls": 1`.  
If the page does not load, ask your developer to check the firewall on the voice server.

---

## Part C — Update Twilio (phone routing)

Phone calls must go to the **voice** server, not the main server.

1. Log in to **Twilio Console**
2. Go to **Elastic SIP Trunking** → your ARIA staging trunk
3. Find **Termination** or **SIP URI / IP** settings
4. Change the IP from `66.70.191.79` to **`158.69.223.111`**
5. Port should stay **5060** (TCP)
6. Save

If you are unsure which screen to use, send a screenshot to your developer.

---

## Part D — Update the MAIN server (`66.70.191.79`)

This step updates the existing staging app. **Do not delete volumes.**

### Step D1 — Backup the database (5 minutes, strongly recommended)

Ask someone with SSH access to run:

```bash
docker exec staging-postgres pg_dump -U aria_staging -d aria_staging_db -Fc > aria_backup_before_split.dump
```

Skip only if no one has SSH access — but backup is strongly recommended.

### Step D2 — Open the existing staging stack

1. Open Portainer on **AI Software Factory** (`66.70.191.79`)
2. Click **Stacks**
3. Click your existing stack (usually named **`aria-staging`**)
4. Click **Editor** (not Delete)

### Step D3 — Replace the compose file

1. **Select all** text in the editor and delete it
2. Paste the full contents of **`docker-compose.main.staging.yml`**
3. Do **not** change the stack name unless your developer asks you to

### Step D4 — Update environment variables

1. Go to **Environment variables** for this stack
2. Replace with the **MAIN server env block** from your developer
3. Confirm these two lines exist:
   - `VOICE_AGENT_URL=http://158.69.223.111:8002`
   - `INTERNAL_SERVICE_SECRET=` (same value as on the voice server)

### Step D5 — Deploy the update

1. Click **Update the stack**
2. Portainer may ask about removing old containers — that is OK
3. If asked **“Remove volumes?”** → click **NO** / leave unchecked
4. Wait until containers are running

Old voice containers (`livekit`, `speech-service`, etc.) on this server will stop — that is expected. Voice now runs on the other server.

---

## Part E — Verify everything works

### Check 1 — Website still loads

Open: https://airesume-staging.thetalogics.com  

Log in and confirm your **users, jobs, and candidates** are still there.

### Check 2 — Voice agent responds

Open: http://158.69.223.111:8002/health  

Should show healthy status.

### Check 3 — One test phone call

1. In the staging app, start **one** voice screening call
2. Only **one call at a time** on the voice server (by design)
3. Confirm you hear the AI greeting and the call completes

If the call fails, note the time and ask your developer to check logs on the voice server.

---

## Part F — Firewall checklist (ask server admin)

**Voice server (`158.69.223.111`) — allow inbound:**

| Type | Ports |
|------|-------|
| TCP | 8002, 7890, 7891, 5060 |
| UDP | 7892, 5060, 10000–10100, 50000–50200 |

**Main server (`66.70.191.79`) — keep as today:**

| Type | Ports |
|------|-------|
| TCP | 80, 443 |

---

## Troubleshooting (simple)

| Problem | What to try |
|---------|-------------|
| Website down after update | In Portainer on main server, check `staging-backend` and `staging-nginx` logs |
| Database looks empty | Volumes were deleted by mistake — restore from backup (`aria_backup_before_split.dump`) |
| Phone calls don't connect | Twilio IP must be `158.69.223.111`; check voice stack logs for `staging-livekit-sip` |
| “Voice capacity reached” | Wait for the current call to finish (only 1 call allowed on voice server) |
| Health page on 8002 won't load | Firewall on voice server blocking port 8002 |

---

## Rollback (if something goes wrong)

1. On **main server**, edit stack back to old `docker-compose.staging.yml` (developer has copy)
2. Restore old environment variables
3. Update stack — **do not remove volumes**
4. Point Twilio back to `66.70.191.79` temporarily
5. Stop the `aria-staging-voice` stack on the voice server if needed

Your database volume `staging_postgres_data` is safe as long as you never checked “Remove volumes.”

---

## Summary checklist

- [ ] Voice stack deployed on `158.69.223.111`
- [ ] `http://158.69.223.111:8002/health` works
- [ ] Twilio SIP points to `158.69.223.111`
- [ ] Main stack updated on `66.70.191.79` (volumes **not** deleted)
- [ ] Website loads and data is present
- [ ] One test phone call succeeded

Done.
