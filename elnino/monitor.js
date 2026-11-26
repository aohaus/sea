'use strict';

const cards = [...document.querySelectorAll('[data-series]')];

function addBulletin(parent, record) {
  const summary = document.createElement('p');
  summary.textContent = record.summary;
  const metadata = document.createElement('p');
  metadata.className = 'muted';
  metadata.textContent = `発表 ${record.published} ／ 対象 ${record.period} ／ ${record.area}`;
  const source = document.createElement('a');
  source.href = record.url;
  source.textContent = `${record.source} ↗`;
  parent.append(summary, metadata, source);
}

async function loadObservations() {
  try {
    const response = await fetch('observations.json');
    if (!response.ok) throw new Error('Observation data unavailable');
    const records = await response.json();
    const history = document.querySelector('#history-list');
    for (const card of cards) {
      const series = records.filter(record => record.series === card.dataset.series)
        .sort((first, second) => second.published.localeCompare(first.published));
      const [latest, ...past] = series;
      if (!latest) continue;
      const bulletin = document.createElement('div');
      bulletin.className = 'stack';
      addBulletin(bulletin, latest);
      card.querySelector('.bulletin').replaceWith(bulletin);
      for (const record of past) {
        const item = document.createElement('article');
        item.className = 'card';
        const heading = document.createElement('h3');
        heading.textContent = card.querySelector('h3').textContent;
        item.append(heading);
        addBulletin(item, record);
        history.append(item);
      }
    }
    document.querySelector('#history').hidden = !history.children.length;
  } catch {
    for (const placeholder of document.querySelectorAll('.bulletin')) {
      placeholder.textContent = '記録を読み込めません。公式発表を確認してください。';
    }
  }
}

loadObservations();
