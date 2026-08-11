"""
아카이브 원본(dochis-archive/data/items.json)에서 공개 자료실용 JSON을 생성합니다.

  python tools/build_public.py

규칙
  - channel == "public" 이고 pack 이 false 가 아닌 항목만 자료실에 싣는다.
  - channel == "dorms" 항목은 이름·설명만 싣고 URL은 넣지 않는다 (DoRms 채널로 안내).
  - channel == "private" 항목은 아예 내보내지 않는다.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent      # dochis-archive
SRC = REPO / "data" / "items.json"
DST = REPO.parent / "dochis-warehouse" / "for-teachers" / "items.json"

DORMS_CHANNEL = "https://dorms.school/channels/1c9ff07b-ef12-47e7-9ddf-9c2e15633cec"
WAREHOUSE_INDEX = "https://thecozyforest.github.io/dochis-warehouse/"


def main() -> int:
    if not SRC.exists():
        print(f"[!] 원본을 찾을 수 없습니다: {SRC}")
        return 1

    data = json.loads(SRC.read_text(encoding="utf-8"))
    items = data["items"]

    public, dorms_only, skipped = [], [], []
    for it in items:
        ch = it.get("channel")
        if ch == "private":
            skipped.append(it["name"])
            continue
        if not it.get("pack", True):
            skipped.append(it["name"])
            continue
        if ch == "dorms":
            dorms_only.append({"name": it["name"], "desc": it["desc"], "tags": it.get("tags", [])})
            continue
        if ch == "public":
            if not it.get("href"):
                skipped.append(it["name"])
                continue
            entry = {
                "name": it["name"],
                "desc": it["desc"],
                "type": it["type"],
                "tags": it.get("tags", []),
                "href": it["href"],
            }
            if it.get("date"):
                entry["date"] = it["date"]
            if it.get("altHref"):
                entry["altHref"] = it["altHref"]
                entry["altLabel"] = it.get("altLabel", "다른 배포판")
            public.append(entry)

    # 앱·도구를 먼저, 그 안에서 최신순. 날짜가 없는 항목은 각 묶음의 끝으로.
    def order(x):
        d = x.get("date")
        return (x["type"] != "app", -int(d.replace("-", "")) if d else 1, x["name"])

    public.sort(key=order)

    out = {
        "updated": data.get("updated", ""),
        "types": data["types"],
        "items": public,
        "dormsOnly": dorms_only,
        "dormsChannel": DORMS_CHANNEL,
        "warehouseIndex": WAREHOUSE_INDEX,
        "warehouseCount": sum(1 for it in items
                              if not it.get("pack") and it["channel"] != "private"),
    }

    # 안전 점검 — URL이 새어 나가면 안 되는 항목이 섞였는지 확인
    leaked = [p["name"] for p in public
              if any(p["name"] == d["name"] for d in dorms_only)]
    assert not leaked, f"DoRms 항목이 공개 목록에 섞였습니다: {leaked}"
    assert all("href" not in d for d in dorms_only), "DoRms 목록에 URL이 들어 있습니다"

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"✓ {DST.relative_to(REPO.parent)}")
    print(f"  공개 자료      {len(public)}개")
    print(f"  DoRms 안내     {len(dorms_only)}개 (이름만, URL 없음)")
    print(f"  제외           {len(skipped)}개 — {', '.join(skipped[:5])}{' 외' if len(skipped) > 5 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
