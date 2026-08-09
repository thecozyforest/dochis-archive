# 도치의 아카이브

도치쌤(기경민)이 만든 앱·자료·연수·저서를 한자리에 모아 둔 아카이브입니다.
캘린더·유형별·태그별 세 가지로 보고, 검색으로 찾습니다.

🔗 https://thecozyforest.github.io/dochis-archive/

## 구조

```
index.html          ← 화면 전체 (빌드 없음, 단일 파일)
data/items.json     ← 모든 산출물의 원본 데이터
```

## 항목 추가하기

`data/items.json`의 `items` 배열에 한 줄 추가하면 끝입니다.

```jsonc
{
  "id": "고유값-kebab-case",
  "name": "이름",
  "desc": "한 줄 설명",
  "type": "app",          // app 앱·도구 | doc 문서·자료 | form 폼·템플릿 | lecture 연수 | book 저서
  "tags": ["진학", "상담"],
  "date": "2026-08-10",   // 모르면 null — 캘린더에는 안 뜨고 목록에는 나옵니다
  "dateNote": "제작일",    // 날짜의 출처
  "channel": "public",    // public 공개 | dorms 교사인증 | private 비공개
  "href": "https://..."   // private 항목에는 넣지 않습니다
}
```

`updated` 날짜도 함께 고쳐 주세요.

## 공개 자료실과의 관계

이 `items.json`이 [공개 자료실](https://thecozyforest.github.io/dochis-warehouse/for-teachers/)의 원본이기도 합니다.
항목을 추가한 뒤 상위 작업 폴더에서 아래를 실행하면 자료실 목록이 갱신됩니다.

```bash
python tools/build_public.py
```

- `channel: public` + `pack != false` → 자료실에 링크와 함께 실림
- `channel: dorms` → 자료실에 **이름만** 실리고 링크는 빠짐 (DoRms 채널로 안내)
- `channel: private` → 자료실에 아예 안 나감

## 라이선스

자료의 저작권은 기경민에게 있습니다. 학교 현장에서 자유롭게 쓰시되 배포 시 출처를 남겨 주세요.
