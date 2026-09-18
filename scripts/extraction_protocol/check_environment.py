"""Check local schema-validator availability without network access.

Input: installed Python modules. Output: version or unavailable.
Identity: importing a validator does not validate research labels.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/check_environment.py
"""
from importlib.metadata import PackageNotFoundError, version

if __name__ == '__main__':
    try:
        print('jsonschema', version('jsonschema'))
    except PackageNotFoundError:
        print('jsonschema unavailable')
