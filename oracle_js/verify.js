#!/usr/bin/env node
/*
 * Independent consumer verifier, written separately from the Python package.
 *
 * It reads only JSON: a derived asset's EM assertion with its dependency
 * declaration, each source's own interval assertion, and optionally the decoded
 * sample count of the asset. It imports nothing from em_audio, and it
 * recomputes the complete-source record of every output sample by brute force,
 * where the Python verifier works on intervals. Agreement between the two on
 * the same cases tests the specification of the declaration, not a shared
 * implementation.
 *
 * Usage:  node verify.js <cases.jsonl>   (writes {id, verdict} lines on stdout)
 */
'use strict';
const fs = require('fs');

const BOT = null;

function meet(a, b) {
  if (a === BOT || b === BOT) return BOT;
  return [...new Set([...a, ...b])].sort();
}

// a is no stronger than b
function leq(a, b) {
  if (a === BOT) return true;
  if (b === BOT) return false;
  return b.every(x => a.includes(x));
}

function evOf(iv) {
  return {
    P: iv.provenance === null ? BOT : [...iv.provenance].sort(),
    S: iv.support || {},
    A: Object.fromEntries(Object.entries(iv.applicability || {}).map(([k, v]) => [k, [...v].sort()])),
    L: [...(iv.lineage || [])].sort()
  };
}

function aggregate(evs) {
  if (evs.length === 0) return { P: BOT, S: {}, A: {}, L: [] };
  let P = evs[0].P;
  for (const e of evs.slice(1)) P = meet(P, e.P);
  const L = [...new Set([].concat(...evs.map(e => e.L)))].sort();
  if (P === BOT) return { P: BOT, S: {}, A: {}, L };
  const S = {}, A = {};
  const chans = new Set();
  evs.forEach(e => Object.keys(e.A).forEach(c => chans.add(c)));
  for (const mu of [...chans].sort()) {
    if (evs.some(e => !(mu in e.A) || !(mu in e.S))) continue;   // every source must supply it
    let scope = new Set(evs[0].A[mu]);
    for (const e of evs.slice(1)) scope = new Set([...scope].filter(x => e.A[mu].includes(x)));
    if (scope.size === 0) continue;
    A[mu] = [...scope].sort();
    S[mu] = Math.min(...evs.map(e => e.S[mu]));
  }
  return { P, S, A, L };
}

function key(e) { return JSON.stringify([e.P, e.S, e.A, e.L]); }

function sources(piece, tl, o) {
  const nOut = piece.output.end - piece.output.start;
  const rate = nOut > 0 ? (piece.sourceRange.end - piece.sourceRange.start) / nOut : 1;
  const s0 = piece.sourceRange.start + (o - piece.output.start) * rate;
  const s1 = piece.sourceRange.start + (o + 1 - piece.output.start) * rate;
  let lo = Math.floor(Math.min(s0, s1)) - piece.footprint;
  let hi = Math.ceil(Math.max(s0, s1)) + piece.footprint;
  if (hi <= lo) hi = lo + 1;
  const start = tl[0].start, end = tl[tl.length - 1].end;
  lo = Math.max(start, Math.min(end, lo));
  hi = Math.max(start, Math.min(end, hi));
  if (hi <= lo) return [tl.find(i => lo >= i.start && lo < i.end) || tl[tl.length - 1]];
  return tl.filter(i => i.end > lo && i.start < hi);
}

function verify(c) {
  const a = c.assertion, d = a.dependencyDeclaration;
  if (!d) return 'NO_DECLARATION';
  const n = d.outputSampleCount;
  if (c.decoded !== undefined && c.decoded !== null && c.decoded !== n) return 'LENGTH_MISMATCH';
  const spans = d.pieces.map(p => [p.output.start, p.output.end]).sort((x, y) => x[0] - y[0]);
  let reach = 0;
  if (n > 0 && (spans.length === 0 || spans[0][0] !== 0)) return 'COVERAGE_FAILURE';
  for (const [s, e] of spans) {
    if (e > n || s > reach) return 'COVERAGE_FAILURE';
    reach = Math.max(reach, e);
  }
  if (reach !== n) return 'COVERAGE_FAILURE';
  const tls = {};
  for (const [name, sa] of Object.entries(c.sources)) {
    tls[name] = sa.intervals.map(i => ({ start: i.samples.start, end: i.samples.end, ev: evOf(i) }))
      .sort((x, y) => x.start - y.start);
  }
  const emitted = a.intervals.map(i => ({ start: i.samples.start, end: i.samples.end, ev: evOf(i) }));
  let promotion = false, mismatch = false, k = 0;
  for (let o = 0; o < n; o++) {
    while (k < emitted.length && emitted[k].end <= o) k++;
    const e = (k < emitted.length && emitted[k].start <= o) ? emitted[k].ev : null;
    const srcs = [];
    for (const p of d.pieces) if (p.output.start <= o && o < p.output.end) srcs.push(...sources(p, tls[p.source], o));
    const r = aggregate(srcs.map(s => s.ev));
    if (e === null) { mismatch = true; continue; }
    if (key(e) === key(r)) continue;
    const stronger = !leq(e.P, r.P)
      || Object.keys(e.S).some(m => !(m in r.S) || e.S[m] > r.S[m])
      || Object.keys(e.A).some(m => (m in r.A) && !e.A[m].every(x => r.A[m].includes(x)))
      || !r.L.every(x => e.L.includes(x));
    if (stronger) promotion = true; else mismatch = true;
  }
  return promotion ? 'PROMOTION' : (mismatch ? 'INCONSISTENT' : 'CONSISTENT');
}

const lines = fs.readFileSync(process.argv[2], 'utf8').split('\n').filter(l => l.trim());
for (const line of lines) {
  const c = JSON.parse(line);
  process.stdout.write(JSON.stringify({ id: c.id, verdict: verify(c) }) + '\n');
}
