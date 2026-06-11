// ════════════════════════════════════════════════════
//  THEME
// ════════════════════════════════════════════════════

function setTheme(isLight){
  document.documentElement.setAttribute('data-theme', isLight?'light':'dark');
  document.getElementById('auth-thm').checked = isLight;
  document.getElementById('app-thm').checked  = isLight;
  localStorage.setItem('cg-theme', isLight?'light':'dark');
}
(function(){
  const t = localStorage.getItem('cg-theme')||'dark';
  document.documentElement.setAttribute('data-theme',t);
  const l = t==='light';
  document.getElementById('auth-thm').checked = l;
  document.getElementById('app-thm').checked  = l;
})();

// ════════════════════════════════════════════════════
//  AUTH CARD SWITCHER
// ════════════════════════════════════════════════════
const CARDS = ['login-card','signup-card','forgot-card'];
function show(id){
  CARDS.forEach(c=>document.getElementById(c).style.display='none');
  document.getElementById(id).style.display='block';
  ['lerr','serr','ferr','fok'].forEach(e=>{
    const el=document.getElementById(e);
    if(el){el.textContent='';el.classList.remove('show');}
  });
}

// ════════════════════════════════════════════════════
//  STATE
// ════════════════════════════════════════════════════
let CU=null,GD=null,SD=null,RD=null,MD=null,FD=null;
let CM=[],allSess=[],curSid=null;
let nodePos={};
let tr={x:0,y:0,s:1};
let panning=false,panSt={},trSt={};
let activeTab='graph';
const ZF=0.28,ZC=0.55,ZN=0.9;

// ════════════════════════════════════════════════════
//  AUTH
// ════════════════════════════════════════════════════
async function checkAuth(){
  try{
    const r=await fetch('/api/auth/me',{credentials:'include'});
    if(!r.ok)throw new Error('not ok');
    const d=await r.json();
    if(d.user){CU=d.user;showApp();}else showAuthScreen();
  }catch{showAuthScreen();}
}
function showAuthScreen(){
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app-screen').classList.remove('visible');
}
function showApp(){
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app-screen').classList.add('visible');
  document.getElementById('u-nm').textContent=CU.name;
  document.getElementById('u-em').textContent=CU.email;
  document.getElementById('u-av').textContent=CU.name[0].toUpperCase();
  loadSessions();
}
async function doLogin(){
  const email=document.getElementById('l-email').value.trim();
  const pw=document.getElementById('l-pw').value;
  const err=document.getElementById('lerr');
  if(!email||!pw){err.textContent='Please fill all fields.';err.classList.add('show');return;}
  try{
    const r=await fetch('/api/auth/login',{method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email,password:pw})});
    const d=await r.json();
    if(d.error){err.textContent=d.error;err.classList.add('show');return;}
    CU=d.user;showApp();
  }catch{err.textContent='Connection error.';err.classList.add('show');}
}
async function doSignup(){
  const name=document.getElementById('s-name').value.trim();
  const email=document.getElementById('s-email').value.trim();
  const pw=document.getElementById('s-pw').value;
  const err=document.getElementById('serr');
  if(!name||!email||!pw){err.textContent='Please fill all fields.';err.classList.add('show');return;}
  try{
    const r=await fetch('/api/auth/signup',{method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,email,password:pw})});
    const d=await r.json();
    if(d.error){err.textContent=d.error;err.classList.add('show');return;}
    CU=d.user;showApp();
  }catch{err.textContent='Connection error.';err.classList.add('show');}
}
async function doForgot(){
  const email=document.getElementById('f-email').value.trim();
  const pw=document.getElementById('f-pw').value;
  const pw2=document.getElementById('f-pw2').value;
  const err=document.getElementById('ferr');
  const ok=document.getElementById('fok');
  err.classList.remove('show');ok.classList.remove('show');
  if(!email||!pw||!pw2){err.textContent='Please fill all fields.';err.classList.add('show');return;}
  if(pw!==pw2){err.textContent='Passwords do not match.';err.classList.add('show');return;}
  if(pw.length<6){err.textContent='Password must be at least 6 characters.';err.classList.add('show');return;}
  try{
    const r=await fetch('/api/auth/forgot-password',{method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email,new_password:pw})});
    const d=await r.json();
    if(d.error){err.textContent=d.error;err.classList.add('show');return;}
    ok.textContent=d.message||'Password updated! You can now sign in.';
    ok.classList.add('show');
    setTimeout(()=>show('login-card'),2200);
  }catch{err.textContent='Connection error.';err.classList.add('show');}
}
async function doLogout(){
  await fetch('/api/auth/logout',{method:'POST',credentials:'include'});
  CU=null;allSess=[];curSid=null;
  GD=null;SD=null;RD=null;MD=null;CM=[];
  newAnalysisUI();showAuthScreen();
}

