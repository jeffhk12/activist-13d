/* Source-only human reading worksheet. No model calls or network requests. */
'use strict';
function validateEvidence(documents, evidence) {
  if (!Array.isArray(evidence)) throw new Error('Evidence must be a JSON array.');
  for (const e of evidence) {
    const d = documents.find(doc => doc.document_id === e.document_id);
    if (!d || typeof d.text !== 'string') throw new Error('Evidence needs an available source document.');
    if (e.text_sha256 !== d.text_sha256) throw new Error('Evidence source hash differs.');
    const points = Array.from(d.text);
    if (!Number.isInteger(e.start) || !Number.isInteger(e.end) || e.start < 0 || e.end <= e.start || e.end > points.length) {
      throw new Error('Evidence offsets must select a nonempty passage in one source document.');
    }
    if (points.slice(e.start, e.end).join('') !== e.quote) throw new Error('Quoted text differs from the source passage.');
  }
  return evidence;
}
function readingRecord(config, values, evidence, completed) {
  const keys = ['identities', 'ownership', 'funding', 'objectives', 'gaps', 'candidate_fields'];
  if (completed && (!values.reviewer.trim() || keys.some(k => !values[k].trim()) || !values.reviewed || values.prior_exposure === 'not_declared' || !evidence.length)) {
    throw new Error('Complete the observations, reviewer, exposure declaration and independent-reading checkbox, and capture supporting evidence. Uncertainty is a valid observation.');
  }
  return {
    record_type: 'ranking-human-reading-draft-v1', protocol: config.protocol,
    accession: config.accession, source_sha256: config.source_sha256,
    bundle_sha256: config.bundle_sha256, sample_manifest_sha256: config.sample_manifest_sha256,
    reviewer: values.reviewer, independent_reading_completed: values.reviewed,
    prior_model_answer_exposure: values.prior_exposure,
    answers: Object.fromEntries(keys.map(k => [k, values[k]])), evidence,
    status: completed ? 'human_reading_submitted_not_semantic_schema_validated' : 'draft',
    reviewed_at_utc: completed ? new Date().toISOString() : null
  };
}
function initializeWorksheet() {
  const config = JSON.parse(document.getElementById('config').textContent);
  const keys = ['reviewer', 'identities', 'ownership', 'funding', 'objectives', 'gaps', 'candidate_fields'];
  const documents = Array.from(document.querySelectorAll('pre[data-document]')).map(p => ({document_id: p.dataset.document, text_sha256: p.dataset.sha, text: p.textContent}));
  const storageKey = 'ranking-human-v1:' + config.sample_manifest_sha256 + ':' + config.accession;
  const status = message => { document.getElementById('status').textContent = message; };
  function values() {
    return {...Object.fromEntries(keys.map(k => [k, document.getElementById(k).value])),
      reviewed: document.getElementById('reviewed').checked,
      prior_exposure: document.getElementById('prior_exposure').value};
  }
  function evidence() { return validateEvidence(documents, JSON.parse(document.getElementById('evidence').value || '[]')); }
  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({...values(), evidence_text: document.getElementById('evidence').value}));
      status('Draft saved in this browser. Download JSON for a durable copy.');
    } catch (e) { status('Browser storage is unavailable. Download a draft JSON to preserve your work.'); }
  }
  function download(completed) {
    try {
      const result = readingRecord(config, values(), evidence(), completed);
      const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2) + '\n'], {type: 'application/json'}));
      const link = document.createElement('a');
      link.href = url;
      link.download = config.accession + (completed ? '-human-reading.json' : '-human-draft.json');
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status(completed ? 'Human reading downloaded. Bring the JSON back to the project for evidence checks and freezing.' : 'Draft downloaded; it is not a completed human reference.');
    } catch (e) { status(e.message); }
  }
  document.getElementById('capture').addEventListener('click', () => {
    try {
      const selection = window.getSelection();
      if (!selection.rangeCount || selection.isCollapsed) throw new Error('Select a passage inside a source document first.');
      const range = selection.getRangeAt(0);
      const node = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
      const pre = node.closest('pre[data-document]');
      if (!pre || !pre.contains(range.endContainer)) throw new Error('Select text within a single source document.');
      const before = range.cloneRange(); before.selectNodeContents(pre); before.setEnd(range.startContainer, range.startOffset);
      const start = Array.from(before.toString()).length;
      const quote = range.toString();
      const e = {document_id: pre.dataset.document, text_sha256: pre.dataset.sha, start, end: start + Array.from(quote).length, quote};
      const items = evidence(); items.push(e); validateEvidence(documents, items);
      document.getElementById('evidence').value = JSON.stringify(items, null, 2);
      status('Exact passage captured. Explain what it supports in your observations.');
    } catch (e) { status(e.message); }
  });
  document.getElementById('save').addEventListener('click', save);
  document.getElementById('downloadDraft').addEventListener('click', () => download(false));
  document.getElementById('downloadCompleted').addEventListener('click', () => download(true));
  document.getElementById('expand').addEventListener('click', () => document.querySelectorAll('details.source-document').forEach(d => {d.open = true;}));
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved) {
      keys.forEach(k => {document.getElementById(k).value = saved[k] || '';});
      document.getElementById('reviewed').checked = !!saved.reviewed;
      document.getElementById('prior_exposure').value = saved.prior_exposure || 'not_declared';
      document.getElementById('evidence').value = saved.evidence_text || '[]';
      status('A draft from this browser was restored.');
    }
  } catch (e) { /* An empty worksheet remains usable without browser storage. */ }
}
if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', initializeWorksheet);
