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