// ════════════════════════════════════════════════════
//  SESSIONS
// ════════════════════════════════════════════════════
async function loadSessions(){
  try{
    const r=await fetch('/api/sessions',{credentials:'include'});
    if(!r.ok){console.warn('sessions not loaded',r.status);return;}
    const d=await r.json();
    allSess=d.sessions||[];renderHist();
  }catch(e){console.warn('loadSessions:',e);}
}
async function saveSess(){
  if(!curSid||!GD)return;
  const p={
    name:SD?.files?.[0]||'Analysis',
    language:SD?.language||'python',
    summary:SD,graphData:GD,riskData:RD,markdownDoc:MD,
    chatMessages:CM,
    label:new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})
  };
  try{
    const r=await fetch(`/api/sessions/${curSid}`,{
      method:'PUT',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(p)});
    if(!r.ok)return;
    const idx=allSess.findIndex(s=>s.sid===curSid);
    const obj={...p,sid:curSid,uid:CU?.uid};
    if(idx>=0)allSess[idx]=obj;else allSess.unshift(obj);
    renderHist();
  }catch(e){console.warn('saveSess:',e);}
}
async function openSess(sid){
  try{
    const r=await fetch(`/api/sessions/${sid}`,{credentials:'include'});
    if(!r.ok){showErr('Could not load session.');return;}
    const d=await r.json();
    if(d.error){showErr(d.error);return;}
    const s=d.session;
    curSid=sid;GD=s.graphData;SD=s.summary;
    RD=s.riskData;MD=s.markdownDoc;
    CM=s.chatMessages||[];nodePos={};
    setupStats();setupBadge();
    document.getElementById('file-label').textContent=s.name||'Loaded';
    document.getElementById('chat-inp').disabled=false;
    document.getElementById('chat-send').disabled=false;
   document.getElementById('tb-stats').style.display='flex';
    document.getElementById('zm-ctrls').style.display='flex';
    document.getElementById('panel-tabs').style.display='flex';
    document.getElementById('btn-fullscreen').style.display='flex';
    document.getElementById('chat-drawer').style.display='';
    const mc=document.getElementById('chat-msgs');
    mc.innerHTML='';
    if(!CM.length) mc.innerHTML=`<div class="chat-welcome">Loaded: <strong>${esc(s.name)}</strong> — ask anything about it.</div>`;
    else CM.forEach(m=>appendMsg(m.role,m.content));
    document.getElementById('upload-zone').classList.add('hidden');
    document.getElementById('gsvg-wrap').classList.add('visible');
    document.getElementById('legend').style.display='block';
    document.getElementById('zoom-ind').classList.add('visible');
    document.getElementById('minimap').classList.add('visible');
    if(RD)updateRiskBadge(RD);
    if(RD)renderRisk(RD);
    if(MD)renderDocs(MD);
    renderGraph();
    switchTab('graph');
    renderHist();
  }catch(e){showErr('Failed to load: '+e.message);}
}
async function delSess(sid,evt){
  evt.stopPropagation();
  if(!confirm("Are you sure you want to permanently delete this analysis?")) return;
  await fetch(`/api/sessions/${sid}`,{method:'DELETE',credentials:'include'});
  allSess=allSess.filter(s=>s.sid!==sid);
  if(curSid===sid)newAnalysis();
  renderHist();
}

// ════════════════════════════════════════════════════
//  FILE UPLOAD
// ════════════════════════════════════════════════════
function dov(e){e.preventDefault();document.getElementById('upl-card').classList.add('drag-over');}
function dol(){document.getElementById('upl-card').classList.remove('drag-over');}
function dod(e){e.preventDefault();dol();const f=e.dataTransfer.files[0];if(f)upload(f);}
function onFileSelect(e){const f=e.target.files[0];if(f)upload(f);}

async function upload(file){
  const lov=document.getElementById('lov');
  const lsub=document.getElementById('lsub');
  lov.classList.remove('hidden');
  lsub.textContent='Uploading…';
  const fd=new FormData();fd.append('file',file);
  try{
    lsub.textContent='Parsing AST · computing risk…';
    const r=await fetch('/api/analyze',{method:'POST',body:fd,credentials:'include'});
    // Always parse as text first to catch HTML error pages
    const text=await r.text();
    let data;
    try{data=JSON.parse(text);}
    catch{lov.classList.add('hidden');showErr('Server error — check that Flask is running.');return;}
    if(data.error){lov.classList.add('hidden');showErr(data.error);return;}
    GD=data.graph;SD=data.summary;RD=data.risk_report;MD=data.markdown_doc;FD=data.files_data;
    CM=[];curSid='sess_'+Date.now();nodePos={};
    setupStats();setupBadge();
    document.getElementById('file-label').textContent=file.name;
    document.getElementById('chat-inp').disabled=false;
    document.getElementById('chat-send').disabled=false;
    document.getElementById('zm-ctrls').style.display='none';
  document.getElementById('panel-tabs').style.display='none';
  document.getElementById('btn-fullscreen').style.display='none';
  document.getElementById('lang-badge').style.display='none';
  document.getElementById('chat-drawer').style.display='none';
    document.getElementById('chat-msgs').innerHTML=
      `<div class="chat-welcome">Loaded <strong>${esc(file.name)}</strong> — ${SD.total_functions} functions, ${SD.total_call_edges} user-defined calls. Risk score: ${RD.summary.health_score}/100. Ask anything!</div>`;
    lsub.textContent='Rendering graph…';
    await new Promise(r=>setTimeout(r,40));
    document.getElementById('upload-zone').classList.add('hidden');
    document.getElementById('gsvg-wrap').classList.add('visible');
    document.getElementById('legend').style.display='block';
    document.getElementById('zoom-ind').classList.add('visible');
    document.getElementById('minimap').classList.add('visible');
    renderGraph();updateRiskBadge(RD);renderRisk(RD);renderDocs(MD);
    lov.classList.add('hidden');
    switchTab('graph');
    allSess.unshift({sid:curSid,uid:CU?.uid,name:file.name,language:SD.language,
      summary:SD,graphData:GD,riskData:RD,markdownDoc:MD,chatMessages:[],
      label:new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})});
    await saveSess();renderHist();
  }catch(e){lov.classList.add('hidden');showErr('Upload failed: '+e.message);}
}

// ════════════════════════════════════════════════════
//  PANEL TABS
// ════════════════════════════════════════════════════
function switchTab(tab){
  activeTab=tab;
  ['graph','risk','docs'].forEach(t=>document.getElementById('tab-'+t)?.classList.toggle('active',t===tab));
  document.getElementById('risk-panel').classList.toggle('visible',tab==='risk');
  document.getElementById('docs-panel').classList.toggle('visible',tab==='docs');
  
  const showGraphUI = (tab==='graph' && GD);
  document.getElementById('zm-ctrls').style.display = showGraphUI ? 'flex' : 'none';
  document.getElementById('legend').style.display = showGraphUI ? 'block' : 'none';
  if(showGraphUI) {
      document.getElementById('zoom-ind').classList.add('visible');
      document.getElementById('minimap').classList.add('visible');
  } else {
      document.getElementById('zoom-ind').classList.remove('visible');
      document.getElementById('minimap').classList.remove('visible');
  }
}
function updateRiskBadge(rr){
  const b=document.getElementById('risk-badge');
  const n=rr.summary.dead_functions_count+rr.summary.high_complexity_count;
  b.textContent=n;b.style.display=n>0?'inline-flex':'none';
}

