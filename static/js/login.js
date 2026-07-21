// ==========================================================
// Convertly - script.js
// Interactions partagées entre toutes les pages du projet
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  /* ---------- 1. Sidebar : surbrillance du lien actif ---------- */
  const sidebarLinks = document.querySelectorAll('.sidebar-nav li a');
  if (sidebarLinks.length) {
    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';

    sidebarLinks.forEach((link) => {
      const linkPage = link.getAttribute('href');
      const parentLi = link.closest('li');
      if (linkPage === currentPage) {
        parentLi.classList.add('active');
      } else {
        parentLi.classList.remove('active');
      }
    });
  }

  /* ---------- 2. Afficher / masquer le mot de passe ---------- */
  const toggles = document.querySelectorAll('.toggle-password');
  toggles.forEach((toggle) => {
    toggle.addEventListener('click', () => {
      const targetInput = document.querySelector(toggle.dataset.target);
      if (!targetInput) return;

      const isPassword = targetInput.getAttribute('type') === 'password';
      targetInput.setAttribute('type', isPassword ? 'text' : 'password');
      toggle.classList.toggle('bi-eye', !isPassword);
      toggle.classList.toggle('bi-eye-slash', isPassword);
    });
  });

  /* ---------- 3. Historique : filtres par statut ---------- */
  const filterButtons = document.querySelectorAll('.filter-pill');
  const tableRows = document.querySelectorAll('.history-table tbody tr');

  if (filterButtons.length && tableRows.length) {
    filterButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        const filter = btn.dataset.filter;

        tableRows.forEach((row) => {
          if (filter === 'all' || row.dataset.status === filter) {
            row.style.display = '';
          } else {
            row.style.display = 'none';
          }
        });
      });
    });
  }

  /* ---------- 4. Formulaire de profil : édition ---------- */
  const editBtn = document.querySelector('.btn-edit-profile');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      const fields = document.querySelectorAll('.profile-editable');
      fields.forEach((field) => field.toggleAttribute('disabled'));
      editBtn.classList.toggle('btn-editing');
    });
  }

});
