"""
MIT 8339 - Stage 3: Interactive BI dashboard (Plotly.js, single self-contained HTML file)

Input : data/BankChurners_cleaned.csv
Output: dashboard/MIT8339_Retention_Dashboard.html
        - Page 1  Executive Overview         (7 KPI cards, 4 visuals)
        - Page 2  Customer Retention Analysis (5 visuals + high-risk watchlist)
        - 6 slicers (gender, age band, income, card, risk band, customer status) apply to every visual
        Works offline: Plotly.js and the data are embedded in the file.

Run   : python src/03_build_dashboard.py
"""
from pathlib import Path
import json
import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "dashboard").mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "BankChurners_cleaned.csv")

CATS = {
    "Gender": ["Female", "Male"],
    "Age_Band": ["<35", "35-44", "45-54", "55+"],
    "Income_Category": ["Less than $40K", "$40K - $60K", "$60K - $80K", "$80K - $120K", "$120K+", "Unknown"],
    "Card_Category": ["Blue", "Silver", "Gold", "Platinum"],
    "Risk_Band": ["Low", "Medium", "High"],
    "Customer_Status": ["Existing", "Attrited"],
    "Customer_Value_Class": ["Low value", "Core value", "High value"],
    "Txn_Frequency_Category": ["Very low (<=40)", "Low (41-60)", "Medium (61-80)", "High (>80)"],
    "Product_Depth": ["Thin (1-2)", "Moderate (3-4)", "Deep (5-6)"],
}
for c, levels in CATS.items():
    assert set(df[c].unique()) <= set(levels), c

# Columnar, index-encoded payload keeps the file small
data = {c: df[c].map({v: i for i, v in enumerate(levels)}).tolist() for c, levels in CATS.items()}
num_cols = {"Churned": "churn", "Total_Trans_Ct": "txct", "Total_Trans_Amt": "txamt", "Total_Ct_Chng_Q4_Q1": "ctchg",
            "Total_Revolving_Bal": "revbal", "Total_Relationship_Count": "rel", "Months_Inactive_12_mon": "inact",
            "Contacts_Count_12_mon": "cont", "Credit_Limit": "cl", "Avg_Utilization_Ratio": "util", "Risk_Score": "score"}
for c, k in num_cols.items():
    data[k] = df[c].round(3).tolist()
# Pseudonymised customer reference for the watchlist (data minimisation - raw CLIENTNUM not shown)
data["ref"] = ("C-" + df["CLIENTNUM"].astype(str).str[-5:]).tolist()

