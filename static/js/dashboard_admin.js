document.addEventListener('DOMContentLoaded', () => {

  /* =========================================================
     SIDEBAR : mobile open/close + active nav state
     ========================================================= */
  const sidebar   = document.getElementById('cvtSidebar');
  const overlay   = document.getElementById('cvtOverlay');
  const burger    = document.getElementById('cvtBurger');
  const closeBtn  = document.getElementById('cvtSidebarClose');

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
      e.preventDefault();
      document.querySelectorAll('.cvt-nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      closeSidebar();
    });
  });

  /* =========================================================
     DATE RANGE / PERIOD SELECTOR (line chart)
     ========================================================= */
  const rangeSelect = document.getElementById('cvtRangeSelect');
  const rangeLabel  = document.getElementById('cvtRangeLabel');

  const rangeDatasets = {
    '7 derniers jours': {
      labels: chartLabels,
      data:   chartValues
    },
    '14 derniers jours': {
      labels: ['08','09','10','11','12','13','14','15','16','17','18','19','20','21'],
      data:   [140,160,120,180,150,210,190,210,130,250,190,400,190,235]
    },
    '30 derniers jours': {
      labels: Array.from({length: 30}, (_, i) => (i + 1).toString()),
      data:   Array.from({length: 30}, () => Math.floor(80 + Math.random() * 340))
    }
  };

  if (rangeSelect){
    rangeSelect.addEventListener('change', () => {
      const key = rangeSelect.value;
      rangeLabel.textContent = key;
      const set = rangeDatasets[key];
      lineChart.data.labels = set.labels;
      lineChart.data.datasets[0].data = set.data;
      lineChart.update();
    });
  }

  /* =========================================================
     SPARKLINES (mini charts on stat cards)
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
        scales: {
          x: { display:false },
          y: { display:false }
        }
      }
    });
  });

  /* =========================================================
     LINE CHART : conversions des 7 derniers jours
     ========================================================= */
  const lineCtx = document.getElementById('lineChart');
  const lineGradient = lineCtx.getContext('2d').createLinearGradient(0, 0, 0, 300);
  lineGradient.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
  lineGradient.addColorStop(1, 'rgba(37, 99, 235, 0)');

  const lineChart = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: rangeDatasets['7 derniers jours'].labels,
      datasets: [{
        label: 'Conversions',
        data: rangeDatasets['7 derniers jours'].data,
        borderColor: '#2563EB',
        backgroundColor: lineGradient,
        borderWidth: 2.5,
        pointRadius: 4,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: '#2563EB',
        pointBorderWidth: 2,
        pointHoverRadius: 6,
        tension: 0.4,
        fill: true
      }]
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
          cornerRadius: 8,
          displayColors: false
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#EDF1F7' },
          border: { dash: [4, 4] },
          ticks: { color: '#94A3B8', font: { family: 'Poppins', size: 12 }, stepSize: 100 }
        }
      }
    }
  });

  /* =========================================================
     DOUGHNUT CHART : conversions par format cible
     ========================================================= */
  const doughnutCtx = document.getElementById('doughnutChart');
  new Chart(doughnutCtx, {
    type: 'doughnut',
    data: {
      labels: formatLabels,
      datasets: [{
        data: formatValues,
        backgroundColor: ['#2563EB', '#38BDF8', '#22C55E', '#F97316', '#A78BFA', '#CBD5E1'],
        borderWidth: 3,
        borderColor: '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleFont: { family: 'Poppins', size: 12, weight: '600' },
          bodyFont: { family: 'Poppins', size: 12 },
          padding: 10,
          cornerRadius: 8,
          displayColors: true,
          callbacks: {
            label: (ctx) => `${ctx.label} : ${ctx.formattedValue}`
          }
        }
      }
    }
  });
  const legendContainer = document.getElementById("formatsLegend");

  const total = formatValues.reduce((a, b) => a + b, 0);

  const colors = [
      "#2563EB",
      "#38BDF8",
      "#22C55E",
      "#F97316",
      "#A78BFA",
      "#CBD5E1"
  ];

  document.getElementById("cvtDonutTotal").textContent = total;
  legendContainer.innerHTML = "";

  formatLabels.forEach((label, index) => {

      const value = formatValues[index];

      const percent = total === 0
          ? 0
          : Math.round(value * 100 / total);

      legendContainer.innerHTML += `
          <div class="cvt-legend-row">
              <span class="cvt-legend-label">
                  <i class="cvt-dot" style="background:${colors[index]}"></i>
                  ${label}
              </span>

              <span>${value}</span>

              <span>${percent}%</span>

          </div>
      `;

  });

});