// ════════════════════════════════════════════════════
//  RISK PANEL RENDER
// ════════════════════════════════════════════════════
function renderRisk(rr){
  const s=rr.summary,h=s.health_score;
  const hb=document.getElementById('risk-health-badge');
  hb.textContent=`${h}/100 ${h>=75?'🟢 Healthy':h>=50?'🟡 Moderate':'🔴 High Risk'}`;
  hb.className=`health-badge ${h>=75?'hg':h>=50?'hm':'hb'}`;
  let html='';
  html+=`<div class="risk-grid">
    <div class="rmc"><div class="rmc-v" style="color:${h>=75?'#10b981':h>=50?'#f59e0b':'#ef4444'}">${h}</div><div class="rmc-l">Health Score</div><div class="rmc-s">out of 100</div></div>
    <div class="rmc"><div class="rmc-v" style="color:${s.dead_functions_count>0?'#6b7280':'#10b981'}">${s.dead_functions_count}</div><div class="rmc-l">Dead Functions</div><div class="rmc-s">never called</div></div>
    <div class="rmc"><div class="rmc-v" style="color:${s.high_complexity_count>0?'#ef4444':'#10b981'}">${s.high_complexity_count}</div><div class="rmc-l">Complex Fns</div><div class="rmc-s">cyclomatic ≥5</div></div>
    <div class="rmc"><div class="rmc-v" style="color:${s.high_fanin_count>0?'#f59e0b':'#10b981'}">${s.high_fanin_count}</div><div class="rmc-l">Deletion Risk</div><div class="rmc-s">many dependents</div></div>
    <div class="rmc"><div class="rmc-v">${s.avg_complexity}</div><div class="rmc-l">Avg Complexity</div><div class="rmc-s">cyclomatic</div></div>
    <div class="rmc"><div class="rmc-v" style="color:#3b82f6">${s.data_points_count}</div><div class="rmc-l">Data I/O Points</div><div class="rmc-s">DB/network/file</div></div>
  </div>`;
  // Dead
  html+=`<div class="rsec"><div class="rsec-h">⚫ Dead Code — Never Called <span>(${rr.dead_functions.length})</span></div>`;
  if(!rr.dead_functions.length){html+=`<div class="no-iss">✅ No dead functions found.</div>`;}
  else{
    html+=`<p style="font-size:10px;color:var(--muted);margin-bottom:9px">Defined but never invoked by any other user function. Safe to remove.</p>
    <table class="rtbl"><thead><tr><th>Function</th><th>File</th><th>Line</th><th>Complexity</th><th>Fan-out</th></tr></thead><tbody>`;
    rr.dead_functions.forEach(d=>{html+=`<tr><td><code>${esc(d.name)}</code> <span class="bdead">⚫ DEAD</span></td><td><code>${esc(d.filename)}</code></td><td>${d.lineno}</td><td>${d.complexity}</td><td>${d.fan_out}</td></tr>`;});
    html+=`</tbody></table>`;
  }
  html+=`</div>`;
  // Complexity
  html+=`<div class="rsec"><div class="rsec-h">🔴 Complexity Hotspots <span>(${rr.complexity_issues.length}) — cyclomatic ≥5</span></div>`;
  if(!rr.complexity_issues.length){html+=`<div class="no-iss">✅ No complexity issues.</div>`;}
  else{
    html+=`<table class="rtbl"><thead><tr><th>Sev</th><th>Function</th><th>File</th><th>Line</th><th>Complexity</th><th>LoC</th></tr></thead><tbody>`;
    rr.complexity_issues.forEach(c=>{
      const pct=Math.min(100,c.complexity*8);
      html+=`<tr><td><span class="${c.severity==='CRITICAL'?'bcrit':'bwarn'}">${c.severity==='CRITICAL'?'🔴':'🟡'} ${c.severity}</span></td>
        <td><code>${esc(c.name)}</code></td><td><code>${esc(c.filename)}</code></td><td>${c.lineno}</td>
        <td><strong>${c.complexity}</strong> <span class="rbar-w"><span class="rbar" style="width:${pct}%;background:${c.severity==='CRITICAL'?'#ef4444':'#f59e0b'}"></span></span></td>
        <td>${c.loc}</td></tr>`;
    });
    html+=`</tbody></table>`;
  }
  html+=`</div>`;
  // Fan-in
  html+=`<div class="rsec"><div class="rsec-h">⚡ Deletion Risk — Heavily Depended-On <span>(${rr.high_fanin_functions.length})</span></div>`;
  if(!rr.high_fanin_functions.length){html+=`<div class="no-iss">✅ No high deletion-risk functions.</div>`;}
  else{
    html+=`<p style="font-size:10px;color:var(--muted);margin-bottom:9px">Deleting these breaks multiple callers. Add tests before modifying.</p>
    <table class="rtbl"><thead><tr><th>Risk Score</th><th>Function</th><th>File</th><th>Callers</th><th>Complexity</th></tr></thead><tbody>`;
    rr.high_fanin_functions.forEach(f=>{
      const c=f.risk_score>=60?'#ef4444':f.risk_score>=30?'#f59e0b':'#3b82f6';
      html+=`<tr><td><strong style="color:${c}">${f.risk_score}/100</strong></td><td><code>${esc(f.name)}</code></td><td><code>${esc(f.filename)}</code></td><td>${f.fan_in}</td><td>${f.complexity}</td></tr>`;
    });
    html+=`</tbody></table>`;
  }
  html+=`</div>`;
  // God functions
  if(rr.god_functions&&rr.god_functions.length){
    html+=`<div class="rsec"><div class="rsec-h">👑 God Functions — Do Too Much <span>(${rr.god_functions.length})</span></div>
    <table class="rtbl"><thead><tr><th>Function</th><th>File</th><th>Complexity</th></tr></thead><tbody>`;
    rr.god_functions.forEach(g=>{html+=`<tr><td><code>${esc(g.name)}</code></td><td><code>${esc(g.filename)}</code></td><td><span class="bcrit">🔴 ${g.complexity}</span></td></tr>`;});
    html+=`</tbody></table></div>`;
  }
  // Coupling
  html+=`<div class="rsec"><div class="rsec-h">🔗 File Coupling <span>(instability = out/(out+in))</span></div><div class="coup-grid">`;
  rr.coupling_metrics.forEach(c=>{
    const ic=c.instability>0.7?'🔴':c.instability>0.4?'🟡':'🟢';
    html+=`<div class="cc"><div class="cc-name">${esc(c.filename)}</div>
      <div class="cc-row"><span>Functions</span><span>${c.total_functions}</span></div>
      <div class="cc-row"><span>Out deps</span><span>${c.efferent_coupling}</span></div>
      <div class="cc-row"><span>In deps</span><span>${c.afferent_coupling}</span></div>
      <div class="cc-row"><span>Instability</span><span>${ic} ${c.instability}</span></div>
      <div class="cc-row"><span>LoC</span><span>${c.loc_total}</span></div>
    </div>`;
  });
  html+=`</div></div>`;
  // Data I/O
  html+=`<div class="rsec"><div class="rsec-h">🗄️ Data Entry/Exit Points</div>`;
  if(!rr.data_entry_exit.length){html+=`<div class="no-iss">No data I/O patterns detected.</div>`;}
  else{
    html+=`<table class="rtbl"><thead><tr><th>Function</th><th>File</th><th>Line</th><th>Complexity</th><th>Fan-in</th></tr></thead><tbody>`;
    rr.data_entry_exit.forEach(d=>{html+=`<tr><td><code>${esc(d.name)}</code> <span class="binfo">🗄️</span></td><td><code>${esc(d.filename)}</code></td><td>${d.lineno}</td><td>${d.complexity}</td><td>${d.fan_in}</td></tr>`;});
    html+=`</tbody></table>`;
  }
  html+=`</div>`;
  // Recommendations
  const recs=buildRecs(rr);
  html+=`<div class="rsec"><div class="rsec-h">💡 Recommendations</div><div class="rec-list">`;
  if(!recs.length){html+=`<div class="no-iss">✅ Codebase looks healthy!</div>`;}
  else recs.forEach(rc=>{html+=`<div class="rec-card"><div class="rec-icon">${rc.icon}</div><div class="rec-txt">${rc.html}</div></div>`;});
  html+=`</div></div>`;
  document.getElementById('risk-body').innerHTML=html;
}
function buildRecs(rr){
  const recs=[],s=rr.summary;
  if(s.dead_functions_count>0) recs.push({icon:'🗑️',html:`<strong>Remove ${s.dead_functions_count} dead function(s).</strong> They add maintenance burden.`});
  if(s.high_complexity_count>0) recs.push({icon:'✂️',html:`<strong>Refactor ${s.high_complexity_count} complex function(s).</strong> High cyclomatic complexity → more bugs.`});
  const crit=rr.high_fanin_functions.filter(f=>f.risk_score>=60);
  if(crit.length) recs.push({icon:'🛡️',html:`<strong>Add tests for:</strong> ${crit.slice(0,3).map(f=>`<code>${esc(f.name)}</code>`).join(', ')}`});
  if(rr.data_entry_exit.length) recs.push({icon:'🔒',html:`<strong>Audit ${rr.data_entry_exit.length} data I/O point(s).</strong> Validate inputs, handle errors, add logging.`});
  if(rr.god_functions&&rr.god_functions.length) recs.push({icon:'👑',html:`<strong>Split ${rr.god_functions.length} god function(s).</strong> High complexity + high fan-out = dangerous.`});
  return recs;
}

