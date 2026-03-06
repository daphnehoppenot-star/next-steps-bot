# Deploy Next Steps Web App to Railway

## Step 1: Push to GitHub

1. Create a new **private** repo on GitHub (e.g. `next-steps-web`)
2. Push this folder to it:
   ```bash
   cd next-steps-web
   git init
   git add .
   git commit -m "Next Steps Web App"
   git remote add origin https://github.com/YOUR-ORG/next-steps-web.git
   git push -u origin main
   ```

## Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub Repo**
3. Select your `next-steps-web` repo
4. Railway auto-detects Python + the Procfile

## Step 3: Add Environment Variables

In your Railway project → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `SF_USERNAME` | Your Salesforce username |
| `SF_PASSWORD` | Your Salesforce password |
| `SF_SECURITY_TOKEN` | Your Salesforce security token |
| `SF_DOMAIN` | `login` (for production) |
| `SECRET_KEY` | Any random string (e.g. `myS3cr3tK3y2026!`) |
| `ALLOWED_EMAIL_DOMAINS` | `voyantis.ai` |

Railway sets `PORT` automatically — you don't need to add it.

## Step 4: Get Your URL

After deploy completes (~1 min), Railway gives you a URL like:
```
https://next-steps-web-production-xxxx.up.railway.app
```

Visit it — you should see the email landing page.

## Step 5: Set Up Weekly Slack Reminder

Any Slack user can do this — no admin needed:

1. In Slack, go to the sales/pipeline channel (e.g. `#sales-pipeline`)
2. Type `/remind #sales-pipeline` and set up:
   ```
   /remind #sales-pipeline "📊 Pipeline check-in time! Update your opportunity next steps — takes 30 seconds per deal: https://YOUR-RAILWAY-URL.up.railway.app" every Monday at 9am
   ```
3. That's it! Every Monday at 9am, Slack posts the reminder with the link.

### Alternative: Slack Workflow Builder (prettier message)

1. Click your workspace name → **Tools** → **Workflow Builder**
2. Click **Create Workflow** → **From a template** → **Scheduled message**
3. Set: Every Monday at 9:00 AM
4. Channel: `#sales-pipeline`
5. Message:
   ```
   📊 *Pipeline Check-In Time!*

   Click below to update your opportunity next steps.
   Takes 30 seconds per deal.

   👉 https://YOUR-RAILWAY-URL.up.railway.app
   ```
6. Publish the workflow

## Getting Your Salesforce Security Token

If you don't have your SF security token:
1. Log into Salesforce
2. Click your avatar → **Settings**
3. Search for **"Reset My Security Token"**
4. Click **Reset Security Token** — it's emailed to you
