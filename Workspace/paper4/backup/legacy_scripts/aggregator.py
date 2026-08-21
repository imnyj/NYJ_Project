import csv, glob, os
from collections import defaultdict
DATA_DIR = 'g:/내 드라이브/개인 자료/YoungjuNam/paper-ai.v1/papers/paper4/paper/data'
COLS = ['method','scenario','seed','runtime_sec','n_cam_events','CBR_mean','AoI_mean','PDR_mean','energy_efficiency','ETSI_compliance']

rows_all = []
for path in sorted(glob.glob(os.path.join(DATA_DIR, 'main_*_urban.csv'))):
    if 'combined' in path: continue
    with open(path) as f:
        for r in csv.DictReader(f):
            rows_all.append(r)

groups = defaultdict(list)
for r in rows_all: groups[r['method']].append(r)

print('method     |   AoI_mean |   CBR_mean | PDR_mean |    n_cam |   ETSI |     EE')
print('-' * 85)
for method in sorted(groups.keys()):
    rs = groups[method]
    def mean(k):
        vs = [float(r[k]) for r in rs if r[k] not in (None,'','None')]
        return sum(vs)/len(vs) if vs else float('nan')
    print(f'{method:<10} | {mean("AoI_mean"):>10.2f} | {mean("CBR_mean"):>10.4f} | {mean("PDR_mean"):>8.2f} | {mean("n_cam_events"):>8.0f} | {mean("ETSI_compliance"):>6.3f} | {mean("energy_efficiency"):>6.3f}')
