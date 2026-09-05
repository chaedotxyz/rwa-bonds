# 최종 레포 정리

이번 버전의 단일 실행 진입점은 run.py이며, 설정은 config/scenarios.json 하나다.

제거한 이전 코드·산출물:

- economic_model.py / integrated_model.py / trade_model.py 및 관련 설정: 금리 민감도·회수금 할인 기반 모델을 src/model.py의 B-1/B-2/B-3 경로로 교체.
- empirical.py / refresh.py / recheck_history.py: 광범위한 잔액 관측·갱신 도구를 제거하고 필요한 원자료와 observations 출력만 유지.
- verify_redemption.py / verification/ / package.json / package-lock.json: 이번 연구 질문과 다른 EVM 상환·롤백 실험과 Node 의존성 제거.
- 과거 그래프와 중복 보고서·CSV: 새 비용·이익, NAV 반영 경로, 파라미터 표본 비율 그래프로 교체.
- 이전 폴더 사본 rwa-bonds 2~5 및 여러 버전 ZIP: 사용자 전달 위치에서 제거하고 작업용 보관 위치로 이동.

최종 전달 위치에는 rwa-bonds 폴더와 rwa-bonds-final.zip만 둔다. 이전 산출물은 복구를 위해 작업 영역의 prior-deliverables에 보관하며 최종 ZIP에는 포함하지 않는다. 원자료는 체크섬을 검증한 필요한 파일만 data에 유지한다.
