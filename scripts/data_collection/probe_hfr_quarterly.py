"""Tier: 0. Inspect nested HFR archive schemas without modifying sources.

Inputs: supplied quarterly ZIP. Outputs: member/schema inventory on stdout.
Identity: original XML cell values, no inferred classifications or dates.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/probe_hfr_quarterly.py
"""
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SOURCE = '/Users/jefflu/Downloads/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip'


def main():
    with ZipFile(SOURCE) as outer:
        names = [n for n in outer.namelist() if n.endswith('.zip')]
        for name in (names[0], names[29], names[30], names[-1]):
            with ZipFile(BytesIO(outer.read(name))) as inner:
                print(name, inner.namelist())
                print('DATESTAMP', repr(inner.read('DATESTAMP.txt')))
                if 'Excel_Fund.xls' in inner.namelist():
                    import xlrd
                    book = xlrd.open_workbook(file_contents=inner.read('Excel_Fund.xls'))
                    sheet = book.sheet_by_index(0)
                    print('XLS', sheet.name, sheet.nrows, sheet.row_values(0))
                    print('XLS first row', sheet.row_values(1)[:22])
                for member in inner.namelist():
                    if 'fund' not in member.lower() or not member.endswith('.xlsx'):
                        continue
                    with ZipFile(BytesIO(inner.read(member))) as book:
                        print(book.read('xl/workbook.xml').decode()[:2000])
                        shared = [''.join(s.itertext()) for s in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('m:si', NS)] if 'xl/sharedStrings.xml' in book.namelist() else []
                        for _, row in ET.iterparse(book.open('xl/worksheets/sheet1.xml'), events=['end']):
                            if row.tag != '{'+NS['m']+'}row':
                                continue
                            vals = []
                            for cell in row.findall('m:c', NS):
                                node = cell.find('m:v', NS)
                                raw = node.text if node is not None else ''
                                val = shared[int(raw)] if cell.get('t') == 's' and raw else raw
                                if cell.get('t') == 'inlineStr':
                                    val = ''.join(cell.find('m:is', NS).itertext())
                                vals.append((cell.get('r'), val))
                            print(vals)
                            if int(row.get('r')) >= 2:
                                break


if __name__ == '__main__':
    main()
