#!/usr/bin/env python3
"""Expand exact Greek musician aliases using ALL pages of Greek Wikipedia categories.

No inferred Greeklish aliases are trusted. A new alias is accepted only if
the linked article has an explicit enwiki title or a Wikidata English label
for that exact article. All missing/conflicting identities go to the audit.
Original, manually reviewed entries stay first and are never replaced.

Usage: python UPDATE_GREEK_ARTISTS_WIKIPEDIA.py
        python UPDATE_GREEK_ARTISTS_WIKIPEDIA.py --output /path/Greek_Artists.csv
Requires only Python standard library and Wikimedia's public APIs.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT="Έλληνες τραγουδιστές"
CATEGORIES=(
    ROOT,
    "Ελληνίδες τραγουδίστριες",
    "Αγγλόφωνοι τραγουδιστές από την Ελλάδα",
    "Λαϊκοί τραγουδιστές",
    "Έλληνες ηθοποιοί μουσικού θεάτρου",
    "Έλληνες τραγουδιστές όπερας",
    "Έλληνες ράπερ",
    "Ελληνίδες ράπερ",
    "Ρεμπέτες",
    "Συμμετέχοντες στο Φεστιβάλ Τραγουδιού Θεσσαλονίκης",
    "Τραγουδιστές ελαφρού τραγουδιού",
    "Έλληνες ψάλτες",
)
API="https://el.wikipedia.org/w/api.php"
WIKIDATA="https://www.wikidata.org/w/api.php"
SOURCE="https://el.wikipedia.org/wiki/"
AGENT="LRCBulkFinder-Greek-Artist-Lexicon/1.0 (+https://github.com/DimitrisLai/LRC-Bulk-Finder)"
LATIN=re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9 .'’\-]+$")
GREEK=re.compile("[\u0370-\u03ff\u1f00-\u1fff]")
ROLE_RE=re.compile(r"\s*\((?:τραγουδιστής|τραγουδίστρια|μουσικός|ράπερ|καλλιτέχνης|"
                   r"λυρικός τραγουδιστής|λαϊκός τραγουδιστής|βαρύτονος|τραγουδοποιός - ποιητής|ηθοποιός|συνθέτης|singer|rapper|musician|"
                   r"singer-songwriter|opera singer|actor|composer)\)\s*$",re.I)
HEADERS=("greeklish","greek")
AUDIT_HEADERS=("greek","greeklish","category","source_page","identity_source","status")
PAGE_SIZE=200
MAX_PAGES=50
MAX_TOTAL=5000


def _api(url, params):
    values=dict(params,format="json",formatversion=2)
    address=url+"?"+urlencode(values)
    req=Request(address,headers={"User-Agent":AGENT,"Accept":"application/json"})
    last=None
    for attempt in range(4):
        try:
            with urlopen(req, timeout=35) as response:
                payload=response.read(4_000_001)
            if len(payload)>4_000_000:
                raise ValueError("Unexpectedly large Wikimedia API response")
            result=json.loads(payload.decode("utf-8"))
            if "error" in result:raise ValueError("Wikimedia API: "+str(result["error"])[:250])
            return result
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last=error
            if isinstance(error, HTTPError) and error.code not in (429,500,502,503,504):
                raise
            if attempt<3:time.sleep(1.5*(attempt+1))
    raise RuntimeError("Unable to access "+url+": "+str(last)) from last


def category_members(category,api=_api):
    """Follow EVERY cmcontinue page, not just Wikipedia's first 200 entries."""
    token=None
    pages=0
    output=[]
    seen_tokens=set()
    while True:
        params={"action":"query","list":"categorymembers",
                "cmtitle":"Category:"+category,"cmtype":"page",
                "cmlimit":PAGE_SIZE}
        if token:params["cmcontinue"]=token
        response=api(API,params)
        members=response.get("query",{}).get("categorymembers",[])
        output.extend(m["title"] for m in members if m.get("ns")==0 and m.get("title"))
        pages+=1
        next_token=response.get("continue",{}).get("cmcontinue")
        if pages>MAX_PAGES or len(output)>MAX_TOTAL:
            raise ValueError("Category traversal exceeded safety bounds")
        if not next_token:break
        if next_token in seen_tokens:raise ValueError("Cyclic category continuation")
        seen_tokens.add(next_token)
        token=next_token
    return sorted(set(output),key=str.casefold),pages


def article_names(titles,api=_api):
    """Batch linked identity labels: enwiki title first, Wikidata label second."""
    records={}
    qids={}
    for start in range(0,len(titles),40):
        batch=titles[start:start+40]
        payload=api(API,{"action":"query","prop":"langlinks|pageprops",
                        "lllang":"en","lllimit":"max","ppprop":"wikibase_item",
                        "redirects":1,"titles":"|".join(batch)})
        # Redirect normalization uses returned Greek display titles.
        normalized={x["from"]:x["to"] for x in payload.get("query",{}).get("normalized",[])}
        redirected={x["from"]:x["to"] for x in payload.get("query",{}).get("redirects",[])}
        for p in payload.get("query",{}).get("pages",[]):
            if p.get("missing") or p.get("ns")!=0:continue
            greek=p["title"]
            en=next((x.get("title") for x in p.get("langlinks",[]) if x.get("lang")=="en"),None)
            qid=p.get("pageprops",{}).get("wikibase_item")
            records[greek]=(en,"enwiki" if en else "")
            if not en and qid:qids[qid]=greek
        for original in batch:
            target=redirected.get(normalized.get(original,original),normalized.get(original,original))
            if original not in records and target in records:
                records[original]=records[target]
    if qids:
        for start in range(0,len(qids),45):
            batch=list(qids)[start:start+45]
            try:
                payload=api(WIKIDATA,{"action":"wbgetentities","ids":"|".join(batch),
                                      "props":"labels","languages":"en"})
            except (ValueError,RuntimeError,HTTPError,URLError):
                # Wikidata fallback is optional; never fabricate missing Latin names.
                continue
            for qid,entity in payload.get("entities",{}).items():
                title=qids.get(qid)
                latin=entity.get("labels",{}).get("en",{}).get("value")
                if title and latin and not records.get(title,("",))[0]:
                    records[title]=(latin,"wikidata-en")
    return records


