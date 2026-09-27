"""Tier: 1. Build outcome-blind six-filing human-first ownership/identity pilot.
Inputs: frozen factual bundles and readiness receipts; no returns or model answers.
Outputs: immutable selection/evidence, blank browser worksheets, exportable answers.
Identity: six distinct issuer candidates, two per mechanical sampling stratum;
all evidence bytes agree with extraction receipts. Run: project Python this file.
"""
import gzip
import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'research/runs/phase2-overnight/20260924-full-v1'
AUDIT = ROOT / 'research/runs/phase2-readiness/20260924-full-v1'
OUT = ROOT / 'review/drafts/ownership-identity-pilot-20260925'
RUN = ROOT / 'research/runs/phase2-identity-pilot/20260925-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze(path, raw):
    raw = raw.encode() if isinstance(raw, str) else raw
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Refusing changed pilot bytes: ' + str(path)
    else:
        path.write_bytes(raw)


def encode(obj):
    return json.dumps(obj, indent=2, sort_keys=True) + '\n'


STYLE = 'body{max-width:1050px;margin:25px auto;padding:18px;font:17px/1.55 system-ui;color:#183044}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.6 monospace;background:#f5f7fa;padding:18px}textarea{width:100%;min-height:135px;font:16px/1.5 system-ui}label{display:block;margin-top:22px}button{padding:12px;margin:12px 8px 12px 0}details{border:1px solid #ccd5de;padding:14px;margin:12px 0}small{overflow-wrap:anywhere}input[type=text]{width:90%;padding:10px}'


