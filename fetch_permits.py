"""
JN Service Construction Leads — Weekly Permit Fetcher
Runs every Monday via GitHub Actions.
Fetches new construction permits from Boston, Cambridge, Somerville.
Adds new permits to history without deleting old ones.
Marks new permits with a timestamp so dashboard can highlight them.
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2

# ── CONFIG ────────────────────────────────────────────────────────────────────
BRAINTREE_LAT = 42.2084
BRAINTREE_LON = -70.9978
MAX_MILES = 35
DATA_FILE = "data/permits.json"

# New construction terms per source
NEW_CONST_BOSTON = ["Erect", "New construction", "Addition", "Garage"]
NEW_CONST_SOMERVILLE_SUBTYPES = [
    "Residential New Construction", "Commercial New Construction",
    "Residential - New", "Commercial - New", "New"
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def haversine_miles(lat, lon):
    R = 3958.8
    lat1, lon1 = map(radians, [BRAINTREE_LAT, BRAINTREE_LON])
    lat2, lon2 = map(radians, [float(lat), float(lon)])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1-a)), 2)

def safe(val, default=""):
    if val is None or str(val).strip() in ("", "nan", "None", "N/A"):
        return default
    return str(val).strip()

def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def fmt_val(n):
    try:
        n = float(n)
        if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
        if n >= 1_000: return f"${n/1_000:.0f}k"
        return f"${n:,.0f}"
    except:
        return "N/A"

SERVICE_MAP = {
    "Erect":                         ["Carpentry","Electrical","Roofing","Masonry & Brickwork","Painting","Flooring","Drainage"],
    "New construction":              ["Carpentry","Electrical","Roofing","Masonry & Brickwork","Painting","Flooring","Drainage"],
    "New Construction":              ["Carpentry","Electrical","Roofing","Masonry & Brickwork","Painting","Flooring","Drainage"],
    "Addition":                      ["Carpentry","Roofing","Electrical","Painting","Flooring"],
    "Garage":                        ["Carpentry","Roofing","Masonry & Brickwork","Electrical"],
    "Residential New Construction":  ["Carpentry","Electrical","Roofing","Painting","Flooring","Drainage"],
    "Commercial New Construction":   ["Carpentry","Electrical","Roofing","Masonry & Brickwork","Painting","Flooring","Drainage"],
    "Residential - New":             ["Carpentry","Electrical","Roofing","Painting","Flooring"],
    "Commercial - New":              ["Carpentry","Electrical","Roofing","Masonry & Brickwork","Painting","Flooring","Drainage"],
    "New":                           ["Carpentry","Electrical","Roofing","Painting","Flooring"],
}

def enrich(p):
    svcs = SERVICE_MAP.get(p.get("description",""), ["Carpentry","Electrical","Roofing","Painting","Flooring"])
    p["services_needed"] = ", ".join(svcs)
    reasons = ["New construction — full scope of finishing trades needed"]
    v = float(p.get("valuation_num", 0) or 0)
    if v > 1_000_000: reasons.append(f"Major project — {fmt_val(v)}")
    elif v > 200_000: reasons.append(f"Solid value — {fmt_val(v)}")
    d = float(p.get("dist", 99))
    if d < 8: reasons.append(f"Very close — {d}mi from Braintree")
    if p.get("company_name"): reasons.append(f"Contractor: {p['company_name']}")
    p["why_visit"] = " | ".join(reasons)
    return p

# ── FETCHERS ──────────────────────────────────────────────────────────────────

def fetch_boston(since_date):
    """Fetch Boston new construction permits via Socrata API."""
    print(f"  Fetching Boston since {since_date}...")
    results = []
    descriptions = ["Erect", "New construction", "Addition", "Garage"]
    for desc in descriptions:
        where = f"description='{desc}' AND issued_date >= '{since_date}T00:00:00'"
        params = urllib.parse.urlencode({
            "$where": where,
            "$limit": 5000,
            "$order": "issued_date DESC"
        })
        url = f"https://data.boston.gov/api/3/action/datastore_search_sql?sql=SELECT%20*%20FROM%20%226ddcd912-32a0-43df-9908-63574f8c7e77%22%20WHERE%20description%20%3D%20%27{urllib.parse.quote(desc)}%27%20AND%20issued_date%20%3E%3D%20%27{since_date}%27%20LIMIT%205000"
        # Use simple datastore_search instead
        url = f"https://data.boston.gov/api/3/action/datastore_search?resource_id=6ddcd912-32a0-43df-9908-63574f8c7e77&filters={{\"description\":\"{desc}\"}}&limit=5000"
        try:
            data = fetch_json(url)
            records = data.get("result", {}).get("records", [])
            for r in records:
                issued = safe(r.get("issued_date", ""))[:10]
                if issued < since_date:
                    continue
                try:
                    lat = float(r.get("y_latitude", 0) or 0)
                    lon = float(r.get("x_longitude", 0) or 0)
                    if not lat or not lon: continue
                    d = haversine_miles(lat, lon)
                    if d > MAX_MILES: continue
                except:
                    continue
                val = 0
                try: val = float(str(r.get("declared_valuation","0")).replace("$","").replace(",",""))
                except: pass
                results.append(enrich({
                    "id": f"BOS-{safe(r.get('permitnumber',''))}",
                    "source": "Boston",
                    "permit_num": safe(r.get("permitnumber","")),
                    "description": desc,
                    "address": f"{safe(r.get('address',''))}, {safe(r.get('city',''))}",
                    "city": safe(r.get("city","")),
                    "lat": lat, "lon": lon,
                    "issued_date": issued,
                    "valuation_num": val,
                    "applicant_name": safe(r.get("applicant","")),
                    "company_name": "",
                    "comments": safe(r.get("comments",""))[:300],
                    "occ": safe(r.get("occupancytype","")),
                    "dist": d,
                    "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }))
        except Exception as e:
            print(f"    Boston '{desc}' error: {e}")
    print(f"  Boston: {len(results)} new permits")
    return results


def fetch_cambridge(since_date):
    """Fetch Cambridge new construction permits via Socrata API."""
    print(f"  Fetching Cambridge since {since_date}...")
    results = []
    try:
        where = f"Issue Date >= '{since_date}'"
        url = "https://data.cambridgema.gov/resource/9qm7-wbdc.json?$limit=5000&$where=Issue_Date+%3E%3D+%27" + since_date + "%27"
        records = fetch_json(url)
        for r in records:
            try:
                lat = float(r.get("Latitude", 0) or 0)
                lon = float(r.get("Longitude", 0) or 0)
                if not lat or not lon: continue
                d = haversine_miles(lat, lon)
                if d > MAX_MILES: continue
            except:
                continue
            issued = safe(r.get("Issue Date",""))[:10]
            if issued < since_date: continue
            val = 0
            for col in ["Total Cost Of Construction","Building Cost","Final Cost"]:
                try:
                    val = float(str(r.get(col,"0")).replace("$","").replace(",",""))
                    break
                except: pass
            results.append(enrich({
                "id": f"CAM-{safe(r.get('ID',''))}",
                "source": "Cambridge",
                "permit_num": safe(r.get("ID","")),
                "description": "New Construction",
                "address": safe(r.get("Address","")),
                "city": "Cambridge",
                "lat": lat, "lon": lon,
                "issued_date": issued,
                "valuation_num": val,
                "applicant_name": safe(r.get("Licensed Construction Supervisor","")),
                "company_name": safe(r.get("Architect: Firm","")),
                "comments": safe(r.get("Description Of Work",""))[:300],
                "occ": safe(r.get("Proposed Building Use","")),
                "dist": d,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }))
    except Exception as e:
        print(f"    Cambridge error: {e}")
    print(f"  Cambridge: {len(results)} new permits")
    return results




def fetch_somerville(since_date):
    """Fetch Somerville new construction permits via Socrata API."""
    print(f"  Fetching Somerville since {since_date}...")
    results = []
    try:
        subtypes = "','".join(NEW_CONST_SOMERVILLE_SUBTYPES)
        url = "https://data.somervillema.gov/resource/nneb-s3f7.json?$limit=5000&$where=Issue_Date+%3E%3D+%27" + since_date + "%27+AND+Application_Type+%3D+%27Building+Permit%27"
        records = fetch_json(url)
        for r in records:
            subtype = safe(r.get("Application Subtype",""))
            if subtype not in NEW_CONST_SOMERVILLE_SUBTYPES: continue
            try:
                lat = float(r.get("Application Latitude", 0) or 0)
                lon = float(r.get("Application Longitude", 0) or 0)
                if not lat or not lon: continue
                d = haversine_miles(lat, lon)
                if d > MAX_MILES: continue
            except:
                continue
            issued = safe(r.get("Issue Date",""))[:10]
            if issued < since_date: continue
            val = 0
            try: val = float(str(r.get("Estimated Construction Cost","0")).replace("$","").replace(",",""))
            except: pass
            company = safe(r.get("Contractor Company Name","")) or safe(r.get("Applicant Company Name",""))
            results.append(enrich({
                "id": f"SOM-{safe(r.get('Application Number',''))}",
                "source": "Somerville",
                "permit_num": safe(r.get("Application Number","")),
                "description": subtype,
                "address": safe(r.get("Application Address","")),
                "city": "Somerville",
                "lat": lat, "lon": lon,
                "issued_date": issued,
                "valuation_num": val,
                "applicant_name": safe(r.get("Contractor Name","")),
                "company_name": company,
                "comments": safe(r.get("Project Description or Business Name",""))[:300],
                "occ": subtype,
                "dist": d,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }))
    except Exception as e:
        print(f"    Somerville error: {e}")
    print(f"  Somerville: {len(results)} new permits")
    return results




# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Load existing data
    existing = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            saved = json.load(f)
            for p in saved.get("permits", []):
                existing[p["id"]] = p
        print(f"Loaded {len(existing)} existing permits")
    else:
        print("No existing data — first run")

    # Determine fetch window
    # First run: fetch from May 1 2026
    # Subsequent runs: fetch from 8 days ago to catch any late-issued permits
    if not existing:
        since_date = "2026-05-01"  # First run: fetch from May 2026
        print(f"First run — fetching from {since_date}")
    else:
        since_date = (now - timedelta(days=8)).strftime("%Y-%m-%d")
        print(f"Weekly update — fetching from {since_date}")

    # Fetch from all sources
    print("\nFetching permits...")
    new_permits = []
    new_permits += fetch_boston(since_date)
    new_permits += fetch_cambridge(since_date)
    new_permits += fetch_somerville(since_date)

    # Merge: add new, keep old
    added_count = 0
    for p in new_permits:
        if p["id"] not in existing:
            p["is_new"] = True  # flag for dashboard highlight
            p["added_week"] = today
            existing[p["id"]] = p
            added_count += 1
        else:
            # Keep existing, just update fetched_at
            existing[p["id"]]["fetched_at"] = today

    # Clear is_new flag for permits older than 7 days
    for pid, p in existing.items():
        added = p.get("added_week", "")
        if added and added < (now - timedelta(days=7)).strftime("%Y-%m-%d"):
            p["is_new"] = False

    all_permits = sorted(existing.values(), key=lambda p: (p.get("issued_date",""), p.get("dist",99)), reverse=True)

    # Stats
    stats = {
        "total": len(all_permits),
        "new_this_week": added_count,
        "boston": sum(1 for p in all_permits if p["source"]=="Boston"),
        "cambridge": sum(1 for p in all_permits if p["source"]=="Cambridge"),
        "somerville": sum(1 for p in all_permits if p["source"]=="Somerville"),
        "last_updated": today,
        "fetch_window_start": since_date,
    }

    # Save data
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump({"stats": stats, "permits": all_permits}, f, indent=2)

    print(f"\n✅ Done!")
    print(f"   Total permits: {stats['total']}")
    print(f"   New this week: {added_count}")
    print(f"   Boston: {stats['boston']} | Cambridge: {stats['cambridge']} | Somerville: {stats['somerville']}")


if __name__ == "__main__":
    main()
