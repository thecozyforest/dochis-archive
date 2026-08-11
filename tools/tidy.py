"""
같은 산출물의 여러 버전을 묶어서 '어느 게 최신인지' 알려줍니다.

  python tools/tidy.py "폴더경로"            ← 보기만 (아무것도 안 건드림)
  python tools/tidy.py "폴더경로" --apply     ← 구버전을 _구버전/ 으로 옮김

파일을 지우지 않습니다. 옮기기만 합니다.

판단 기준은 **파일 수정시각**입니다. 이름에 붙은 '_최종', 'v5', '(3)' 은
서로 순서를 알려주지 못하기 때문입니다. (실제로 '_최종'보다 'v5b'가
나중인 경우가 흔합니다.)
"""
import argparse
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 이름에서 걷어낼 '버전 표시'들. 이걸 지운 나머지가 같으면 같은 산출물로 본다.
NOISE = [
    r"\(정리본\)", r"\(최종\)", r"\(수정본\)",
    r"\(\s*\d+\s*\)",              # (1) (2) (3)
    r"[-_ ]복사본",
    r"[-_ ]?v\d+(\.\d+)?[a-z]?(?![가-힣A-Za-z0-9])",   # v3, v5b, v2.1
    r"[-_ ]?\d{6,8}(?![가-힣A-Za-z0-9])",              # 20260729
    # 한글 단어 뒤에 '_'가 오면 \b 가 성립하지 않으므로 직접 경계를 쓴다
    r"[-_ ](최종|최종본|완성본|수정본|정리본|배포용|검수본|무왜곡검수본|"
    r"원문재검증|맥락보완|크레딧수정|재검증|보완|final|fix)(?![가-힣A-Za-z0-9])",
]
NOISE_RE = [re.compile(p, re.I) for p in NOISE]


def base_name(stem: str) -> str:
    """버전 표시를 걷어낸 '산출물 이름'."""
    s = stem
    for _ in range(4):  # 겹쳐 붙은 표시를 반복해서 제거
        for r in NOISE_RE:
            s = r.sub(" ", s)
    s = re.sub(r"[\s_\-.]+", " ", s).strip()
    return s.lower()


# 이 말들이 한쪽에만 붙어 있으면 '구버전'이 아니라 '용도가 다른 파일'이다
USE_WORDS = ["정리본", "배포용", "공개용", "소장용", "원본", "풀버전",
             "요약본", "인쇄용", "발표용", "교사용", "학생용"]


def use_tag(name: str) -> frozenset:
    return frozenset(w for w in USE_WORDS if w in name)


def version_key(name: str):
    """이름에 박힌 버전 번호. 수정시각이 같을 때만 보조로 쓴다."""
    m = re.search(r"v(\d+)(?:\.(\d+))?", name, re.I)
    v = (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)
    c = re.search(r"\((\d+)\)", name)
    return (*v, int(c.group(1)) if c else 0)


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--apply", action="store_true", help="구버전을 _구버전/ 으로 옮긴다")
    a = ap.parse_args()

    root = Path(a.folder)
    if not root.is_dir():
        print(f"[!] 폴더가 아닙니다: {root}")
        return 1

    groups = defaultdict(list)
    for f in root.iterdir():
        if f.is_file() and f.name != "_구버전" and not f.name.startswith("."):
            groups[(base_name(f.stem), f.suffix.lower())].append(f)

    multi = {k: v for k, v in groups.items() if len(v) > 1}
    single = {k: v for k, v in groups.items() if len(v) == 1}

    print(f"📂 {root.name}")
    print(f"   파일 {sum(len(v) for v in groups.values())}개 → 산출물 {len(groups)}개\n")

    if not multi:
        print("✓ 버전이 겹치는 파일이 없습니다.")
        return 0

    old_files, kept_groups = [], 0
    for (name, ext), files in sorted(multi.items()):
        # 수정시각이 먼저, 같으면 이름의 버전 번호로
        files.sort(key=lambda f: (f.stat().st_mtime, version_key(f.name)), reverse=True)
        sizes = [f.stat().st_size for f in files]
        # ① 이름에 붙은 용도 표시가 서로 다르거나
        # ② 크기가 10배 넘게 벌어지면 → 구버전이 아니라 '용도가 다른 파일'로 본다
        uses = {use_tag(f.name) for f in files}
        mixed = len([u for u in uses if u]) > 0 and len(uses) > 1
        if not mixed and min(sizes):
            mixed = max(sizes) > min(sizes) * 10
        tie = len(files) > 1 and files[0].stat().st_mtime == files[1].stat().st_mtime

        print(f"■ {name}{ext}  — {len(files)}개")
        for i, f in enumerate(files):
            when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            mark = "👑 최신 " if i == 0 else ("   ?    " if mixed else "   구버전")
            print(f"   {mark}  {when}  {human(f.stat().st_size):>7}  {f.name}")
            if i > 0 and not mixed:
                old_files.append(f)
        if mixed:
            kept_groups += 1
            print("   ⚠ 크기가 크게 다릅니다. 구버전이 아니라 용도가 다른 파일일 수 있어")
            print("     (예: 공개용 정리본 vs 소장용 원본) 자동 이동에서 뺐습니다.")
        elif tie:
            print("   ⚠ 위 두 파일의 수정시각이 같습니다. 이름의 버전 번호로 정했으니 한 번 확인해 주세요.")
        print()

    if not a.apply:
        print(f"→ 구버전 {len(old_files)}개를 _구버전/ 으로 옮기려면 --apply 를 붙여 다시 실행하세요.")
        print("  (지우지 않고 옮기기만 합니다)")
        return 0

    dest = root / "_구버전"
    dest.mkdir(exist_ok=True)
    for f in old_files:
        target = dest / f.name
        n = 1
        while target.exists():
            target = dest / f"{f.stem}__{n}{f.suffix}"
            n += 1
        shutil.move(str(f), str(target))
        print(f"  옮김: {f.name}")
    print(f"\n✓ {len(old_files)}개를 {dest} 로 옮겼습니다. 최신본만 남았습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
