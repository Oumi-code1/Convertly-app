document.addEventListener('DOMContentLoaded', () => {

  /* ================= SIDEBAR (inchangé) ================= */
  const sidebar  = document.getElementById('cvtSidebar');
  const overlay  = document.getElementById('cvtOverlay');
  const burger   = document.getElementById('cvtBurger');
  const closeBtn = document.getElementById('cvtSidebarClose');

  function openSidebar(){ sidebar.classList.add('cvt-open'); overlay.classList.add('cvt-visible'); }
  function closeSidebar(){ sidebar.classList.remove('cvt-open'); overlay.classList.remove('cvt-visible'); }

  burger && burger.addEventListener('click', openSidebar);
  closeBtn && closeBtn.addEventListener('click', closeSidebar);
  overlay && overlay.addEventListener('click', closeSidebar);

  /* ================= TOAST ================= */
  const toast = document.getElementById('cvtToast');
  const toastMsg = document.getElementById('cvtToastMsg');
  function showToast(message = 'Action effectuée'){
    toastMsg.textContent = message;
    toast.classList.add('cvt-visible');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove('cvt-visible'), 3200);
  }

  /* ================= ÉTAT ================= */
  const tableBody   = document.getElementById('cvtHistoryBody');
  const emptyState  = document.getElementById('cvtEmptyState');
  const paginationInfo = document.getElementById('cvtPaginationInfo');
  const paginationControls = document.getElementById('cvtPaginationControls');

  const searchInput  = document.getElementById('cvtHistorySearch');
  const statusFilter = document.getElementById('cvtStatusFilter');
  const statusFilterLabel = document.getElementById('cvtStatusFilterLabel');
  const formatFilter = document.getElementById('cvtFormatFilter');
  const formatFilterLabel = document.getElementById('cvtFormatFilterLabel');

  let state = { search: '', status: '', format: '', page: 1 };
  let searchDebounce = null;

  /* ================= APPEL API ================= */
  async function fetchHistory(){
    const params = new URLSearchParams({
      search: state.search,
      status: state.status,
      format: state.format,
      page: state.page
    });

    const res = await fetch(`/api/history_admin?${params.toString()}`);
    const data = await res.json();

    if (!data.success){
      showToast('Erreur lors du chargement des données');
      return;
    }

    renderRows(data.conversions);
    renderPagination(data);
  }

  function escapeHtml(str){
    return String(str ?? '').replace(/[&<>"']/g, s => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[s]));
  }

  function renderRows(conversions){
    if (conversions.length === 0){
      tableBody.innerHTML = '';
      emptyState.classList.add('cvt-visible');
      return;
    }
    emptyState.classList.remove('cvt-visible');

    tableBody.innerHTML = conversions.map(c => `
      <tr data-status="${escapeHtml(c.status_label)}" data-id="${c.id_conversion}">
        <td>
          <div class="cvt-user-cell">
            <img src="https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(c.user_name)}&backgroundColor=2563eb" alt="">
            <span>${escapeHtml(c.user_name)}</span>
          </div>
        </td>
        <td><i class="${c.file_fa_icon} cvt-file-icon ${c.file_css_class}"></i> ${escapeHtml(c.file_name)}</td>
        <td>
          <span class="cvt-format-chip ${c.format_origin_chip_class}">${escapeHtml(c.format_origin)}</span>
          <i class="fa-solid fa-arrow-right-long cvt-arrow-mini"></i>
          <span class="cvt-format-chip ${c.format_cible_chip_class}">${escapeHtml(c.format_cible)}</span>
        </td>
        <td>${escapeHtml(c.file_size)}</td>
        <td>${escapeHtml(c.date_conversion)}</td>
        <td><span class="cvt-badge-status ${c.status_class}">${escapeHtml(c.status_label)}</span></td>
        <td>
          <div class="cvt-row-actions">
            <button class="cvt-icon-action" title="Voir les détails" data-action="view" data-id="${c.id_conversion}"><i class="fa-regular fa-eye"></i></button>
            ${c.status_filter === 'success'
              ? `<button class="cvt-icon-action" title="Télécharger" data-action="download" data-id="${c.id_conversion}"><i class="fa-solid fa-download"></i></button>`
              : ``}
          </div>
        </td>
      </tr>
    `).join('');
  }

  function renderPagination(data){
    paginationInfo.innerHTML = data.total > 0
      ? `Affichage de <strong>${data.debut}-${data.fin}</strong> sur <strong>${data.total}</strong> conversions`
      : `Aucune conversion trouvée`;

    const { page, total_pages } = data;
    let pages = [];
    const windowSize = 1;

    for (let p = 1; p <= total_pages; p++){
      if (p === 1 || p === total_pages || (p >= page - windowSize && p <= page + windowSize)){
        pages.push(p);
      } else if (pages[pages.length - 1] !== '…'){
        pages.push('…');
      }
    }

    let html = `<button class="cvt-page-btn" id="cvtPagePrev" ${page <= 1 ? 'disabled' : ''} aria-label="Page précédente"><i class="fa-solid fa-chevron-left"></i></button>`;

    pages.forEach(p => {
      if (p === '…'){
        html += `<span class="cvt-page-dots">…</span>`;
      } else {
        html += `<button class="cvt-page-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
      }
    });

    html += `<button class="cvt-page-btn" id="cvtPageNext" ${page >= total_pages ? 'disabled' : ''} aria-label="Page suivante"><i class="fa-solid fa-chevron-right"></i></button>`;

    paginationControls.innerHTML = html;

    paginationControls.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.page = parseInt(btn.dataset.page, 10);
        fetchHistory();
      });
    });
    document.getElementById('cvtPagePrev')?.addEventListener('click', () => {
      if (state.page > 1){ state.page--; fetchHistory(); }
    });
    document.getElementById('cvtPageNext')?.addEventListener('click', () => {
      state.page++; fetchHistory();
    });
  }

  /* ================= RECHERCHE + FILTRES ================= */
  searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      state.search = searchInput.value.trim();
      state.page = 1;
      fetchHistory();
    }, 300);
  });

  statusFilter.addEventListener('change', () => {
    statusFilterLabel.textContent = statusFilter.value || 'Tous les statuts';
    state.status = statusFilter.value;
    state.page = 1;
    fetchHistory();
  });

  formatFilter.addEventListener('change', () => {
    formatFilterLabel.textContent = formatFilter.value || 'Tous les formats';
    state.format = formatFilter.value;
    state.page = 1;
    fetchHistory();
  });

  /* ================= MODALE DÉTAILS ================= */
  const detailModalOverlay = document.getElementById('cvtDetailModalOverlay');
  const detailId       = document.getElementById('cvtDetailId');
  const detailAvatar   = document.getElementById('cvtDetailAvatar');
  const detailUserName = document.getElementById('cvtDetailUserName');
  const detailUserMail = document.getElementById('cvtDetailUserMail');
  const detailStatusBadge = document.getElementById('cvtDetailStatusBadge');
  const detailFile     = document.getElementById('cvtDetailFile');
  const detailFormat   = document.getElementById('cvtDetailFormat');
  const detailSize     = document.getElementById('cvtDetailSize');
  const detailDuration = document.getElementById('cvtDetailDuration');
  const detailDate     = document.getElementById('cvtDetailDate');
  const detailError    = document.getElementById('cvtDetailError');
  const detailAction   = document.getElementById('cvtDetailModalAction');

  const statusClassMap = { 'Réussi': 'cvt-status-success', 'Échec': 'cvt-status-failed' };
  let currentDetail = null;

  async function openDetailModal(id){
    const res = await fetch(`/api/history_admin/${id}/details`);
    const data = await res.json();

    if (!data.success){
      showToast('Impossible de charger les détails');
      return;
    }

    const c = data.conversion;
    currentDetail = c;

    detailId.textContent = `CVT-${String(c.id_conversion).padStart(5, '0')}`;
    detailAvatar.src = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(c.user_name)}&backgroundColor=2563eb`;
    detailUserName.textContent = c.user_name;
    detailUserMail.textContent = c.user_email;
    detailStatusBadge.textContent = c.status_label;
    detailStatusBadge.className = 'cvt-badge-status ' + statusClassMap[c.status_label];
    detailFile.textContent = c.file_name;
    detailFormat.textContent = `${c.format_origin} → ${c.format_cible}`;
    detailSize.textContent = c.file_size;
    detailDuration.textContent = 'Non disponible';
    detailDate.textContent = c.date_conversion;

    // Pas de colonne "message d'erreur" en base : on n'invente pas de texte,
    // on masque simplement le bloc d'erreur.
    detailError.classList.remove('cvt-visible');

    if (c.can_download){
      detailAction.innerHTML = '<i class="fa-solid fa-download"></i> Télécharger le fichier';
      detailAction.disabled = false;
    } else {
      detailAction.innerHTML = '<i class="fa-solid fa-ban"></i> Fichier indisponible';
      detailAction.disabled = true;
    }

    detailModalOverlay.classList.add('cvt-visible');
  }

  function closeDetailModal(){
    detailModalOverlay.classList.remove('cvt-visible');
    currentDetail = null;
  }

  document.getElementById('cvtDetailModalClose').addEventListener('click', closeDetailModal);
  document.getElementById('cvtDetailModalCloseBtn').addEventListener('click', closeDetailModal);
  detailModalOverlay.addEventListener('click', (e) => { if (e.target === detailModalOverlay) closeDetailModal(); });

  detailAction.addEventListener('click', () => {
    if (currentDetail && currentDetail.can_download){
      window.location.href = currentDetail.download_url;
    }
  });

  /* ================= ACTIONS DANS LE TABLEAU ================= */
  tableBody.addEventListener('click', (e) => {
    const btn = e.target.closest('.cvt-icon-action');
    if (!btn) return;
    const action = btn.dataset.action;
    const id = btn.dataset.id;

    if (action === 'view'){
      openDetailModal(id);
    } else if (action === 'download'){
      window.location.href = `/history_admin/download/${id}`;
    }
  });

  /* ================= EXPORT (données filtrées réelles) ================= */
  document.getElementById('cvtExportBtn').addEventListener('click', () => {
    const params = new URLSearchParams({
      search: state.search,
      status: state.status,
      format: state.format
    });
    window.location.href = `/history_admin/export?${params.toString()}`;
  });

  /* ================= CHARGEMENT INITIAL ================= */
  fetchHistory();
});