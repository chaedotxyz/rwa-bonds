"""Default: product evidence. Prior assumptions require explicit --conditional."""
import argparse
from pathlib import Path
from src.inputs import ROOT
from src.empirical import generate as generate_empirical
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'results')
    p.add_argument('--conditional',action='store_true')
    p.add_argument('--config',type=Path,default=ROOT/'config/scenarios.json')
    p.add_argument('--samples',type=int,default=None)
    a=p.parse_args()
    if a.conditional:
        from src.reporting import generate
        print(generate(a.config,a.out/'conditional',a.samples))
    else:
        if a.samples is not None:p.error('--samples requires --conditional')
        generate_empirical(a.out)
        from src.nav_results import generate as generate_nav
        print(generate_nav(a.out))
