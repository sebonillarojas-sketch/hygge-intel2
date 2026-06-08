#!/usr/bin/env python3
"""
HYGGE INTEL — Nexo Scraper
Runs via GitHub Actions daily at 6am Lima time.
Outputs: data/projects.json + data/snapshots/YYYY-MM-DD.json
"""
import requests, re, json, time
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, date

TC = 3.78
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-PE,es;q=0.9",
}
DISTRICT_MAP = {
    "jesus maria":"Jesús María","san isidro":"San Isidro","miraflores":"Miraflores",
    "barranco":"Barranco","surco":"Surco","santiago de surco":"Surco",
    "san borja":"San Borja","la molina":"La Molina","magdalena del mar":"Magdalena",
    "lince":"Lince","pueblo libre":"Pueblo Libre","san miguel":"San Miguel",
    "los olivos":"Los Olivos","ate":"Ate","san juan de lurigancho":"SJL",
    "callao":"Callao","villa el salvador":"VES","chorrillos":"Chorrillos",
    "cercado de lima":"Cercado","rimac":"Rímac","breña":"Breña",
    "la victoria":"La Victoria","surquillo":"Surquillo",
}
ZONE_MAP = {
    "San Isidro":"Lima Moderna","Miraflores":"Lima Moderna","Barranco":"Lima Moderna",
    "Surco":"Lima Moderna","San Borja":"Lima Moderna","La Molina":"Lima Moderna",
    "Jesús María":"Lima Moderna","Magdalena":"Lima Moderna","Lince":"Lima Moderna",
    "Pueblo Libre":"Lima Moderna","San Miguel":"Lima Moderna","Surquillo":"Lima Moderna",
    "Los Olivos":"Lima Norte","Ate":"Lima Este","SJL":"Lima Este",
    "Callao":"Callao","VES":"Lima Sur","Chorrillos":"Lima Sur",
    "Cercado":"Lima Centro","Rímac":"Lima Centro","Breña":"Lima Centro","La Victoria":"Lima Centro",
}

def parse_area(text):
    nums = [float(n) for n in re.findall(r'[\d]+\.?[\d]*', text.replace(",",".")) if float(n) > 5]
    return (min(nums), max(nums)) if len(nums) >= 2 else (nums[0], nums[0]) if nums else (None, None)

def parse_price_cell(text):
    curr = "USD" if ("$" in text and "S/" not in text and "S/." not in text) else "PEN"
    nums = re.findall(r'\d+', text.replace(",","").replace(".",""))
    if nums:
        v = int(nums[0])
        if 10000 < v < 100000000:
            return v, curr
    return None, None

