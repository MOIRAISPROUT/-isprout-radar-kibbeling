# scraper.py — scant ALLE accountancykantoren uit de NBA-export (kantoren.json)
import feedparser, json, time, datetime

RAW = json.load(open("kantoren.json", encoding="utf-8"))

# 1. Unieke kantoren uit vestigingsdata (dedupe op naam, coördinaat = HQ-pin)
kantoren = {}
for r in RAW:
    naam = (r.get("Name") or "").strip()
    if not naam or len(naam) < 3:
        continue
    key = naam.lower()
    if key not in kantoren:
        kantoren[key] = {
            "name": naam,
            "city": (r.get("City") or "").title(),
            "lat": r.get("Latitude"),
            "lng": r.get("Longitude"),
        }
print(f"{len(RAW)} vestigingen ingelezen → {len(kantoren)} unieke kantoren")

# 2. Signaalwoorden (A = outsourcing, B = plaatsing NL)
WOORDEN_A = {"outsourc":5,"uitbested":5,"backoffice":4,"werkvoorraad":4,"werkdruk":3,
             "capaciteit":4,"capacity":4,"remote":3,"op afstand":3}
WOORDEN_B = {"vacature":2,"werving":3,"relocatie":4,"expat":4,"instroom":2,"rekruteert":3}
WOORDEN_G = {"overname":3,"fusie":3,"groei":2,"groeit":2,"expandert":2}

def gewicht(t, wb):
    t = t.lower()
    return sum(w for kw, w in wb.items() if kw in t)

# 3. Scan (één Google News-query per kantoor — bevat ook AV-artikelen)
leads = []
for i, k in enumerate(kantoren.values()):
    q = f'"{k["name"]}" (overname OR groei OR vacature OR outsourcing OR uitbesteden OR werving)'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    sigs = []
    try:
        for e in feedparser.parse(url).entries[:10]:
            gA, gB, gG = (gewicht(e.title, wb) for wb in (WOORDEN_A, WOORDEN_B, WOORDEN_G))
            if gA + gB + gG > 0:
                sigs.append({"titel": e.title, "link": e.link, "datum": e.published,
                             "bron": "Google News", "a": gA, "b": gB, "groei": gG})
    except Exception as ex:
        print(f"fout bij {k['name']}: {ex}")
    sA = min(100, 30 + sum(s["a"] for s in sigs) * 8 + sum(s["groei"] for s in sigs) * 4)
    sB = min(100, 30 + sum(s["b"] for s in sigs) * 8)
    leads.append({**k, "score_out": sA, "score_nl": sB, "signalen": sigs})
    if i % 100 == 0:
        print(f"...{i}/{len(kantoren)} gescand")

json.dump({"gegenereerd": str(datetime.datetime.now()), "bron": "NBA kantorenzoeker + Google News",
           "let_op": "Keyword-scores, geen AI.", "leads": leads},
          open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Klaar.")
