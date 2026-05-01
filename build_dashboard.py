"""
Builds the dashboard HTML from permits.json.
Runs after fetch_permits.py as part of the weekly GitHub Actions workflow.
"""

import json
import os
from datetime import datetime, timezone

DATA_FILE = "data/permits.json"
OUT_FILE = "docs/index.html"

def build():
    with open(DATA_FILE) as f:
        data = json.load(f)

    permits = data["permits"]
    stats = data["stats"]
    permits_js = json.dumps(permits)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JN Service Construction Leads</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@300;400;500;600&family=Barlow+Condensed:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<style>
:root {
  --bg: #0c0b09; --surface: #131108; --surface2: #1a1710; --border: #2c2510;
  --orange: #f97316; --orange-dim: rgba(249,115,22,0.12); --orange-border: rgba(249,115,22,0.28);
  --amber: #fbbf24; --green: #4ade80; --blue: #60a5fa;
  --text: #f0ece4; --muted: #7a6a4a; --muted2: #4a3f28;
  --new-glow: rgba(249,115,22,0.35);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'IBM Plex Mono', monospace; height: 100vh; overflow: hidden; }

/* HEADER */
header {
  height: 58px; padding: 0 24px;
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface); border-bottom: 2px solid var(--orange);
  position: relative; overflow: hidden;
}
header::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(249,115,22,0.08) 0%, transparent 60%);
  pointer-events: none;
}
.hdr-left { display: flex; align-items: center; gap: 16px; z-index: 1; }
.hdr-brand h1 { font-family: 'Bebas Neue', sans-serif; font-size: 24px; letter-spacing: 2px; color: var(--orange); line-height: 1; }
.hdr-brand p { font-size: 9px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; margin-top: 2px; }
.hdr-right { display: flex; align-items: center; gap: 12px; z-index: 1; }
.hdr-badge {
  font-family: 'Barlow Condensed', sans-serif; font-size: 11px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase; padding: 4px 10px; border-radius: 3px;
}
.hdr-badge.orange { background: var(--orange-dim); color: var(--orange); border: 1px solid var(--orange-border); }
.hdr-badge.new { background: rgba(249,115,22,0.25); color: #fff; border: 1px solid var(--orange); animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.6; } }
.hdr-date { font-size: 9px; color: var(--muted); text-align: right; line-height: 1.7; }

/* LAYOUT */
.main { display: grid; grid-template-columns: 400px 1fr; height: calc(100vh - 58px); }

/* SIDEBAR */
.sidebar { display: flex; flex-direction: column; border-right: 1px solid var(--border); overflow: hidden; }

.source-tabs { display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid var(--border); background: var(--surface); }
.tab {
  padding: 8px 4px; text-align: center; cursor: pointer;
  font-family: 'Barlow Condensed', sans-serif; font-size: 10px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase; color: var(--muted);
  border-right: 1px solid var(--border); transition: all 0.15s;
}
.tab:last-child { border-right: none; }
.tab.active { color: var(--orange); background: var(--orange-dim); }
.tab .n { display: block; font-size: 18px; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }
.tab.t-cam.active { color: var(--amber); background: rgba(251,191,36,0.1); }
.tab.t-som.active { color: var(--green); background: rgba(74,222,128,0.08); }

.filters { padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--surface2); display: flex; flex-direction: column; gap: 6px; }
.filter-row { display: flex; gap: 6px; }
select, input {
  background: var(--bg); border: 1px solid var(--border); color: var(--text);
  font-family: 'IBM Plex Mono', monospace; font-size: 10px;
  padding: 5px 8px; border-radius: 3px; flex: 1; outline: none;
}
select:focus, input:focus { border-color: var(--orange); }

.list-hdr {
  padding: 7px 12px; font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px;
  border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;
  background: var(--surface);
}

.permit-list { overflow-y: auto; flex: 1; }
.permit-list::-webkit-scrollbar { width: 3px; }
.permit-list::-webkit-scrollbar-thumb { background: var(--border); }

