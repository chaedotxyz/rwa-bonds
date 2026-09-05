# 실측 검증 방법과 식별 한계

검증 대상은 BUIDL과 Goldfinch Lend East다. 보고서의 공격 비율이나 가정 NAV 경로를 목표값으로 쓰지 않는다. 기본 실행에는 무작위 표본이 없다.

## 자료와 계산

- `history.json`, `chain.json`: RPC 호출 주소, 입력, 원시 반환값, 블록 번호·해시·시각. 원문은 checksum으로 무결성을 검사한다. 해시는 자료의 외부 진실성·합의 정상성을 보증하지 않는다.
- BUIDL 경로: `buidl-route-state.json`의 19660000, 25911544 블록. 후자의 원시 계약 반환값은 `buidl-verified-state.json`, `buidl-settlement-state.json`, `buidl-liquidity-state.json`에도 저장되어 있다. 과거 경로 요약에는 모든 호출 원문이 없다는 재검증 제한이 있다. 출처 RPC는 https://ethereum-rpc.publicnode.com 이다.
- BUIDL settlement: `0x57dd4e92712b0fbc8d3f3e3645eebcf2600acef0`, liquidity source: `0x9ba14ce55d7a508a9bb7d50224f0eb91745744b7`, USDC holder: `0x13e003a57432062e4eda204f687be80139ad622f`. 중지 시 경로 상한 0; 그 외 `min(allowance, holder USDC)`는 필요조건 상한이다. 승인·현금 외 제한 때문에 실제 체결 가능량과 다를 수 있다. 다른 경로의 상태를 뜻하지 않는다.
- Lend East credit line: `0x5424b911d04f71357468743b24b868db0706048c`. 최근 블록의 pool `creditLine()`으로 연결을 확인했다. 과거 자료에는 주소 연결 호출이 없으므로 과거 귀속에 이 제한을 명시한다.
- 잔액 변화는 마지막 `balance()` - 첫 `balance()`다. 원금 변제, 상각, 재구조화 등을 분리할 이벤트 자료가 없으므로 현금 회수로 분류하지 않는다.
- 만기 후 경과 일수는 `(관측 블록 시각 - termEndTime()) / 86400`. 그 관측점에서 미지급 원금이 있을 때만 제시한다. 연속된 연체 상태나 NAV 반영 지연의 길이를 입증하지 않는다.
- 공식 예상 부족분은 2024-04-02 공지의 원금에서 예상 상환액을 뺀 값이다. USD 공지값과 USDC 장부는 구분하고 환율 1:1을 임의로 적용하지 않는다.
- Senior Pool은 집합 포트폴리오다. 지분가격·상각 변화는 Lend East 단독 NAV 또는 손실로 귀속하지 않는다.

## 전체 명제에 필요한 추가 증거

“PoS가 정상적으로 작동해도 온체인 참조가격과 실제 시장 위험의 괴리 때문에 경제적 손실이 남는다”는 다음 조건을 각각 확인해야 한다.

| 검증 항목 | 필요한 증거 | 현재 판정 |
|---|---|---|
| 사건 중 합의 정상성 | 동일 기간 finalized checkpoint·finality 지연·재조직 자료 | 미검증; RPC 블록 존재만으로 대체하지 않음 |
| 실제 NAV 괴리 | 동일 시각의 온체인 참조값과 독립 포트폴리오 평가 | 두 상품 모두 미식별 |
| 손실 실현 | 투자자별 원가·분배·상환·매도 현금흐름, 종결 또는 잔존가치 | 미식별; 예상 손실은 분리 |
| 공격자의 실행 가능 이익 | 실제 접근 권한·체결 가격·수량·비용·법적 청구권 | 미식별 |

자료가 없는 값을 0으로 출력하지 않는다. 서로 다른 상품의 관측을 합쳐 하나의 인과적 입증으로 제시하지 않는다. 현재 결과는 신용 문제 및 특정 출구 제약에 대한 부분 검증이며 전체 명제의 입증 완료가 아니다.

공식 후속 안내: [BUIDL RFQ 경로](https://blog.uniswap.org/unlocking-defi-liquidity-for-buidl), [Lend East 당시 예상 회수 공지](https://gov.goldfinch.finance/t/update-on-lend-east-pool/1957), [추가 상환 요구 공지](https://gov.goldfinch.finance/t/actions-against-lend-east/2052). 웹 안내는 2026-09-06 재열람했으며 체인 자료를 실시간 갱신한 것은 아니다.
