# rwa-bonds · BUIDL / Lend East 실측 검증

BUIDL의 특정 Circle 상환 경로 상태와 Lend East의 대출 장부·공식 공지를 실제 관측으로 분석합니다. 기존 보고서의 공격 비율을 재현하지 않습니다.

폴더를 연 터미널에서 다음 순서로 실행하세요. Python 3.10 이상이 필요합니다.

```bash
python3 -m pip install -r requirements.txt
python3 run.py
python3 plot.py
```

계산은 저장된 자료로 실행되므로 RPC 키가 필요하지 않습니다. 그래프에는 한국어 글꼴이 필요합니다(macOS 기본 글꼴 지원; Linux는 Noto Sans CJK KR).

- 결과 설명: [results/empirical_report.md](results/empirical_report.md)
- 수치와 판정: [results/empirical_findings.csv](results/empirical_findings.csv)
- 두 상품 비교: [results/empirical_comparison.csv](results/empirical_comparison.csv)
- 그래프: [figures/empirical](figures/empirical)
- 원시 자료·블록·해시: data 및 results/empirical_manifest.json

## 추가 수집 결과를 먼저 확인하세요

[최종 공개자료 검증 결과](results/final_verification.md)가 가장 최근 결과입니다. BUIDL NAV 피드 8개 관측과 Lend East 보전금 관련 거래를 추가했습니다. 실제 경제적 NAV 괴리는 두 상품 모두 독립 평가자료 부족으로 판정 불가입니다.

새 그래프는 figures/empirical/04_buidl_nav_observed.png 및 05_lendeast_verified_payment.png입니다.

공개 RPC 자료만 다시 수집하려면 다음을 실행합니다. curl과 네트워크가 필요하며 거래를 전송하지 않습니다. 기존 관측 파일을 새 수집으로 교체합니다. 보전금 거래·공식 공지 자료는 고정된 사건 증거로 유지됩니다.

```bash
python3 collect_nav.py
python3 run.py
python3 plot.py
```

실제 NAV 비교에 부족한 자료의 상세 목록은 data/nav-source-audit.json에 있습니다.

## 기존 관측 결과와 범위

2026-09-05 저장 관측에서 Lend East 미지급 원금은 약 947.6만 USDC입니다. BUIDL 특정 Circle 경로는 블록 19660000에서 승인·자금 기준 상한 1,950만 USDC, 블록 25911544에서 중지 조건에 따라 상한 0입니다. 전자는 실제 체결 보장이 아니며 후자는 BUIDL 전체 상환 중단이 아닙니다.

**현재 자료로 실제 NAV 괴리·실현 투자 손실·공격 이익은 확정하지 못했습니다.** 사건 중 PoS 정상성도 별도 검증하지 않았습니다. 미확인 값은 null이며 손실 0이나 안전 판정을 뜻하지 않습니다. 자료는 2024년 선택 블록과 2026-09-05 관측이며 실행 시 자동 갱신되지 않습니다.

[검증 방법](docs/empirical-method.md)에 계산식·자료 제한·추가로 필요한 증거를 명시했습니다. 과거 Lend East 주소 연결은 같은 과거 블록에서 추가 확인했습니다. 전체 Senior Pool의 수치를 Lend East 단독 손실로 해석하지 않습니다.

## 검증 및 과거 가정 부록

```bash
python3 -m unittest discover -s tests -v
```

과거 가정 분석이 필요한 경우에만 다음을 사용합니다. 부록의 양의 이익 비율은 실측 확률이 아닙니다.

```bash
python3 run.py --conditional
python3 plot.py --conditional
```

GitHub에는 이 README가 있는 폴더의 내용 전체를 올리세요. `.venv`, `__pycache__`는 제외합니다. ZIP은 배포용이므로 레포 내부에 함께 올릴 필요가 없습니다.