// ════════════════════════════════════════════════════
//  DOCS PANEL
// ════════════════════════════════════════════════════
function renderDocs(md){
  const b=document.getElementById('docs-body');
  if(!md){b.innerHTML='<div class="chat-welcome">No docs available.</div>';return;}
  b.innerHTML=`<div style="max-width:860px;margin:0 auto">
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:6px 12px;margin-bottom:14px;display:flex;align-items:center;gap:10px;font-size:11px;color:var(--muted)">
      <span>📄</span><span>Markdown documentation preview</span>
      <button class="btn-dl" style="margin-left:auto;font-size:10px" onclick="dlDocs()">⬇ Download .md</button>
    </div>
    <pre style="background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.7;color:var(--text);white-space:pre-wrap;word-break:break-word">${esc(md)}</pre>
  </div>`;
}

// ════════════════════════════════════════════════════
//  DOWNLOAD
// ════════════════════════════════════════════════════
async function dlDocs(){
  if(!MD){showErr('No documentation. Upload a file first.');return;}
  const fname=(SD?.files?.[0]||'project').replace(/[^a-zA-Z0-9_-]/g,'_');
  try{
    const r=await fetch('/api/download/docs',{method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({markdown:MD,filename:fname})});
    if(!r.ok){showErr('Download failed ('+r.status+')');return;}
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=fname+'_docs.md';a.click();
    URL.revokeObjectURL(url);showOk('Documentation downloaded!');
  }catch(e){showErr('Download error: '+e.message);}
}

