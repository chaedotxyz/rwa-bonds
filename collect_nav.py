"""Read-only public RPC collection. Requires curl; never sends a transaction."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
FEED='0xb9BD795BB71012c0F3cd1D9c9A4c686F2d3524A4'
POOL='0xb26b42dd5771689d0a7faeea32825ff9710b9c11'
CREDIT='0x5424b911d04f71357468743b24b868db0706048c'

def rpc(method,params,url='https://eth.drpc.org'):
    if method not in {'eth_call','eth_getBlockByNumber','eth_getLogs','eth_getTransactionReceipt'}:
        raise ValueError('Read-only method required')
    request=dict(jsonrpc='2.0',id=1,method=method,params=params)
    p=subprocess.run(['curl','-fSs','--max-time','25',url,'-H','Content-Type: application/json','--data-binary','@-'],input=json.dumps(request),capture_output=True,text=True)
    if p.returncode:
        return dict(request=request,rpc=url,result=None,error=p.stderr.strip())
    try:r=json.loads(p.stdout)
    except ValueError:r={'error':'Invalid JSON response'}
    return dict(request=request,rpc=url,result=r.get('result'),error=r.get('error'))

def call(address,selector,block):
    return rpc('eth_call',[dict(to=address,data=selector),hex(block)])

def snapshot(block):
    return dict(block_number=block,header=rpc('eth_getBlockByNumber',[hex(block),False]),
        nav=call(FEED,'0xfeaf968c',block),decimals=call(FEED,'0x313ce567',block),
        pool_credit_line=call(POOL,'0x47195e13',block),
        balance=call(CREDIT,'0xb69ef8a8',block),principal_owed=call(CREDIT,'0x19350114',block))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'data/nav-public.json')
    a=parser.parse_args()
    finalized=rpc('eth_getBlockByNumber',['finalized',False],'https://ethereum-rpc.publicnode.com')
    if not finalized['result']:raise SystemExit(str(finalized['error']))
    end=int(finalized['result']['number'],16)
    # Block intervals are explicit, not claimed to be exact daily UTC closes.
    blocks=sorted({end-7200*i for i in range(8)}|{19560000,19660000,19760000})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        rows=list(executor.map(snapshot,blocks))
    doc=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),feed_address=FEED,
        feed_source='https://app.redstone.finance/push-feeds?cryptos=BUIDL_FUNDAMENTAL',
        finalized_at_collection=finalized,description=call(FEED,'0x7284e416',end),snapshots=rows,
        limitations=['NAV feed is issuer-related, not independent market NAV.',
            'Finalized snapshot is not a historical consensus-health audit.',
            'Block-spaced observations are not a complete time series.'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    if a.out.resolve().parent==(ROOT/'data').resolve():
        cpath=ROOT/'data/checksums.json';c=json.loads(cpath.read_text())
        c[a.out.name]=hashlib.sha256(a.out.read_bytes()).hexdigest()
        cpath.write_text(json.dumps(c,indent=2)+'\n')
    print('Saved',len(rows),'observations:',a.out)
    print('Failed/empty NAV observations:',sum(r['nav']['result'] in (None,'0x') for r in rows))

if __name__=='__main__':main()
