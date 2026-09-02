document.addEventListener('DOMContentLoaded', () => {

  const notifBtn      = document.getElementById('cvtNotifBtn');
  const notifDropdown = document.getElementById('cvtNotifDropdown');
  const notifList     = document.getElementById('cvtNotifList');
  const notifBadge    = document.getElementById('cvtNotifBadge');

  if (!notifBtn || !notifDropdown) return;

  let isOpen = false;

  function updateBadge(count){
    if (count > 0){
      notifBadge.textContent = count;
      notifBadge.style.display = '';
    } else {
      notifBadge.style.display = 'none';
    }
  }

  function iconForType(icon){
    return icon || 'fa-bell';
  }

  function escapeHtml(str){
    return String(str ?? '').replace(/[&<>"']/g, s => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[s]));
  }

  function renderNotifications(notifications){
    if (!notifications.length){
      notifList.innerHTML = '<div class="cvt-notif-empty">Aucune notification dans les dernières 24h</div>';
      return;
    }

    notifList.innerHTML = notifications.map(n => `
      <div class="cvt-notif-item">
        <div class="cvt-notif-icon"><i class="fa-solid ${iconForType(n.icon)}"></i></div>
        <div class="cvt-notif-content">
          <strong>${escapeHtml(n.titre)}</strong>
          <p>${escapeHtml(n.message)}</p>
          <span class="cvt-notif-date">${escapeHtml(n.date_display)}</span>
        </div>
      </div>
    `).join('');
  }

  async function fetchNotifications(){
    try {
      const res = await fetch('/api/admin_notifications');
      const data = await res.json();
      if (!data.success) return;
      updateBadge(data.count);
      renderNotifications(data.notifications);
    } catch (err){
      notifList.innerHTML = '<div class="cvt-notif-empty">Erreur de chargement</div>';
    }
  }

  notifBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isOpen = !isOpen;
    notifDropdown.classList.toggle('cvt-visible', isOpen);
    if (isOpen){
      fetchNotifications();
    }
  });

  document.addEventListener('click', (e) => {
    if (isOpen && !notifDropdown.contains(e.target) && e.target !== notifBtn){
      isOpen = false;
      notifDropdown.classList.remove('cvt-visible');
    }
  });

});