/* CARDS */
.card {
  padding: 12px 12px 12px 15px; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background 0.1s; position: relative;
}
.card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--orange); }
.card.src-Cambridge::before { background: var(--amber); }
.card.src-Somerville::before { background: var(--green); }
.card:hover { background: var(--surface2); }

/* NEW permit highlight */
.card.is-new { background: rgba(249,115,22,0.06); }
.card.is-new::after {
  content: 'NEW';
  position: absolute; top: 8px; right: 8px;
  font-family: 'Bebas Neue', sans-serif; font-size: 11px; letter-spacing: 2px;
  color: #000; background: var(--orange); padding: 1px 5px; border-radius: 2px;
}

.card-top { display: flex; align-items: flex-start; margin-bottom: 4px; gap: 6px; }
.card-addr { font-size: 11px; font-weight: 600; color: var(--text); flex: 1; line-height: 1.3; }
.src-pill {
  font-family: 'Barlow Condensed', sans-serif; font-size: 9px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase; padding: 2px 6px; border-radius: 2px; flex-shrink: 0;
}
.src-pill.Boston { background: var(--orange-dim); color: var(--orange); border: 1px solid var(--orange-border); }
.src-pill.Cambridge { background: rgba(251,191,36,0.1); color: var(--amber); border: 1px solid rgba(251,191,36,0.25); }
.src-pill.Somerville { background: rgba(74,222,128,0.08); color: var(--green); border: 1px solid rgba(74,222,128,0.2); }

.card-type { font-size: 9px; color: var(--orange); font-weight: 600; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }
.card-company { font-size: 10px; color: var(--amber); margin-bottom: 3px; }
.card-svcs { font-size: 9px; color: var(--muted); margin-bottom: 4px; }
.card-meta { font-size: 9px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }
.card-why { font-size: 9px; color: var(--green); margin-top: 5px; line-height: 1.4; }

