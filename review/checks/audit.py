# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only arithmetic audit of processed outputs; prints counts for methodology review."""
from pathlib import Path
import csv, json, collections, datetime
p=Path(__file__).resolve().parents[3]/'southwest-solar-siting'/'data'/'processed'
def rows(path):
    with open(path, newline='') as f: return list(csv.DictReader(f))
grid=p/'grid'; infra=p/'infra'; land=p/'land'
q=rows(grid/'queue_projects.csv'); a=[r for r in q if r['status']=='active']; c=rows(grid/'queue_by_county.csv')
print('queue rows/active/unique IDs',len(q),len(a),len({r['queue_id'] for r in q}))
print('active MW total / solar / storage',*[round(sum(float(r[k] or 0) for r in a),1) for k in ['mw','mw_solar','mw_storage']])
print('active matched POI',sum(bool(r['poi_sub_id']) for r in a),'active missing county',sum(not r['county'] for r in a))
print('county active MW sum',round(sum(float(r['active_mw_total']) for r in c),1))
print('county active sum solar+storage',round(sum(float(r['active_mw_solar'])+float(r['active_mw_storage']) for r in c),1))
print('hybrid active',sum(r['type']=='hybrid' for r in a),'MW',round(sum(float(r['mw'] or 0) for r in a if r['type']=='hybrid'),1))
print('county missing sentinel rows',sum(r['county']=='(county not reported)' for r in c))
for name in ['transmission_lines','substations']:
 m=json.loads((grid/'MANIFEST.json').read_text()); x=next(x for x in m['layers'] if x['layer']==name); s=x['stats']; print(name,'records',x['record_count'],'unknown',s['by_volt_class']['unknown'],'share',round(s['by_volt_class']['unknown']/x['record_count']*100,2),'state',s['by_state'])
print('substation raw last data edit UTC',datetime.datetime.fromtimestamp(json.loads((Path(__file__).resolve().parents[3]/'southwest-solar-siting'/'data/raw/grid/hifld_substations/_complete.json').read_text())['layer_meta']['editingInfo']['dataLastEditDate']/1000,datetime.timezone.utc).isoformat())
f=json.loads((infra/'MANIFEST.json').read_text()); fi=next(x for x in f if x['layer']=='fiber'); print('fiber',fi['counts_by_basis'],'proxies',sum(v for k,v in fi['counts_by_basis'].items() if k!='osm_fiber_tagged'),'of',fi['record_count'])
r=rows(infra/'blm_solar_row_cases.csv'); print('ROW table total/active/no coord',len(r),sum(x['active'].lower()=='true' for x in r),sum(not x['centroid_lat'] for x in r)); print('active cases by type',collections.Counter(x['case_type'] for x in r if x['active'].lower()=='true'))
l=json.loads((land/'MANIFEST.json').read_text()); print('land counts',[(x['layer'],x['record_count']) for x in l if x['layer'] in ['blm_solar_available','solar_energy_zones','ownership','exclusion_wetlands']])
