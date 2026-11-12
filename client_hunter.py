#!/usr/bin/env python3
"""Daily public-web prospect discovery for Fahim Graphic Design."""
import csv, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

MAX_LEADS = int(os.getenv("MAX_LEADS", "8"))
OUT = Path("out"); OUT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FahimClientResearch/1.0)"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+351|00351|\+44|0044)?[\s().-]*(?:\d[\s().-]*){8,13}\d")
SKIP = {"facebook.com","linkedin.com","tripadvisor.com","yelp.com","thefork.com","ubereats.com","just-eat.co.uk","deliveroo.com","wikipedia.org","yellowpages.com","google.com","bing.com"}
SEARCHES = [
("Portugal","Porto","independent cafe restaurant official website menu Porto Portugal"),
("Portugal","Lisbon","independent cafe restaurant official website menu Lisbon Portugal"),
("Portugal","Beja / Alentejo","restaurant cafe bakery official website Alentejo Portugal"),
("Portugal","Faro / Algarve","independent restaurant cafe official website Algarve Portugal"),
("Portugal","Setúbal / Évora","restaurant cafe bakery official website Setubal Evora Portugal"),
("Portugal","Portugal","independent salon gym boutique official website Portugal"),
("UK","Sheffield","independent cafe restaurant official website menu Sheffield UK"),
("UK","London","independent cafe restaurant official website menu London UK"),
("UK","Manchester","independent cafe restaurant official website menu Manchester UK"),
("UK","UK","independent salon gym boutique official website UK"),
]
def canonical(url):
    p=urlparse(url)
    if p.scheme not in ("http","https") or not p.netloc: return ""
    return urlunparse(("https",p.netloc.lower().removeprefix("www."),p.path.rstrip("/"),"","",""))
def domain_of(url): return urlparse(url).netloc.lower().removeprefix("www.")
def fetch_page(url):
    try:
        r=requests.get(url,headers=HEADERS,timeout=12,allow_redirects=True)
        if r.status_code>=400 or "text/html" not in r.headers.get("content-type",""): return None
        soup=BeautifulSoup(r.text[:1500000],"html.parser")
        for tag in soup(["script","style","noscript","svg"]): tag.decompose()
        title=soup.title.get_text(" ",strip=True)[:180] if soup.title else ""
        meta=soup.find("meta",attrs={"name":"description"})
        desc=(meta.get("content","") if meta else "")[:400]
        text=soup.get_text(" ",strip=True)[:12000]
        emails=sorted(set(EMAIL_RE.findall(r.text)))[:3]
        phones=sorted(set(PHONE_RE.findall(text)))[:2]
        socials=[]
        for a in soup.find_all("a",href=True):
            h=a["href"].strip()
            if "instagram.com/" in h or "facebook.com/" in h: socials.append(h)
        return {"url":r.url,"title":title,"description":desc,"text":text,"emails":emails,"phones":phones,"socials":sorted(set(socials))[:3]}
    except requests.RequestException: return None
def discover():
    leads=[]; seen=set()
    for country in ("Portugal","UK"):
        if country=="UK" and len(leads)>=MAX_LEADS: break
        for c,area,phrase in SEARCHES:
            if c!=country or len(leads)>=MAX_LEADS: continue
            try: results=DDGS().text(f"{phrase} -directory -tripadvisor -booking",max_results=10)
            except Exception as e:
                print(f"Search warning ({area}): {type(e).__name__}"); continue
            for item in results or []:
                if len(leads)>=MAX_LEADS: break
                url=canonical(item.get("href",""))
                if not url: continue
                domain=domain_of(url)
                if not domain or domain in SKIP or any(domain.endswith("."+d) for d in SKIP) or domain in seen: continue
                page=fetch_page(url)
                if not page: continue
                blob=(page["title"]+" "+page["description"]+" "+page["text"][:2500]).lower()
                terms=("restaurant","cafe","café","coffee","bakery","salon","gym","fitness","boutique","bistro","menu","hair","beauty")
                if not any(t in blob for t in terms): continue
                seen.add(domain)
                name=(page["title"] or item.get("title","")).split("|")[0].split("–")[0].split("-")[0].strip()[:100]
                is_food=any(t in blob for t in ("restaurant","cafe","café","coffee","menu","bistro"))
                leads.append({
                    "business_name":name,"country":country,"area":area,"website":page["url"],"domain":domain,
                    "public_email":page["emails"][0] if page["emails"] else "",
                    "public_phone":page["phones"][0] if page["phones"] else "",
                    "social_profiles":page["socials"],"evidence":(page["description"] or item.get("body",""))[:350],
                    "design_opportunity":"Review the published menu, promotions and social visuals; offer a consistent refresh only where a specific improvement is visible.",
                    "recommended_service":"Restaurant/café menu design and matching social graphics" if is_food else "Branded social media graphics and promotional design",
                    "source_url":item.get("href",""),
                    "verification":"Website fetched successfully; category checked against public page content. Contact details included only when published on that page."
                })
                time.sleep(0.7)
        if country=="Portugal" and len(leads)<MAX_LEADS:
            print(f"Portugal yielded {len(leads)} qualified websites; checking UK for remaining places.")
    return leads[:MAX_LEADS]
def main():
    leads=discover(); stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload={"generated_at":stamp,"count":len(leads),"leads":leads}
    (OUT/"prospects.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["business_name","country","area","website","public_email","public_phone","social_profiles","evidence","design_opportunity","recommended_service","source_url","verification"]
    with (OUT/"prospects.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for lead in leads:
            row={k:lead.get(k,"") for k in fields}; row["social_profiles"]="; ".join(lead["social_profiles"]); w.writerow(row)
    lines=["# Fahim Graphic Design — Daily Client Discovery","",f"Generated: {stamp}",f"Qualified public websites: **{len(leads)}** (target: {MAX_LEADS})","","Research only. Verify the business and opportunity manually before contacting. No messages were sent.",""]
    for i,x in enumerate(leads,1):
        lines += [f"## {i}. {x['business_name']}",f"- **Location:** {x['area']}, {x['country']}",f"- **Website:** {x['website']}",f"- **Public email:** {x['public_email'] or 'Not found on checked page'}",f"- **Public phone:** {x['public_phone'] or 'Not found on checked page'}",f"- **Social profiles:** {', '.join(x['social_profiles']) if x['social_profiles'] else 'Not found on checked page'}",f"- **Evidence:** {x['evidence'] or 'No useful page description found'}",f"- **Potential offer:** {x['design_opportunity']}",f"- **Suggested service:** {x['recommended_service']}",f"- **Source:** {x['source_url']}",""]
    if not leads: lines += ["No prospects passed website and category checks. This may reflect rate limits or weak search results, not absence of suitable businesses."]
    lines += ["","Portfolio: https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/"]
    (OUT/"prospects.md").write_text("\n".join(lines),encoding="utf-8")
    print(f"Completed: {len(leads)} prospects. Reports: out/prospects.md, .csv, .json")
if __name__=="__main__": main()
