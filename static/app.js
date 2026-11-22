let csrf = '', currentUser = null;
const $ = id => document.getElementById(id);
async function api(path, method='GET', payload) {
  const response = await fetch('/api' + path, {method, headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:payload ? JSON.stringify(payload) : undefined});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed. Try again.');
  if (result.csrf) csrf = result.csrf;
  return result;
}
function message(text, error=false) { $('message').textContent=text; $('message').className='notice'+(error?' error':''); $('message').hidden=!text; }
function element(tag, text, parent) { const node=document.createElement(tag); node.textContent=text; if(parent)parent.append(node); return node; }
function action(label, handler, parent, style='') { const b=element('button',label,parent); b.type='button'; b.className=style; b.onclick=()=>Promise.resolve(handler()).catch(e=>message(e.message,true)); return b; }
async function authenticate(register=false) {
  try {
    const payload={username:$('username').value,password:$('password').value};
    if(register){const r=await api('/register','POST',payload);message(r.message);return;}
    const result=await api('/login','POST',payload);currentUser=result.user;$('password').value='';await showApp();message('');
  } catch(e) {message(e.message,true);}
}
async function showApp() {
  $('auth').hidden=!!currentUser;$('workspace').hidden=!currentUser;
  $('account').textContent=currentUser ? 'Signed in as '+currentUser.username : '';
  if(currentUser) await load();
}
async function initialize() {
  try { const state=await api('/session');currentUser=state.user;await showApp(); } catch(e){message(e.message,true);}
  $('login').onsubmit=e=>{e.preventDefault();authenticate();};
  $('register').onclick=()=>authenticate(true);
  $('logout').onclick=async()=>{try{await api('/logout','POST');location.reload();}catch(e){message(e.message,true);}};
}

let editing=null,page=1,chart;
const money=c=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(c/100);
const today=new Date();const localDate=new Date(today.getTime()-today.getTimezoneOffset()*60000).toISOString().slice(0,10);$('month').value=localDate.slice(0,7);$('date').value=localDate;
async function load(){
 const month=$('month').value;
 const [r,s]=await Promise.all([api('/transactions?month='+month+'&page='+page),api('/summary?month='+month)]);
 $('income').textContent=money(s.income_cents);$('expense').textContent=money(s.expense_cents);$('balance').textContent=money(s.balance_cents);
 $('rows').replaceChildren();for(const t of r.items){const tr=element('tr','',$('rows'));for(const value of [t.occurred_on,t.kind,t.category,t.note,money(t.amount_cents)])element('td',value,tr);const td=element('td','',tr);action('Edit',()=>{editing=t.id;$('kind').value=t.kind;$('amount').value=(t.amount_cents/100).toFixed(2);$('category').value=t.category;$('date').value=t.occurred_on;$('note').value=t.note;$('form-title').textContent='Edit transaction';$('amount').focus();},td,'secondary');action('Delete',async()=>{if(confirm('Delete this transaction?')){await api('/transactions/'+t.id,'DELETE');if(r.items.length===1&&page>1)page--;await load();}},td,'danger');}
 if(!r.items.length){const tr=element('tr','',$('rows'));const td=element('td','No transactions this month. Add your first transaction above.',tr);td.colSpan=6;}
 $('page').textContent='Page '+page+' · '+r.total+' transaction(s)';$('previous').disabled=page===1;$('next').disabled=page*r.limit>=r.total;
 $('categories').replaceChildren();for(const c of s.categories)element('li',c.category+': '+money(c.cents),$('categories'));
 $('chart-note').textContent=!s.categories.length?'No expenses to chart this month.':(!window.Chart?'Chart unavailable offline. Category totals are listed below.':'Expense totals by category.');
 if(chart)chart.destroy();if(window.Chart&&s.categories.length)chart=new Chart($('chart'),{type:'bar',data:{labels:s.categories.map(c=>c.category),datasets:[{label:'Expenses (INR)',data:s.categories.map(c=>c.cents/100),backgroundColor:'#126e82'}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
}
$('month').onchange=async()=>{page=1;try{await load();}catch(e){message(e.message,true);}};
$('previous').onclick=async()=>{page--;try{await load();}catch(e){message(e.message,true);}};$('next').onclick=async()=>{page++;try{await load();}catch(e){message(e.message,true);}};
$('clear').onclick=()=>{editing=null;$('transaction-form').reset();$('date').value=localDate;$('form-title').textContent='Record a transaction';};
$('transaction-form').onsubmit=async e=>{e.preventDefault();try{await api('/transactions'+(editing?'/'+editing:''),editing?'PUT':'POST',{kind:$('kind').value,amount:$('amount').value,category:$('category').value,occurred_on:$('date').value,note:$('note').value});$('month').value=$('date').value.slice(0,7);page=1;$('clear').click();await load();message('Transaction saved.');}catch(e){message(e.message,true);}};
initialize();