def scrape_project(pid):
    url = f"https://nexoinmobiliario.pe/proyecto/venta-de-departamento-{pid}-x"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        jld = soup.find("script", type="application/ld+json")
        name, dev, price_jld, dist_raw = None, "?", None, ""
        if jld:
            try:
                d = json.loads(jld.string)
                if d.get("@type") == "Organization":
                    return None
                name = d.get("name", "").split(" - ")[0].strip()
                dev = d.get("brand", {}).get("name", "")
                dist_raw = d.get("areaServed", {}).get("name", "").lower().split(",")[0].strip()
                lp = d.get("offers", {}).get("lowPrice")
                if lp:
                    price_jld = int(float(lp))
            except:
                return None
        if not name:
            return None

        district = next((v for k, v in DISTRICT_MAP.items() if k in dist_raw), dist_raw.title() or "?")
        zone = ZONE_MAP.get(district, "Otro")

        tables = soup.find_all("table")
        stage = delivery = min_area = max_area = None
        dorms_min = dorms_max = None
        banks = []
        price_history = []
        cur_price, cur_curr = price_jld, "PEN"

        for t in tables:
            for row in t.find_all("tr"):
                cells = [c.text.strip() for c in row.find_all(["td", "th"])]
                if len(cells) >= 2:
                    k, v = cells[0].lower(), cells[1]
                    if "etapa" in k: stage = v
                    if "fecha de entrega" in k: delivery = v
                    if "área total" in k:
                        mn, mx = parse_area(v)
                        if mn: min_area, max_area = mn, mx
                    if "dorm" in k:
                        nums = re.findall(r'\d+', v)
                        if nums: dorms_min = int(nums[0]); dorms_max = int(nums[-1])
                    if "financiamiento" in k and len(v) > 2:
                        banks.append(v)
                if len(cells) >= 3 and re.search(r'\d{2}/\d{2}/\d{4}', cells[1]):
                    p, curr = parse_price_cell(cells[2])
                    if p:
                        price_history.append({
                            "estado": cells[0], "fecha": cells[1], "precio": p,
                            "currency": curr,
                            "precio_usd": p if curr == "USD" else round(p / TC),
                        })
                        if not cur_price: cur_price, cur_curr = p, curr

        if not cur_price: return None
        pusd = cur_price if cur_curr == "USD" else round(cur_price / TC)
        pm2 = round(pusd / min_area) if (min_area and min_area > 15) else None
        seg = "A" if (pm2 or 0) > 2500 else "B" if (pm2 or 0) > 1400 else "C"
        sl = (stage or "").lower()
        disc = 0.07 if "plano" in sl else 0.05 if "construcci" in sl else 0.03 if "entrega" in sl else 0.06
        if seg == "A": disc = max(0.03, disc - 0.01)
        if seg == "C": disc = min(0.13, disc + 0.02)
        # Refine close estimate from price history trend
        if len(price_history) >= 2:
            h_usd = [h["precio_usd"] for h in price_history if h.get("precio_usd")]
            if len(h_usd) >= 2:
                delta = (h_usd[0] - h_usd[-1]) / h_usd[-1]
                if delta > 0.05: disc = max(0.03, disc - 0.015)
                elif delta < -0.02: disc = min(0.13, disc + 0.02)
        cm2 = round(pm2 * (1 - disc)) if pm2 else None

        return {
            "id": f"nexo_{pid}", "nexo_id": int(pid), "source": "nexo", "url": r.url,
            "name": name, "developer": dev, "district": district, "zone": zone, "segment": seg,
            "stage": stage, "delivery": delivery,
            "min_area_m2": min_area, "max_area_m2": max_area,
            "dorms_min": dorms_min, "dorms_max": dorms_max, "banks": banks,
            "list_price_pen": cur_price if cur_curr == "PEN" else None,
            "list_price_usd": pusd, "list_price_m2_usd": pm2,
            "close_price_m2_usd": cm2, "discount_pct": round(disc * 100),
            "list_ticket_usd": pusd,
            "close_ticket_usd": round(cm2 * min_area) if (cm2 and min_area) else None,
            "price_history": price_history,
            "scraped_at": datetime.now().isoformat(),
            "scraped_date": str(date.today()),
        }
    except:
        return None


def get_all_ids():
    r = requests.get("https://nexoinmobiliario.pe/sitemap-proyectos.xml", headers=HEADERS, timeout=15)
    ids = []
    for su in re.findall(r'<loc>([^<]+)</loc>', r.text):
        if "/departamentos/" not in su: continue
        m = re.search(r'-(\d+)$', su.split("/")[-1])
        if m: ids.append(m.group(1))
    return ids


def main():
    root = Path(__file__).parent.parent
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    snap_dir = data_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)

    print(f"[{datetime.now():%H:%M:%S}] HYGGE INTEL Scraper START")
    all_ids = get_all_ids()
    print(f"[{datetime.now():%H:%M:%S}] IDs from sitemap: {len(all_ids)}")

    # Load previous for history merging
    prev_file = data_dir / "projects.json"
    prev = {}
    if prev_file.exists():
        try:
            prev = {str(p["nexo_id"]): p for p in json.loads(prev_file.read_text()).get("projects", [])}
            print(f"[{datetime.now():%H:%M:%S}] Previous: {len(prev)} projects")
        except: pass

    results = []
    errors = 0
    start = time.time()

    for i, pid in enumerate(all_ids):
        p = scrape_project(pid)
        if p and p.get("list_price_m2_usd"):
            # Merge price history with previous
            if pid in prev:
                old_h = prev[pid].get("price_history", [])
                new_h = p.get("price_history", [])
                existing = {h["fecha"] for h in new_h}
                for h in old_h:
                    if h["fecha"] not in existing: new_h.append(h)
                p["price_history"] = sorted(new_h, key=lambda h: h["fecha"], reverse=True)
            results.append(p)
            elapsed = time.time() - start
            eta = (len(all_ids) - i - 1) / ((i + 1) / elapsed)
            print(f"[{i+1:3}/{len(all_ids)}] ✓ {p['name'][:22]:22} | {p['district']:12} | "
                  f"${p['list_price_m2_usd']:,}L/${p.get('close_price_m2_usd') or 0:,}C | "
                  f"hist:{len(p['price_history'])} | ETA:{eta/60:.0f}m", flush=True)
        else:
            errors += 1
        time.sleep(0.65)

    today = str(date.today())
    out = {"scraped_at": datetime.now().isoformat(), "date": today,
           "total": len(results), "errors": errors, "projects": results}
    prev_file.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    (snap_dir / f"{today}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n[{datetime.now():%H:%M:%S}] DONE — {len(results)} projects | {errors} errors | {(time.time()-start)/60:.1f}min")


if __name__ == "__main__":
    main()