/* MAP */
#map { height: 100%; width: 100%; }
.leaflet-container { background: #0c0b09 !important; }

/* DETAIL PANEL */
.dp {
  position: absolute; right: 0; top: 0; width: 360px; height: 100%;
  background: var(--surface); border-left: 2px solid var(--orange);
  z-index: 1000; transform: translateX(100%); transition: transform 0.22s ease;
  overflow-y: auto; display: flex; flex-direction: column;
}
.dp.open { transform: translateX(0); }
.dp-hdr {
  padding: 14px 16px; border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: var(--surface); z-index: 2;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.dp-hdr h3 { font-family: 'Barlow Condensed', sans-serif; font-size: 16px; font-weight: 700; color: var(--orange); line-height: 1.3; }
.dp-hdr span { font-size: 9px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }
.close-btn { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 22px; line-height: 1; padding: 0 2px; }
.dp-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.dp-row { display: flex; flex-direction: column; gap: 2px; }
.dp-key { font-size: 8px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--muted); }
.dp-val { font-size: 12px; color: var(--text); line-height: 1.4; }
.dp-val.big { font-family: 'Bebas Neue', sans-serif; font-size: 28px; color: var(--orange); }
.dp-divider { border: none; border-top: 1px solid var(--border); margin: 2px 0; }
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; }
.chip { font-size: 9px; padding: 2px 7px; border-radius: 2px; background: var(--orange-dim); color: var(--orange); border: 1px solid var(--orange-border); font-family: 'Barlow Condensed', sans-serif; font-weight: 700; }
.new-banner { background: rgba(249,115,22,0.15); border: 1px solid var(--orange); border-radius: 4px; padding: 8px 12px; font-family: 'Barlow Condensed', sans-serif; font-size: 13px; font-weight: 700; color: var(--orange); letter-spacing: 1px; text-align: center; }
.contractor-box { background: rgba(251,191,36,0.06); border: 1px solid rgba(251,191,36,0.2); border-radius: 4px; padding: 11px; }
.contractor-title { font-size: 8px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--amber); margin-bottom: 7px; }
.contractor-name { font-size: 14px; font-weight: 600; color: var(--amber); font-family: 'Barlow Condensed', sans-serif; }
.contractor-company { font-size: 11px; color: var(--text); margin: 3px 0 8px; }
.ct-links { display: flex; flex-direction: column; gap: 4px; }
.ct-link { font-size: 9px; color: var(--orange); text-decoration: none; padding: 5px 8px; border: 1px solid var(--orange-border); border-radius: 3px; text-align: center; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.ct-link:hover { background: var(--orange-dim); }
.why-box { background: rgba(74,222,128,0.05); border: 1px solid rgba(74,222,128,0.18); border-radius: 4px; padding: 11px; }
.why-title { font-size: 8px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--green); margin-bottom: 6px; }
.why-box p { font-size: 11px; color: var(--text); line-height: 1.7; }
.map-link { display: block; text-align: center; padding: 10px; margin-top: 2px; background: var(--orange); color: #000; font-weight: 700; font-size: 12px; text-decoration: none; border-radius: 3px; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 2px; text-transform: uppercase; }
.map-link:hover { opacity: 0.88; }
.no-results { padding: 40px 20px; text-align: center; color: var(--muted); font-size: 11px; line-height: 2; }
</style>
</head>
<body>

<header>
  <div class="hdr-left">
    <span style="font-size:26px">&#x1F3D7;</span>
    <div class="hdr-brand">
      <h1>JN Service Construction Leads</h1>
      <p>New Construction &middot; 35mi Radius &middot; Braintree MA &middot; Auto-updated weekly</p>
    </div>
  </div>
  <div class="hdr-right">
    <span class="hdr-badge orange">NEW CONST ONLY</span>
    <span class="hdr-badge new" id="new-badge" style="display:none"></span>
    <div class="hdr-date" id="hdr-date"></div>
  </div>
</header>

<div class="main">
  <div class="sidebar">
    <div class="source-tabs">
      <div class="tab active" id="tab-all" onclick="setSource('')">
        <span class="n" id="cnt-all">-</span>All
      </div>
      <div class="tab" id="tab-Boston" onclick="setSource('Boston')" style="border-left:3px solid var(--orange)">
        <span class="n" id="cnt-Boston">-</span>Boston
      </div>
      <div class="tab t-cam" id="tab-Cambridge" onclick="setSource('Cambridge')" style="border-left:3px solid var(--amber)">
        <span class="n" id="cnt-Cambridge">-</span>Cambridge
      </div>
      <div class="tab t-som" id="tab-Somerville" onclick="setSource('Somerville')" style="border-left:3px solid var(--green)">
        <span class="n" id="cnt-Somerville">-</span>Somerville
      </div>
    </div>

    <div class="filters">
      <div class="filter-row">
        <input type="text" id="search" placeholder="Search address, applicant or company...">
      </div>
      <div class="filter-row">
        <select id="f-new">
          <option value="">All Permits</option>
          <option value="new">&#x1F525; New This Week Only</option>
        </select>
        <select id="f-dist">
          <option value="">Any Distance</option>
          <option value="5">Within 5mi</option>
          <option value="10">Within 10mi</option>
          <option value="20">Within 20mi</option>
          <option value="35">Within 35mi</option>
        </select>
      </div>
      <div class="filter-row">
        <select id="f-val">
          <option value="">Any Value</option>
          <option value="100000">$100k+</option>
          <option value="500000">$500k+</option>
          <option value="1000000">$1M+</option>
        </select>
        <select id="f-month">
          <option value="">All Months</option>
        </select>
      </div>
    </div>

    <div class="list-hdr">
      <span id="showing-count">Loading...</span>
      <span style="font-size:8px;letter-spacing:1px">NEWEST FIRST</span>
    </div>
    <div class="permit-list" id="permit-list"></div>
  </div>

  <div style="position:relative;flex:1;">
    <div id="map"></div>
    <div class="dp" id="dp">
      <div class="dp-hdr">
        <div>
          <h3 id="dp-title">Select a permit</h3>
          <span id="dp-sub"></span>
        </div>
        <button class="close-btn" onclick="closeDP()">&#x2715;</button>
      </div>
      <div class="dp-body" id="dp-body"></div>
    </div>
  </div>
</div>

<script>
var ALL = PERMITS_DATA_PLACEHOLDER;
var STATS = STATS_DATA_PLACEHOLDER;
var activeSource = '';

// Header
var lastUpdated = STATS.last_updated || '';
var newCount = STATS.new_this_week || 0;
document.getElementById('hdr-date').innerHTML = 'Last updated: ' + lastUpdated + '<br>Total: ' + STATS.total + ' permits';
if (newCount > 0) {
  var nb = document.getElementById('new-badge');
  nb.textContent = newCount + ' NEW THIS WEEK';
  nb.style.display = '';
}

// Tab counts
document.getElementById('cnt-all').textContent = ALL.length;
['Boston','Cambridge','Somerville'].forEach(function(s) {
  document.getElementById('cnt-' + s).textContent = ALL.filter(function(p){ return p.source===s; }).length;
});

// Month filter options
var months = [...new Set(ALL.map(function(p){ return p.issued_date ? p.issued_date.substring(0,7) : ''; }).filter(Boolean))].sort().reverse();
var msel = document.getElementById('f-month');
months.forEach(function(m) {
  var o = document.createElement('option');
  o.value = m; o.textContent = m;
  msel.appendChild(o);
});

// MAP
var map = L.map('map', {center:[42.2084,-70.9978], zoom:11});
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution:'&copy; CartoDB &copy; OpenStreetMap', subdomains:'abcd', maxZoom:19
}).addTo(map);
L.circleMarker([42.2084,-70.9978],{radius:9,color:'#f97316',fillColor:'#f97316',fillOpacity:0.2,weight:2})
  .addTo(map).bindTooltip('Braintree',{permanent:true,direction:'top'});
