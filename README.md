# B.PREMIER 로스터 뷰어 (2025-26)

B리그 B.PREMIER 동·서부 26팀 코어 로테이션(주전 5 + 벤치 4) 리서치 뷰어.

## 사이트

https://2021147566.github.io/bleague-viewer/

## 로컬 실행

```bash
npm install
npm run dev
```

## 데이터 갱신

```bash
python crawl_bleague_rosters.py
python export_research_sheet.py --sync-all
```

Google Sheets OAuth는 `../token-sheets.json` (저장소에 포함하지 않음).
