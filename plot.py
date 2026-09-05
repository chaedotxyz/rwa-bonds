"""Plot saved B-1/B-2/B-3 results; does not silently change inputs or resample."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--conditional',action='store_true',help='Explicitly plot assumption-based appendix')
    p.add_argument('--results',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    a.results=a.results or ROOT/('results/conditional' if a.conditional else 'results')
    a.out=a.out or ROOT/('figures/conditional' if a.conditional else 'figures/empirical')
    a.out.mkdir(parents=True,exist_ok=True)
    font=Path('/System/Library/Fonts/AppleSDGothicNeo.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    else:
        names={f.name for f in font_manager.fontManager.ttflist}
        for n in ['Noto Sans CJK KR','NanumGothic','Malgun Gothic']:
            if n in names:plt.rcParams['font.family']=n;break
        else:raise SystemExit('Install a Korean font: Noto Sans CJK KR or NanumGothic.')
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,'svg.fonttype':'path','axes.spines.top':False,'axes.spines.right':False})
    if not a.conditional:
        from src.empirical_plot import plot
        plot(a.results,a.out)
        return
    d=json.loads((a.results/'manifest.json').read_text())
    def save(fig,name):
        for ext in ['png','svg']:fig.savefig(a.out/(name+'.'+ext),dpi=180)
        plt.close(fig)
    points=d['point_results']
    fig,axes=plt.subplots(1,3,figsize=(14,6));fig.subplots_adjust(top=.77,bottom=.22,wspace=.34)
    fig.suptitle('B-1 · B-2 · B-3: 이익과 비용을 분리한 조건부 판정',fontsize=18,y=.96)
    for ax,z,title in zip(axes,points,['국채 · 합의 비용','신용 · NAV 지연','동일 신용 · 합의 대조']):
        vals=[z[k]/1e6 for k in ['pfc_usd','coc_usd','net_profit_usd']]
        bars=ax.bar(['PfC','CoC','순이익'],vals,color=['#2778A6','#BD743A','#7A50A8'])
        ax.axhline(0,color='#333',linewidth=.7);ax.set_title(z['scenario']+' '+title);ax.set_ylabel('백만 달러')
        span=max(vals)-min(vals);span=max(span,1)
        ax.set_ylim(min(0,min(vals))-.2*span,max(0,max(vals))+.2*span)
        for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+(1 if v>=0 else -1)*span*.03,f'{v:,.2f}',ha='center',va='bottom' if v>=0 else 'top')
        ax.grid(axis='y',alpha=.18)
    fig.text(.5,.075,'패널별 세로축 범위가 다릅니다. 지분 확보 자본 전액은 CoC에서 제외하고 조달비·기대손실만 반영했습니다.\n실제 공격·출구 검증 결과가 아니라 선언한 NAV·재원·제재손실 가정 아래의 계산입니다.',ha='center',fontsize=10)
    save(fig,'01_cost_profit')
    with (a.results/'nav_path.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    b2=[z for z in rows if z['scenario']=='B-2'];b3=[z for z in rows if z['scenario']=='B-3']
    cfg=d['inputs']['groups']['credit'];grace=cfg['grace_days']['value'];end=grace+cfg['write_down_days']['value']
    fig,axes=plt.subplots(1,2,figsize=(13,6));fig.subplots_adjust(top=.78,bottom=.23,wspace=.3)
    fig.suptitle('신용: 부실 반영 지연이 만드는 NAV 창',fontsize=18,y=.96)
    x=[float(z['action_day']) for z in b2]
    axes[0].plot(x,[float(z['mark']) for z in b2],label='정산 시점 소비자 NAV',color='#2978A0')
    axes[0].plot(x,[float(z['fair']) for z in b2],label='경제적 가치 대용',color='#A36828',linestyle='--')
    axes[0].set(ylabel='액면 1단위당 가치',xlabel='부실 후 거래 시작일',title='부실을 늦게 반영하는 소비자 NAV')
    for series,label,color in [(b2,'B-2 순이익','#2978A0'),(b3,'B-3 순이익','#90519D')]:
        axes[1].plot(x,[float(z['net_profit_usd']) for z in series],label=label,color=color)
    axes[1].set_yscale('symlog',linthresh=10000)
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v,pos: f'{v:.0e}' if abs(v)>=10000 else f'{v:g}'))
    axes[1].axhline(0,color='#444',linewidth=.8)
    axes[1].set(ylabel='순이익 USD · 부호 보존 로그축',xlabel='부실 후 거래 시작일',title='같은 신용 이익에 다른 경로 비용')
    for ax in axes:ax.legend(fontsize=9);ax.grid(alpha=.18)
    fig.text(.5,.07,f'grace {grace:g}일 + 선형 NAV 조정 {end-grace:g}일은 보고서에서 가져온 시나리오 가정입니다.\n실제 Lend East/FIDU NAV 반영 시계열이 아닙니다. 거래 실행기간을 더한 정산 시점의 NAV를 사용합니다.',ha='center',fontsize=10)
    save(fig,'02_nav_window')
    summary=d['sample_summary'];fig,ax=plt.subplots(figsize=(10,6));fig.subplots_adjust(top=.79,bottom=.24)
    fig.suptitle('선언한 파라미터 공간에서 순이익이 양수인 표본',fontsize=17,y=.96)
    y=[s['positive_sample_fraction']*100 for s in summary]
    ax.bar([s['scenario'] for s in summary],y,color=['#2778A6','#90519D','#2778A6'],width=.5)
    ax.set_ylim(0,110);ax.set_ylabel('양의 순이익 표본 비율 (%)');ax.grid(axis='y',alpha=.18)
    for i,v in enumerate(y):ax.text(i,v+2,f'{v:.2f}%',ha='center')
    fig.text(.5,.065,f"LHS {d['runtime_samples']:,}표본 / 시나리오 · seed {d['seed']} · 범위와 균등 주변분포는 config에 명시\n현실 공격 확률이 아니며 원본 보고서의 61.7%를 재현하거나 보정한 결과가 아닙니다.",ha='center',fontsize=10)
    save(fig,'03_parameter_space')
    print('Saved PNG/SVG charts:',a.out)
if __name__=='__main__':main()