L.circle([42.2084,-70.9978],{radius:56327,color:'#f97316',fill:false,weight:1,dashArray:'5,5',opacity:0.25}).addTo(map);
var markerLayer = L.layerGroup().addTo(map);

var SRC_COLOR = {Boston:'#f97316', Cambridge:'#fbbf24', Somerville:'#4ade80'};

function fmt(n) {
  try {
    n = parseFloat(n);
    if (isNaN(n)||n===0) return 'N/A';
    if (n>=1000000) return '$'+(n/1000000).toFixed(1)+'M';
    if (n>=1000) return '$'+(n/1000).toFixed(0)+'k';
    return '$'+n.toLocaleString();
  } catch(e) { return 'N/A'; }
}

function sv(v) {
  if (!v || v==='N/A' || v==='nan' || v==='None') return '';
  return String(v).trim();
}

function renderMap(permits) {
  markerLayer.clearLayers();
  permits.forEach(function(p) {
    if (!p.lat||!p.lon) return;
    var color = SRC_COLOR[p.source]||'#f97316';
    var isNew = p.is_new;
    var m = L.circleMarker([p.lat,p.lon], {
      radius: isNew ? 10 : 7,
      color: isNew ? '#ffffff' : color,
      fillColor: color,
      fillOpacity: isNew ? 1 : 0.75,
      weight: isNew ? 2 : 1
    });
    m.on('click', function(){ showDP(p); });
    m.bindPopup(
      '<div style="font-family:monospace;font-size:11px;line-height:1.6;min-width:190px;background:#1a1710;color:#f0ece4;padding:4px">' +
      (isNew ? '<b style="color:#f97316">&#x1F525; NEW THIS WEEK</b><br>' : '') +
      '<b style="color:'+color+'">' + p.source + '</b> &bull; ' + p.description + '<br>' +
      '<b>' + p.address + '</b><br>' +
      '&#x1F4B0; ' + fmt(p.valuation_num) + ' &bull; &#x1F4CD; ' + p.dist + 'mi' +
      '</div>'
    );
    markerLayer.addLayer(m);
  });
}

