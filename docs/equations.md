# 계산식·단위·가정

모든 금액은 USD, 가격은 액면 1단위당 USD로 정규화한다. USD/USDC가 동일하다는 단위 가정을 사용하며 디페그는 포함하지 않는다.

## 자산 가치와 NAV

국채: `v = 1 − gap_bps/10000`. 여기서 gap은 시장 할인율 변화가 아니라 NAV 대비 가치 괴리의 스트레스다.

신용: `v = 1 − w × (1 − expected_repayment/principal)`.

`progress = clamp((action_day + execution_days − extension − grace)/write_down, 0, 1)`

`mark = 1 − (1−v) × progress`.

w는 가상 펀드 중 해당 신용에 대한 비례 노출이다. 시간에 따라 변하는 것은 회수 전망의 현재가치가 아니라 이를 반영하는 소비자 NAV다. 45+120일은 실제 NAV 경로가 확인된 값이 아니다.

## 거래 현금흐름

상환: `exit_price = mark`. 담보대출: `exit_price = LTV × mark`.

`Q = min(requested_face, market_depth_face, exit_capacity/exit_price)`

`A = Q × v × (1+slippage_bps/10000)`

`R = Q × exit_price`

`PfC = R − A`.

담보대출은 청구권을 매입해 담보로 넣고 비소구 채무불이행 후 담보를 넘기는 조건부 전략이다. 일반 상환의무가 남는 대출을 무상 수익으로 취급하지 않는다. 상환과 대출 출구를 동시에 사용하거나 수익을 합산하지 않는다. 매입원금은 PfC에서 이미 차감했으므로 CoC에서 다시 빼지 않는다. 최초에 이미 보유한 투자자도 A에 해당하는 경제적 기회비용을 무시하지 않는다.

평가 차액 `requested_face × max(mark−v,0)`는 전체 요청 노출의 차이이며 실현 PfC가 아니다. `Q × max(mark−v,0)`는 체결량에 한정한 낙관적 차액 상한으로 별도 표시한다.

## CoC와 자본

공통비용:

- 실행 수수료 `R × fee_bps/10000`
- 매입 자금 조달비 `A × capital_apr × execution_days/365`
- 고정비
- 가정한 사후 집행손실 `max(PfC,0) × permissioned_share × legal_probability × legal_loss_fraction`

사후 집행손실은 양의 매입·지급 잉여 중 반환될 수 있는 부분을 가정한다. 실제 법적 책임·집행 확률을 추정하지 않으며 원금까지 반환하는 손실, 형사벌·기타 비용은 포함하지 않는다.

B-2 경로비용: `coordination + extension_days × delay_cost_per_day`.

B-1/B-3 지분 통제 자본 K:

- 기존 지분 이전: `K = f × staked_ETH × ETHUSD`
- 외부에서 신규 예치: `K = f/(1−f) × staked_ETH × ETHUSD`

후자는 신규 예치로 전체 지분 분모가 증가하는 효과만 반영한다. 실제 시장 충격·활성화 대기열·확보 가능성을 모델링하지 않는다.

합의 비용: `K × funding_apr × attack_days/365 + K × penalty_probability × penalty_fraction + consensus_coordination`.

**K 자체는 회수 가능한 자본을 포함하므로 자동으로 CoC에 전액 더하지 않는다.** 보고서와 대조할 때 K/PfC도 별도 열로 보지만 자본장벽과 경제적 비용의 비율은 다르다. 자본 가격 하락과 제재손실을 동시에 추가하지 않아 중복 계산을 피한다. 기대손실의 확률·크기는 선언한 가정이다.

`CoC = common_cost + route_cost`, `net = PfC − CoC`. 순이익이 양수이고 거래 조건이 열려 있으면 조건부 open이다. 실제 증거 판정은 별도 `not_empirically_identified`로 남는다. PfC가 음수이면 CoC/PfC는 해석하지 않고 null로 둔다.

## 손익분기점

단위 PfC에서 비례 비용을 뺀 `unit_margin`이 양수일 때:

`break_even_face = fixed_and_route_cost / unit_margin`.

재원·매입수량 상한보다 크면 도달 불가능으로 표시한다. 국채 NAV 괴리와 신용 회수율은 순이익 함수의 부호가 바뀌는 구간에 이분법을 적용한다. 해 없음은 지정한 구간에서의 결과이며 모든 시장의 안전성 증명이 아니다.

## LHS

각 주변분포를 명시된 범위의 균등분포로 놓고 Latin hypercube로 20,000개를 생성한다. B-2/B-3에 같은 표본을 적용한다. 노출 상한은 실제 재원과 매입 깊이로 다시 제한된다. 범위 안에서 순이익이 양수인 표본 비율은 파라미터 공간의 비율이다. 현실 공격 확률이나 경험적 발생빈도가 아니다. LHS에 단순 이항 독립표본 오차를 붙이지 않는다. seed만 같아도 원본 수식·분포·난수 구현이 다르면 원본 보고서 수치를 재현할 수 없다.
