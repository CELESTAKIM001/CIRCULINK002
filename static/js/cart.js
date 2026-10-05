(function(){
  const KEY='circulink_cart_v1';
  const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch{return[]}};
  const write=items=>localStorage.setItem(KEY,JSON.stringify(items));
  const money=n=>'KES '+Number(n||0).toLocaleString('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2});
  const render=()=>{
    const items=read();
    const count=document.getElementById('cart-count');
    const box=document.getElementById('cart-items');
    const total=document.getElementById('cart-total');
    const json=document.getElementById('cart-json');
    if(count) count.textContent=items.reduce((s,x)=>s+Number(x.quantity||1),0);
    if(total) total.textContent=money(items.reduce((s,x)=>s+(Number(x.line_total)||0),0));
    if(json) json.value=JSON.stringify(items);
    if(box){
      box.innerHTML=items.length?items.map((x,i)=>`<div class="cart-row"><div><strong>${escapeHtml(x.title)}</strong><small>${money(x.price)} / ${escapeHtml(x.unit||'unit')}</small></div><div class="cart-row-actions"><span>${money(x.line_total)}</span><button type="button" class="remove-cart" data-index="${i}" aria-label="Remove ${escapeHtml(x.title)}">Remove</button></div></div>`).join(''):'<p class="muted">Your cart is empty.</p>';
      box.querySelectorAll('.remove-cart').forEach(btn=>btn.addEventListener('click',()=>{const a=read();a.splice(Number(btn.dataset.index),1);write(a);render();}));
    }
  };
  const escapeHtml=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  document.addEventListener('DOMContentLoaded',()=>{
    render();
    document.querySelectorAll('.add-cart').forEach(btn=>btn.addEventListener('click',()=>{
      const items=read();
      const id=btn.dataset.id;
      const existing=items.find(x=>x.id===id);
      if(existing){existing.quantity=Number(existing.quantity||1)+1;existing.line_total=Number(existing.price)*existing.quantity;}
      else items.push({id,title:btn.dataset.title,price:Number(btn.dataset.price),unit:btn.dataset.unit,quantity:1,line_total:Number(btn.dataset.price)});
      write(items);render();openCart();
    }));
    document.getElementById('cart-open')?.addEventListener('click',openCart);
    document.getElementById('cart-close')?.addEventListener('click',closeCart);
    document.getElementById('cart-checkout')?.addEventListener('submit',e=>{if(!read().length){e.preventDefault();openCart();}});
  });
  function openCart(){const p=document.getElementById('cart-panel');if(p){p.hidden=false;document.body.classList.add('cart-open');render();}}
  function closeCart(){const p=document.getElementById('cart-panel');if(p){p.hidden=true;document.body.classList.remove('cart-open');}}
})();
