"""Verify invented model examples and package the offline Windows comparison.

Inputs: fixed nonlinear code/protocol, preserved feature/preparation/reference data.
Outputs: new dated preparation run, test/lint receipts, Windows ZIP and file hashes.
Identity: zip member bytes must equal included source bytes; no real nonlinear
model fits. run_nonlinear --prepare reconstructs all training-only matrices.
Tier: 1 packaging, not an investment estimator. Never upload or overwrite a run.
Run: .venv/bin/python scripts/ml_experiment/prepare_windows_models.py --output NEW_RUN
"""

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_nonlinear as runner  # noqa: E402

TESTS = ["tests/test_ml_nonlinear.py", "tests/test_ml_baselines.py", "tests/test_ml_preprocessing.py"]
CODE = ["scripts/ml_experiment/nonlinear_models.py", "scripts/ml_experiment/run_nonlinear.py",
        "scripts/ml_experiment/run_baselines.py", "scripts/ml_experiment/prepare_inputs.py"]

CHECK_CMD = r'''@echo off
setlocal
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONIOENCODING=utf-8"
set "BASE_PY=python"
if exist "C:\_dev\activist13d-migration-20260927\.venv\Scripts\python.exe" set "BASE_PY=C:\_dev\activist13d-migration-20260927\.venv\Scripts\python.exe"
if exist ".venv-ml\Scripts\python.exe" goto dependencies
"%BASE_PY%" -m venv .venv-ml
if errorlevel 1 goto failed
:dependencies
set "MODEL_PY=%CD%\.venv-ml\Scripts\python.exe"
"%MODEL_PY%" -m pip install -r requirements-ml.txt
if errorlevel 1 goto failed
"%MODEL_PY%" -m pytest tests/test_ml_nonlinear.py tests/test_ml_preprocessing.py -q
if errorlevel 1 goto failed
"%MODEL_PY%" scripts/ml_experiment/run_nonlinear.py --prepare --output "research\runs\ml-nonlinear\windows-preflight-%RANDOM%-%RANDOM%"
if errorlevel 1 goto failed
echo.
echo Checks passed. Actual 13D network and tree fitting has NOT run.
echo Read README.html, then use Run Models.cmd when ready for the Windows fit.
pause
exit /b 0
:failed
echo.
echo Check stopped. Keep this message and any failure.json for diagnosis.
echo Python 3.13 or 3.14 is required; do not paste PowerShell error text as commands.
pause
exit /b 1
'''

RUN_CMD = r'''@echo off
setlocal
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONIOENCODING=utf-8"
if not exist ".venv-ml\Scripts\python.exe" goto missing
".venv-ml\Scripts\python.exe" scripts/ml_experiment/run_nonlinear.py --fit --output "research\runs\ml-nonlinear\windows-fit-%RANDOM%-%RANDOM%"
if errorlevel 1 goto failed
echo.
echo Finished. The full output directory is printed above. Keep the whole folder.
echo The output index.html explains results; this is development evaluation.
pause
exit /b 0
:missing
echo Run Check Models.cmd first to create and verify the model environment.
pause
exit /b 1
:failed
echo The run stopped. Preserve its output folder and failure.json; do not overwrite it.
pause
exit /b 1
'''

