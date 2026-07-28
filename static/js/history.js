// ==========================================================
// Convertly - history.js
// Logique spécifique à la page Historique
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  const historyTable = document.querySelector('.history-table');
  if (!historyTable) return;

  const filterButtons = document.querySelectorAll('.filter-pill');
  const rows = Array.from(historyTable.querySelectorAll('tbody .history-row'));

  function updateEmptyState(visibleCount) {
    const existingEmptyRow = historyTable.querySelector('tbody .history-empty-row');
    if (existingEmptyRow) {
      existingEmptyRow.remove();
    }

    if (visibleCount === 0) {
      const tbody = historyTable.querySelector('tbody');
      const emptyRow = document.createElement('tr');
      emptyRow.className = 'history-empty-row';
      emptyRow.innerHTML = '<td colspan="6" class="text-center empty-state-cell">Aucune conversion ne correspond à ce filtre.</td>';
      tbody.appendChild(emptyRow);
    }
  }

  function applyFilter(filter) {
    let visibleCount = 0;

    rows.forEach((row) => {
      const rowStatus = row.dataset.status || 'all';
      const shouldShow = filter === 'all' || rowStatus === filter;
      row.style.display = shouldShow ? '' : 'none';
      if (shouldShow) visibleCount += 1;
    });

    updateEmptyState(visibleCount);
  }

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      filterButtons.forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      applyFilter(button.dataset.filter || 'all');
    });
  });

  applyFilter('all');

  historyTable.querySelectorAll('.icon-btn-blue[data-action="download"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = btn.closest('tr');
      const fileName = row ? row.querySelector('.file-name')?.textContent.trim() : 'fichier';
      console.log('Téléchargement de :', fileName);
    });
  });

  historyTable.querySelectorAll('.icon-btn-red[data-action="delete"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = btn.closest('tr');
      if (!row) return;

      const confirmDelete = confirm('Supprimer cette conversion de l\'historique ?');
      if (confirmDelete) {
        row.remove();
        rows.splice(rows.indexOf(row), 1);
        applyFilter(document.querySelector('.filter-pill.active')?.dataset.filter || 'all');
      }
    });
  });

});
