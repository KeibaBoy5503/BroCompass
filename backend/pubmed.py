"""PubMed(NCBI E-utilities) 요청 URL 생성과 응답 파싱. 네트워크 호출은 하지 않는다(순수 함수).

NCBI 이용 규칙: API 키 없이는 초당 3회, 키가 있으면 초당 10회까지. 대량 작업은 미국 동부 기준
주말 또는 평일 밤 9시~새벽 5시에 하라고 안내한다. (https://www.ncbi.nlm.nih.gov/books/NBK25497/)
"""
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional

from papers import Paper

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MAX_IDS_PER_FETCH = 100


def _query(extra: dict[str, str], api_key: str, tool: str, email: str) -> str:
    q = {**extra, "tool": tool}
    if email:
        q["email"] = email
    if api_key:
        q["api_key"] = api_key
    return urllib.parse.urlencode(q, safe=",")  # id 목록의 쉼표는 그대로 둔다 (NCBI 문서 기준)


def esearch_url(term: str, retmax: int = 30, *, api_key: str = "", tool: str = "BroCompass", email: str = "") -> str:
    q = {"db": "pubmed", "term": term, "retmax": str(retmax), "retmode": "json", "sort": "relevance"}
    return f"{BASE}/esearch.fcgi?{_query(q, api_key, tool, email)}"


def efetch_url(pmids: list[str], *, api_key: str = "", tool: str = "BroCompass", email: str = "") -> str:
    # XML 은 rettype 없이 retmode=xml 만 지정한다 (NLM 문서 기준).
    q = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    return f"{BASE}/efetch.fcgi?{_query(q, api_key, tool, email)}"


def parse_esearch(text: str) -> list[str]:
    try:
        data = json.loads(text)
        result = data["esearchresult"]
    except (ValueError, KeyError, TypeError):
        raise ValueError("esearch 응답을 해석하지 못했습니다.")
    if isinstance(result, dict) and result.get("ERROR"):
        raise ValueError(f"esearch 오류: {str(result['ERROR'])[:200]}")
    ids = result.get("idlist", []) if isinstance(result, dict) else []
    return [i for i in ids if isinstance(i, str) and i.isdigit()]


_WS = re.compile(r"\s+")


def _text(el: Optional[ET.Element]) -> str:
    """<i>, <sup> 같은 인라인 태그가 섞여 있어도 글자만 이어 붙이고 공백을 정리한다."""
    return _WS.sub(" ", "".join(el.itertext())).strip() if el is not None else ""


def _year(article: ET.Element) -> Optional[int]:
    pub = article.find("Journal/JournalIssue/PubDate")
    candidates = []
    if pub is not None:
        candidates += [pub.findtext("Year") or "", pub.findtext("MedlineDate") or ""]
    candidates.append(article.findtext("ArticleDate/Year") or "")
    for c in candidates:
        m = re.search(r"\b(19|20)\d{2}\b", c)  # MedlineDate 는 "2019 Jan-Feb" 같은 형태
        if m:
            return int(m.group())
    return None


def _authors(article: ET.Element) -> str:
    names = []
    for a in article.findall("AuthorList/Author"):
        coll = _text(a.find("CollectiveName"))
        last, ini = _text(a.find("LastName")), _text(a.find("Initials"))
        name = coll or " ".join(x for x in (last, ini) if x)
        if name:
            names.append(name)
    if not names:
        return ""
    return names[0] + (" et al." if len(names) > 1 else "")


def parse_efetch(xml_text: str) -> list[Paper]:
    """efetch(XML) -> Paper 목록. 제목이나 초록이 없는 항목은 건너뛴다."""
    if "<!ENTITY" in xml_text:  # 엔티티 폭탄 등 악의적 XML 방어. 정상 PubMed 응답에는 없다.
        raise ValueError("허용되지 않는 XML 입니다.")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"XML 해석 실패: {e}")

    papers: dict[str, Paper] = {}
    for art in root.iter("PubmedArticle"):
        pmid = _text(art.find("MedlineCitation/PMID"))
        article = art.find("MedlineCitation/Article")
        if not pmid.isdigit() or article is None:
            continue
        title = _text(article.find("ArticleTitle"))

        parts, conclusions = [], []
        for at in article.findall("Abstract/AbstractText"):
            text = _text(at)
            if not text:
                continue
            label = (at.get("Label") or "").strip()
            parts.append(f"{label}: {text}" if label and label.upper() != "UNLABELLED" else text)
            if re.search(r"conclusion", label, re.I) or (at.get("NlmCategory") or "").upper() == "CONCLUSIONS":
                conclusions.append(text)
        abstract = " ".join(parts)
        if not title or not abstract:
            continue

        doi = ""
        for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = _text(aid)
                break

        papers[pmid] = Paper(
            pmid=pmid,
            title=title,
            abstract=abstract,
            conclusion=" ".join(conclusions),
            journal=_text(article.find("Journal/Title")) or _text(article.find("Journal/ISOAbbreviation")),
            year=_year(article),
            doi=doi,
            pub_types=[t for t in (_text(pt) for pt in article.findall("PublicationTypeList/PublicationType")) if t],
            authors=_authors(article),
        )
    return list(papers.values())
