# 2번째 용병 슬롯 계산기 (로컬 웹)

**API 없음.** 브라우저에서 3팀 Role W·유사도·코칭 힌트를 한 번에 계산합니다.  
Python `second_import_slot.py` / 학술보완 보고서와 **동일 Role W 수식**.

## 실행 (통합 사이트 권장)

```bash
cd code
npm install
npm run dev
```

→ http://localhost:5173 (로스터) · http://localhost:5173/calc (2빅 슬롯)

## 단독 실행 (calc만)

```bash
cd code/research/calc
python export_baseline.py   # xlsx 갱신 시
python -m http.server 8080
```

## UI

| 기능 | 설명 |
|------|------|
| **구단용 / 학회용** | 코치 친화 vs Wasserstein·SLSQP 정의 |
| **종합 · 브렉스 · 미카와 · 군마** | 탭 내비 — 3팀 전부 동시 계산 |
| **프리셋** | 제이크 레이맨 · 우드버리 placeholder |
| **Markdown** | 하단 접이식 — 복사/다운로드 |

## parity 검증

```bash
python compare_with_reports.py
```

레이맨·Woodbury 각각 `학술보완_MPG가중` 보고서 `w_dual_import` 와 일치 확인.

## 폴더

```
calc/
  index.html
  export_baseline.py
  compare_with_reports.py
  js/engine.js · views.js · app.js
  data/baseline.json
  css/style.css
```
