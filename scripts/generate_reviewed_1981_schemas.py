"""Generate reviewed YAMLs only from explicit, state-specific review decisions.

Never reads old schemas as content, never invents district layouts, and never writes
outside schemas_reviewed. Review decisions must explicitly account for every PDF page.
"""
import argparse
import copy
import json
import re
from pathlib import Path

import yaml

from review_1981_sources import ROOT, DEST, inventory


class ReviewDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def generate(state, category):
    fid = f'format_{category:03d}'
    review = load(DEST / '_review' / state / (fid + '.json'))
    evidence = load(DEST / '_evidence' / state / (fid + '.json'))
    profiles = load(DEST / '_review/column_profiles.json')
    assert set(review['districts']) == {r['district'] for r in evidence}
    assignments = {k: [] for k in review['types']}
    files = []
    page_counts = {}
    sequences = {}
    unresolved = []
    for item in evidence:
        district = item['district']
        decision = review['districts'][district]
        typ = decision.get('format_type')
        if typ:
            assignments[typ].append(district)
        else:
            assert decision.get('unresolved'), district
        assert len(decision['pages']) == len(item['pages']), district
        pages = []
        for i, spec in enumerate(decision['pages']):
            if isinstance(spec, str):
                spec = {'panels':spec.split(), 'region':'table area'}
            entry = {'pdf_page':i+1, 'source_pdf_page':item['pages'][i]['source_page'],
                     'review_status':'verified', **spec}
            if entry.get('unresolved'):
                entry['review_status'] = 'unresolved'
            assert entry.get('panels') or entry.get('excluded') or entry.get('unresolved'), (district, i+1)
            for panel in entry.get('panels', []):
                assert panel in review['types'][typ]['panels'], (district, panel)
            pages.append(entry)
        page_counts[district] = len(pages)
        file_record = {'district':district, 'filename':Path(item['output']).name,
                       'output_path':item['output'], 'page_count':len(pages),
                       'sha256':item['sha256'], 'source_volume':item['source'],
                       'source_pages_selected':item['source_pages_selected'],
                       'format_type':typ, 'review_status':'unresolved' if decision.get('unresolved') else 'verified'}
        if decision.get('notes'): file_record['notes'] = decision['notes']
        if decision.get('wording_variations'): file_record['wording_variations'] = decision['wording_variations']
        if decision.get('unresolved'):
            unresolved.append({'district':district, 'reason':decision['unresolved']})
        files.append(file_record)
        sequences[district] = pages
    layouts = {}
    definitions = {}
    for typ, config in review['types'].items():
        columns = copy.deepcopy(profiles[config['column_profile']])
        for column in columns:
            column.update(config.get('column_overrides', {}).get(str(column['column_no']), {}))
        definitions[typ] = columns
        panels = []
        for panel_id, panel in config['panels'].items():
            panels.append({'panel_id':panel_id, **panel,
                           'column_definition_order':panel['printed_columns'],
                           'identity_columns':[n for n in panel['printed_columns'] if n in config.get('identity_columns',[1,2])]})
        layouts[typ] = {'districts':assignments[typ], 'district_count':len(assignments[typ]),
                        'logical_column_count':len(columns), 'arrangement':config['arrangement'],
                        'panels':panels, 'notes':config.get('notes',[])}
    result = {'format_id':fid, 'name':f"{review['table_key']}_1981_{re.sub('[^a-z0-9]+','_',state.lower()).strip('_')}",
              'state':state, 'source_year':1981, 'table':review['table'],
              'printed_table_title':review['title'], 'table_description':review['description'],
              'district_format_assignments':assignments,
              'availability':{'trimmed_pdf_count':len(files), 'district_count':len(files),
                              'measured_pdf_page_count':sum(page_counts.values()),
                              'verified_district_count':len(files)-len(unresolved),
                              'unresolved_district_count':len(unresolved),
                              'page_count_by_district':page_counts, 'source_files':files},
              'page_layout':{'page_numbering':'All PDF page numbers are 1-based; panel order is physical printed order.',
                             'format_types':layouts, 'district_page_sequences':sequences},
              'column_definitions':definitions, 'format_notes':review['format_notes'],
              'review':{'method':review['review_method'],
                         'evidence_file':str((DEST/'_evidence'/state/(fid+'.json')).relative_to(ROOT)).replace('\\','/'),
                         'decision_file':str((DEST/'_review'/state/(fid+'.json')).relative_to(ROOT)).replace('\\','/'),
                         'unresolved_records':unresolved,
                         'scope_note':'Schema/layout review, not a transcription or validation of every numeric town value.'}}
    out=DEST/state/(fid+'.yaml')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(yaml.dump(result,Dumper=ReviewDumper,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
    print(f'{out}: {len(files)} PDFs, {sum(page_counts.values())} pages, {len(layouts)} layout types')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',required=True)
    parser.add_argument('--category',type=int,choices=[1,2])
    args=parser.parse_args()
    for category in ([args.category] if args.category else [1,2]):
        generate(args.state,category)
