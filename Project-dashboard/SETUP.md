# District Census Handbook (DCHB) Archive Dashboard

Live tracking dashboard for digitised District Census Handbooks from the 1971 and 1981 Census of India.

**Live at:** `https://MohdSadiq8447.github.io/Archival-Digitisation-Project`

## Setup Instructions

### 1. Enable GitHub Pages
- Go to **Settings → Pages**
- Under "Build and deployment", select **Source: GitHub Actions**

### 2. Add Dropbox Secrets
- Go to **Settings → Secrets and variables → Actions → New repository secret**
- Add:
  - `DROPBOX_CENSUS_1971_URL` = `https://www.dropbox.com/scl/fi/ouep88b5q9ln5xstly03w/Census_1971.xlsx?rlkey=fnn3qthzf23tkbfz6cvf4remz&st=q1lskr26&dl=1`
  - `DROPBOX_CENSUS_1981_URL` = `https://www.dropbox.com/scl/fi/77jgh5ahsk3c0olfhcwcm/Census_1981.xlsx?rlkey=mlgfb6uwkz1qq5twzqyv7vmey&st=mtr29ode&dl=1`

  > **Important:** Make sure the URLs end with `dl=1` (direct download), not `dl=0`.

### 3. Push to GitHub
```bash
git init
git add .
git commit -m "Initial dashboard setup"
git remote add origin https://github.com/MohdSadiq8447/Archival-Digitisation-Project.git
git push -u origin main
```

### How It Works
- GitHub Actions runs on every push (and daily at 6 AM)
- Downloads latest Excel files from Dropbox
- Processes data into JSON
- Deploys updated dashboard to GitHub Pages

### Updating the Data
- Update the Excel files in Dropbox
- Trigger a manual run via **Actions → Update Dashboard → Run workflow**
- Or wait for the daily scheduled run
