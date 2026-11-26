'use strict';

const plan = document.querySelector('#plan');
const statusMessage = document.querySelector('#save-status');
const fields = [...plan.querySelectorAll('[name]')];
const storageKey = 'sea-elnino-office-plan';
const month = plan.elements.namedItem('month');

const malaysiaDate = new Intl.DateTimeFormat('en', {
  timeZone: 'Asia/Kuala_Lumpur', year: 'numeric', month: 'numeric',
}).formatToParts();
const yearNumber = Number(malaysiaDate.find(part => part.type === 'year').value);
const monthNumber = Number(malaysiaDate.find(part => part.type === 'month').value);
month.value = monthNumber === 12
  ? `${yearNumber + 1}-01`
  : `${yearNumber}-${String(monthNumber + 1).padStart(2, '0')}`;

try {
  const saved = JSON.parse(localStorage.getItem(storageKey));
  for (const field of fields) {
    if (typeof saved?.[field.name] === 'string') field.value = saved[field.name];
  }
} catch {
  statusMessage.textContent = '保存済みの入力内容を読み込めませんでした。';
}

plan.addEventListener('input', () => {
  try {
    localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(new FormData(plan))));
    statusMessage.textContent = 'このブラウザーに保存しました。';
  } catch {
    statusMessage.textContent = 'ブラウザーに保存できません。印刷またはPDF保存を使ってください。';
  }
});
plan.addEventListener('submit', event => event.preventDefault());

document.querySelector('#print').addEventListener('click', () => window.print());
window.addEventListener('beforeprint', () => {
  for (const field of fields) {
    const value = document.createElement('span');
    value.className = 'print-value';
    value.textContent = field.value || '未記入';
    field.after(value);
  }
  plan.classList.add('print-ready');
});
window.addEventListener('afterprint', () => {
  for (const value of plan.querySelectorAll('.print-value')) value.remove();
  plan.classList.remove('print-ready');
});
