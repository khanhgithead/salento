# Copyright 2017 Rice University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import itertools
import math
import numpy as np

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('kld_out', type=str, nargs=1,
                       help='kld.out file')
    argparser.add_argument('--topk', type=float, default=None,
                       help='sort top-k% of KLD values and print the top KLD from each package')
    argparser.add_argument('--plot', type=str, default=None,
           help='outfile for plotting all KLDs on a heat map, drawing a cutoff line if --topk is used')
    argparser.add_argument('--compare', type=str, default=None,
                       help='compare with the given kld.out')
    argparser.add_argument('--hexes', action='store_true',
                       help='print the hex colors of the KLDs into a file')
    args = argparser.parse_args()
    if args.topk is None and args.plot is None and args.compare is None and not args.hexes:
        argparser.error('Provide at least one option')

    print(args)
    cutoff = 0
    klds = read_klds(args.kld_out[0])

    if args.topk is not None:
        cutoff = do_topk(klds, args.topk)
    if args.plot:
        do_plot(klds, args.plot, cutoff)
    if args.compare is not None:
        klds2 = read_klds(args.compare)
        do_compare(klds, klds2)
    if args.hexes:
        do_hexes(klds)

def do_hexes(klds):
    from matplotlib.colors import PowerNorm, rgb2hex
    from matplotlib.cm import ScalarMappable
    klds = to_dict(klds)
    for pack in klds:
        m = ScalarMappable(norm=PowerNorm(math.e, vmin=0), cmap='OrRd')
        loc, k = zip(*sorted(klds[pack].items(), key=lambda x:x[1], reverse=True))
        hexes = [rgb2hex(c) for c in m.to_rgba(k)]
        print("### " + pack)
        for i, l in enumerate(loc):
            print('  {:35s} : {:.2f} : {:7s}'.format(l, klds[pack][l], hexes[i]))

def do_plot(klds, plotfile, cutoff):
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    x = np.array(range(len(klds)))
    y = np.array([kld for (_, _, kld) in klds])
    plt.hist2d(x, y, bins=[20,20], norm=Normalize(vmin=1, vmax=50), cmap='gray_r')
    plt.colorbar()
    plt.xlabel('Program models', fontsize='large')
    plt.ylabel('Anomaly scores', fontsize='large')
    if cutoff > 0:
        plt.axhline(cutoff, color='r', linewidth=2)
    plt.savefig(plotfile, bbox_inches='tight')

def do_topk(klds, topk):
    top_klds = sorted(klds, key=lambda x: -x[2])[:int(np.ceil(len(klds) * topk / 100))]
    packs, t = [], []
    for p, l, k in top_klds:
        if p not in packs:
            packs += [p]
            t += [(p,l, k)]
    top_klds = t
    print('\n'.join(['{} {} {}'.format(p, l, k) for p, l, k in top_klds]))
    return top_klds[-1][2]

def to_dict(klds):
    packs = [pack for pack, _ in itertools.groupby(klds, lambda x: x[0])]
    locs = [list(filter(lambda x: x[0] == pack, klds)) for pack in packs]
    locs = [list(map(lambda x: (x[1], x[2]), loc)) for loc in locs]
    dic = { pack : dict(loc) for pack, loc in zip(packs, locs) }
    return dic

def do_compare(klds, klds2):
    klds = to_dict(klds)
    klds2 = to_dict(klds2)

    for pack in klds:
        if pack not in klds2:
            continue
        print('### ' + pack)
        for loc in klds[pack]:
            if loc not in klds2[pack]:
                continue
            kld1 = klds[pack][loc]
            kld2 = klds2[pack][loc]
            mag = kld2 / kld1
            print('  {:35s} : {:.2f} : {:.2f} : {:.2f}'.format(loc, kld1, kld2, mag))

def read_klds(outfile):
    klds = [] # list of triples (package, location, kld)
    with open(outfile) as f:
        for line in f:
            if line.startswith('###'):
                pack = line.split('### ')[1].rstrip('\n')
            elif line.startswith('  '):
                loc = line.split(':')[0].strip()
                kld = float(line.split(':')[1])
                klds.append((pack, loc, kld))
    return klds

if __name__ == '__main__':
    main()
