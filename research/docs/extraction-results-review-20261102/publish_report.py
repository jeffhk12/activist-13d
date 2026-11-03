"""Publish the completed review into active project navigation and Downloads.
Inputs: rendered report, QA receipts, active navigation. Outputs: surgical links,
navigation snapshots, verification.json and byte-identical Downloads PDF.
Identity: all 2,394 recorded research inputs retain their original hashes.
Tier: 1 publication/integrity. Run only after visual review; project Python FILE.
"""
import hashlib
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path('/Users/jefflu/Projects/activist-13d')
HERE=Path(__file__).resolve().parent
PDF_NAME='13D_Extraction_Results_and_Methods_20261102.pdf'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.hrefs.extend(value for key,value in attrs if key=='href')


def main():
    qa=json.loads((HERE/'qa-results.json').read_bytes())
    ui=json.loads((HERE/'ui-test-results.json').read_bytes())
    visual=json.loads((HERE/'visual-review.json').read_bytes())
    assert ui['passed'] and visual['passed'] and visual['pdf_sha256']==sha(HERE/PDF_NAME)
    assert qa['broken_links']==0 and qa['pdf_pages']==25
    a=json.loads((HERE/'analysis.json').read_bytes())
    for name,expected in a['input_sha256'].items():assert sha(ROOT/name)==expected,name
    paths=[ROOT/'START-HERE.html',ROOT/'research/docs/ml-checkpoints.html',ROOT/'research/docs/PROJECT-PLAN.md']
    before=HERE/'navigation-before';before.mkdir(exist_ok=True)
    for path in paths:
        copy=before/path.name
        if not copy.exists():copy.write_bytes(path.read_bytes())
    marker='<!-- extraction-results-review-20261102 -->'
    home=paths[0].read_text()
    block='''<!-- extraction-results-review-20261102 --><section><h2>Current: extraction results and methods review - November 2</h2><p>The eligible extraction collection is complete: 640 filings, including 627 in the production run and 13 earlier cases. The detailed review explains the investment question, all nine objective questions, funding and ownership, the three-agent workflow, quality checks and remaining uncertainty.</p><a class="button" href="research/docs/extraction-results-review-20261102/report.html">Read the detailed report and searchable results</a><a href="research/docs/extraction-results-review-20261102/13D_Extraction_Results_and_Methods_20261102.pdf">25-page reading PDF</a><p>Production readers agree on 5,581/5,643 objective states; 5,478 pass the experimental-use rule. The 221 critic flags overlap 64 of 165 excluded objective decisions. Labels remain experimental, accuracy unmeasured and the investment comparison unrun. Original records are preserved; no flags were adjudicated.</p></section>'''
    if marker not in home:home=home.replace('<body><main>','<body><main>\n'+block,1)
    home=home.replace('Current: 13D extraction in batches — October 28','Completed: 13D extraction batches - October 28 to November 2',1)
    paths[0].write_text(home)
    checkpoint=paths[1].read_text()
    block2='''<!-- extraction-results-review-20261102 --><section class="current"><h2>Current learning checkpoint: understand the completed extraction - November 2</h2><p>The 25-page review starts with the investment question and explains each measurement question, the three-agent review, technical versus semantic quality, all category results, 221 critic flags and the wider 165-decision objective uncertainty queue. It includes worked examples, a glossary and the proposed adjudication sequence.</p><p><a href="extraction-results-review-20261102/report.html">Detailed report with searchable filing and flag appendices</a> · <a href="extraction-results-review-20261102/13D_Extraction_Results_and_Methods_20261102.pdf">Reading PDF</a></p><p>Learn why 98.9% agreement is not accuracy, why positive-set overlap is a separate consistency measure, and why the known flags do not capture all possible omissions. The completed production scope is 627 filings; 13 earlier cases bring the eligible collection to 640. No new labeling, adjudication or investment model was performed for this report.</p></section>'''
    if marker not in checkpoint:checkpoint=checkpoint.replace('<body><main>','<body><main>\n'+block2,1)
    checkpoint=checkpoint.replace('Current checkpoint: extraction in saved batches','Completed workflow checkpoint: extraction in saved batches',1)
    checkpoint=checkpoint.replace('Updated October 27, 2026 | Shared-rule extraction retest and separate operational batch complete','Updated November 2, 2026 | Production extraction complete and detailed results review available',1)
    paths[1].write_text(checkpoint)
    plan=paths[2].read_text()
    block3='''<!-- extraction-results-review-20261102 -->
## Extraction results and methods review - November 2, 2026

The eligible collection is complete: 640 filings, including 627 in the production run and 13 earlier v3 cases. The detailed review explains the investment question, nine objective definitions, funding/ownership/transaction fields, the three-agent workflow, quality methods, category results and open decisions. Its HTML appendices search every production filing and every original critic flag.

[Detailed report](extraction-results-review-20261102/report.html) · [25-page PDF](extraction-results-review-20261102/13D_Extraction_Results_and_Methods_20261102.pdf)

There are 221 critic flags across 127 production filings, overlapping 64 of the 165 excluded objective decisions. The distinct combined open inventory is 322 field decisions. No flags were adjudicated for this report. Prioritize all 165 unresolved objective decisions and 43 funding flags, with their material evidence dependencies. Funding feature transformation and Bloomberg historical timing/mapping remain pending; ownership-derived features and transaction counts retain the existing first-model exclusions. Accuracy and incremental investment value remain unmeasured.

'''
    if marker not in plan:plan=plan.replace('<!-- extraction-batches-current -->',block3+'<!-- extraction-batches-current -->',1)
    plan=plan.replace('## Extraction batches underway — October 28, 2026','## Extraction batches completed - October 28 to November 2, 2026',1)
    paths[2].write_text(plan)
    target=Path('/Users/jefflu/Downloads')/PDF_NAME
    if target.exists():assert sha(target)==sha(HERE/PDF_NAME),'Existing Downloads PDF differs; preserve it'
    else:shutil.copy2(HERE/PDF_NAME,target)
    assert sha(target)==sha(HERE/PDF_NAME)
    navigation=[]
    for path in paths[:2]:
        parser=Links();parser.feed(path.read_text());checked=0
        for href in parser.hrefs:
            parsed=urlsplit(href)
            if parsed.scheme or not parsed.path:continue
            assert(path.parent/unquote(parsed.path)).resolve().exists(),(path,href)
            checked+=1
        navigation.append({'path':str(path.relative_to(ROOT)),'links_checked':checked,'broken_links':0,
                           'before_sha256':sha(before/path.name),'after_sha256':sha(path)})
    for name,expected in a['input_sha256'].items():assert sha(ROOT/name)==expected,name
    qa['visual_review']='passed; see visual-review.json'
    (HERE/'qa-results.json').write_text(json.dumps(qa,indent=2)+'\n')
    build=json.loads((HERE/'build-verification.json').read_bytes())
    build['report_status']='complete_and_verified'
    (HERE/'build-verification.json').write_text(json.dumps(build,indent=2)+'\n')
    result={'status':'complete','production_filings':627,'total_completed_filings':640,'pdf_pages':25,
            'sections':22,'source_hashes_verified_unchanged':len(a['input_sha256']),
            'pdf_visual_review':visual,'pdf_text_geometry':'passed','html_embedded_data_parity':'passed',
            'html_static_links_and_images_checked':qa['local_html_links_and_images_checked'],
            'all_case_evidence_links_verified':627,'ui_filter_and_pagination_tests':len(ui['checks']),
            'ui_test_method':ui['method'],'live_browser_preview':qa['live_browser_preview'],
            'new_extraction_labels':0,'flags_adjudicated':0,'new_investment_fits':0,
            'analysis_byte_identical_rerun':'passed','navigation':navigation,
            'downloads_pdf':str(target),'downloads_pdf_sha256':sha(target),
            'outputs_sha256':{name:sha(HERE/name)for name in ['report.html',PDF_NAME,'analysis.json','explorer.json']}}
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['pdf_visual_review','outputs_sha256','navigation']},indent=2))


if __name__=='__main__':main()