// ════════════════════════════════════════════════════
//  GRAPH LAYOUT
// ════════════════════════════════════════════════════
function renderGraph(){
  if(!GD)return;
  nodePos={};
  computeLayout(GD.nodes,GD.edges);
  drawEdges(GD.edges);drawNodes(GD.nodes);
  fitScreen();updateMinimap();updateZoomInd();
}
function computeLayout(nodes,edges){
  const FN=nodes.filter(n=>n.type==='file');
  const CN=nodes.filter(n=>n.type==='class');
  const NN=nodes.filter(n=>n.type==='function');
  const ch={};
  edges.filter(e=>e.type==='contains').forEach(e=>{if(!ch[e.from])ch[e.from]=[];ch[e.from].push(e.to);});
  const dm=n=>n.type==='file'?{w:180,h:52}:n.type==='class'?{w:152,h:44}:{w:130,h:36};
  FN.forEach((fn,fi)=>{
    const fx=fi*340+80,fy=60;
    nodePos[fn.id]={x:fx,y:fy,...dm(fn)};
    const fcs=(ch[fn.id]||[]).map(id=>CN.find(n=>n.id===id)).filter(Boolean);
    fcs.forEach((cls,ci)=>{
      const cx=fx+(ci-(fcs.length-1)/2)*210,cy=fy+120;
      nodePos[cls.id]={x:cx,y:cy,...dm(cls)};
      const mfs=(ch[cls.id]||[]).map(id=>NN.find(n=>n.id===id)).filter(Boolean);
      mfs.forEach((m,mi)=>{nodePos[m.id]={x:cx+(mi-(mfs.length-1)/2)*160,y:cy+110,...dm(m)};});
    });
    const tfs=(ch[fn.id]||[]).map(id=>NN.find(n=>n.id===id)).filter(Boolean);
    const oy=fcs.length>0?230:120;
    tfs.forEach((f,i)=>{nodePos[f.id]={x:fx+(i-(tfs.length-1)/2)*160,y:fy+oy,...dm(f)};});
  });
  nodes.forEach(n=>{if(!nodePos[n.id]){const d=dm(n);nodePos[n.id]={x:Math.random()*500,y:Math.random()*300,...d};}});
  for(let it=0;it<80;it++){
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
      const a=nodePos[nodes[i].id],b=nodePos[nodes[j].id];
      if(!a||!b)continue;
      const dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1,mn=(a.w+b.w)/2+28;
      if(d<mn){const f=(mn-d)/d*.4;b.x+=dx*f;b.y+=dy*f;a.x-=dx*f;a.y-=dy*f;}
    }
    edges.filter(e=>e.type==='contains').forEach(e=>{
      const a=nodePos[e.from],b=nodePos[e.to];if(!a||!b)return;
      const dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-140)/d*.06;
      a.x+=dx*f;a.y+=dy*f;b.x-=dx*f;b.y-=dy*f;
      if(b.y<a.y+80)b.y=a.y+80;
    });
  }
}
function riskSets(){
  if(!RD)return{dead:new Set(),complex:new Set()};
  return{dead:new Set(RD.dead_functions.map(d=>d.id)),complex:new Set(RD.complexity_issues.map(c=>c.id))};
}
function drawEdges(edges){
  const el=document.getElementById('el');el.innerHTML='';
  edges.forEach(e=>{
    const fr=nodePos[e.from],to=nodePos[e.to];if(!fr||!to)return;
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    const x1=fr.x,y1=fr.y+fr.h/2,x2=to.x,y2=to.y-to.h/2;
    path.setAttribute('d',`M${x1},${y1} C${x1},${y1+40} ${x2},${y2-40} ${x2},${y2}`);
    path.setAttribute('class',e.type==='calls'?'edge-calls':'edge-contains');
    if(e.type==='calls')path.setAttribute('marker-end','url(#arrow-calls)');
    path.setAttribute('data-et',e.type);el.appendChild(path);
  });
}
function drawNodes(nodes){
  const nl=document.getElementById('nl');nl.innerHTML='';
  const{dead,complex}=riskSets();
  nodes.forEach(n=>{
    const pos=nodePos[n.id];if(!pos)return;
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    g.setAttribute('class',`node-group`);
    g.setAttribute('transform',`translate(${pos.x-pos.w/2},${pos.y-pos.h/2})`);
    g.setAttribute('data-id',n.id);g.setAttribute('data-type',n.type);
    const rx=n.type==='class'?22:n.type==='file'?10:6;
    let fc,sc;
    if(n.type==='file'){fc='rgba(56,189,248,.07)';sc='var(--file)';}
    else if(n.type==='class'){fc='rgba(168,85,247,.09)';sc='var(--cls)';}
    else if(dead.has(n.id)){fc='rgba(107,114,128,.1)';sc='#6b7280';}
    else if(complex.has(n.id)){fc='rgba(239,68,68,.1)';sc='#ef4444';}
    else{fc='rgba(16,185,129,.07)';sc='var(--func)';}
    const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
    rect.setAttribute('width',pos.w);rect.setAttribute('height',pos.h);
    rect.setAttribute('rx',rx);rect.setAttribute('ry',rx);
    rect.setAttribute('fill',fc);rect.setAttribute('stroke',sc);
    rect.setAttribute('stroke-width',n.type==='function'?'1':'1.5');
    g.appendChild(rect);
    const ic=document.createElementNS('http://www.w3.org/2000/svg','text');
    ic.setAttribute('x','10');ic.setAttribute('y',String(pos.h/2));
    ic.setAttribute('dominant-baseline','middle');ic.setAttribute('font-size','12');
    ic.setAttribute('fill',sc);
    ic.textContent=n.type==='file'?'📄':n.type==='class'?'◈':'ƒ';
    g.appendChild(ic);
    const lb=document.createElementNS('http://www.w3.org/2000/svg','text');
    lb.setAttribute('x','27');lb.setAttribute('y',String(pos.h/2));
    lb.setAttribute('dominant-baseline','middle');
    lb.setAttribute('font-size',n.type==='file'?'12':n.type==='class'?'11':'10');
    lb.setAttribute('font-weight',n.type==='file'?'700':'400');
    lb.setAttribute('font-family','JetBrains Mono,monospace');
    lb.setAttribute('fill',sc);
    const mc=n.type==='file'?18:14;
    lb.textContent=n.label.length>mc?n.label.slice(0,mc)+'…':n.label;
    g.appendChild(lb);
    if(dead.has(n.id)||complex.has(n.id)){
      const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
      dot.setAttribute('cx',String(pos.w-8));dot.setAttribute('cy','8');dot.setAttribute('r','5');
      dot.setAttribute('fill',dead.has(n.id)?'#6b7280':'#ef4444');g.appendChild(dot);
    }
    if(n.is_async){
      const ab=document.createElementNS('http://www.w3.org/2000/svg','rect');
      ab.setAttribute('x',String(pos.w-32));ab.setAttribute('y','6');
      ab.setAttribute('width','26');ab.setAttribute('height','12');ab.setAttribute('rx','3');
      ab.setAttribute('fill','rgba(16,185,129,.18)');ab.setAttribute('stroke','var(--func)');ab.setAttribute('stroke-width','0.5');
      g.appendChild(ab);
      const at=document.createElementNS('http://www.w3.org/2000/svg','text');
      at.setAttribute('x',String(pos.w-19));at.setAttribute('y','14');
      at.setAttribute('dominant-baseline','middle');at.setAttribute('text-anchor','middle');
      at.setAttribute('font-size','7');at.setAttribute('fill','var(--func)');
      at.textContent='async';g.appendChild(at);
    }
    g.addEventListener('mouseenter',ev=>showTT(ev,n));
    g.addEventListener('mouseleave',hideTT);
    g.addEventListener('click',()=>onNodeClick(n));
    nl.appendChild(g);
  });
}

