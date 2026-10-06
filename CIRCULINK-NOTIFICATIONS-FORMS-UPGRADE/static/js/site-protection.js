(function(){
  "use strict";
  const block=(e)=>{ e.preventDefault(); return false; };
  document.addEventListener("contextmenu", block, {capture:true});
  document.addEventListener("dragstart", function(e){ if(e.target && e.target.tagName === "IMG") e.preventDefault(); }, {capture:true});
  document.addEventListener("selectstart", function(e){
    const tag=(e.target && e.target.tagName)||"";
    if(!/INPUT|TEXTAREA|SELECT/.test(tag)) e.preventDefault();
  }, {capture:true});
  document.addEventListener("copy", function(e){
    const tag=(e.target && e.target.tagName)||"";
    if(!/INPUT|TEXTAREA/.test(tag)){ e.preventDefault(); }
  }, {capture:true});
  document.addEventListener("cut", function(e){
    const tag=(e.target && e.target.tagName)||"";
    if(!/INPUT|TEXTAREA/.test(tag)) e.preventDefault();
  }, {capture:true});
  document.addEventListener("keydown", function(e){
    if((e.ctrlKey||e.metaKey) && /[ucsa]/i.test(e.key) && !/INPUT|TEXTAREA/.test((e.target&&e.target.tagName)||"")) e.preventDefault();
    if(e.key === "F12" || (e.ctrlKey && e.shiftKey && /I|J|C/i.test(e.key))) e.preventDefault();
  }, {capture:true});
})();
