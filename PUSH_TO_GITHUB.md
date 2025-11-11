# Push to GitHub - Step by Step

## Prerequisites

Make sure you have a GitHub account. If not, create one at https://github.com/signup

## Step 1: Create Public GitHub Repository

1. Go to: **https://github.com/new**

2. Fill in:
   - **Repository name:** `ADK` (or any name you prefer)
   - **Description:** Multi-agent Instagram carousel generator with Web UI
   - **Visibility:** ✓ **Public** (IMPORTANT - so you can clone without login on RunPod)
   - **Initialize repository:** Leave ALL checkboxes UNCHECKED
     - ✗ Do NOT add README
     - ✗ Do NOT add .gitignore  
     - ✗ Do NOT add license

3. Click **"Create repository"**

4. GitHub will show you a URL like:
   ```
   https://github.com/YOUR_USERNAME/ADK.git
   ```
   
   **Copy this URL!** You'll need it in Step 2.

## Step 2: Run These Commands

Open terminal and run:

```bash
# Navigate to project
cd /Users/most/Documents/Projects/Moonly/ADK

# Initialize git (if not already)
git init

# Add all files (gitignore will exclude sensitive data)
git add .

# Create initial commit
git commit -m "Initial commit: Multi-agent content generator

- Multi-agent Instagram carousel generator
- Random post selection from Google Sheets
- 10-image carousel with 3D plasticine style
- Flask Web UI for SMM team testing
- RunPod deployment ready
- Cost-safe: manual trigger only"

# Add your GitHub repository as remote
# REPLACE with your actual GitHub URL from Step 1!
git remote add origin https://github.com/YOUR_USERNAME/ADK.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 3: Verify on GitHub

1. Go to your repository: `https://github.com/YOUR_USERNAME/ADK`
2. You should see all files EXCEPT:
   - `.env` files (credentials - excluded)
   - `credentials.json` files (excluded)
   - `output/` folder (generated content - excluded)
   - `.venv/` (virtual environment - excluded)
   - `logs/` (log files - excluded)

## Step 4: Clone on RunPod

Since your repo is PUBLIC, you can clone it without authentication:

```bash
# On RunPod or any server
git clone https://github.com/YOUR_USERNAME/ADK.git
cd ADK

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r web_ui/requirements.txt

# Add your credentials
# Upload your service-account.json to the server
# Create content_generator/.env with your settings

# Run
export STYLE="pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine"
python -m flask --app web_ui.app run --host=0.0.0.0 --port=5000
```

## Important Notes

### What's Excluded from Git (in .gitignore):

✅ **Excluded (safe):**
- All `.env` files (your credentials)
- `credentials.json` files
- Generated content (`output/`)
- Logs (`logs/`)
- Virtual environment (`.venv/`)
- Runtime state (`web_ui/jobs.json`)

✅ **Included (safe to share):**
- All code files
- Web UI files
- Dockerfile
- Documentation
- `.env.example` (template without real values)

### Security Checklist

Before pushing, verify no credentials are committed:

```bash
# Check what will be committed
git status

# Review specific file if unsure
git diff --cached

# Search for potential secrets
grep -r "GOOGLE_CLOUD_PROJECT" . --exclude-dir=.git --exclude-dir=.venv
```

If you see actual project IDs or credentials, they should be in `.gitignore`.

## Troubleshooting

### "Remote already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/ADK.git
```

### "Permission denied (publickey)"
Use HTTPS URL (not SSH):
```
https://github.com/YOUR_USERNAME/ADK.git  ✓ Correct
git@github.com:YOUR_USERNAME/ADK.git      ✗ Wrong (needs SSH key)
```

### "Nothing to commit"
```bash
git add .
git status  # Should show files to commit
```

### Need to Update Later
```bash
git add .
git commit -m "Update: description of changes"
git push
```

## Done! 🎉

Your code is now on GitHub as a public repository!

RunPod can clone it with:
```bash
git clone https://github.com/YOUR_USERNAME/ADK.git
```

No authentication needed!