// ════════════════════════════════════════════════════
//  TOOLTIP
// ════════════════════════════════════════════════════
function showTT(ev,n){
  const tt=document.getElementById('tooltip');
  const th=document.getElementById('tt-h');
  const tb=document.getElementById('tt-b');
  th.textContent=n.label;
  th.style.color=n.type==='file'?'var(--file)':n.type==='class'?'var(--cls)':'var(--func)';
  let h=`<div class="tt-r"><span>Type</span><span>${n.type}</span></div>`;
  if(n.filename)h+=`<div class="tt-r"><span>File</span><span>${esc(n.filename)}</span></div>`;
  if(n.lineno)h+=`<div class="tt-r"><span>Line</span><span>${n.lineno}${n.end_lineno?'–'+n.end_lineno:''}</span></div>`;
  if(n.args?.length)h+=`<div class="tt-r"><span>Args</span><span>${n.args.join(', ')}</span></div>`;
  if(n.complexity)h+=`<div class="tt-r"><span>Complexity</span><span>${n.complexity}</span></div>`;
  if(GD){
    const fi=GD.edges.filter(e=>e.type==='calls'&&e.to===n.id).length;
    const fo=GD.edges.filter(e=>e.type==='calls'&&e.from===n.id).length;
    if(fi||fo)h+=`<div class="tt-r"><span>Fan-in/out</span><span>${fi} / ${fo}</span></div>`;
  }
  if(RD){
    const{dead,complex}=riskSets();
    if(dead.has(n.id))h+=`<span class="tt-badge" style="background:rgba(107,114,128,.2);color:#9ca3af">⚫ DEAD CODE</span>`;
    if(complex.has(n.id))h+=`<span class="tt-badge" style="background:rgba(239,68,68,.2);color:#ef4444">🔴 HIGH COMPLEXITY</span>`;
    if(n.has_db_io)h+=`<span class="tt-badge" style="background:rgba(59,130,246,.2);color:#3b82f6">🗄️ DATA I/O</span>`;
  }
  tb.innerHTML=h;
  const cont=document.getElementById('graph-area');
  const rect=cont.getBoundingClientRect();
  let tx=ev.clientX-rect.left+16,ty=ev.clientY-rect.top+16;
  if(tx+280>rect.width)tx-=300;if(ty+200>rect.height)ty-=180;
  tt.style.left=tx+'px';tt.style.top=ty+'px';tt.classList.add('visible');
}
function hideTT(){document.getElementById('tooltip').classList.remove('visible');}
function onNodeClick(n){
  const aG=document.querySelectorAll('.node-group');
  const aE=document.querySelectorAll('#el path');
  const conn=new Set([n.id]);
  GD.edges.forEach(e=>{if(e.from===n.id||e.to===n.id){conn.add(e.from);conn.add(e.to);}});
  aG.forEach(g=>{g.style.opacity=conn.has(g.dataset.id)?'1':'0.12';});
  aE.forEach(p=>p.style.opacity='0.07');
  GD.edges.forEach((e,i)=>{if(e.from===n.id||e.to===n.id)aE[i]&&(aE[i].style.opacity='1');});
  if(n.type==='function'||n.type==='class')
    document.getElementById('chat-inp').value=`Tell me about the ${n.type} "${n.label}" — what does it do and what does it call?`;
  const svg=document.getElementById('gsvg');
  const reset=()=>{aG.forEach(g=>g.style.opacity='1');aE.forEach(p=>p.style.opacity='');svg.removeEventListener('click',reset);};
  setTimeout(()=>svg.addEventListener('click',reset),10);
}

