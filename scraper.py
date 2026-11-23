# scraper.py — dagelijkse scan van echte nieuwsbronnen voor iSprout Radar
# Output: leads.json (leest de app automatisch in)
import feedparser, json, datetime

# MASTERLIJST — vul aan met namen uit het NBA-register (nba.nl → zoek een accountantskantoor)
KANTOREN = [
    "H2K Penning", "VBK Groep", "Flynth Adviseurs en Accountants",
    "Ten Holter Nolet", "Withaccountants", "Accon AVM", "JA Accountants",
    "Meijburg & Co", "BDO Nederland", "Grant Thornton", "Baker Tilly",
    "Deloitte Nederland", "Hof Hoorneman bedrijfsadviseurs",
    "Draaijer & Partners", "Krüger Accountants", "Swinkels Accountants",
    "Van Wijgerden accountants", "Furas Groep", "Moïse Partners", "Efficiensia",
]

# Signaalwoorden — Optie A (outsourcing) en Optie B (plaatsing in NL)
WOORDEN_A = {"outsourc": 5, "uitbested": 5, "backoffice": 4, "werkvoorraad": 4,
             "werkdruk": 3, "capaciteit": 4, "capacity": 4, "remote": 3, "op afstand": 3}
WOORDEN_B = {"vacature": 2, "werving": 3, "aanname": 3, "relocatie": 4,
             "internationaal talent": 4, "expat": 4, "instroom": 2, "rekruteert": 3}
WOORDEN_GROEI = {"overname": 3, "fusie": 3, "groei": 2, "groeit": 2, "expandert": 2}

def gewicht(titel, woordenboek):
    t = titel.lower()
    return sum(w for kw, w in woordenboek.items() if kw in t)

def scan(kantoor):
    """Zoekt Google News (hiar ook Accountancy Vanmorgen-artikelen binnenkomen) en accountant.nl."""
    q = f'"{kantoor}" (overname OR fusie OR groei OR vacature OR outsourcing OR uitbesteden OR werving)'
    url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=nl&gl=NL&ceid=NL:nl"
    hit = []
    for e in feedparser.parse(url).entries[:15]:
        t = e.title
        gA = gewicht(t, WOORDEN_A)
        gB = gewicht(t, WOORDEN_B)
        gG = gewicht(t, WOORDEN_GROEI)
        if gA + gB + gG == 0:
            continue
        hit.append({
            "titel": t, "link": e.link, "datum": e.published,
            "bron": "Google News", "a": gA, "b": gB, "groei": gG,
        })
    return hit

leads = []
for k in KANTOREN:
    sigs = scan(k)
    sA = min(100, 35 + sum(s["a"] for s in sigs) * 8 + sum(s["groei"] for s in sigs) * 4)
    sB = min(100, 35 + sum(s["b"] for s in sigs) * 8)
    if sigs:
        leads.append({"name": k, "score_out": sA, "score_nl": sB, "signalen": sigs})
        print(f"[✓] {k}: A={sA} B={sB} ({len(sigs)} signalen)")
    else:
        print(f"[ ] {k}: geen signalen")

json.dump({
    "gegenereerd": str(datetime.datetime.now()),
    "let_op": "Scores zijn keyword-based, geen AI. Signalen bevatten echte titels, data en links.",
    "leads": leads,
}, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\nKlaar — leads.json geschreven.")
