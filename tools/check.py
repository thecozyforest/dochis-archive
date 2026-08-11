"""
items.json에 적힌 링크가 아직 살아 있는지 확인합니다.

  python tools/check.py            ← 창고 안 경로만 (빠름, 인터넷 안 씀)
  python tools/check.py --online   ← 바깥 주소까지 실제로 접속해 확인

창고 폴더 이름이 바뀌거나 지워지면 링크가 조용히 깨집니다.
자료를 올린 뒤나, 창고를 정리한 뒤에 한 번씩 돌려 보세요.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib import error, request

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
ITEMS = REPO / "data" / "items.json"
WAREHOUSE = REPO.parent / "dochis-warehouse"
PAGES = "https://thecozyforest.github.io/dochis-warehouse/"


def alive(url: str) -> tuple[bool, str]:
    req = request.Request(url, method="HEAD",
                          headers={"User-Agent": "dochis-archive-check"})
    try:
        with request.urlopen(req, timeout=12) as r:
            return (200 <= r.status < 400), str(r.status)
    except error.HTTPError as e:
        return False, str(e.code)
    except Exception as e:
        return False, type(e).__name__


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true", help="바깥 주소까지 접속해 확인")
    a = ap.parse_args()

    items = json.loads(ITEMS.read_text(encoding="utf-8"))["items"]
    bad, checked, skipped = [], 0, 0

    for it in items:
        for field in ("href", "altHref"):
            url = it.get(field)
            if not url:
                continue

            if url.startswith(PAGES):
                # 창고 안 경로 — 폴더가 실제로 있는지 파일로 확인한다 (인터넷 불필요)
                rel = url[len(PAGES):].strip("/")
                if not rel:
                    continue
                folder = WAREHOUSE / rel
                ok = (folder / "index.html").exists() or folder.with_suffix(".html").exists()
                checked += 1
                if not ok:
                    bad.append((it["id"], field, url, "창고에 그 폴더가 없습니다"))
            elif a.online:
                ok, why = alive(url)
                checked += 1
                if not ok:
                    bad.append((it["id"], field, url, f"응답 {why}"))
            else:
                skipped += 1

    print(f"항목 {len(items)}개 · 링크 {checked}개 확인" +
          (f" · 바깥 주소 {skipped}개는 건너뜀 (--online 을 붙이면 확인합니다)" if skipped else ""))

    if not bad:
        print("\n✓ 깨진 링크가 없습니다.")
        return 0

    print(f"\n✗ 깨진 링크 {len(bad)}개\n")
    for item_id, field, url, why in bad:
        print(f"  [{item_id}] {field}")
        print(f"    {url}")
        print(f"    → {why}\n")
    print("data/items.json 에서 위 항목의 주소를 고치거나,")
    print("공개하지 않을 자료라면 channel 을 dorms/private 으로 바꾸고 href 를 지우세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
