"""Strict validation of schemas_reviewed, with explicit partial/final audit states."""
import argparse
import json
from pathlib import Path

import fitz
import yaml

from review_1981_sources import ROOT, DEST, TABLES, digest, save


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result={}
    for key_node, value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key!r}, line {key_node.start_mark.line+1}')
        result[key]=loader.construct_object(value_node,deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def read_yaml(path):
    return yaml.load(path.read_text(encoding='utf-8'),Loader=UniqueLoader)


def validate_file(path, expected):
    data=read_yaml(path)
    assert data['source_year']==1981 and data['state']==path.parent.name
    assert data['format_id']==path.stem
    files=data['availability']['source_files']
    by_district={r['district']:r for r in expected}
    assert len(files)==len(by_district)==data['availability']['trimmed_pdf_count']
    assert len({r['district'] for r in files})==len(files)
    assert {r['district'] for r in files}==set(by_district)
    types=data['page_layout']['format_types']
    assignments=data['district_format_assignments']
    assigned=[d for districts in assignments.values() for d in districts]
    assert len(assigned)==len(set(assigned))
    assert set(types)==set(assignments)==set(data['column_definitions'])
    for typ,layout in types.items():
        assert layout['districts']==assignments[typ]
        assert layout['district_count']==len(assignments[typ])
        columns=data['column_definitions'][typ]
        ids=[r['column_no'] for r in columns]
        assert len(ids)==len(set(ids))==layout['logical_column_count']
        assert len({r['variable'] for r in columns})==len(ids)
        panel_ids=[r['panel_id'] for r in layout['panels']]
        assert len(panel_ids)==len(set(panel_ids))
        covered=set()
        for panel in layout['panels']:
            order=panel['column_definition_order']
            assert len(order)==len(panel['printed_columns'])
            assert set(order)<=set(ids)
            assert set(panel['identity_columns'])<=set(order)
            covered.update(order)
        assert covered==set(ids), (path,typ,'definition not covered by panels')
    pages=0
    for record in files:
        district=record['district']
        ref=by_district[district]
        assert record['output_path']==ref['output']
        pdf=ROOT/record['output_path']
        assert record['filename']==pdf.name
        assert record['sha256']==ref['sha256']==digest(pdf), pdf
        with fitz.open(pdf) as doc:
            count=len(doc)
        assert record['page_count']==ref['page_count']==count
        assert data['availability']['page_count_by_district'][district]==count
        seq=data['page_layout']['district_page_sequences'][district]
        assert [r['pdf_page'] for r in seq]==list(range(1,count+1))
        assert [r['source_pdf_page'] for r in seq]==ref['source_pages_selected']
        typ=record['format_type']
        if typ:
            assert district in assignments[typ]
        else:
            assert any(r['district']==district for r in data['review']['unresolved_records'])
        for page in seq:
            assert page.get('panels') or page.get('excluded') or page.get('unresolved')
            if page.get('panels'):
                assert set(page['panels'])<={p['panel_id'] for p in types[typ]['panels']}
        pages+=count
    assert pages==data['availability']['measured_pdf_page_count']
    assert data['availability']['verified_district_count']+data['availability']['unresolved_district_count']==len(files)
    assert data['availability']['unresolved_district_count']==len(data['review']['unresolved_records'])
    return {'yaml':str(path.relative_to(ROOT)).replace('\\','/'),'pdf_count':len(files),
            'page_count':pages,'format_type_count':len(types),
            'unresolved_records':data['review']['unresolved_records'],'validation':'pass'}


def regressions():
    out={}
    for fid in ['format_001','format_002']:
        path=DEST/'Arunachal Pradesh'/(fid+'.yaml')
        if not path.exists():
            out[fid+'_lohit']='not yet reviewed'
            continue
        d=read_yaml(path)
        typ=next(t for t,ds in d['district_format_assignments'].items() if 'Lohit' in ds)
        layout=d['page_layout']['format_types'][typ]
        if fid=='format_002':
            assert [p['column_definition_order'] for p in layout['panels']]==[list(range(1,11)),list(range(11,21))]
            assert len(d['page_layout']['district_page_sequences']['Lohit'])==1
        else:
            col=next(c for c in d['column_definitions'][typ] if c['variable']=='population')
            assert col['reference_year']==1981 and '1981' in col['column_name']
        out[fid+'_lohit']='pass'
    return out


def main(state=None, final=False, protect=False):
    preflight=json.loads((DEST/'_audit/preflight.json').read_text(encoding='utf-8'))
    allstates=sorted({r['state'] for r in preflight['entries']})
    assert len(allstates)==22
    assert sum(r['table']==TABLES[0] for r in preflight['entries'])==279
    assert sum(r['table']==TABLES[1] for r in preflight['entries'])==280
    summaries=[]
    for name in allstates:
        results=[]
        for category,table in enumerate(TABLES,1):
            path=DEST/name/f'format_{category:03d}.yaml'
            if not path.exists():
                results.append({'yaml':str(path.relative_to(ROOT)).replace('\\','/'),'validation':'not_created'})
            elif state is None or name==state:
                refs=[r for r in preflight['entries'] if r['state']==name and r['table']==table]
                results.append(validate_file(path,refs))
            else:
                previous=DEST/name/'review_record.json'
                results.extend([r for r in json.loads(previous.read_text())['schemas'] if r['yaml'].endswith(path.name)])
        complete=all(r['validation']=='pass' for r in results)
        summary={'state':name,'status':'reviewed' if complete else 'pending','schemas':results}
        summaries.append(summary)
        if complete and (state is None or name==state):
            save(DEST/name/'review_record.json',summary)
    protected='not checked this run'
    if protect or final:
        changed=[p for p,h in preflight['protected_files_sha256'].items() if not Path(p).exists() or digest(Path(p))!=h]
        assert not changed, changed
        protected=f"pass: {len(preflight['protected_files_sha256'])} protected files unchanged"
    audit={'scope_pdf_count':preflight['pdf_count'],'measured_page_count':preflight['page_count'],
           'completed_states':sum(s['status']=='reviewed' for s in summaries),
           'completed_yaml_count':sum(r['validation']=='pass' for s in summaries for r in s['schemas']),
           'protected_files':protected,'regressions':regressions(),
           'manifest_discrepancies':[r for r in preflight['entries'] if not r['manifest_count_matches']],
           'states':summaries}
    save(DEST/'_audit/progress.json',audit)
    lines=['# 1981 reviewed schema audit','',f"Reviewed states: {audit['completed_states']}/22; YAMLs: {audit['completed_yaml_count']}/44.",
           f"Inventory: 279 civic + 280 mededu PDFs; {preflight['page_count']} measured pages.",'',
           'Existing PDFs, old schemas and 1971 references are outside the write scope.','',
           '| State | Status | Civic PDFs/pages | Mededu PDFs/pages | Unresolved records |',
           '|---|---|---:|---:|---:|']
    for s in summaries:
        quantities=[f"{r['pdf_count']}/{r['page_count']}" if r['validation']=='pass' else 'pending' for r in s['schemas']]
        n=sum(len(r.get('unresolved_records',[])) for r in s['schemas'])
        lines.append(f"| {s['state']} | {s['status']} | {quantities[0]} | {quantities[1]} | {n if s['status']=='reviewed' else 'not assessed'} |")
    lines.extend(['','## Manifest discrepancy','',
                  'Bilaspur (Madhya Pradesh) mededu measures 4 pages. The legacy verification.output_pages field says 5; its source-page list has 4. The old manifest is preserved.','',
                  '## Validation scope','',
                  'Duplicate-key-safe YAML parsing, exact inventory coverage, PDF SHA-256 and measured page counts, page-sequence coverage, column/panel cross-references and Lohit regression checks. Visual decisions are documented separately; structural validation alone does not establish visual correctness.','',str(protected),''])
    (DEST/'AUDIT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k not in ['states','manifest_discrepancies']},indent=2))
    if final:
        assert audit['completed_yaml_count']==44 and audit['completed_states']==22
        assert set(audit['regressions'].values())=={'pass'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state')
    p.add_argument('--final',action='store_true')
    p.add_argument('--protect',action='store_true')
    a=p.parse_args()
    main(a.state,a.final,a.protect)
