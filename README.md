# HYGGE INTEL

Real estate intelligence platform for Lima, Peru.
Scrapes Nexo Inmobiliario daily (689 projects) and deploys automatically.

## Stack
- **Scraper**: Python + requests + BeautifulSoup (no Playwright needed)
- **Data**: JSON files committed to repo
- **Frontend**: Vanilla HTML/JS — no build step
- **Hosting**: Netlify (free tier)
- **Automation**: GitHub Actions (daily 6am Lima)

## Setup (one-time, ~10 min)

### 1. Fork / create repo on GitHub
```bash
git init
git add .
git commit -m "initial"
gh repo create hygge-intel --private --push --source=.
```

### 2. Create Netlify site
1. Go to app.netlify.com → "Add new site" → "Import from Git"
2. Connect your GitHub repo
3. Build command: (leave empty)
4. Publish directory: `public`
5. Deploy → get your site URL

### 3. Add GitHub Secrets
Go to repo → Settings → Secrets → Actions → New secret:

| Secret | Where to get |
|--------|--------------|
| `NETLIFY_AUTH_TOKEN` | Netlify → User Settings → Personal access tokens |
| `NETLIFY_SITE_ID` | Netlify → Site → Site configuration → Site ID |

### 4. Run first scrape manually
```bash
pip install -r scraper/requirements.txt
python scraper/scrape.py
```
Takes ~8 minutes for all 689 projects.
Then commit `data/` and push.

### 5. Enable GitHub Actions
The workflow runs automatically at 6am Lima (11am UTC) every day.
Or trigger manually: Actions tab → "HYGGE INTEL Daily Scraper" → Run workflow.

## Data structure

`data/projects.json`:
```json
{
  "scraped_at": "2026-06-06T11:00:00",
  "date": "2026-06-06",
  "total": 650,
  "projects": [{
    "id": "nexo_3693",
    "name": "Eterna",
    "developer": "Zafira Inmobiliaria",
    "district": "San Isidro",
    "zone": "Lima Moderna",
    "segment": "A",
    "stage": "En construcción",
    "delivery": "Dic 2026",
    "min_area_m2": 127.8,
    "max_area_m2": 152.0,
    "list_price_m2_usd": 3326,
    "close_price_m2_usd": 3193,
    "discount_pct": 4,
    "list_ticket_usd": 425000,
    "close_ticket_usd": 408000,
    "price_history": [
      {"estado": "En construcción", "fecha": "01/06/2026", "precio": 1257000, "currency": "PEN", "precio_usd": 332500}
    ],
    "scraped_at": "2026-06-06T11:00:00",
    "scraped_date": "2026-06-06"
  }]
}
```

## How close price is estimated

No public source has real closing prices (that's SUNARP territory).
The app estimates it based on:
1. **Stage**: planos → -7%, construcción → -5%, entrega → -3%
2. **Segment**: A gets -1% discount, C gets +2%
3. **Price history trend**: if price dropped in history → more discount; if rose → less

As daily snapshots accumulate, the model self-calibrates.

## Sources roadmap

| Source | Status | Data |
|--------|--------|------|
| Nexo sitemap | ✅ Live | 689 projects, price history |
| BCRP API | ✅ Live | TC, inflation |
| SUNARP | 🔜 Phase 2 | Real closing prices |
| Urbania | 🔜 Phase 2 | Additional listings |
| SBS | 🔜 Phase 2 | Mortgage rates |

## Adding your projects

Click "★ + MI PROYECTO" in the top bar.
Your projects appear on the map in purple and get compared against market automatically.
