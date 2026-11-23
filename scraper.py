# scraper.py — iSprout Radar: scant ALLE kantoren uit de NBA-export
# Bronnen: Google News per kantoor (incl. Accountancy Vanmorgen-artikelen),
#          accountant.nl (globale feed), AFM (globale feed), vacature-scan per kantoor.
# Output: leads.json — leest de app automatisch in.
import feedparser, json, sys, datetime

# ---------- 1. KANTOREN INLEZEN (NBA-export) ----------
try:
    RAW = json.load(open("kantoren.json", encoding="utf-8"))
except FileNotFoundError:
    sys.exit("kantoren.json niet gevonden — upload eerst de NBA-export naar de repo.")

kantoren = {}
for r in RAW:
    naam = (r.get("Name") or r.get("name") or "").strip()
    if not naam or len(naam) < 3:
        continue
    key = naam.lower()
    if key not in kantoren:
        kantoren[key] = {
            "name": naam,
            "city": ((r.get("City") or r.get("city") or "") or "").title(),
            "lat": r.get("Latitude") or r.get("latitude") or r.get("lat"),
            "lng": r.get("Longitude") or r.get("longitude") or r.get("lng"),
        }
print(f"{len(RAW)} vestigingen ingelezen -> {len(kantoren)} unieke kantoren")

# ---------- 2. SIGNAALWOORDEN ----------
# A = outsourcing (remote capacity vanuit Zuid-Afrika)
WOORDEN_A = {"outsourc": 5, "uitbested": 5, "backoffice": 4, "werkvoorraad": 4,
             "werkdruk": 3, "capaciteit": 4, "capacity": 4, "remote": 3, "op afstand": 3}
# B = plaatsing van ZA-professional in Nederland
WOORDEN_B = {"vacature": 2, "werving": 3, "relocatie": 4, "expat": 4,
             "instroom": 2, "rekruteert": 3, "internationaal talent": 4}
# Groeisignalen (versterken A)
WOORDEN_G = {"overname": 3, "fusie": 3, "groei": 2, "groeit": 2, "expandert": 2}

def gewicht(t, wb):
    t = t.lower()
    return sum(w for kw, w in wb.items() if kw in t)

# ---------- 3. GLOBALE FEEDS (eenmalig ophalen, dan matchen op alle namen) ----------
def laad_feed(url, bron):
    out = []
    try:
        for e in feedparser.parse(url).entries[:80]:
            out.append({"titel": e.title, "link": e.link,
                        "datum": getattr(e, "published", ""), "bron": bron})
    except Exception as ex:
        print(f"  (feed {bron} niet beschikbaar: {ex})")
    return out

GLOBAL_FEEDS = (
    laad_feed("https://www.accountant.nl/rss/nieuws/", "accountant.nl")
    + laad_feed("https://www.afm.nl/nl/nieuwsberichten/rss", "AFM")
)
print(f"Globale feeds opgehaald: {len(GLOBAL_FEEDS)} artikelen")

def match_globale_feeds(naam):
    """Matcht globale nieuws op de naam van het kantoor (eerste herkenbare token)."""
    token = naam.lower().split()[0]
    if len(token) < 5:   # te generiek ('de', 'van') -> overslaan
        return []
    hits = []
    for e in GLOBAL_FEEDS:
        if token in e["titel"].lower():
            gA = gewicht(e["titel"], WOORDEN_A)
            gB = gewicht(e["titel"], WOORDEN_B)
            gG = gewicht(e["titel"], WOORDEN_G)
            if gA + gB + gG > 0:
                hits.append({**e, "a": gA, "b": gB, "groei": gG})
    return hits

# ---------- 4. SCANS PER KANTOOR ----------
def scan_nieuws(naam):
    q = f'"{naam}" (overname OR groei OR vacature OR outsourcing OR uitbesteden OR werving)'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    sigs = []
    try:
        for e in feedparser.parse(url).entries[:10]:
            gA = gewicht(e.title, WOORDEN_A)
            gB = gewicht(e.title, WOORDEN_B)
            gG = gewicht(e.title, WOORDEN_G)
            if gA + gB + gG > 0:
                sigs.append({"titel": e.title, "link": e.link,
                             "datum": getattr(e, "published", ""),
                             "bron": "Google News", "a": gA, "b": gB, "groei": gG})
    except Exception:
        pass
    return sigs

def scan_vacatures(naam):
    q = f'"{naam}" (vacature OR "wij zoeken" OR gezocht OR aanname)'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    sigs = []
    try:
        for e in feedparser.parse(url).entries[:10]:
            t = e.title.lower()
            if "vacature" in t or "zoeken" in t or "gevraagd" in t:
                sigs.append({"titel": e.title, "link": e.link,
                             "datum": getattr(e, "published", ""),
                             "bron": "Google News (vacatures)", "a": 1, "b": 3, "groei": 0})
    except Exception:
        pass
    return sigs

# ---------- 5. HOOFDLOOP ----------
leads = []
totaal = len(kantoren)
for i, k in enumerate(kantoren.values()):
    sigs = scan_nieuws(k["name"]) + scan_vacatures(k["name"]) + match_globale_feeds(k["name"])
    n_vac = sum(1 for s in sigs if "vacature" in s["bron"].lower())
    sA = min(100, 30 + sum(s["a"] for s in sigs) * 8 + sum(s["groei"] for s in sigs) * 4 + min(15, n_vac * 5))
    sB = min(100, 30 + sum(s["b"] for s in sigs) * 8 + min(20, n_vac * 5))
    leads.append({**k, "score_out": sA, "score_nl": sB,
                  "vacatures": n_vac, "signalen": sigs})
    if i % 100 == 0:
        print(f"...{i}/{totaal} gescand", flush=True)

# ---------- 6. WEGSCHRIJVEN ----------
json.dump({
    "gegenereerd": str(datetime.datetime.now()),
    "bron": "NBA kantorenzoeker + Google News (+vacatures) + accountant.nl + AFM",
    "let_op": "Scores zijn keyword-based, geen AI. Signalen bevatten echte titels, datums en links.",
    "leads": leads,
}, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nKlaar — {len(leads)} kantoren in leads.json.")