// ════════════════════════════════════════════════════
//  PAN / ZOOM
// ════════════════════════════════════════════════════
const gsvg=document.getElementById('gsvg');
gsvg.addEventListener('mousedown',e=>{
  if(e.target===gsvg||e.target.closest('#el')){
    panning=true;gsvg.classList.add('grabbing');
    panSt={x:e.clientX,y:e.clientY};trSt={x:tr.x,y:tr.y};
  }
});
window.addEventListener('mousemove',e=>{
  if(!panning)return;
  tr.x=trSt.x+e.clientX-panSt.x;tr.y=trSt.y+e.clientY-panSt.y;
  applyTr();updateMinimap();
});
window.addEventListener('mouseup',()=>{panning=false;gsvg.classList.remove('grabbing');});
gsvg.addEventListener('wheel',e=>{
  e.preventDefault();
  const f=e.deltaY<0?1.12:0.89;
  const rect=gsvg.getBoundingClientRect();
  const mx=e.clientX-rect.left,my=e.clientY-rect.top;
  tr.x=mx-(mx-tr.x)*f;tr.y=my-(my-tr.y)*f;
  tr.s=Math.max(.06,Math.min(8,tr.s*f));
  applyTr();updateZoomInd();updateMinimap();updateNodeVis();
},{passive:false});
function zoomBy(f){
  const rect=gsvg.getBoundingClientRect(),cx=rect.width/2,cy=rect.height/2;
  tr.x=cx-(cx-tr.x)*f;tr.y=cy-(cy-tr.y)*f;
  tr.s=Math.max(.06,Math.min(8,tr.s*f));
  applyTr();updateZoomInd();updateMinimap();updateNodeVis();
}
function applyTr(){
  document.getElementById('groot').setAttribute('transform',`translate(${tr.x},${tr.y}) scale(${tr.s})`);
  document.getElementById('zm-pct').textContent=Math.round(tr.s*100)+'%';
}
function fitScreen(){
  const cont=document.getElementById('graph-area');
  const w=cont.clientWidth,h=cont.clientHeight;
  let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
  Object.values(nodePos).forEach(p=>{minX=Math.min(minX,p.x-p.w/2);minY=Math.min(minY,p.y-p.h/2);maxX=Math.max(maxX,p.x+p.w/2);maxY=Math.max(maxY,p.y+p.h/2);});
  const bw=maxX-minX+80,bh=maxY-minY+80;
  tr.s=Math.min(w/bw,h/bh,1.5);
  tr.x=(w-bw*tr.s)/2-minX*tr.s+40*tr.s;
  tr.y=(h-bh*tr.s)/2-minY*tr.s+40*tr.s;
  applyTr();updateZoomInd();updateNodeVis();
}
function resetView(){fitScreen();updateMinimap();}
function updateNodeVis(){
  if(!GD)return;const s=tr.s;
  document.querySelectorAll('.node-group').forEach(g=>{
    const t=g.dataset.type;let v=true,op=1;
    if(s<ZF){v=t==='file';}
    else if(s<ZC){v=t!=='function';op=t==='file'?1:.85;}
    else if(s<ZN){if(t==='function')op=(s-ZC)/(ZN-ZC);}
    g.style.display=v?'':'none';if(v)g.style.opacity=String(op);
  });
  document.querySelectorAll('#el path').forEach((p,i)=>{
    if(!GD.edges[i])return;const e=GD.edges[i];
    if(e.type==='contains'){p.style.display=s>=ZF?'':'none';}
    else{p.style.display=s>=ZC?'':'none';p.style.opacity=s<ZN?String((s-ZC)/(ZN-ZC)*.7):'.7';}
  });
}
function updateZoomInd(){
  const s=tr.s,lv=document.getElementById('zi-lv'),ht=document.getElementById('zi-ht');
  if(s<ZF){lv.textContent='Project View';ht.textContent='Scroll to see files';}
  else if(s<ZC){lv.textContent='File View';ht.textContent='Scroll to see classes';}
  else if(s<ZN){lv.textContent='Class View';ht.textContent='Scroll to see functions';}
  else{lv.textContent='Function View';ht.textContent='Click a node to explore';}
}
function updateMinimap(){
  if(!GD||!Object.keys(nodePos).length)return;
  const mm=document.getElementById('minimap');
  const mw=mm.clientWidth,mh=mm.clientHeight;
  let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
  Object.values(nodePos).forEach(p=>{minX=Math.min(minX,p.x-p.w/2);minY=Math.min(minY,p.y-p.h/2);maxX=Math.max(maxX,p.x+p.w/2);maxY=Math.max(maxY,p.y+p.h/2);});
  const bw=maxX-minX+40,bh=maxY-minY+40,sc=Math.min(mw/bw,mh/bh);
  const mc=document.getElementById('mm-c');mc.innerHTML='';
  const{dead,complex}=riskSets();
  GD.nodes.forEach(n=>{
    const pos=nodePos[n.id];if(!pos)return;
    const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
    r.setAttribute('x',(pos.x-minX-pos.w/2)*sc);r.setAttribute('y',(pos.y-minY-pos.h/2)*sc);
    r.setAttribute('width',pos.w*sc);r.setAttribute('height',pos.h*sc);r.setAttribute('rx',1);
    let col=n.type==='file'?'#38bdf8':n.type==='class'?'#a855f7':'#10b981';
    if(dead.has(n.id))col='#6b7280';if(complex.has(n.id))col='#ef4444';
    r.setAttribute('fill',col);r.setAttribute('opacity','.5');mc.appendChild(r);
  });
  const cont=document.getElementById('graph-area');
  const vp=document.getElementById('mm-vp');
  vp.setAttribute('x',(-tr.x/tr.s-minX)*sc);vp.setAttribute('y',(-tr.y/tr.s-minY)*sc);
  vp.setAttribute('width',cont.clientWidth/tr.s*sc);vp.setAttribute('height',cont.clientHeight/tr.s*sc);
}

// ════════════════════════════════════════════════════
//  FULLSCREEN
// ════════════════════════════════════════════════════
function toggleFullscreen(){
  document.body.classList.toggle('fullscreen');
  const btn=document.getElementById('btn-fullscreen');
  btn.textContent=document.body.classList.contains('fullscreen')?'⊠':'⊞';
  btn.title=document.body.classList.contains('fullscreen')?'Exit fullscreen':'Fullscreen graph';
  setTimeout(()=>{if(GD){fitScreen();updateMinimap();}},50);
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('fullscreen'))toggleFullscreen();});

// ════════════════════════════════════════════════════
//  CHAT DRAWER
// ════════════════════════════════════════════════════
let chatCollapsed=false;
function toggleChat(){
  chatCollapsed=!chatCollapsed;
  document.getElementById('chat-drawer').classList.toggle('collapsed',chatCollapsed);
  document.getElementById('chat-tog-btn').textContent=chatCollapsed?'▲':'▼';
}
function resizeChat(size){
  const d=document.getElementById('chat-drawer');
  d.classList.remove('collapsed');chatCollapsed=false;
  document.getElementById('chat-tog-btn').textContent='▼';
  if(size==='sm') d.style.height='180px';
  else if(size==='md') d.style.height='260px';
  else if(size==='lg') d.style.height='420px';
  else if(size==='full') d.style.height='calc(100vh - 47px)'; 
}

// ════════════════════════════════════════════════════
//  CHAT SEND
// ════════════════════════════════════════════════════
function chatKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat();}}

async function sendChat(){
  const inp=document.getElementById('chat-inp');
  const text=inp.value.trim();
  if(!text||!GD)return;
  // Make sure chat is visible
  if(chatCollapsed)toggleChat();
  inp.value='';inp.disabled=true;document.getElementById('chat-send').disabled=true;
  CM.push({role:'user',content:text});
  appendMsg('user',text);
  const tid=appendThinking();
  try{
    const gc=JSON.stringify({
      nodes:GD.nodes.slice(0,60),
      edges:GD.edges.filter(e=>e.type==='calls').slice(0,80)
    },null,2);
    const rc=RD?`Health:${RD.summary.health_score}/100, Dead:${RD.summary.dead_functions_count}, Complex:${RD.summary.high_complexity_count}, DataIO:${RD.summary.data_points_count}`:'';

    const r=await fetch('/api/chat',{
      method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:CM,graph_context:gc,summary:SD,risk_context:rc, files_data: FD})
    });

    // Safe parse — don't assume JSON
    const rawText=await r.text();
    let data;
    try{data=JSON.parse(rawText);}
    catch{
      removeThinking(tid);
      appendMsg('assistant','⚠ Server returned an unexpected response. Make sure Flask is running on port 5000.');
      inp.disabled=false;inp.focus();document.getElementById('chat-send').disabled=false;
      return;
    }
    removeThinking(tid);
    if(data.error){
      appendMsg('assistant','⚠ '+data.error);
    }else{
      const reply=data.reply||'(no response)';
      CM.push({role:'assistant',content:reply});
      appendMsg('assistant',reply);
      await saveSess();
    }
  }catch(e){
    removeThinking(tid);
    appendMsg('assistant','⚠ Network error: '+e.message);
  }
  inp.disabled=false;inp.focus();document.getElementById('chat-send').disabled=false;
}

