# rwa-bonds · 보고서 3장 B-1 / B-2 / B-3

채영 파트의 **합의 예산과 NAV · 국채와 신흥국 신용**을 비교하는 Python 연구 모델입니다.

- **B-1:** 국채 렌딩 담보의 조건부 PfC와 합의 경로 비용.
- **B-2:** 신용 부실의 NAV 반영 지연 동안 상환/담보 경로의 비용·이익.
- **B-3:** B-2와 동일한 이익에 합의 비용을 적용한 대조군.

실제 관측·당사자 공지·보고서 앵커·가정을 분리합니다. 보고서의 61.7%를 재현한 코드가 아니며, 실제 공격이나 체인 확정 상태를 시뮬레이션하지 않습니다.

## 실행

Python 3.10 이상. 기본 계산에 인터넷·추가 설치가 필요 없습니다.

```bash
python3 run.py
```

`results/report.md`에 기준점과 20,000개 LHS 표본 결과가 저장됩니다. 빠른 점검은 `python3 run.py --samples 200`입니다. 표본 비율은 가정한 파라미터 공간의 비율이고 실제 공격 확률이 아닙니다.

## 파일

| 경로 | 역할 |
|---|---|
| `config/scenarios.json` | 모든 입력의 값·단위·분류·출처·가정 |
| `src/model.py` | NAV 반영 지연, 거래 현금흐름, CoC/PfC, 자본·손익분기 |
| `src/sampling.py` | 동일 표본으로 B-2/B-3를 비교하는 LHS |
| `results/scenarios.csv` | 기준점의 비용 항·이익·판정·자본 |
| `results/controls.csv` | 출구 폐쇄·즉시 NAV 갱신·제재손실 0 등 대조 |
| `results/thresholds.csv` | 손익분기 노출·국채 NAV 괴리·신용 회수율 |
| `results/samples.csv` | sample_id로 짝지은 3개 시나리오 전체 표본 |
| `results/observations.csv` | 2024년/2026-09-05 고정 블록 관측. 최신 실시간 자료 아님 |
| `results/manifest.json` | 실제 입력·분포·표본 수·코드/자료 체크섬 |
| `data/` | 필요한 원자료와 보고서 발췌·출처 |

PfC는 지급액에서 매입원금을 뺀 금액입니다. CoC는 실행비·조달비·기대 집행손실·경로 비용입니다. 스테이킹 자본 전액을 손실로 중복 계산하지 않습니다. 상환 재원·실제 호가·접근권한은 조건부 가정이며, 결과의 `evidence_verdict`는 실제 공격 구간의 실증 여부를 별도로 표시합니다.

## 그래프

완성된 PNG·SVG는 `figures/`에 있습니다. 다시 생성하려면:

```bash
python3 -m pip install -r requirements.txt
python3 plot.py
```

그래프는 `results/manifest.json`과 그 결과 파일을 읽습니다. 설정을 바꿨다면 먼저 `python3 run.py`를 실행하세요. macOS 기본 한글 글꼴 또는 Noto Sans CJK KR/NanumGothic이 필요합니다.

## 검증과 보고서 사용

```bash
python3 -m unittest discover -s tests -v
```

[3장 시나리오](docs/chapter3.md), [수식](docs/equations.md), [보고서 대응·수정 사항](docs/report-alignment.md)을 함께 확인하세요.

GitHub `rwa-bonds`에는 이 폴더 **내부 전체**를 올리면 됩니다. 이전 모델과 혼합하지 말고 교체하세요. `.github`와 `.gitignore`를 포함합니다. Node.js·npm·Ganache는 더 이상 필요하지 않습니다.
