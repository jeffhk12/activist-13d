"""Tier 1 pins for deterministic selection and evidence search; no network."""
import unittest
import prepare
class Tests(unittest.TestCase):
    def test_selection_and_rerun(self):
        rows=[]
        for year in [2014,2017,2020,2023]:
            for i in range(12):rows.append({'accession':f'{year}-{i}','filing_date':f'{year}-01-02','filers':[{'cik':f'{year}{i}','name':'Sample Capital' if i<6 else 'Person'}],'subjects':[{'cik':f'{year}{i}'}],'item4_text':'We nominate a director' if i<9 else ''})
        a,_=prepare.select(rows,{'2014-0'},20);b,_=prepare.select(list(reversed(rows)),{'2014-0'},20)
        self.assertEqual(a,b);self.assertEqual(len(a),20);self.assertNotIn('2014-0',{e['record']['accession'] for e in a});self.assertEqual(len({e['record']['accession'] for e in a}),20)
    def test_quote_and_not_label(self):
        text='An investment adviser may discuss matters; a third party runs a hedge fund.'
        docs=[{'document_id':'DOCUMENT[1]','text':text,'text_sha256':prepare.sha(text.encode())}]
        ev=prepare.cues(docs);self.assertTrue(any(e['cue']=='Hedge-fund phrase' for e in ev))
        for e in ev:self.assertEqual(text[e['start']:e['end']],e['quote']);self.assertNotIn('classification',e)
        self.assertEqual(prepare.cues([{'document_id':'DOCUMENT[1]','text':'Nothing specified','text_sha256':'x'}]),[])
    def test_security(self):
        self.assertEqual(prepare.security_hint(None),'Unresolved');self.assertEqual(prepare.security_hint('Class A ordinary shares'),'Common/ordinary');self.assertEqual(prepare.security_hint('Series A preferred stock'),'Preferred')
        self.assertEqual(prepare.security_hint('Units consisting of common stock'),'Units / Common/ordinary')
if __name__=='__main__':unittest.main()
