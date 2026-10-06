document.addEventListener('DOMContentLoaded',()=>{
  const toggle=document.querySelector('.nav-toggle');
  const nav=document.querySelector('#site-nav');
  if(toggle&&nav){
    toggle.addEventListener('click',()=>{
      const open=nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded',String(open));
      toggle.setAttribute('aria-label',open?'Close navigation':'Open navigation');
    });
    nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');}));
  }
  document.querySelectorAll('.toast-close').forEach(btn=>btn.addEventListener('click',()=>btn.closest('.toast')?.remove()));
  const startup=document.getElementById('startup');
  if(startup){setTimeout(()=>startup.remove(),2200);}

  // Graceful feedback for ordinary POST forms. Server-side redirects/flash messages
  // remain authoritative, while the user immediately sees that the action is running.
  document.querySelectorAll('form').forEach(form=>{
    if(form.dataset.noProgress==='true') return;
    form.addEventListener('submit',()=>{
      if(form.dataset.submitted==='true') return;
      form.dataset.submitted='true';
      const submitters=form.querySelectorAll('button[type="submit"],input[type="submit"]');
      submitters.forEach(btn=>{btn.dataset.busy='true';btn.disabled=true;btn.dataset.originalText=btn.textContent;btn.textContent='Processing…';});
      let progress=form.querySelector('.form-progress');
      if(!progress){progress=document.createElement('div');progress.className='form-progress';progress.setAttribute('role','status');progress.innerHTML='<i aria-hidden="true"></i><span>Processing your request. Please wait…</span>';form.prepend(progress);}
      progress.classList.add('is-visible');
    });
  });
});
