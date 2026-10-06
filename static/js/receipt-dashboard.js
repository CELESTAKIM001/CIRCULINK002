(function(){
  const search=document.getElementById('receipt-search');
  const table=document.getElementById('receipt-table');
  if(!table)return;
  const rows=Array.from(table.querySelectorAll('tbody tr.receipt-row'));
  const count=document.getElementById('receipt-result-count');
  function filter(){const q=(search?.value||'').trim().toLowerCase();let visible=0;rows.forEach(row=>{const detail=row.nextElementSibling;const show=!q||(row.dataset.search||'').toLowerCase().includes(q)||row.innerText.toLowerCase().includes(q);row.hidden=!show;if(detail&&detail.classList.contains('ice-detail-row')&&!show)detail.hidden=true;if(show)visible++;});if(count)count.textContent=visible+' record'+(visible===1?'':'s');}
  search?.addEventListener('input',filter);
  table.addEventListener('click',function(event){const button=event.target.closest('[data-receipt-open]');if(!button)return;const detail=document.getElementById(button.dataset.receiptOpen);if(!detail)return;const opening=detail.hidden;detail.hidden=!opening;button.setAttribute('aria-expanded',String(opening));button.innerHTML=opening?'Hide record <span>↑</span>':'View record <span>→</span>';});
})();
