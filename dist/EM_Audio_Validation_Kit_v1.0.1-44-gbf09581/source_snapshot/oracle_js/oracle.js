#!/usr/bin/env node
/*
 * Independent second implementation of the evidence-monotone contract.
 *
 * Deliberately uses a DIFFERENT algorithm from the Python core: it evaluates
 * evidence per output sample by brute force and then run-length-encodes the
 * result, whereas the Python core works with interval algebra and pulled-back
 * boundaries.  Agreement between the two therefore tests the specification, not
 * a shared implementation shortcut.
 *
 * Both implementations are written by the same author.  This is a differential
 * test against transcription and interval-arithmetic error; it is not evidence
 * of author independence, and the manuscript says so.
 *
 * Usage:  node oracle.js <cases.jsonl>   (writes JSONL results on stdout)
 */
'use strict';
const fs = require('fs');

const BOT = null;                       // unverified / unavailable

function meetClaim(a, b) {
  if (a === BOT || b === BOT) return BOT;
  const s = new Set([...a, ...b]);
  return [...s].sort();
}

function meetClaims(cs) {
  if (cs.length === 0) return BOT;
  let acc = cs[0];
  for (let i = 1; i < cs.length; i++) acc = meetClaim(acc, cs[i]);
  return acc;
}

function labelOf(c) {
  if (c === BOT) return 'UNVERIFIED';
  const k = c.join(',');
  if (k === 'C') return 'CAPTURED';
  if (k === 'G') return 'GENERATED';
  if (k === 'C,G') return 'MIXED';
  throw new Error('bad claim ' + k);
}

/* Aggregate a list of evidence records (the complete required source set). */
function aggregate(evs) {
  if (evs.length === 0) return { P: BOT, S: {}, A: {}, L: [] };
  const P = meetClaims(evs.map(e => e.P));
  const L = [...new Set([].concat(...evs.map(e => e.L)))].sort();
  if (P === BOT) return { P: BOT, S: {}, A: {}, L };
  const channels = new Set();
  evs.forEach(e => Object.keys(e.A).forEach(c => channels.add(c)));
  const S = {}, A = {};
  [...channels].sort().forEach(mu => {
    const app = evs.filter(e => Object.prototype.hasOwnProperty.call(e.A, mu));
    if (app.length === 0) return;
    let scope = new Set(app[0].A[mu]);
    for (const e of app.slice(1)) scope = new Set([...scope].filter(x => e.A[mu].includes(x)));
    if (scope.size === 0) return;
    if (app.some(e => !Object.prototype.hasOwnProperty.call(e.S, mu))) return;
    A[mu] = [...scope].sort();
    S[mu] = Math.min(...app.map(e => e.S[mu]));
  });
  return { P, S, A, L };
}

/* Sample-wise evaluation of one output range under one policy. */
function sourcesForSample(piece, timeline, outPos, footprintAware) {
  const nOut = piece.out_end - piece.out_start;
  const rate = nOut > 0 ? (piece.src_end - piece.src_start) / nOut : 1.0;
  const s0 = piece.src_start + (outPos - piece.out_start) * rate;
  const s1 = piece.src_start + (outPos + 1 - piece.out_start) * rate;
  let lo = Math.floor(Math.min(s0, s1));
  let hi = Math.ceil(Math.max(s0, s1));
  if (footprintAware) { lo -= piece.footprint; hi += piece.footprint; }
  if (hi <= lo) hi = lo + 1;
  const start = timeline[0].start, end = timeline[timeline.length - 1].end;
  lo = Math.max(start, Math.min(end, lo));
  hi = Math.max(start, Math.min(end, hi));
  if (hi <= lo) { const iv = timeline.find(i => lo >= i.start && lo < i.end) || timeline[timeline.length - 1]; return [iv]; }
  return timeline.filter(i => i.end > lo && i.start < hi);
}

function evidenceKey(e) {
  return JSON.stringify([e.P, e.S, e.A, e.L]);
}

/* EM policy: complete-source, per output sample, then run-length encoded. */
function emIntervals(model, timelines, footprintAware) {
  const out = [];
  model.pieces.forEach((p, pi) => {
    const tl = timelines[p.src];
    let runStart = p.out_start, runEv = null, runKey = null;
    for (let o = p.out_start; o < p.out_end; o++) {
      const srcs = sourcesForSample(p, tl, o, footprintAware);
      const ev = aggregate(srcs.map(s => s.ev));
      const k = evidenceKey(ev);
      if (runKey === null) { runKey = k; runEv = ev; runStart = o; }
      else if (k !== runKey) {
        out.push({ out_start: runStart, out_end: o, ev: runEv, piece: pi });
        runKey = k; runEv = ev; runStart = o;
      }
    }
    if (runKey !== null) out.push({ out_start: runStart, out_end: p.out_end, ev: runEv, piece: pi });
  });
  return out;
}

/* Baseline: boundary-only inheritance, one record per span, footprint-blind. */
function baselineSpans(model, timelines) {
  return model.pieces.map((p, pi) => {
    const tl = timelines[p.src];
    const first = sourcesForSample(p, tl, p.out_start, false);
    const last = sourcesForSample(p, tl, p.out_end - 1, false);
    const ends = [first[0], last[last.length - 1]];
    return { out_start: p.out_start, out_end: p.out_end, ev: aggregate(ends.map(s => s.ev)), piece: pi };
  });
}

function main() {
  const file = process.argv[2];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(l => l.trim());
  for (const line of lines) {
    const c = JSON.parse(line);
    const timelines = {};
    for (const [name, ivs] of Object.entries(c.timelines)) timelines[name] = ivs;
    const em = emIntervals(c.model, timelines, true);
    const emNoFp = emIntervals(c.model, timelines, false);
    const bs = baselineSpans(c.model, timelines);
    const whole = aggregate(em.map(i => i.ev));
    const wholeB = aggregate(bs.map(i => i.ev));
    process.stdout.write(JSON.stringify({
      id: c.id,
      em_intervals: em.map(i => [i.out_start, i.out_end, labelOf(i.ev.P), i.ev.S, i.ev.L]),
      em_nofp_state: labelOf(aggregate(emNoFp.map(i => i.ev)).P),
      em_whole_state: labelOf(whole.P),
      em_whole_support: whole.S,
      em_whole_lineage: whole.L,
      baseline_whole_state: labelOf(wholeB.P),
      baseline_whole_support: wholeB.S,
      baseline_whole_lineage: wholeB.L
    }) + '\n');
  }
}

main();
