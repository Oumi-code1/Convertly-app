document.addEventListener('DOMContentLoaded', () => {

  /* =========================================================
     SIDEBAR : mobile open/close
     ========================================================= */
  const sidebar  = document.getElementById('cvtSidebar');
  const overlay  = document.getElementById('cvtOverlay');
  const burger   = document.getElementById('cvtBurger');
  const closeBtn = document.getElementById('cvtSidebarClose');

  function openSidebar(){
    sidebar.classList.add('cvt-open');
    overlay.classList.add('cvt-visible');
  }
  function closeSidebar(){
    sidebar.classList.remove('cvt-open');
    overlay.classList.remove('cvt-visible');
  }

  burger && burger.addEventListener('click', openSidebar);
  closeBtn && closeBtn.addEventListener('click', closeSidebar);
  overlay && overlay.addEventListener('click', closeSidebar);

  document.querySelectorAll('.cvt-nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (!href || href === '#'){ e.preventDefault(); }
      document.querySelectorAll('.cvt-nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      closeSidebar();
    });
  });

  /* =========================================================
     TOAST
     ========================================================= */
  const toast = document.getElementById('cvtToast');
  const toastMsg = document.getElementById('cvtToastMsg');

  function showToast(message = 'Modifications enregistrées'){
    toastMsg.textContent = message;
    toast.classList.add('cvt-visible');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove('cvt-visible'), 3200);
  }

  /* =========================================================
     GRILLE : références
     ========================================================= */
  const grid = document.getElementById('cvtFormatsGrid');
  const cards = () => Array.from(grid.querySelectorAll('.cvt-format-card'));
  const emptyState = document.getElementById('cvtEmptyState');

  const searchInput = document.getElementById('cvtFormatSearch');
  const categoryFilter = document.getElementById('cvtCategoryFilter');
  const categoryFilterLabel = document.getElementById('cvtCategoryFilterLabel');
  const statusFilter = document.getElementById('cvtStatusFilter');
  const statusFilterLabel = document.getElementById('cvtStatusFilterLabel');

  /* =========================================================
     RECHERCHE + FILTRES (combinés, en direct)
     ========================================================= */
  function applyFilters() {

    const query = searchInput?.value.trim().toLowerCase() || '';
    const category = categoryFilter?.value || '';
    const status = statusFilter?.value || '';

    let visibleCount = 0;

    cards().forEach(card => {

        const name = card.dataset.name || '';

        /* =========================================
           RECHERCHE
           ========================================= */

        const matchesQuery =
            !query || name.includes(query);


        /* =========================================
           DÉTERMINER LA CATÉGORIE
           ========================================= */

        const chips = card.querySelectorAll('.cvt-format-chip');

        let formatOrigine = '';
        let formatCible = '';

        if (chips.length >= 2) {

            formatOrigine =
                chips[0].textContent.trim().toUpperCase();

            formatCible =
                chips[1].textContent.trim().toUpperCase();
        }


        /*
         * Formats DOCUMENT
         */

        const formatsDocument = [
            'DOCX',
            'PDF',
            'XLSX',
            'PPTX',
            'TXT'
        ];


        /*
         * Formats IMAGE
         */

        const formatsImage = [
            'PNG',
            'JPG',
            'JPEG'
        ];


        let cardCategory = '';


        if (
            formatsDocument.includes(formatOrigine) &&
            formatsDocument.includes(formatCible)
        ) {

            cardCategory = 'Document';

        }
        else if (
            formatsImage.includes(formatOrigine) &&
            formatsImage.includes(formatCible)
        ) {

            cardCategory = 'Image';
        }


        /* =========================================
           FILTRE CATÉGORIE
           ========================================= */

        const matchesCategory =
            !category ||
            category.toLowerCase() === cardCategory.toLowerCase();


        /* =========================================
           FILTRE STATUT
           ========================================= */

        const matchesStatus =
            !status ||
            card.dataset.status === status;


        /* =========================================
           AFFICHER / CACHER
           ========================================= */

        const visible =
            matchesQuery &&
            matchesCategory &&
            matchesStatus;

        card.style.display = visible ? '' : 'none';

        if (visible) {
            visibleCount++;
        }

    });


    /* =========================================
       EMPTY STATE
       ========================================= */

    if (emptyState) {
        emptyState.classList.toggle(
            'cvt-visible',
            visibleCount === 0
        );
    }

    if (grid) {
        grid.style.display =
            visibleCount === 0 ? 'none' : '';
    }
  }

  // Appliquer les filtres au changement
  searchInput?.addEventListener('input', applyFilters);
  categoryFilter?.addEventListener('change', applyFilters);
  statusFilter?.addEventListener('change', applyFilters);

  // Appliquer les filtres au chargement
  applyFilters();

  /* =========================================================
     VUE GRILLE / LISTE
     ========================================================= */
  const viewGridBtn = document.getElementById('cvtViewGrid');
  const viewListBtn = document.getElementById('cvtViewList');

  viewGridBtn && viewGridBtn.addEventListener('click', () => {
    grid.classList.remove('cvt-formats-list');
    viewGridBtn.classList.add('active');
    viewListBtn.classList.remove('active');
  });
  
  viewListBtn && viewListBtn.addEventListener('click', () => {
    grid.classList.add('cvt-formats-list');
    viewListBtn.classList.add('active');
    viewGridBtn.classList.remove('active');
  });

  /* =========================================================
     TOGGLE STATUT (actif / inactif) - AVEC APPEL API
     ========================================================= */
  grid.addEventListener('change', async (e) => {
    if (!e.target.classList.contains('cvt-format-toggle')) return;
    
    const card = e.target.closest('.cvt-format-card');
    const origin = e.target.dataset.origin;
    const target = e.target.dataset.target;
    
    if (!origin || !target) return;
    
    try {
      const response = await fetch('/api/format/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin, target })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const isActive = data.status === 1;
        card.dataset.status = isActive ? 'Actif' : 'Inactif';
        card.classList.toggle('cvt-format-card-inactive', !isActive);
        e.target.checked = isActive;
        showToast(data.message);
        applyFilters();
      } else {
        e.target.checked = !e.target.checked;
        showToast('Erreur: ' + data.error);
      }
    } catch (error) {
      e.target.checked = !e.target.checked;
      showToast('Erreur: ' + error.message);
    }
  });

  /* =========================================================
     MODALE : AJOUTER UN FORMAT
     ========================================================= */
  const formatModalOverlay = document.getElementById('cvtFormatModalOverlay');
  const formatModalTitle   = document.getElementById('cvtFormatModalTitle');
  const formatModalSubmit  = document.getElementById('cvtFormatModalSubmit');
  const formatForm         = document.getElementById('cvtFormatForm');

  const sourceInput   = document.getElementById('cvtFormatSource');
  const targetInput   = document.getElementById('cvtFormatTarget');

  function openFormatModal(mode){
    if (mode === 'add'){
      formatModalTitle.textContent = 'Ajouter une conversion';
      formatModalSubmit.innerHTML = '<i class="fa-solid fa-check"></i> Ajouter';
      formatForm.reset();
    }
    formatModalOverlay.classList.add('cvt-visible');
  }

  function closeFormatModal(){
    formatModalOverlay.classList.remove('cvt-visible');
    formatForm.reset();
  }

  document.getElementById('cvtAddFormatBtn')?.addEventListener('click', () => openFormatModal('add'));
  document.getElementById('cvtFormatModalClose')?.addEventListener('click', closeFormatModal);
  document.getElementById('cvtFormatModalCancel')?.addEventListener('click', closeFormatModal);
  formatModalOverlay?.addEventListener('click', (e) => { 
    if (e.target === formatModalOverlay) closeFormatModal(); 
  });

  // Soumettre le formulaire pour ajouter ou modifier une conversion
  formatForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const mode = formatForm.dataset.mode || 'add';
    const newOrigin = sourceInput.value.trim().toUpperCase();
    const newTarget = targetInput.value.trim().toUpperCase();
    
    if (!newOrigin || !newTarget) {
      showToast('Veuillez remplir tous les champs');
      return;
    }
    
    try {
      let response;
      let payload;
      let endpoint;

      if (mode === 'edit') {
        // Mode modification : appeler /api/format/edit
        const oldOrigin = formatForm.dataset.oldOrigin || '';
        const oldTarget = formatForm.dataset.oldTarget || '';
        
        endpoint = '/api/format/edit';
        payload = {
          old_origin: oldOrigin,
          old_target: oldTarget,
          new_origin: newOrigin,
          new_target: newTarget
        };
      } else {
        // Mode ajout : appeler /api/format/add
        endpoint = '/api/format/add';
        payload = {
          origin: newOrigin,
          target: newTarget
        };
      }

      response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (data.success) {
        closeFormatModal();
        // Réinitialiser le mode à "add"
        formatForm.dataset.mode = 'add';
        formatForm.dataset.oldOrigin = '';
        formatForm.dataset.oldTarget = '';
        
        showToast(data.message);
        // Recharger la page pour voir les changements
        setTimeout(() => location.reload(), 800);
      } else {
        showToast('Erreur: ' + data.error);
      }
    } catch (error) {
      showToast('Erreur: ' + error.message);
    }
  });

  /* =========================================================
     MODALE : CONFIRMATION SUPPRESSION
     ========================================================= */
  const deleteModalOverlay = document.getElementById('cvtDeleteModalOverlay');
  const deleteFormatName   = document.getElementById('cvtDeleteFormatName');
  const deleteCancelBtn    = document.getElementById('cvtDeleteModalCancel');
  const deleteConfirmBtn   = document.getElementById('cvtDeleteModalConfirm');

  let pendingDelete = { origin: null, target: null, card: null };

  function openDeleteModal(origin, target, title){
    pendingDelete = { origin, target, card: null };
    deleteFormatName.textContent = title;
    deleteModalOverlay.classList.add('cvt-visible');
  }
  
  function closeDeleteModal(){
    deleteModalOverlay.classList.remove('cvt-visible');
    pendingDelete = { origin: null, target: null, card: null };
  }

  deleteCancelBtn?.addEventListener('click', closeDeleteModal);
  deleteModalOverlay?.addEventListener('click', (e) => { 
    if (e.target === deleteModalOverlay) closeDeleteModal(); 
  });

  deleteConfirmBtn?.addEventListener('click', async () => {
    if (!pendingDelete.origin || !pendingDelete.target) return;
    
    try {
      const response = await fetch('/api/format/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin: pendingDelete.origin, target: pendingDelete.target })
      });
      
      const data = await response.json();
      
      if (data.success) {
        closeDeleteModal();
        showToast(data.message);
        // Recharger la page pour voir la suppression
        setTimeout(() => location.reload(), 800);
      } else {
        showToast('Erreur: ' + data.error);
      }
    } catch (error) {
      showToast('Erreur: ' + error.message);
    }
  });

  /* =========================================================
     DELEGATION : boutons modifier / supprimer dans la grille
     ========================================================= */
    grid?.addEventListener('click', (e) => {

      const btn = e.target.closest('.cvt-icon-action');

      if (!btn) return;

      const card = btn.closest('.cvt-format-card');

      const action = btn.dataset.action;
      const origin = btn.dataset.origin;
      const target = btn.dataset.target;


      /* =====================================================
        MODIFIER
        ===================================================== */

      if (action === 'edit') {

          // Ouvrir la même modal que pour ajouter
          formatModalTitle.textContent = 'Modifier la conversion';

          formatModalSubmit.innerHTML =
              '<i class="fa-solid fa-check"></i> Enregistrer';

          // Remplir les champs avec les valeurs actuelles
          sourceInput.value = origin || '';
          targetInput.value = target || '';

          // Stocker les anciennes valeurs
          formatForm.dataset.mode = 'edit';
          formatForm.dataset.oldOrigin = origin || '';
          formatForm.dataset.oldTarget = target || '';

          // Afficher la modal
          formatModalOverlay.classList.add('cvt-visible');

          return;
      }


      /* =====================================================
        SUPPRIMER
        ===================================================== */

      if (action === 'delete') {

          const title =
              card.querySelector('.cvt-format-title')?.textContent
              || `${origin} → ${target}`;

          openDeleteModal(origin, target, title);

          return;
      }

  });
 
});