GUIDE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D Windows nonlinear model run</title><style>body{font:17px/1.65 system-ui,sans-serif;max-width:960px;margin:30px auto;padding:24px;color:#203448}code{overflow-wrap:anywhere}li{margin:12px 0}a{color:#155c99}</style></head><body>
<h1>First neural-network and tree comparison on Windows</h1><p>Prepared October 19, 2026. The Mac verified synthetic calculations and input preparation; actual 13D nonlinear fitting has not been run there. Windows checks have not yet been performed.</p>
<p>The question is whether nonlinear methods improve later-year post-13D return predictions using the same information. The target, observations and references are preserved. No Bloomberg financials, LLM calls, credentials, stock orders or paid APIs are used.</p>
<ol><li>Copy the ZIP to the Windows laptop and use <strong>Extract All</strong>. Extract to a new local folder, for example <code>C:\\Users\\jeffh\\Projects\\13D-Models-20261019</code>. Keep every subfolder. Run from the extracted folder, not from inside the ZIP. This standalone package does not require a git pull or a full raw-filing archive.</li>
<li>Open <strong>Check Models.cmd</strong>. It creates an isolated <code>.venv-ml</code>, downloads pinned model packages and runs synthetic tests plus a preparation check. It uses the known existing runtime at <code>C:\\_dev\\activist13d-migration-20260927\\.venv\\Scripts\\python.exe</code>, otherwise <code>python</code> on PATH. It never calls the missing <code>py</code> launcher. Python 3.13 or 3.14 is required. The initial package download can take time; the scripts require no GPU.</li>
<li>After checks pass, read the accompanying <a href="research/docs/neural-network-lessons/20261019/comparison-plan.html">method lesson</a>. <strong>Run Models.cmd</strong> is the separate action that starts actual 13D fitting. It trains the fixed comparison, saves every forecast, then scores it. It uses CPU float64 for the network, one thread and five declared seeds. The forest and boosting also use fixed settings.</li>
<li>The console prints the saved folder under <code>research\\runs\\ml-nonlinear\\windows-fit-...</code>. Open its <code>index.html</code> for the comparison and keep the entire folder, including manifests, JSON model states, predictions and diagnostics. Bring that folder back for checkpoint 4B; screenshots alone do not preserve the evidence.</li></ol>
<p>Repeated runs create separate directories. An existing run is never overwritten. If a command fails, preserve its output and any <code>failure.json</code>; do not delete seeds, change settings or select a favorable run. Fixed 500 updates do not prove convergence. Review loss/gradient curves and inactive neurons before interpreting later errors.</p>
<p>Report all three prediction years and all five neural seeds, as well as the declared equal-weight neural ensemble. Compare RMSE and MAE in percentage points and within-year Spearman with the existing mean, zero-excess and ridge references. These are previously inspected development years with overlapping return windows, not an untouched final test or after-cost investment returns. No invest/no-invest threshold or portfolio sizing is selected.</p>
<p>The final fitted model uses the last update. New losses, features, depths, seed choices or tuning require a separately identified experiment. The downloaded Bloomberg workbook is excluded because its annual-period rule does not establish what was public at each cutoff.</p>
<p><a href="research/protocol/ml-nonlinear-v1.json">Frozen settings</a> · <a href="package-manifest.json">Packaged file hashes</a> · <a href="requirements-ml.txt">Pinned model dependencies</a></p>
</body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
    verification_sources = {p: runner.baseline.digest(ROOT / p) for p in
                            CODE + TESTS + ["research/protocol/ml-nonlinear-v1.json", "requirements-ml.txt"]}
    commands = [
        [sys.executable, "-m", "ruff", "check", *CODE[:2], TESTS[0], str(Path(__file__).relative_to(ROOT))],
        [sys.executable, "-m", "pytest", *TESTS, "-q", f"--junitxml={out / 'tests.xml'}"],
    ]
    for number, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
        (out / f"verification-{number}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"Verification failed; see {out / f'verification-{number}.log'}")
    cases = ET.parse(out / "tests.xml").findall(".//testcase")
    assert len(cases) >= 20
    assert not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
    assert all(runner.baseline.digest(ROOT / p) == sha for p, sha in verification_sources.items())

    def emit(name, payload):
        path = out / "preflight" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    first, summary = runner.build(fit=False, emit_to_disk=emit)
    second, _ = runner.build(fit=False)
    assert first == second and summary["real_data_model_fits"] == 0
    receipt = {"status": "Mac verification passed; Windows not yet checked; real nonlinear fit not run",
               "tests": len(cases), "skipped": sum(c.find("skipped") is not None for c in cases),
               "verification_source_sha256": verification_sources, "exact_preparation_replay": True,
               "actual_13d_nonlinear_model_fits": 0, "environment": runner.environment()}
    (out / "verification.json").write_bytes(runner.baseline.encode(receipt))

    relatives = CODE + TESTS + ["tests/conftest.py", "requirements-ml.txt", "pyproject.toml",
        "research/protocol/ml-baselines-v1.json", "research/protocol/ml-preprocessing-v1.json",
        "research/protocol/ml-nonlinear-v1.json",
        "research/docs/neural-network-lessons/20261019/comparison-plan.html"]
    for directory, names in [
        (runner.baseline.PREVIEW, ["features.jsonl", "targets.jsonl", "row-metadata.jsonl", "feature-dictionary.json", "provenance.json"]),
        (runner.baseline.PREP, ["fold-inputs.json", "preprocessing-state.json", "protocol.json", "summary.json", "provenance.json"]),
        (runner.REFERENCE, ["predictions.jsonl", "provenance.json"]),
    ]:
        relatives += [str((directory / name).relative_to(ROOT)) for name in names]
    payloads = {name: (ROOT / name).read_bytes() for name in relatives}
    payloads.update({"README.html": GUIDE.encode(),
                     "Check Models.cmd": CHECK_CMD.replace('\n', '\r\n').encode(),
                     "Run Models.cmd": RUN_CMD.replace('\n', '\r\n').encode()})
    lesson_name = "research/docs/neural-network-lessons/20261019/comparison-plan.html"
    lesson = payloads[lesson_name].decode()

    def keep_available_link(match):
        link = match.group(1)
        if link.startswith(("https:", "http:", "#")):
            return match.group(0)
        destination = posixpath.normpath(posixpath.join(posixpath.dirname(lesson_name), link))
        return match.group(0) if destination in payloads else ""

    # The standalone lesson retains teaching text; project-only navigation is
    # unlinked instead of pointing outside this intentionally bounded package.
    payloads[lesson_name] = re.sub(r'href="([^"]+)"', keep_available_link, lesson).encode()
    manifest = {name: hashlib.sha256(value).hexdigest() for name, value in sorted(payloads.items())}
    payloads["package-manifest.json"] = runner.baseline.encode({"files_sha256": manifest,
        "purpose": "Offline fixed comparison; saved development targets included for the user's Windows run",
        "excluded": "raw filings, vendor credentials, new Bloomberg data, LLM results, fitted nonlinear outputs",
        "lesson_adaptation": "Teaching text preserved; navigation to unpackaged project evidence is unlinked"})
    for name, payload in payloads.items():
        if name.endswith('.html'):
            for link in re.findall(r'href="([^"]+)"', payload.decode()):
                if not link.startswith(("https:", "http:", "#")):
                    assert posixpath.normpath(posixpath.join(posixpath.dirname(name), link)) in payloads
        path = out / "windows-package" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    archive = out / "13D_Nonlinear_Windows_20261019.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, payload in sorted(payloads.items()):
            bundle.writestr(f"13D_Nonlinear_Windows_20261019/{name}", payload)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for name, payload in payloads.items():
            assert bundle.read(f"13D_Nonlinear_Windows_20261019/{name}") == payload
    (out / "package-receipt.json").write_bytes(runner.baseline.encode({
        "archive": archive.name, "sha256": runner.baseline.digest(archive),
        "bytes": archive.stat().st_size, "members": len(payloads), "all_members_verified": True}))
    (out / "windows-guide.html").write_text(re.sub(r'href="(?!https?:)([^"]+)"',
                                                   r'href="windows-package/\1"', GUIDE))
    index = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D nonlinear preparation — October 19</title><style>body{{font:17px/1.65 system-ui,sans-serif;color:#203448;max-width:980px;margin:30px auto;padding:24px}}a{{color:#155c99}}li{{margin:10px 0}}</style></head><body><h1>Ready to check and fit on Windows</h1><p>October 19, 2026 · Preparation complete; actual nonlinear 13D comparison not run</p><p>The question remains whether nonlinear methods improve post-13D return prediction on the same information. The network, shallow tree, forest and gradient boosting are implemented with fixed settings. {len(cases)} local tests passed, with {receipt['skipped']} skipped; code passes targeted lint. Checks include hand-calculated loss/derivatives, numerical gradient checks, Adam, tree/boosting arithmetic, serialized state parity, invalid-input refusals and exact replay. This is local Mac evidence, not a remote CI or Windows result.</p><p>Preparation reconstructs all three training-only matrices and aligns all 302 saved later reference forecasts. Repeating preparation produces identical artifacts, with zero real-data predictor fits. No new model scores or Bloomberg inputs were used.</p><ol><li><a href="../../../docs/neural-network-lessons/20261019/comparison-plan.html">Read the method lesson and worked examples</a>.</li><li>Transfer <a href="{archive.name}">the complete Windows ZIP</a> and extract it into a new local folder.</li><li>Use Check Models.cmd for setup and verification, then Run Models.cmd for the separate actual training action. See <a href="windows-guide.html">Windows instructions</a>.</li><li>Return the complete Windows output folder for checkpoint 4B. Report every model/year/seed; do not choose favorable seeds or change settings after seeing results.</li></ol><p>A successful synthetic test does not establish investment skill. Training samples are small, outcomes overlap, and the historical development labels were already inspected. No portfolio rule or alpha claim follows.</p><p><a href="verification.json">Verification receipt</a> · <a href="preflight/preparation.json">Zero-fit preparation status</a> · <a href="preflight/prefit-manifest.json">Input/environment snapshot</a> · <a href="package-receipt.json">Archive hash</a> · <a href="tests.xml">Test receipt</a> · <a href="../../../../START-HERE.html">Project home</a></p></body></html>'''
    (out / "index.html").write_text(index)
    print(json.dumps({"preparation": str(out), "tests": len(cases), "zip": str(archive),
                      "zip_bytes": archive.stat().st_size, "real_nonlinear_fits": 0}, indent=2))


if __name__ == "__main__":
    main()
