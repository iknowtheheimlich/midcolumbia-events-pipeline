// ==UserScript==
// @name         Cargo Collector for AllEvents
// @namespace    https://github.com/iknowtheheimlich/midcolumbia-events-pipeline
// @version      0.1.0
// @description  Export visible AllEvents event cards to Cargo Harvester JSON.
// @match        https://allevents.in/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  function abs(url) {
    try { return new URL(url, location.href).href; } catch { return url || ''; }
  }

  function probableEventUrl(url) {
    if (!/allevents\.in/i.test(url)) return false;
    if (/\/(all|events|tickets|calendar|signin|login|signup|help|support|about|organizer|create-event|add-event|pricing|sell-tickets)(\?|$|\/)/i.test(url)) return false;
    if (/\/(music|concerts|parties|performances|comedy|dance|entertainment|fine-arts|theatre|theater|literary-art|crafts|photography|cooking|arts|food-drinks|business|festivals|meetups|sports|workshops|webinars|kids|health-wellness|trips-adventures|4th-of-july|best-events-this-weekend)(\?|$|\/)/i.test(url)) return false;
    const slug = url.split('/').filter(Boolean).pop() || '';
    return /\d{6,}/.test(url) || slug.length >= 12;
  }

  function cardFor(el) {
    let cur = el;
    for (let i = 0; i < 8 && cur; i++) {
      const text = (cur.innerText || '').trim();
      if (text.length > 35) return cur;
      cur = cur.parentElement;
    }
    return el;
  }

  function imgFor(card) {
    const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll('img') : []);
    for (const img of imgs) {
      const url = abs(img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '');
      if (url && !/logo|icon|avatar|default|blank|svg/i.test(url)) return url;
    }
    return '';
  }

  function collectVisibleEvents() {
    const seen = new Set();
    const out = [];
    const anchors = Array.from(document.querySelectorAll('a[href]'));

    for (const a of anchors) {
      const url = abs(a.getAttribute('href') || a.href || '').split('?')[0].replace(/\/$/, '');
      if (!probableEventUrl(url) || seen.has(url)) continue;
      seen.add(url);
      const card = cardFor(a);
      out.push({
        url,
        listing_text: (card.innerText || a.innerText || '').trim(),
        listing_image_url: imgFor(card),
        collector_url: location.href,
        collected_at: new Date().toISOString()
      });
    }
    return out;
  }

  function downloadJson(events) {
    const payload = {
      source: 'Cargo Harvester browser collector',
      page_url: location.href,
      collected_at: new Date().toISOString(),
      count: events.length,
      events
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'cargo_events_' + new Date().toISOString().slice(0, 10) + '.json';
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      URL.revokeObjectURL(link.href);
      link.remove();
    }, 500);
  }

  function makeButton() {
    if (document.getElementById('cargo-collector-button')) return;
    const button = document.createElement('button');
    button.id = 'cargo-collector-button';
    button.textContent = 'CARGO';
    button.title = 'Export visible AllEvents cards to Cargo Harvester JSON';
    button.style.position = 'fixed';
    button.style.top = '72px';
    button.style.right = '18px';
    button.style.zIndex = '999999';
    button.style.padding = '10px 14px';
    button.style.border = '0';
    button.style.borderRadius = '999px';
    button.style.background = '#22242b';
    button.style.color = '#fff';
    button.style.fontWeight = '700';
    button.style.fontSize = '13px';
    button.style.boxShadow = '0 2px 10px rgba(0,0,0,.25)';
    button.style.cursor = 'pointer';

    button.addEventListener('click', () => {
      const events = collectVisibleEvents();
      downloadJson(events);
      button.textContent = 'CARGO: ' + events.length;
      setTimeout(() => { button.textContent = 'CARGO'; }, 2500);
    });

    document.body.appendChild(button);
  }

  makeButton();
  setTimeout(makeButton, 1500);
})();
