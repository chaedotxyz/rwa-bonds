# rwa-bonds · BUIDL / Lend East 실측 검증

BUIDL의 특정 Circle 상환 경로 상태와 Lend East의 대출 장부·공식 공지를 실제 관측으로 분석합니다.

```bash
python3 -m pip install -r requirements.txt
python3 run.py
python3 plot.py
```

- 결과 설명: [results/empirical_report.md](results/empirical_report.md)
- 수치와 판정: [results/empirical_findings.csv](results/empirical_findings.csv)
- 두 상품 비교: [results/empirical_comparison.csv](results/empirical_comparison.csv)
- 그래프: [figures/empirical](figures/empirical)
- 원시 자료·블록·해시: data 및 results/empirical_manifest.json

## 추가 수집 결과

[최종 공개자료 검증 결과](results/final_verification.md). BUIDL NAV 피드 8개 관측과 Lend East 보전금 관련 거래를 추가. 실제 경제적 NAV 괴리는 두 상품 모두 독립 평가자료 부족으로 판정 불가.

```bash
python3 collect_nav.py
python3 run.py
python3 plot.py
```

실제 NAV 비교에 부족한 자료의 상세 목록은 data/nav-source-audit.json에 있습니다.

## 기존 관측 결과와 범위

2026-09-05 저장 관측에서 Lend East 미지급 원금은 약 947.6만 USDC. BUIDL 특정 Circle 경로는 블록 19660000에서 승인·자금 기준 상한 1,950만 USDC, 블록 25911544에서 중지 조건에 따라 상한 0. 전자는 실제 체결 보장이 아니며 후자는 BUIDL 전체 상환 중단이 아님.

**현재 자료로 실제 NAV 괴리·실현 투자 손실·공격 이익은 확정하지 못했습니다.** 자료는 2024년 선택 블록과 2026-09-05 관측이며 실행 시 자동 갱신되지 않음.

[검증 방법](docs/empirical-method.md).

## 검증 및 과거 가정 부록

```bash
python3 -m unittest discover -s tests -v
```

과거 가정 분석이 필요한 경우에만 다음을 사용합니다. 부록의 양의 이익 비율은 실측 확률이 아닙니다.

```bash
python3 run.py --conditional
python3 plot.py --conditional
```
