const formatMeta = {
  PDF:  {icon:'bi-filetype-pdf', color:'text-red-500 bg-red-50'},
  DOCX: {icon:'bi-filetype-docx', color:'text-blue-500 bg-blue-50'},
  XLSX: {icon:'bi-filetype-xlsx', color:'text-green-600 bg-green-50'},
  PPTX: {icon:'bi-filetype-pptx', color:'text-orange-500 bg-orange-50'},
};
const statusBadge = {
  'Converti':  'bg-green-100 text-green-700',
  'En attente':'bg-amber-100 text-amber-700',
  'Échec':     'bg-red-100 text-red-700',
};


const tbody = document.getElementById('docTableBody');
const countLabel = document.getElementById('docCountLabel');
const pageInfo = document.getElementById('pageInfo');

function toast(msg, type='success'){
  const host = document.getElementById('toastHost');
  const colors = { success:'bg-slate-900', error:'bg-red-600' };
  const el = document.createElement('div');
  el.className = `toast ${colors[type]} text-white text-sm px-4 py-2.5 rounded-lg shadow-lg opacity-0 translate-y-2`;
  el.textContent = msg;
  host.appendChild(el);
  requestAnimationFrame(()=>{ el.classList.remove('opacity-0','translate-y-2'); });
  setTimeout(()=>{
    el.classList.add('opacity-0');
    setTimeout(()=>el.remove(), 300);
  }, 2400);
}

function render(){
  const checked = [...document.querySelectorAll('.statusFilter:checked')].map(c=>c.value);
  const filtered = documents.filter(d =>
    checked.includes(d.status)
  );

  tbody.innerHTML = filtered.map((d, i) => {
    const fm = formatMeta[d.format];
    return `
    <tr class="row-fade border-b border-slate-50 hover:bg-slate-50/60" data-idx="${documents.indexOf(d)}">
      <td class="py-3 px-5 flex items-center gap-2 font-medium text-slate-700">
        <span class="w-7 h-7 rounded-lg flex items-center justify-center ${fm.color}"><i class="bi ${fm.icon}"></i></span>
        ${d.name}
      </td>
      <td class="py-3 px-5"><span class="px-2 py-0.5 rounded-md text-xs font-semibold ${fm.color}">${d.format}</span></td>
      <td class="py-3 px-5 text-slate-500">${d.size}</td>
      <td class="py-3 px-5 text-slate-500">${d.date}</td>
      <td class="py-3 px-5"><span class="px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[d.status]}">${d.status}</span></td>
      <td class="py-3 px-5 text-right">
        <div class="inline-flex items-center gap-1">
          <button title="Télécharger" class="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-500"><i class="bi bi-download"></i></button>
          <button title="Supprimer" onclick="deleteDoc(${documents.indexOf(d)})" class="w-8 h-8 rounded-lg hover:bg-red-50 text-slate-500 hover:text-red-600"><i class="bi bi-trash"></i></button>
        </div>
      </td>
    </tr>`;
  }).join('') || `<tr><td colspan="6" class="py-10 text-center text-slate-400">Aucun document trouvé.</td></tr>`;

  countLabel.textContent = `Tous les documents (${documents.length})`;
  pageInfo.textContent = `Affichage de 1 à ${filtered.length} sur ${documents.length} documents`;
}

function deleteDoc(idx){
  const row = tbody.querySelector(`tr[data-idx="${idx}"]`);
  if(row){ row.classList.add('leaving'); }
  setTimeout(()=>{
    documents.splice(idx,1);
    render();
    toast('Document déplacé vers la corbeille');
  }, 280);
}

document.querySelectorAll('.statusFilter').forEach(c => c.addEventListener('change', render));

document.getElementById('filterBtn').addEventListener('click', () => {
  document.getElementById('filterPanel').classList.toggle('hidden');
});
document.addEventListener('click', (e) => {
  if(!e.target.closest('#filterBtn') && !e.target.closest('#filterPanel')){
    document.getElementById('filterPanel').classList.add('hidden');
  }
});

let sortDir = {name:1, date:1};
document.querySelectorAll('[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.sort;
    documents.sort((a,b) => a[key === 'name' ? 'name' : 'date'].localeCompare(b[key === 'name' ? 'name' : 'date']) * sortDir[key]);
    sortDir[key] *= -1;
    render();
  });
});

document.querySelectorAll('.page-btn[data-page]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.page-btn[data-page]').forEach(b => b.classList.remove('bg-brand-600','text-white'));
    btn.classList.add('bg-brand-600','text-white');
  });
});

const fileInput = document.getElementById('fileInput');
document.getElementById('addDocBtn').addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  [...fileInput.files].forEach(file => {
    const ext = file.name.split('.').pop().toUpperCase();
    if(!formatMeta[ext]) return;
    const sizeKB = file.size / 1024;
    const sizeLabel = sizeKB > 1024 ? (sizeKB/1024).toFixed(2)+' MB' : Math.round(sizeKB)+' KB';
    const now = new Date();
    const dateLabel = `${String(now.getDate()).padStart(2,'0')}/${String(now.getMonth()+1).padStart(2,'0')}/${now.getFullYear()} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    documents.unshift({name:file.name, format:ext, size:sizeLabel, date:dateLabel, status:'En attente'});
    render();
    toast(`${file.name} ajouté — conversion en cours...`);
    setTimeout(()=>{
      const doc = documents.find(d => d.name === file.name);
      if(doc){ doc.status = 'Converti'; render(); toast(`${file.name} converti avec succès`); }
    }, 2200);
  });
  fileInput.value = '';
});

render();