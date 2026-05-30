# 삼성 × B.League · 로컬 도구

B.PREMIER 로스터 뷰어 + 2번째 용병 슬롯 계산기 (통합 사이트).

## 사이트

https://2021147566.github.io/bleague-viewer/

| 페이지 | 경로 |
|--------|------|
| B.PREMIER 로스터 | `/` |
| 2빅 슬롯 계산 | `/calc` |

## 로컬 실행

```bash
npm install
npm run dev
```

→ http://localhost:5173 · http://localhost:5173/calc

## 배포

`main` 브랜치 push 시 GitHub Actions → GitHub Pages 자동 배포 (`.github/workflows/deploy-pages.yml`).

## 데이터 갱신

```bash
python crawl_bleague_rosters.py
python export_research_sheet.py --sync-all
python research/calc/export_baseline.py   # 계산기 baseline
```

Google Sheets OAuth는 `../token-sheets.json` (저장소에 포함하지 않음).
