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
     SPARKLINES (cartes stats)
     ========================================================= */
  document.querySelectorAll('.cvt-spark').forEach(canvas => {
    const values = canvas.dataset.values.split(',').map(Number);
    const isUp = canvas.dataset.spark === 'up';
    const color = isUp ? '#16A34A' : '#DC2626';

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: values.map((_, i) => i),
        datasets: [{
          data: values,
          borderColor: color,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: false
        }]
      },
      options: {
        responsive: false,
        animation: { duration: 700 },
        plugins: { legend: { display:false }, tooltip: { enabled:false } },
        scales: { x: { display:false }, y: { display:false } }
      }
    });
  });

  /* =========================================================
     DONNEES PAR PERIODE (depuis le backend)
     ========================================================= */
  const statsData = window.statisticsData || {};
  
  const periodData = {
    week: {
      labels: statsData.evolutionLabels || ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
      current: statsData.evolutionCurrent || [210, 130, 250, 190, 400, 190, 235],
      previous: statsData.evolutionPrevious || [180, 150, 200, 210, 320, 170, 200]
    },
    month: {
      labels: statsData.evolutionLabels || ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4'],
      current: statsData.evolutionCurrent || [980, 1120, 1340, 1542],
      previous: statsData.evolutionPrevious || [860, 990, 1180, 1300]
    },
    year: {
      labels: statsData.evolutionLabels || ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'],
      current: statsData.evolutionCurrent || [820, 940, 1010, 1100, 1250, 1180, 1320, 1400, 1290, 1460, 1510, 1542],
      previous: statsData.evolutionPrevious || [700, 780, 860, 900, 980, 1020, 1080, 1150, 1090, 1200, 1260, 1300]
    }
  };

  /* =========================================================
     LINE CHART : évolution des conversions
     ========================================================= */
  const evolutionCtx = document.getElementById('evolutionChart');
  const evoGradient = evolutionCtx.getContext('2d').createLinearGradient(0, 0, 0, 300);
  evoGradient.addColorStop(0, 'rgba(37, 99, 235, 0.22)');
  evoGradient.addColorStop(1, 'rgba(37, 99, 235, 0)');

  const evolutionChart = new Chart(evolutionCtx, {
    type: 'line',
    data: {
      labels: periodData.week.labels,
      datasets: [
        {
          label: 'Période actuelle',
          data: periodData.week.current,
          borderColor: '#2563EB',
          backgroundColor: evoGradient,
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#2563EB',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          tension: 0.4,
          fill: true
        },
        {
          label: 'Période précédente',
          data: periodData.week.previous,
          borderColor: '#CBD5E1',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0.4,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: 'easeOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleFont: { family: 'Poppins', size: 12, weight: '600' },
          bodyFont: { family: 'Poppins', size: 12 },
          padding: 10,
          cornerRadius: 8
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } } },
        y: { beginAtZero: true, grid: { color: '#EDF1F7' }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } } }
      }
    }
  });

  /* =========================================================
     SELECTEUR DE PERIODE (rechargement avec la période)
     ========================================================= */
  const periodSelect = document.getElementById('cvtPeriodSelect');
  const periodLabel = document.getElementById('cvtPeriodLabel');

  periodSelect.addEventListener('change', () => {
    const key = periodSelect.value;
    periodLabel.textContent = periodSelect.options[periodSelect.selectedIndex].text;
    
    // Rediriger vers la même page avec le paramètre 'period'
    window.location.href = `${window.location.pathname}?period=${key}`;
  });
  
  // Définir la période actuelle dans le select au chargement
  const currentPeriod = statsData.period || 'week';
  if (periodSelect) {
    periodSelect.value = currentPeriod;
  }

  /* =========================================================
     DOUGHNUT : répartition par statut (données dynamiques)
     ========================================================= */
  new Chart(document.getElementById('statusChart'), {
    type: 'doughnut',
    data: {
      labels: ['Réussi', 'Échec'],
      datasets: [{
        data: [statsData.statusSuccess ?? 0, statsData.statusFailed ?? 0],
        backgroundColor: ['#16A34A', '#DC2626'],
        borderWidth: 3,
        borderColor: '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '74%',
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleFont: { family: 'Poppins', size: 12, weight: '600' },
          bodyFont: { family: 'Poppins', size: 12 },
          padding: 10,
          cornerRadius: 8
        }
      }
    }
  });

  /* =========================================================
     BAR CHART : conversions par jour de la semaine (données dynamiques)
     ========================================================= */
  new Chart(document.getElementById('weekdayChart'), {
    type: 'bar',
    data: {
      labels: statsData.weekdayLabels || ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
      datasets: [{
        label: 'Conversions',
        data: statsData.weekdayValues || [210, 130, 250, 190, 400, 190, 235],
        backgroundColor: '#2563EB',
        borderRadius: 8,
        maxBarThickness: 36
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleFont: { family: 'Poppins', size: 12, weight: '600' },
          bodyFont: { family: 'Poppins', size: 12 },
          padding: 10,
          cornerRadius: 8
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } } },
        y: { beginAtZero: true, grid: { color: '#EDF1F7' }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } } }
      }
    }
  });

  /* =========================================================
     BAR CHART (horizontal) : heures de pointe (données dynamiques)
     ========================================================= */
  new Chart(document.getElementById('hoursChart'), {
    type: 'bar',
    data: {
      labels: statsData.hoursLabels || ['00h', '04h', '08h', '12h', '16h', '20h'],
      datasets: [{
        label: 'Conversions',
        data: statsData.hoursValues || [12, 8, 145, 210, 260, 95],
        backgroundColor: '#7C3AED',
        borderRadius: 8,
        maxBarThickness: 22
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleFont: { family: 'Poppins', size: 12, weight: '600' },
          bodyFont: { family: 'Poppins', size: 12 },
          padding: 10,
          cornerRadius: 8
        }
      },
      scales: {
        x: { beginAtZero: true, grid: { color: '#EDF1F7' }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 11 } } },
        y: { grid: { display: false }, ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } } }
      }
    }
  });

  /* =========================================================
     PROGRESS BARS : formats les plus utilisés (animation à l'entrée)
     ========================================================= */
  const progressBars = document.querySelectorAll('.cvt-progress-bar span');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting){
        entry.target.classList.add('cvt-filled');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  progressBars.forEach(bar => observer.observe(bar));

  /* =========================================================
     EXPORT (données réelles en CSV)
     ========================================================= */
  document.getElementById('cvtExportBtn').addEventListener('click', () => {
    const period = statsData.period || 'week';
    const btn = document.getElementById('cvtExportBtn');
    const originalHTML = btn.innerHTML;
    
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Rapport en cours...';
    btn.disabled = true;
    
    // Rediriger vers la route d'export
    window.location.href = `/statistics_admin/export?period=${period}`;
    
    // Restaurer le bouton après un délai
    setTimeout(() => {
      btn.innerHTML = originalHTML;
      btn.disabled = false;
    }, 2000);
  });

});