function renderList(permits) {
  document.getElementById('showing-count').textContent = permits.length + ' permits';
  var list = document.getElementById('permit-list');
  if (!permits.length) {
    list.innerHTML = '<div class="no-results">No permits match your filters.</div>';
    return;
  }
  var html = '';
  permits.forEach(function(p) {
    var company = sv(p.company_name);
    var applicant = sv(p.applicant_name);
    var firstWhy = p.why_visit ? p.why_visit.split(' | ')[0] : '';
    var isNew = p.is_new;
    html += '<div class="card src-' + p.source + (isNew?' is-new':'') + '" data-id="' + p.id + '">' +
      '<div class="card-top">' +
        '<div class="card-addr">' + p.address + '</div>' +
        '<span class="src-pill ' + p.source + '">' + p.source + '</span>' +
      '</div>' +
      '<div class="card-type">' + p.description + '</div>' +
      (applicant ? '<div class="card-company">&#x1F464; ' + applicant + (company?' &bull; <b>'+company+'</b>':'') + '</div>' : '') +
      '<div class="card-svcs">&#x1F527; ' + (p.services_needed||'') + '</div>' +
      '<div class="card-meta">' +
        '<span>&#x1F4CD; ' + p.dist + 'mi</span>' +
        '<span>&#x1F4B0; ' + fmt(p.valuation_num) + '</span>' +
        '<span>&#x1F4C5; ' + p.issued_date + '</span>' +
      '</div>' +
      (firstWhy ? '<div class="card-why">&#x2192; ' + firstWhy + '</div>' : '') +
    '</div>';
  });
  list.innerHTML = html;
  // attach clicks
  var cards = list.querySelectorAll('.card');
  permits.forEach(function(p, i) {
    if (cards[i]) cards[i].addEventListener('click', function(){ showDP(p); });
  });
}

function showDP(p) {
  var color = SRC_COLOR[p.source]||'#f97316';
  var company = sv(p.company_name);
  var applicant = sv(p.applicant_name);
  var chips = '';
  (p.services_needed||'').split(', ').forEach(function(s){ if(s.trim()) chips+='<span class="chip">'+s.trim()+'</span>'; });
  var whyParts = '';
  (p.why_visit||'').split(' | ').forEach(function(r){ if(r.trim()) whyParts+='&bull; '+r.trim()+'<br>'; });
  var mapsUrl = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(p.address+' MA');
  var lookupName = encodeURIComponent(company||applicant||'');
  var sosUrl = 'https://corp.sec.state.ma.us/CorpWeb/CorpSearch/CorpSearch.aspx?QUERY=' + lookupName;
  var licUrl = 'https://license.reg.state.ma.us/public/licque.asp?query=individual&BOARD=CS&sSearch=' + encodeURIComponent(applicant||'');

  document.getElementById('dp-title').textContent = p.address;
  document.getElementById('dp-sub').textContent = p.source + ' \u00b7 ' + p.description + ' \u00b7 ' + p.issued_date;
  document.getElementById('dp').style.borderLeftColor = color;

  var b = '';
  if (p.is_new) b += '<div class="new-banner">&#x1F525; NEW THIS WEEK &mdash; Added ' + (p.added_week||'') + '</div>';
  b += '<div class="dp-row"><span class="dp-key">Project Value</span><span class="dp-val big">' + fmt(p.valuation_num) + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Source</span><span class="dp-val" style="color:'+color+';font-weight:600">'+p.source+'</span></div>';
  b += '<hr class="dp-divider">';
  b += '<div class="dp-row"><span class="dp-key">Your Services That Apply</span><div class="chips">' + chips + '</div></div>';
  b += '<hr class="dp-divider">';
  b += '<div class="dp-row"><span class="dp-key">Permit Type</span><span class="dp-val">' + p.description + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Address</span><span class="dp-val">' + p.address + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Occupancy</span><span class="dp-val">' + (p.occ||'N/A') + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Permit #</span><span class="dp-val">' + p.permit_num + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Issued</span><span class="dp-val">' + p.issued_date + '</span></div>';
  b += '<div class="dp-row"><span class="dp-key">Distance</span><span class="dp-val">' + p.dist + ' miles from Braintree</span></div>';
  if (p.comments) { b += '<hr class="dp-divider"><div class="dp-row"><span class="dp-key">Description</span><span class="dp-val" style="font-size:10px;line-height:1.5">'+p.comments+'</span></div>'; }
  b += '<hr class="dp-divider">';
  if (applicant||company) {
    b += '<div class="contractor-box">';
    b += '<div class="contractor-title">&#x1F464; Applicant / Contractor</div>';
    if (applicant) b += '<div class="contractor-name">' + applicant + '</div>';
    if (company) b += '<div class="contractor-company">&#x1F3E2; ' + company + '</div>';
    b += '<div style="font-size:9px;color:var(--muted);margin-bottom:8px">Verify registration &amp; license:</div>';
    b += '<div class="ct-links">';
    b += '<a class="ct-link" href="'+sosUrl+'" target="_blank">&#x1F3E2; MA Secretary of State</a>';
    b += '<a class="ct-link" href="'+licUrl+'" target="_blank">&#x1FA96; MA Contractor License</a>';
    b += '</div></div>';
  }
  b += '<div class="why-box"><div class="why-title">&#x1F4A1; Why Visit?</div><p>'+(whyParts||'New construction permit in your zone.')+'</p></div>';
  b += '<a class="map-link" href="'+mapsUrl+'" target="_blank">&#x1F4CD; Open in Google Maps</a>';

  document.getElementById('dp-body').innerHTML = b;
  document.getElementById('dp').classList.add('open');
  if (p.lat&&p.lon) map.panTo([p.lat,p.lon]);
}