def page(title, body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + escape(title) + '</title><style>' + STYLE + '</style><body><h1>' + escape(title) + '</h1>' + body + '</body></html>'


def main():
    selection = json.loads((SRC / 'selection.json').read_text())
    pools = {s: [] for s in ['multiple_people_complete_percentages', 'multiple_people_incomplete_percentages', 'single_person_incomplete_percentages']}
    for s in selection:
        a = s['accession']
        r = json.loads((AUDIT / 'receipts' / (a + '.json')).read_text())
        n = r.get('reporting_person_rows', 0)
        complete = r.get('ownership', {}).get('percent_of_class', {}).get('all_present', False)
        stratum = ('multiple_people_complete_percentages' if complete else 'multiple_people_incomplete_percentages') if n >= 2 else ('single_person_incomplete_percentages' if n == 1 and not complete else None)
        if stratum:
            pools[stratum].append(s)
    chosen, used = [], set()
    for stratum, pool in pools.items():
        for era in ['early', 'recent']:
            candidates = [s for s in pool if (s['accepted'][:4] <= '2020') == (era == 'early')]
            for s in sorted(candidates, key=lambda s: sha(('identity-pilot-v1:' + s['accession']).encode())):
                a = s['accession']
                facts = json.loads(gzip.decompress((SRC / 'facts' / (a + '.json.gz')).read_bytes()))
                issuers = [r['cik']['value'] for r in facts['issuers'] if r['cik']['status'] == 'present']
                if len(issuers) == 1 and issuers[0] not in used:
                    used.add(issuers[0])
                    chosen.append({**s, 'stratum': stratum, 'era': era, 'issuer_cik': issuers[0]})
                    break
            else:
                raise ValueError('Unfilled stratum')
    assert len(chosen) == len(used) == 6
    assert all(s['accepted'][:4] <= '2025' for s in chosen)
    assert all(sum(s['stratum'] == k for s in chosen) == 2 for k in pools)
    manifest, links = [], []
    for i, s in enumerate(chosen, 1):
        a = s['accession']
        raw = (SRC / 'bundles' / (a + '.json.gz')).read_bytes()
        receipt = json.loads((SRC / 'receipts' / (a + '.json')).read_text())
        assert sha(raw) == receipt['bundle_sha256']
        bundle = json.loads(gzip.decompress(raw))
        freeze(OUT / 'bundles' / (a + '.json.gz'), raw)
        doc_html = ''
        for j, d in enumerate(bundle['documents']):
            text = d.get('text')
            if text is not None:
                assert sha(text.encode()) == d['text_sha256']
            doc_html += '<details><summary>' + escape(str(d['document_id']) + ' — ' + str(d.get('type')) + ' — ' + str(d.get('filename'))) + '</summary><small>Document SHA-256: ' + escape(str(d.get('text_sha256'))) + '</small><pre id="doc' + str(j) + '" data-document="' + escape(d['document_id'], quote=True) + '" data-sha="' + escape(str(d.get('text_sha256')), quote=True) + '">' + escape(text if text is not None else 'Binary attachment: not converted. This is an evidence gap; consult the original submission.') + '</pre></details>'
        body = '<p><a href="index.html">All six cases</a></p><p><strong>Unreviewed human reference. No model answers or returns are included.</strong></p><p>Accession: ' + a + ' · Filed: ' + escape(bundle['filing_date']) + '</p><p>Read the full source, including ownership footnotes and relevant exhibits. Search within expanded documents using your browser. If the evidence is insufficient, explain what cannot be determined. Similar names and equal share counts alone do not establish common control or overlapping ownership.</p><p><a href="' + escape(bundle['source_url'], quote=True) + '">Original SEC submission</a> · <a href="bundles/' + a + '.json.gz">Preserved evidence bundle</a></p>'
        body += '<h2>Source documents</h2>' + doc_html
        body += '<h2>Your independent reading</h2><p>Select an exact passage in a source document and click Capture evidence to record its document and character offsets. The saved quotation can support your answers below.</p><button onclick="capture()">Capture evidence</button><label>Reviewer name<input id="reviewer" type="text"></label>'
        questions = [('identities', '1. Who are the reporting parties, and what does the filing establish about their roles and relationships?'), ('ownership', '2. What shares and percentages does each party report? Does the filing establish any overlap, separate holdings, or uncertainty?'), ('limits', '3. What remains unresolved, and what additional evidence would be needed?'), ('evidence', 'Supporting passages (captured quotes or your source references)')]
        for key, question in questions:
            body += '<label for="' + key + '">' + escape(question) + '</label><textarea id="' + key + '"></textarea>'
        body += '<label><input type="checkbox" id="reviewed"> I completed my independent reading before seeing any model answer.</label><button onclick="downloadAnswer()">Download completed human answer</button><button onclick="saveDraft()">Save draft in this browser</button><p id="status" role="status"></p><p>Download is the durable handoff. Browser drafts may not persist across browsers or devices. Your answers are not automatically sent to the project.</p>'
        config = json.dumps(dict(accession=a, bundle_sha256=sha(raw), source_sha256=bundle['source_sha256'], protocol='ownership-identity-pilot-v1', stage='human_reference')).replace('<', '\\u003c')
        body += '''<script>
const config=CONFIG;const ids=['reviewer','identities','ownership','limits','evidence'];const key='identity-human-v1:'+config.accession;
function collect(){let a={...config,reviewed:document.getElementById('reviewed').checked};for(const id of ids)a[id]=document.getElementById(id).value;return a;}
function saveDraft(){try{localStorage.setItem(key,JSON.stringify(collect()));document.getElementById('status').textContent='Draft saved in this browser. Download when complete.';}catch(e){document.getElementById('status').textContent='Browser storage unavailable. Download your answer to preserve it.';}}
function capture(){const s=window.getSelection();if(!s.rangeCount||s.isCollapsed)return;const r=s.getRangeAt(0);let node=r.commonAncestorContainer;let p=(node.nodeType===1?node:node.parentElement).closest('pre[data-document]');if(!p){document.getElementById('status').textContent='Select text inside a single source document.';return;}let before=r.cloneRange();before.selectNodeContents(p);before.setEnd(r.startContainer,r.startOffset);let start=Array.from(before.toString()).length;let quote=r.toString();let ev={document_id:p.dataset.document,text_sha256:p.dataset.sha,start:start,end:start+Array.from(quote).length,quote:quote};document.getElementById('evidence').value+=JSON.stringify(ev,null,2)+'\\n';document.getElementById('status').textContent='Evidence captured.';}
function downloadAnswer(){const a=collect();if(!a.reviewed||ids.some(id=>!a[id].trim())){document.getElementById('status').textContent='Complete all answers and reviewer name, include evidence, and check the independent-review box. Describe uncertainty rather than guessing.';return;}a.reviewed_at_utc=new Date().toISOString();const u=URL.createObjectURL(new Blob([JSON.stringify(a,null,2)+'\\n'],{type:'application/json'}));const link=document.createElement('a');link.href=u;link.download=config.accession+'-human-answer.json';link.click();setTimeout(()=>URL.revokeObjectURL(u),1000);saveDraft();}
try{const saved=JSON.parse(localStorage.getItem(key));if(saved){for(const id of ids)document.getElementById(id).value=saved[id]||'';document.getElementById('reviewed').checked=!!saved.reviewed;}}catch(e){}
</script>'''.replace('CONFIG', config)
        rendered = page('Ownership and identity — case ' + str(i), body)
        assert all('<textarea id="' + key + '"></textarea>' in rendered for key, _ in questions)
        freeze(OUT / (a + '.html'), rendered)
        links.append('<li><a href="' + a + '.html">Case ' + str(i) + ' — ' + bundle['filing_date'] + '</a></li>')
        manifest.append({**s, 'bundle_sha256': sha(raw), 'page_sha256': sha(rendered.encode())})
    index = page('Ownership and identity: six-case pilot', '<p><strong>Stage: independent human review; NLP comparison pending.</strong></p><p>Can NLP help distinguish the actual share position from related reporting parties? Start with case 1. Read the source, answer three questions, capture evidence and download your answer. A completed case can then be frozen before a separate model interpretation is produced.</p><p>The six cases were selected using mechanical extraction conditions and filing era, without returns or investor success. They are a deliberately varied development sample, not a representative accuracy test. No suggested interpretations are included.</p><ol>' + ''.join(links) + '</ol><p>Uncertainty is a valid answer. No later amendments or outside campaign knowledge should fill gaps in the original disclosure. Existing human review packs remain unchanged.</p>')
    freeze(OUT / 'index.html', index)
    freeze(RUN / 'selection.json', encode(manifest))
    freeze(RUN / 'build_identity_pilot.py', Path(__file__).read_bytes())
    freeze(RUN / 'checks.json', encode(dict(cases=6, distinct_issuers=6, per_stratum=2, canonical_and_bundle_hashes='passed', blank_answer_fields='passed', model_answers_created=0, outcome_data_read=False)))
    print(encode(dict(pack=str(OUT / 'index.html'), first_case=str(OUT / (chosen[0]['accession'] + '.html')), checks='passed')))


if __name__ == '__main__':
    main()
