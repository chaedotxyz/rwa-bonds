"""Static figures from saved measurements; gaps remain gaps."""
import json
import matplotlib.pyplot as plt


def plot(results,out):
    d=json.loads((results/'empirical_manifest.json').read_text())
    def save(fig,name):
        for ext in ['png','svg']:
            fig.savefig(out/(name+'.'+ext),dpi=180,facecolor='white')
        plt.close(fig)
    routes=d['buidl_routes']
    fig,axes=plt.subplots(1,len(routes),figsize=(12,6),squeeze=False)
    fig.subplots_adjust(top=.77,bottom=.26,wspace=.3)
    fig.suptitle('BUIDL: 특정 Circle 상환 경로의 실제 관측',fontsize=20,y=.96)
    maxval=max(max(r['holder_cash_usdc'],r['allowance_usdc'])/1e6 for r in routes)
    for ax,r in zip(axes[0],routes):
        vals=[r['allowance_usdc']/1e6,r['holder_cash_usdc']/1e6,r['necessary_condition_ceiling_usdc']/1e6]
        ax.bar(['승인 한도','보유 USDC','필요조건 상한'],vals,color=['#4d8dad','#b6c9cf','#a97147'])
        ax.set_ylim(0,maxval*1.24 if maxval else 1)
        ax.set_ylabel('백만 USDC')
        ax.set_title(f'{r["as_of"][:10] if r["as_of"] else "날짜 미확인"} · 블록 {r["block"]}\n정산 계약 중지: {"예" if r["settlement_paused"] else "아니오"}',fontsize=12)
        for i,v in enumerate(vals):ax.text(i,v+maxval*.035,f'{v:,.2f}',ha='center')
        ax.grid(axis='y',alpha=.15)
    fig.text(.5,.075,'상한 = 중지 시 0, 그 외 min(승인 한도, 보유 자금). 양수여도 실제 체결·접근 권한은 미확인.\n이 경로의 0을 BUIDL 전체 상환 중단이나 투자 손실로 해석할 수 없습니다.\n출처: 저장된 Ethereum 계약 상태 · data/buidl-route-state.json',ha='center',fontsize=10)
    save(fig,'01_buidl_route')
    rows=[r for r in d['observations'] if r['product']=='Lend East']
    blocks=sorted({r['block'] for r in rows})
    fig,ax=plt.subplots(figsize=(12,6));fig.subplots_adjust(top=.8,bottom=.29)
    fig.suptitle('Lend East: 대출 잔액과 미지급 원금의 관측점',fontsize=20,y=.96)
    labels=[]
    for i,b in enumerate(blocks):
        rr=[r for r in rows if r['block']==b];labels.append(rr[0]['as_of'][:10]+'\n'+str(b))
        for metric,offset,color,marker,label in [('credit_line_balance()',-.08,'#277c9b','o','대출 잔액'),('credit_line_principalOwed()',.08,'#b87536','x','미지급 원금')]:
            v=next((r['value'] for r in rr if r['metric']==metric),None)
            if v is not None:
                ax.scatter(i+offset,v/1e6,c=color,marker=marker,s=95,label=label if i==0 else None,zorder=3)
                ax.annotate(f'{v/1e6:.3f}',(i+offset,v/1e6),xytext=(-22 if offset<0 else 22,13 if offset<0 or v==0 else -23),textcoords='offset points',ha='center',fontsize=10,color=color)
    ax.set_xticks(range(len(blocks)),labels);ax.set_ylim(-.8,12);ax.set_xlim(-.4,len(blocks)-.6);ax.set_ylabel('백만 USDC');ax.legend(loc='center right');ax.grid(axis='y',alpha=.15)
    fig.text(.5,.07,'가로축은 선택한 관측점 순서이며 실제 시간 간격과 비례하지 않습니다. 관측 사이를 보간하지 않았습니다.\n미지급 원금은 계약 장부이며 실제 NAV·최종 손실·현금 회수액이 아닙니다.\n출처: data/history.json, data/chain.json · 주소 연결 추가 확인: data/nav-public.json',ha='center',fontsize=10)
    save(fig,'02_lendeast_observations')
    fig,ax=plt.subplots(figsize=(13,6));ax.axis('off')
    fig.suptitle('BUIDL · Lend East: 실측으로 확인한 범위',fontsize=20,y=.96)
    table=ax.table(cellText=[
        ['상품 장부','Ethereum 토큰 발행량','대출 잔액·미지급 원금'],
        ['출구 상태','특정 Circle 경로 상태 관측','청구권 체결·상환 경로 미확인'],
        ['신용 손실 자료','실현 손실 미확인','당시 예상 부족분 공지'],
        ['실제 NAV 괴리','미확인','미확인'],
        ['실현 거래 이익','미확인','미확인'],
        ['사건 기간 PoS 정상성','별도 검증 미수행','별도 검증 미수행'],
    ],colLabels=['검증 항목','BlackRock BUIDL','Goldfinch Lend East'],cellLoc='center',colWidths=[.24,.37,.39],bbox=[0,.15,1,.7])
    table.auto_set_font_size(False);table.set_fontsize(12)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#d5dde2')
        cell.set_facecolor('#ddeaf0' if row==0 else '#f6f8fa' if row%2 else 'white')
    fig.text(.5,.065,'미확인은 0 또는 안전을 뜻하지 않습니다. 동일 사건의 수익률·인과효과 비교가 아닙니다.\n실제 NAV·현금흐름·체결·합의 자료가 연결되어야 전체 명제를 검증할 수 있습니다.',ha='center',fontsize=11)
    save(fig,'03_empirical_comparison')
    navpath=results/'nav_verification.json'
    if navpath.exists():
        measured=json.loads(navpath.read_text())
        rows=[r for r in measured['nav_observations'] if r['nav_usd'] is not None]
        fig,axes=plt.subplots(1,2,figsize=(13,6));fig.subplots_adjust(top=.79,bottom=.28,wspace=.3)
        fig.suptitle('BUIDL: 실제 NAV 피드 값과 갱신 후 경과 시간',fontsize=19,y=.96)
        x=list(range(len(rows)));labels=[r['as_of'][5:10] for r in rows]
        axes[0].scatter(x,[r['nav_usd'] for r in rows],color='#287e9a',s=45)
        axes[0].set_ylim(.98,1.02);axes[0].set_ylabel('피드 값 · USD');axes[0].set_title('발행사 관련 NAV 전달값')
        axes[1].bar(x,[r['age_hours'] for r in rows],color='#7896ad');axes[1].set_ylabel('시간');axes[1].set_title('관측 시각 - 피드 updatedAt')
        for ax in axes:ax.set_xticks(x,labels,rotation=45);ax.grid(axis='y',alpha=.15)
        fig.text(.5,.06,'선택 블록의 관측값이며 일별 종가나 연속 시계열이 아닙니다.\n1달러 피드와 독립 시장 NAV의 차이는 미확인입니다. 갱신 후 경과 시간은 부실 반영 지연이 아닙니다.\n출처: RedStone BUIDL_FUNDAMENTAL · data/nav-public.json',ha='center',fontsize=10)
        save(fig,'04_buidl_nav_observed')
        p=measured['payment'];fig,ax=plt.subplots(figsize=(12,6));fig.subplots_adjust(top=.8,bottom=.29)
        fig.suptitle('Lend East: 확인한 USDC 유입의 원금·이자 반영',fontsize=19,y=.96)
        principal=p['principal_applied_usdc'];interest=p['interest_applied_usdc']
        ax.barh(['확인한 거래'],[principal],color='#287e9a',label='원금 반영')
        ax.barh(['확인한 거래'],[interest],left=[principal],color='#b77b4b',label='이자 반영')
        ax.text(principal/2,0,f'{principal:,.2f}',ha='center',va='center',color='white',fontsize=14)
        ax.text(principal+interest/2,0,f'{interest:,.2f}',ha='center',va='center',color='white',fontsize=12)
        ax.set_xlabel('USDC');ax.set_ylim(-1,1);ax.legend(loc='upper left');ax.grid(axis='x',alpha=.15)
        fig.text(.5,.07,'2025-01-09 거래 · 유입 826,881.78 USDC. 전체 기간 누적 회수액이 아닙니다.\n같은 거래의 Senior Pool 지급액은 GIP-67 보전금 공지와 일치합니다. 차입자 회수로 분류하지 않습니다.\n실제 NAV·최종 손실은 이 거래만으로 계산할 수 없습니다.',ha='center',fontsize=10)
        save(fig,'05_lendeast_verified_payment')
    print('Saved empirical PNG/SVG:',out)