function closeDP() { document.getElementById('dp').classList.remove('open'); }

function setSource(src) {
  activeSource = src;
  ['','Boston','Cambridge','Somerville'].forEach(function(s) {
    var id = s==='' ? 'tab-all' : 'tab-'+s;
    var el = document.getElementById(id);
    if (el) el.classList.toggle('active', s===src);
  });
  applyFilters();
}

function applyFilters() {
  var search = document.getElementById('search').value.toLowerCase();
  var onlyNew = document.getElementById('f-new').value === 'new';
  var dist = parseFloat(document.getElementById('f-dist').value)||999;
  var val = parseFloat(document.getElementById('f-val').value)||0;
  var month = document.getElementById('f-month').value;

  var filtered = ALL.filter(function(p) {
    if (activeSource && p.source!==activeSource) return false;
    if (onlyNew && !p.is_new) return false;
    var s = ((p.address||'')+' '+(p.applicant_name||'')+' '+(p.company_name||'')+' '+(p.city||'')).toLowerCase();
    if (search && s.indexOf(search)===-1) return false;
    if ((p.dist||999)>dist) return false;
    if ((p.valuation_num||0)<val) return false;
    if (month && (!p.issued_date||p.issued_date.substring(0,7)!==month)) return false;
    return true;
  });

  renderList(filtered);
  renderMap(filtered);
}

['search','f-new','f-dist','f-val','f-month'].forEach(function(id) {
  var el = document.getElementById(id);
  if (el) { el.addEventListener('input',applyFilters); el.addEventListener('change',applyFilters); }
});

applyFilters();
</script>
</body>
</html>"""

    # Inject data
    html = html.replace("PERMITS_DATA_PLACEHOLDER", json.dumps(permits))
    html = html.replace("STATS_DATA_PLACEHOLDER", json.dumps(stats))

    os.makedirs("docs", exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard built: {OUT_FILE} ({len(html)//1024}KB)")
    print(f"Permits: {stats['total']} total, {stats.get('new_this_week',0)} new this week")

if __name__ == "__main__":
    build()