function appendMsg(role,text){
  const c=document.getElementById('chat-msgs');
  const d=document.createElement('div');
  d.className='msg '+role;
  d.innerHTML=`<div class="msg-av">${role==='assistant'?'⬡':'U'}</div><div class="msg-bubble">${esc(text)}</div>`;
  c.appendChild(d);c.scrollTop=c.scrollHeight;
}
let thC=0;
function appendThinking(){
  const id='th-'+(++thC);
  const c=document.getElementById('chat-msgs'),d=document.createElement('div');
  d.className='msg assistant';d.id=id;
  d.innerHTML=`<div class="msg-av">⬡</div><div class="msg-bubble"><div class="thinking"><span></span><span></span><span></span></div></div>`;
  c.appendChild(d);c.scrollTop=c.scrollHeight;return id;
}
function removeThinking(id){const el=document.getElementById(id);if(el)el.remove();}

// ════════════════════════════════════════════════════
//  HISTORY SIDEBAR
// ════════════════════════════════════════════════════
function renderHist(filter=''){
  const list=document.getElementById('hist-list');
  const empty=document.getElementById('hist-empty');
  const sess=filter?allSess.filter(s=>(s.name||'').toLowerCase().includes(filter.toLowerCase())):allSess;
  list.querySelectorAll('.cs').forEach(el=>el.remove());
  if(!sess.length){empty.style.display='block';return;}
  empty.style.display='none';
  sess.forEach(s=>{
    const d=document.createElement('div');
    d.className='cs'+(s.sid===curSid?' active':'');
    d.innerHTML=`<div class="cs-icon">${s.language==='python'?'🐍':'☕'}</div>
      <div class="cs-body"><div class="cs-title">${esc(s.name||'Analysis')}</div>
      <div class="cs-meta">${s.summary?.files?.length||1} file(s) · ${s.summary?.total_functions||0} funcs · ${s.label||''}</div></div>
      <button class="cs-del" title="Delete" onclick="delSess('${s.sid}',event)">✕</button>`;
    d.addEventListener('click',()=>openSess(s.sid));
    list.appendChild(d);
  });
}
function filterHist(v){renderHist(v);}

// ════════════════════════════════════════════════════
//  NEW ANALYSIS
// ════════════════════════════════════════════════════
function newAnalysisUI(){
  GD=null;SD=null;RD=null;MD=null;CM=[];nodePos={};
  tr={x:0,y:0,s:1};
  document.getElementById('upload-zone').classList.remove('hidden');
  document.getElementById('gsvg-wrap').classList.remove('visible');
  document.getElementById('legend').style.display='none';
  document.getElementById('zoom-ind').classList.remove('visible');
  document.getElementById('minimap').classList.remove('visible');
  document.getElementById('tb-stats').style.display='none';
  document.getElementById('zm-ctrls').style.display='none';
  document.getElementById('panel-tabs').style.display='none';
  document.getElementById('btn-fullscreen').style.display='none';
  document.getElementById('lang-badge').style.display='none';
  document.getElementById('file-label').textContent='No file loaded';
  document.getElementById('chat-inp').disabled=true;
  document.getElementById('chat-send').disabled=true;
  document.getElementById('chat-msgs').innerHTML='<div class="chat-welcome">Upload a codebase then ask anything about its architecture, functions, or risks.</div>';
  document.getElementById('el').innerHTML='';
  document.getElementById('nl').innerHTML='';
  document.getElementById('file-input').value='';
  document.getElementById('groot').setAttribute('transform','translate(0,0) scale(1)');
  document.getElementById('risk-body').innerHTML='<div class="chat-welcome">Upload a file to generate the risk report.</div>';
  document.getElementById('docs-body').innerHTML='<div class="chat-welcome">Upload a file to generate documentation.</div>';
  document.getElementById('risk-health-badge').textContent='–/100';
  document.getElementById('risk-badge').style.display='none';
  document.getElementById('risk-panel').classList.remove('visible');
  document.getElementById('docs-panel').classList.remove('visible');
  document.getElementById('tab-graph')?.classList.add('active');
  document.getElementById('tab-risk')?.classList.remove('active');
  document.getElementById('tab-docs')?.classList.remove('active');
  activeTab='graph';
  // Restore chat drawer if fullscreen
  if(document.body.classList.contains('fullscreen'))toggleFullscreen();
}
function newAnalysis(){curSid=null;newAnalysisUI();renderHist();}

// ════════════════════════════════════════════════════
//  STATS
// ════════════════════════════════════════════════════
function setupStats(){
  document.getElementById('s-f').textContent=SD.total_files||SD.files?.length||0;
  document.getElementById('s-c').textContent=SD.total_classes;
  document.getElementById('s-fn').textContent=SD.total_functions;
  document.getElementById('s-ca').textContent=SD.total_call_edges;
}
function setupBadge(){
  const b=document.getElementById('lang-badge');
  b.textContent=SD.language==='python'?'Python':'Java';
  b.className='lang-badge '+(SD.language||'python');
  b.style.display='inline-block';
}

// ════════════════════════════════════════════════════
//  UTILS
// ════════════════════════════════════════════════════
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/\n/g,'<br>');}
function showErr(m){const el=document.getElementById('err-toast');el.textContent='⚠ '+m;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),5500);}
function showOk(m){const el=document.getElementById('ok-toast');el.textContent='✓ '+m;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3000);}

window.addEventListener('resize',()=>{if(GD){fitScreen();updateMinimap();}});

// BOOT
checkAuth();
