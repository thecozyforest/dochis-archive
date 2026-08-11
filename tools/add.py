"""
자료 하나를 아카이브(+공개 자료실)에 추가합니다.

  python tools/add.py "C:/경로/자료.html"

물어보는 대로 답하면 됩니다. HTML이면 도치의 창고에 폴더를 만들어 넣고,
공개 링크까지 만들어 줍니다.

한 번에 여러 개를 넣으려면 폴더를 주세요. 안에 있는 HTML을 하나씩 물어봅니다.

  python tools/add.py "C:/경로/폴더"

미리 보기만 (아무것도 안 건드림):
  python tools/add.py "..." --dry-run
"""
import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent      # dochis-archive
ITEMS = REPO / "data" / "items.json"
WAREHOUSE = REPO.parent / "dochis-warehouse"
PAGES_BASE = "https://thecozyforest.github.io/dochis-warehouse/"

TYPES = {"1": ("app", "앱·도구"), "2": ("doc", "문서·자료"), "3": ("form", "폼·템플릿"),
         "4": ("lecture", "연수·강의"), "5": ("book", "저서·집필")}
CHANNELS = {"1": ("public", "공개 — 누구나 열람"),
            "2": ("dorms", "DoRms 한정 — 교사 인증 필요"),
            "3": ("private", "비공개 — 링크를 넣지 않음")}


def ask(q: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    v = input(f"{q}{hint}: ").strip()
    return v or default


def pick(q: str, options: dict, default: str) -> str:
    print(f"\n{q}")
    for k, (_, label) in options.items():
        print(f"  {k}. {label}")
    while True:
        v = input(f"번호 [{default}]: ").strip() or default
        if v in options:
            return options[v][0]
        print("  번호를 다시 골라 주세요.")


def slugify(name: str) -> str:
    """한글 이름에서 폴더용 영문 slug를 만든다. 영문이 없으면 빈 문자열."""
    s = unicodedata.normalize("NFKD", name)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)


def load():
    return json.loads(ITEMS.read_text(encoding="utf-8"))


def save(data):
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_one(src: Path, data: dict, dry: bool) -> bool:
    ids = {x["id"] for x in data["items"]}
    print("\n" + "─" * 60)
    print(f"📄 {src.name}  ({src.stat().st_size / 1024:.0f}KB)")

    name = ask("이름 (사람들에게 보일 제목)", src.stem[:40])
    if not name:
        print("  건너뜁니다.")
        return False
    desc = ask("한 줄 설명")
    typ = pick("어떤 자료인가요?", TYPES, "1")
    tags = [t.strip() for t in ask("태그 (쉼표로 구분)", "진학").split(",") if t.strip()]
    channel = pick("누가 볼 수 있나요?", CHANNELS, "1")

    pack = False
    if channel in ("public", "dorms"):
        pack = ask("\n진학 자료실(진학방 배포용)에 실을까요? y/n", "n").lower().startswith("y")

    href, slug = "", ""
    if channel != "private" and src.suffix.lower() == ".html":
        up = ask("\n도치의 창고에 올려서 공개 링크를 만들까요? y/n", "y").lower().startswith("y")
        if up:
            default_slug = slugify(src.stem) or slugify(name)
            while True:
                slug = ask("창고 안 폴더 이름 (영문·숫자·하이픈)", default_slug)
                if not slug:
                    print("  폴더 이름이 필요합니다.")
                    continue
                if (WAREHOUSE / slug).exists():
                    print(f"  '{slug}' 폴더가 이미 있습니다. 다른 이름을 쓰세요.")
                    continue
                break
            href = PAGES_BASE + slug + "/"
            if dry:
                print(f"  [미리보기] {WAREHOUSE / slug / 'index.html'} 로 복사")
            else:
                (WAREHOUSE / slug).mkdir(parents=True)
                shutil.copy2(src, WAREHOUSE / slug / "index.html")
                print(f"  ✓ 창고에 복사했습니다 → {slug}/index.html")
    if not href and channel != "private":
        href = ask("링크 주소 (없으면 비워 두세요)")

    # 한글 이름은 slug가 거의 안 남으므로 창고 폴더 이름을 먼저 쓴다
    item_id = slug or slugify(name) or slugify(src.stem) or f"item-{len(ids) + 1}"
    base, n = item_id, 2
    while item_id in ids:
        item_id, n = f"{base}-{n}", n + 1

    item = {
        "id": item_id,
        "name": name,
        "desc": desc,
        "type": typ,
        "tags": tags,
        "date": date.today().isoformat(),
        "dateNote": "등록일",
        "channel": channel,
        "pack": pack,
    }
    if href:
        item["href"] = href

    print("\n등록할 내용:")
    print("  " + json.dumps(item, ensure_ascii=False, indent=2).replace("\n", "\n  "))
    if not ask("\n이대로 추가할까요? y/n", "y").lower().startswith("y"):
        print("  취소했습니다.")
        return False

    data["items"].append(item)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    p = Path(a.path)
    if not p.exists():
        print(f"[!] 없는 경로입니다: {p}")
        return 1

    targets = sorted(f for f in p.iterdir() if f.is_file()) if p.is_dir() else [p]
    if not targets:
        print("[!] 파일이 없습니다.")
        return 1

    data = load()
    added = 0
    for f in targets:
        try:
            if add_one(f, data, a.dry_run):
                added += 1
        except (KeyboardInterrupt, EOFError):
            print("\n\n중단했습니다.")
            break

    if not added:
        print("\n추가한 자료가 없습니다.")
        return 0

    data["updated"] = date.today().isoformat()
    if a.dry_run:
        print(f"\n[미리보기] {added}개를 추가할 참이었습니다. 파일은 그대로입니다.")
        return 0

    save(data)
    print(f"\n✓ {added}개를 items.json에 추가했습니다. (총 {len(data['items'])}개)")

    print("\n" + "═" * 60)
    print("마지막으로 인터넷에 올리려면 아래를 실행하세요.")
    print("(자료실은 이 items.json을 직접 읽으므로 따로 만들 것이 없습니다.)\n")
    print(f'  cd "{REPO}" && git add -A && git commit -m "add: {added}개 추가" && git push')
    print(f'  cd "{WAREHOUSE}" && git add -A && git commit -m "add: 자료 추가" && git push')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