def normalize_person(text):
    name=ROLE_RE.sub("",str(text)).strip()
    return unicodedata.normalize("NFC"," ".join(name.split()))


def mapping(greek, latin):
    greek=normalize_person(greek)
    latin=normalize_person(latin)
    if not greek or not latin or greek==latin:return None
    if not GREEK.search(greek) or not LATIN.fullmatch(latin):return None
    if len(greek)>90 or len(latin)>90:return None
    if greek.startswith(("Κατάλογος ","Δισκογραφία ","Συλλογή ")):return None
    if re.search(r"\b(?:album|discography|band|group)\b",latin,re.I):return None
    return latin,greek


def key(latin):
    """Match LRC_Bulk_Finder.normalize exactly, including punctuation folding."""
    string=unicodedata.normalize("NFKD",str(latin)).casefold()
    string="".join(ch for ch in string if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in string).split())


def expand(old_rows,member_sources,identities):
    preserved={}
    output=[]
    for row in old_rows:
        latin=(row.get("greeklish") or "").strip()
        greek=(row.get("greek") or "").strip()
        if not latin or not greek:continue
        k=key(latin)
        if k in preserved:
            if preserved[k]!=greek:raise ValueError("Conflicting existing CSV alias "+latin)
            continue
        preserved[k]=greek
        output.append((latin,greek))
    proposals={}
    audits=[]
    for article,categories in sorted(member_sources.items(),key=lambda p:p[0].casefold()):
        latin,method=identities.get(article,("",""))
        row=mapping(article,latin) if latin else None
        source=SOURCE+quote(article.replace(" ","_"))
        greek=normalize_person(article)
        if row is None:
            audits.append((greek,latin or "", "|".join(sorted(categories)),source,method,"needs-manual-identity"))
            continue
        roman,greek=row
        k=key(roman)
        status="approved-source-linked"
        if k in preserved:
            status="existing-preserved" if preserved[k]==greek else "collision-existing-skipped"
        elif k in proposals:
            status="duplicate-source" if proposals[k][1]==greek else "collision-new-skipped"
            if status=="collision-new-skipped":
                # Do not guess between two different people bearing same Latin name.
                proposals.pop(k)
                preserved[k]="(reserved-conflict)"
        else:
            proposals[k]=(roman,greek)
        audits.append((greek,roman,"|".join(sorted(categories)),source,method,status))
    addition=sorted(proposals.values(),key=lambda x:(x[1].casefold(),x[0].casefold()))
    return output+addition, audits, len(output), len(addition)


def read_existing(path):
    with Path(path).open("r",encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        if tuple(reader.fieldnames or [])!=HEADERS:
            raise ValueError("Refusing to modify an unfamiliar Greek_Artists.csv schema")
        return list(reader)


def make_csv(headers,rows):
    buf=io.StringIO(newline="")
    writer=csv.writer(buf,lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return "\ufeff"+buf.getvalue()


def build(root,output=None,api=_api):
    destination=Path(output) if output else root/"Greek_Artists.csv"
    baseline=root/"Greek_Artists_Baseline_Approved.csv"
    if not baseline.is_file():
        raise FileNotFoundError("Approved baseline required; refusing to regenerate public artist CSV")
    if not (root/"Greek_Artists.csv").is_file():
        raise FileNotFoundError("Original Greek_Artists.csv required")
    # Stable, idempotent import. Previously generated Wikipedia entries are
    # NOT considered newly manual-approved on the next refresh.
    old=read_existing(baseline)
    collected={}
    pages={}
    for cat in CATEGORIES:
        members,visited=category_members(cat,api=api)
        pages[cat]=visited
        for title in members:collected.setdefault(title,set()).add(cat)
        print(f"READ ALL PAGES: {cat}: {len(members)} articles in {visited} page(s)",flush=True)
    # Incomplete fetches must NEVER overwrite the public dictionary.
    if len([x for x in collected if ROOT in collected[x]])<350:
        raise ValueError("Root category incomplete (expected at least 350 direct articles)")
    if len([x for x in collected if "Ελληνίδες τραγουδίστριες" in collected[x]])<200:
        raise ValueError("Female singers category incomplete (expected at least 200)")
    print(f"Unique Greek Wikipedia articles gathered: {len(collected)}",flush=True)
    identities=article_names(sorted(collected),api=api)
    merged,audit,original_count,new_count=expand(old,collected,identities)
    if new_count<70:
        raise ValueError("Too few verified new artists; refusing to replace source")
    auditpath=root/"Greek_Artists_Wikipedia_Audit.csv"
    proposed=make_csv(HEADERS,merged)
    audit_csv=make_csv(AUDIT_HEADERS,audit)
    if destination.resolve()==auditpath.resolve():raise ValueError("CSV paths collide")
    destination.write_text(proposed,encoding="utf-8")
    auditpath.write_text(audit_csv,encoding="utf-8")
    print(f"VERIFIED: original {original_count} aliases preserved; +{new_count} Wikipedia-linked; final {len(merged)}",flush=True)
    print("SOURCE PAGINATION: "+json.dumps(pages,ensure_ascii=False,sort_keys=True),flush=True)
    return original_count,new_count,len(merged),pages


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    build(args.root.resolve(),args.output)


if __name__=="__main__":main()
