"""부산 응급의료기관 목록을 공공데이터포털에서 받아 emergency.json 으로 저장합니다.
GitHub Actions 가 매주 실행합니다. 인증키는 환경변수 DATA_GO_KR_KEY 로만 받습니다."""
import json, os, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
URL = "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytListInfoInqire"
OUT = "emergency.json"

if not KEY:
    sys.exit("DATA_GO_KR_KEY 가 비어 있습니다. GitHub Secrets 를 확인하세요.")


def fetch(page):
    # 인코딩 키·디코딩 키 어느 쪽을 넣어도 동작하도록 한 번 풀었다가 다시 인코딩
    q = "serviceKey=" + urllib.parse.quote(urllib.parse.unquote(KEY), safe="")
    q += "&" + urllib.parse.urlencode({"Q0": "부산광역시", "pageNo": page, "numOfRows": 100})
    with urllib.request.urlopen(URL + "?" + q, timeout=30) as r:
        return ET.fromstring(r.read())


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


items, page, total = [], 1, None
while page <= 10:
    root = fetch(page)
    code = root.findtext(".//resultCode")
    if code != "00":
        sys.exit("API 오류: %s %s" % (code, root.findtext(".//resultMsg")))
    if total is None:
        total = int(root.findtext(".//totalCount") or 0)
    rows = root.findall(".//item")
    if page == 1 and rows:
        print("응답 항목 이름:", sorted(c.tag for c in rows[0]))  # 필드명 확인용 로그
    for it in rows:
        g = lambda t: (it.findtext(t) or "").strip()
        items.append({
            "name": g("dutyName"),
            "addr": g("dutyAddr"),
            "tel": g("dutyTel1"),
            "tel3": g("dutyTel3"),
            "emcls": g("dutyEmclsName") or g("dutyEmcls"),
            "lat": num(g("wgs84Lat")),
            "lon": num(g("wgs84Lon")),
        })
    if not rows or len(items) >= total:
        break
    page += 1

if not items:
    sys.exit("받아온 항목이 0건이라 기존 파일을 유지합니다.")

items.sort(key=lambda x: x["name"])
old = None
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        old = json.load(f).get("items")
if old == items:
    print("바뀐 내용이 없어 저장하지 않습니다.")
else:
    kst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": kst, "source": "국립중앙의료원 전국 응급의료기관 정보 조회 서비스", "items": items},
                  f, ensure_ascii=False, indent=1)
    print("저장 완료: %d곳" % len(items))