payload = json.dumps({"cats": CATS, "d": data}, separators=(",", ":"))

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retention Intelligence Dashboard</title>
<style>
:root{--bg:#f5f4f1;--card:#fff;--ink:#0b0b0b;--ink2:#52514e;--muted:#7a7974;--line:#e4e3df;
--blue:#2a78d6;--orange:#eb6834;--navy:#0d366b;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 "Segoe UI",system-ui,-apple-system,Arial,sans-serif}
header{background:var(--navy);color:#fff;padding:14px 24px;display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap}
header h1{margin:0;font-size:20px;font-weight:600}header p{margin:2px 0 0;font-size:12px;opacity:.8}
nav{display:flex;gap:4px}nav button{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.35);padding:7px 14px;border-radius:6px;cursor:pointer;font:inherit;font-size:13px}
nav button.on{background:#fff;color:var(--navy);font-weight:600}
.filters{display:flex;flex-wrap:wrap;gap:12px;padding:12px 24px;background:#fff;border-bottom:1px solid var(--line);align-items:flex-end;position:sticky;top:0;z-index:5}
.filters label{display:flex;flex-direction:column;font-size:11px;color:var(--ink2);text-transform:uppercase;letter-spacing:.04em;gap:3px}
.filters select{font:inherit;font-size:13px;padding:5px 8px;border:1px solid #cfcdc7;border-radius:6px;min-width:130px;background:#fff}
.filters button{font:inherit;font-size:13px;padding:6px 12px;border-radius:6px;border:1px solid #cfcdc7;background:#fff;cursor:pointer}
.filters .count{margin-left:auto;font-size:12px;color:var(--ink2)}
main{padding:16px 24px 32px;max-width:1500px;margin:0 auto}.page{display:none}.page.on{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .l{font-size:11px;color:var(--ink2);text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:26px;font-weight:650;margin-top:2px;font-variant-numeric:tabular-nums}
.kpi .s{font-size:11.5px;color:var(--muted)}
.kpi.alert .v{color:var(--crit)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px 10px;min-width:0}
.panel h2{font-size:14px;margin:0 0 2px;font-weight:600}.panel .sub{font-size:12px;color:var(--ink2);margin:0 0 4px}
.chart{height:300px}.wide{grid-column:1/-1}
.insight{font-size:12.5px;color:var(--ink);background:#f0f5fc;border-left:3px solid var(--blue);padding:6px 10px;margin-top:6px;border-radius:0 6px 6px 0}
.insight b{color:var(--navy)}
table{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right}th{color:var(--ink2);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em}
td:first-child,th:first-child{text-align:left}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff}
.b-High{background:var(--crit)}.b-Medium{background:#b07a00}.b-Low{background:#0a7d0a}
.scroll{max-height:300px;overflow:auto}
footer{font-size:11px;color:var(--muted);padding:0 24px 20px;max-width:1500px;margin:0 auto}
@media(max-width:900px){.grid{grid-template-columns:1fr}.filters .count{margin-left:0}}
</style></head><body>
<header><div><h1>Customer Retention &amp; Performance Intelligence</h1>
<p>Retail card portfolio &middot; BankChurners dataset (n = 10,127) &middot; MIT 8339 BI/DSS virtual lab</p></div>
<nav><button class="on" data-p="p1">1 &middot; Executive overview</button><button data-p="p2">2 &middot; Retention analysis</button></nav></header>
<div class="filters" id="filters"></div>
<main>
<section class="page on" id="p1">
 <div class="kpis" id="kpis"></div>
 <div class="grid">
  <div class="panel"><h2>Retention-risk segmentation</h2><p class="sub">Customers and attrition rate by rule-based risk band</p><div class="chart" id="c_risk"></div>
   <div class="insight"><b>Decision:</b> the High band holds ~18% of customers but ~68% of all attriters (61% churn) &mdash; the primary target list for retention spend.</div></div>
  <div class="panel"><h2>Attrition rate by income category</h2><p class="sub">% of customers in each category who closed their account</p><div class="chart" id="c_income"></div>
   <div class="insight"><b>Read:</b> income spreads churn only ~13.5&ndash;17.3%; income alone is a weak targeting variable compared with behaviour.</div></div>
  <div class="panel"><h2>Portfolio mix by customer value class</h2><p class="sub">Customers by 12-month spend tier, split by status</p><div class="chart" id="c_value"></div>
   <div class="insight"><b>Read:</b> the bottom spend quartile churns at 24.4% vs 11.5% in the top quartile &mdash; low spend is an engagement warning, not just a value measure.</div></div>
  <div class="panel"><h2>Attrition rate by card category</h2><p class="sub">Bars show rate; hover for customer counts (Gold/Platinum bases are small)</p><div class="chart" id="c_card"></div>
   <div class="insight"><b>Caution:</b> Platinum (n = 20) and Gold (n = 116) are too small for reliable conclusions; Blue is 93% of the book.</div></div>
 </div>
</section>
<section class="page" id="p2">
 <div class="grid">
  <div class="panel"><h2>Attrition by transaction frequency</h2><p class="sub">12-month transaction count band</p><div class="chart" id="c_freq"></div>
   <div class="insight"><b>Pattern 1:</b> customers with &le;60 transactions churn at ~34% vs ~4% above 60 &mdash; activity is the strongest early-warning signal.</div></div>
  <div class="panel"><h2>Attrition heatmap: frequency &times; product depth</h2><p class="sub">Attrition rate (%) in each cell; darker = higher</p><div class="chart" id="c_heat"></div>
   <div class="insight"><b>Pattern 2:</b> &le;60 transactions plus only 1&ndash;2 products gives 86&ndash;88% churn vs 18&ndash;32% for deeper relationships at the same activity level.</div></div>
  <div class="panel"><h2>Inactivity and service contacts</h2><p class="sub">Attrition rate by months inactive and by service contacts (last 12 months)</p><div class="chart" id="c_line"></div>
   <div class="insight"><b>Pattern 3:</b> churn rises steadily with service contacts (6 contacts = 100% churn, n = 54) &mdash; repeated contact is a complaint/friction signal.</div></div>
  <div class="panel"><h2>Spend vs transaction count</h2><p class="sub">Each dot is a customer; colour = status</p><div class="chart" id="c_scatter"></div>
   <div class="insight"><b>Read:</b> attriters cluster in the low-count, low-spend corner; no customer with more than 94 transactions attrited.</div></div>
  <div class="panel"><h2>Attrited vs existing &mdash; profile comparison</h2><p class="sub">Mean values for the current filter selection</p><div class="scroll" id="t_comp"></div></div>
  <div class="panel"><h2>High-risk watchlist (existing customers)</h2><p class="sub">Top 25 by risk score, then lowest transaction count &middot; pseudonymised references</p><div class="scroll" id="t_watch"></div></div>
 </div>
</section>
</main>
<footer>Source: Goyal, S. (2020). <i>Credit card customers</i> [Data set]. Kaggle. Risk band = rule-based score 0&ndash;10 (Low 0&ndash;3, Medium 4&ndash;5, High 6&ndash;10). Insight boxes describe the full portfolio; charts and KPIs respond to the filters. Dataset is US-origin; values are in USD.</footer>
<script>__PLOTLY__</script>
<script>
const P=__PAYLOAD__;const C=P.cats,D=P.d,N=D.churn.length;
const COL={blue:'#2a78d6',orange:'#eb6834',navy:'#0d366b',ink2:'#52514e',line:'#e4e3df',risk:['#0ca30c','#fab219','#d03b3b']};
const FILTERS=[['Gender','Gender'],['Age_Band','Age band'],['Income_Category','Income'],['Card_Category','Card'],['Risk_Band','Risk band'],['Customer_Status','Status']];
const fbox=document.getElementById('filters');const state={};
FILTERS.forEach(([k,lab])=>{state[k]=-1;const l=document.createElement('label');l.textContent=lab;const s=document.createElement('select');s.id='f_'+k;
 s.innerHTML='<option value="-1">All</option>'+C[k].map((v,i)=>`<option value="${i}">${v}</option>`).join('');
 s.onchange=()=>{state[k]=+s.value;render()};l.appendChild(s);fbox.appendChild(l)});
const rb=document.createElement('button');rb.textContent='Reset filters';rb.onclick=()=>{FILTERS.forEach(([k])=>{state[k]=-1;document.getElementById('f_'+k).value=-1});render()};fbox.appendChild(rb);
const cnt=document.createElement('span');cnt.className='count';fbox.appendChild(cnt);
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on',x===b));
 document.querySelectorAll('.page').forEach(p=>p.classList.toggle('on',p.id===b.dataset.p));window.dispatchEvent(new Event('resize'));render()});
const fmt=(v,d=0)=>v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(a,b)=>b?100*a/b:0;
const base={margin:{l:56,r:12,t:8,b:56},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'Segoe UI,system-ui,Arial',size:12,color:'#52514e'},
 xaxis:{gridcolor:'#eeede9',linecolor:'#e4e3df',zeroline:false},yaxis:{gridcolor:'#eeede9',linecolor:'#e4e3df',zeroline:false},hoverlabel:{font:{size:12}},bargap:.35};
const cfg={displaylogo:false,responsive:true,modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d']};
function lay(o){const L=Object.assign({},base,o,{xaxis:Object.assign({},base.xaxis,o.xaxis||{}),yaxis:Object.assign({},base.yaxis,o.yaxis||{})});
 ['xaxis','yaxis'].forEach(a=>{if(typeof L[a].title==='string')L[a].title={text:L[a].title,font:{size:12}}});return L}
function idx(){const r=[];for(let i=0;i<N;i++){let ok=true;for(const k in state){if(state[k]>=0&&D[k][i]!==state[k]){ok=false;break}}if(ok)r.push(i)}return r}
function groupRate(ix,key,n){const c=Array(n).fill(0),a=Array(n).fill(0);ix.forEach(i=>{c[D[key][i]]++;a[D[key][i]]+=D.churn[i]});return{c,a,r:c.map((v,j)=>v?100*a[j]/v:null)}}
function render(){
 const ix=idx(),n=ix.length;cnt.textContent=`${fmt(n)} of ${fmt(N)} customers in view`;
 let att=0,act=0,cl=0,ut=0,amt=0,hi=0,ct=0,attAmt=0;ix.forEach(i=>{att+=D.churn[i];act+=D.inact[i]<=2;cl+=D.cl[i];ut+=D.util[i];amt+=D.txamt[i];hi+=D.Risk_Band[i]===2&&D.churn[i]===0;ct+=D.txct[i];if(D.churn[i])attAmt+=D.txamt[i]});
 const K=[['Customers',fmt(n),'in current view'],['Attrition rate',n?fmt(pct(att,n),1)+'%':'–',fmt(att)+' attrited',att/n>0.2],['Active customer ratio',n?fmt(pct(act,n),1)+'%':'–','inactive ≤ 2 of last 12 months'],
  ['Avg credit limit',n?'$'+fmt(cl/n):'–','per customer'],['Avg utilisation',n?fmt(100*ut/n,1)+'%':'–','revolving ÷ limit'],['Transaction value','$'+fmt(amt/1e6,1)+'M',fmt(pct(attAmt,amt),1)+'% from attriters'],
  ['At-risk existing',fmt(hi),'High band, still active',true]];
 document.getElementById('kpis').innerHTML=K.map(k=>`<div class="kpi${k[3]?' alert':''}"><div class="l">${k[0]}</div><div class="v">${k[1]}</div><div class="s">${k[2]}</div></div>`).join('');
 const p1=document.getElementById('p1').classList.contains('on');
 if(p1){
  const r=groupRate(ix,'Risk_Band',3);
  Plotly.react('c_risk',[{type:'bar',name:'Customers',x:C.Risk_Band.map(v=>v+' risk'),y:r.c,marker:{color:COL.risk},text:r.r.map((v,j)=>v==null?'':`${fmt(r.c[j])} customers · ${fmt(v,1)}% churn`),textposition:'outside',cliponaxis:false,
   hovertemplate:'%{x}<br>Customers: %{y:,}<br>Attrited: %{customdata:,}<extra></extra>',customdata:r.a}],lay({showlegend:false,yaxis:{title:'Customers',rangemode:'tozero'},margin:{l:56,r:12,t:24,b:40}}),cfg);
  const inc=groupRate(ix,'Income_Category',6);
  Plotly.react('c_income',[{type:'bar',x:C.Income_Category,y:inc.r,marker:{color:COL.blue},text:inc.r.map(v=>v==null?'':fmt(v,1)+'%'),textposition:'outside',cliponaxis:false,customdata:inc.c,
   hovertemplate:'%{x}<br>Attrition: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>'}],lay({yaxis:{title:'Attrition rate (%)',rangemode:'tozero'},margin:{l:56,r:12,t:20,b:60}}),cfg);
  const vc=[[],[]];C.Customer_Value_Class.forEach(()=>{vc[0].push(0);vc[1].push(0)});ix.forEach(i=>vc[D.churn[i]][D.Customer_Value_Class[i]]++);
  Plotly.react('c_value',[{type:'bar',name:'Existing',x:C.Customer_Value_Class,y:vc[0],marker:{color:COL.blue,line:{color:'#fff',width:2}},hovertemplate:'%{x}<br>Existing: %{y:,}<extra></extra>'},
   {type:'bar',name:'Attrited',x:C.Customer_Value_Class,y:vc[1],marker:{color:COL.orange,line:{color:'#fff',width:2}},hovertemplate:'%{x}<br>Attrited: %{y:,}<extra></extra>'}],
   lay({barmode:'stack',yaxis:{title:'Customers'},xaxis:{title:'Customer value class (12-month spend)'},legend:{orientation:'h',y:1.12,x:0,traceorder:'normal'}}),cfg);
  const cc=groupRate(ix,'Card_Category',4);
  Plotly.react('c_card',[{type:'bar',x:C.Card_Category.map((v,j)=>`${v} (n=${fmt(cc.c[j])})`),y:cc.r,marker:{color:COL.blue},text:cc.r.map(v=>v==null?'':fmt(v,1)+'%'),textposition:'outside',cliponaxis:false,
   hovertemplate:'%{x}<br>Attrition: %{y:.1f}%<extra></extra>'}],lay({yaxis:{title:'Attrition rate (%)',rangemode:'tozero'},margin:{l:56,r:12,t:20,b:44}}),cfg);
 } else {
  const f=groupRate(ix,'Txn_Frequency_Category',4);
  Plotly.react('c_freq',[{type:'bar',x:C.Txn_Frequency_Category,y:f.r,marker:{color:COL.blue},text:f.r.map(v=>v==null?'':fmt(v,1)+'%'),textposition:'outside',cliponaxis:false,customdata:f.c,
   hovertemplate:'%{x}<br>Attrition: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>'}],lay({yaxis:{title:'Attrition rate (%)',rangemode:'tozero'},xaxis:{title:'Transactions in last 12 months'},margin:{l:56,r:12,t:20,b:56}}),cfg);
  const z=[],t=[],hc=[];C.Txn_Frequency_Category.forEach((_,a)=>{z.push([]);t.push([]);hc.push([]);C.Product_Depth.forEach((_,b)=>{let c=0,s=0;ix.forEach(i=>{if(D.Txn_Frequency_Category[i]===a&&D.Product_Depth[i]===b){c++;s+=D.churn[i]}});
   const v=c?100*s/c:null;z[a].push(v);t[a].push(c?fmt(v,1)+'%':'');hc[a].push(c)})});
  Plotly.react('c_heat',[{type:'heatmap',x:C.Product_Depth,y:C.Txn_Frequency_Category,z,text:t,texttemplate:'%{text}',customdata:hc,zmin:0,zmax:100,
   colorscale:[[0,'#f0f5fc'],[.25,'#9ec5f4'],[.5,'#5598e7'],[.75,'#256abf'],[1,'#0d366b']],colorbar:{title:{text:'%',side:'top'},thickness:10},xgap:2,ygap:2,
   hovertemplate:'Txn: %{y}<br>Products: %{x}<br>Attrition: %{z:.1f}%<br>Customers: %{customdata:,}<extra></extra>'}],lay({xaxis:{title:'Product relationship depth'},yaxis:{autorange:'reversed'},margin:{l:110,r:12,t:8,b:56}}),cfg);
  const L=k=>{const c=Array(7).fill(0),a=Array(7).fill(0);ix.forEach(i=>{c[D[k][i]]++;a[D[k][i]]+=D.churn[i]});return{r:c.map((v,j)=>v?100*a[j]/v:null),c}};
  const li=L('inact'),lc=L('cont'),xs=[0,1,2,3,4,5,6];
  Plotly.react('c_line',[{type:'scatter',mode:'lines+markers',name:'Months inactive',x:xs,y:li.r,customdata:li.c,line:{color:COL.blue,width:2},marker:{size:8},connectgaps:false,hovertemplate:'%{x} months inactive<br>Attrition: %{y:.1f}%<br>n = %{customdata:,}<extra></extra>'},
   {type:'scatter',mode:'lines+markers',name:'Service contacts',x:xs,y:lc.r,customdata:lc.c,line:{color:COL.orange,width:2},marker:{size:8,symbol:'diamond'},hovertemplate:'%{x} contacts<br>Attrition: %{y:.1f}%<br>n = %{customdata:,}<extra></extra>'}],
   lay({hovermode:'x unified',xaxis:{title:'Count in last 12 months (0–6)',dtick:1},yaxis:{title:'Attrition rate (%)',rangemode:'tozero'},legend:{orientation:'h',y:1.12,x:0}}),cfg);
  const sx=[[],[]],sy=[[],[]];ix.forEach(i=>{sx[D.churn[i]].push(D.txct[i]);sy[D.churn[i]].push(D.txamt[i])});
  Plotly.react('c_scatter',[{type:'scattergl',mode:'markers',name:'Existing',x:sx[0],y:sy[0],marker:{color:COL.blue,size:4,opacity:.35},hovertemplate:'Txns: %{x}<br>Spend: $%{y:,}<extra>Existing</extra>'},
   {type:'scattergl',mode:'markers',name:'Attrited',x:sx[1],y:sy[1],marker:{color:COL.orange,size:5,opacity:.6,symbol:'diamond'},hovertemplate:'Txns: %{x}<br>Spend: $%{y:,}<extra>Attrited</extra>'}],
   lay({xaxis:{title:'Transactions (12 months)'},yaxis:{title:'Transaction amount ($)'},legend:{orientation:'h',y:1.12,x:0}}),cfg);
  const vars=[['txct','Transactions (12m)',0],['txamt','Transaction amount ($)',0],['ctchg','Q4/Q1 count change',2],['revbal','Revolving balance ($)',0],['util','Utilisation ratio',2],['rel','Products held',2],['inact','Months inactive',2],['cont','Service contacts',2],['cl','Credit limit ($)',0]];
  const m=[{},{}],c2=[0,0];ix.forEach(i=>{const g=D.churn[i];c2[g]++;vars.forEach(([k])=>{m[g][k]=(m[g][k]||0)+D[k][i]})});
  document.getElementById('t_comp').innerHTML=`<table><tr><th>Variable</th><th>Existing</th><th>Attrited</th><th>Diff.</th></tr>`+vars.map(([k,l,d])=>{const e=c2[0]?m[0][k]/c2[0]:NaN,a=c2[1]?m[1][k]/c2[1]:NaN;const df=isFinite(e)&&isFinite(a)&&e?(100*(a/e-1)):NaN;
   return `<tr><td>${l}</td><td>${isFinite(e)?fmt(e,d):'–'}</td><td>${isFinite(a)?fmt(a,d):'–'}</td><td>${isFinite(df)?(df>0?'+':'')+fmt(df,0)+'%':'–'}</td></tr>`}).join('')+`<tr><td>Customers</td><td>${fmt(c2[0])}</td><td>${fmt(c2[1])}</td><td></td></tr></table>`;
  const w=ix.filter(i=>D.churn[i]===0).sort((a,b)=>D.score[b]-D.score[a]||D.txct[a]-D.txct[b]).slice(0,25);
  document.getElementById('t_watch').innerHTML=`<table><tr><th>Ref</th><th>Score</th><th>Band</th><th>Txns</th><th>Q4/Q1</th><th>Rev. bal</th><th>Products</th><th>Contacts</th></tr>`+
   (w.length?w.map(i=>`<tr><td>${D.ref[i]}</td><td>${D.score[i]}</td><td><span class="badge b-${C.Risk_Band[D.Risk_Band[i]]}">${C.Risk_Band[D.Risk_Band[i]]}</span></td><td>${D.txct[i]}</td><td>${fmt(D.ctchg[i],2)}</td><td>$${fmt(D.revbal[i])}</td><td>${D.rel[i]}</td><td>${D.cont[i]}</td></tr>`).join(''):'<tr><td colspan="8">No existing customers in this selection</td></tr>')+'</table>';
 }
}
render();
</script></body></html>"""

out = ROOT / "dashboard" / "MIT8339_Retention_Dashboard.html"
out.write_text(HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__PAYLOAD__", payload), encoding="utf-8")
print(f"Saved {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
