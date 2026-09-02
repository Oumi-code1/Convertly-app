document.addEventListener('DOMContentLoaded', () => {

  /* =========================================================
     SIDEBAR : mobile open/close + active nav state
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
    link.addEventListener('click', () => {
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

  // Affiche automatiquement le message renvoyé par Flask après une redirection
  // (ex: "Profil mis à jour avec succès.", "Mot de passe modifié avec succès.")
  if (window.CVT_PROFILE_MESSAGE){
    showToast(window.CVT_PROFILE_MESSAGE);
  }

  /* =========================================================
     TABS
     ========================================================= */
  const tabs   = document.querySelectorAll('.cvt-tab');
  const panels = document.querySelectorAll('.cvt-tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.querySelector(`.cvt-tab-panel[data-panel="${tab.dataset.tab}"]`).classList.add('active');
    });
  });

  /* =========================================================
     AVATAR : upload + prévisualisation instantanée
     La sauvegarde réelle se fait via la soumission du formulaire
     cvtInfoForm (POST vers /modifier_profil), qui enregistre le
     fichier sur le disque et met à jour la colonne "photo" en base.
     ========================================================= */
  const avatarInput   = document.getElementById('cvtAvatarInput');
  const avatarEditBtn = document.getElementById('cvtAvatarEditBtn');
  const avatarPreview = document.getElementById('cvtProfileAvatarPreview');

  avatarEditBtn && avatarEditBtn.addEventListener('click', () => avatarInput.click());

  avatarInput && avatarInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml'];
    if (!allowedTypes.includes(file.type)){
      showToast('Seules les images JPG, JPEG, PNG et SVG sont acceptées');
      avatarInput.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      avatarPreview.src = ev.target.result;
    };
    reader.readAsDataURL(file);

    showToast('Photo sélectionnée — cliquez sur "Enregistrer les modifications" pour la sauvegarder');
  });

  /* =========================================================
     MOT DE PASSE : afficher / masquer
     ========================================================= */
  document.querySelectorAll('.cvt-pwd-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      const icon = btn.querySelector('i');
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      icon.classList.toggle('fa-eye');
      icon.classList.toggle('fa-eye-slash');
    });
  });

  /* =========================================================
     MOT DE PASSE : indicateur de force
     ========================================================= */
  const newPwdInput = document.getElementById('cvtNewPwd');
  const strengthFill = document.getElementById('cvtPwdStrengthFill');
  const strengthLabel = document.getElementById('cvtPwdStrengthLabel');

  function scorePassword(value){
    let score = 0;
    if (value.length >= 8) score++;
    if (/[A-Z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^A-Za-z0-9]/.test(value)) score++;
    return score;
  }

  newPwdInput && newPwdInput.addEventListener('input', () => {
    const value = newPwdInput.value;
    const score = value ? scorePassword(value) : 0;
    const levels = [
      { width: '0%',   color: 'var(--cvt-border)', label: 'Sécurité du mot de passe' },
      { width: '25%',  color: 'var(--cvt-red)',     label: 'Faible' },
      { width: '50%',  color: 'var(--cvt-orange)',  label: 'Moyen' },
      { width: '75%',  color: 'var(--cvt-blue)',    label: 'Bon' },
      { width: '100%', color: 'var(--cvt-green)',   label: 'Excellent' }
    ];
    const level = levels[score];
    strengthFill.style.width = level.width;
    strengthFill.style.background = level.color;
    strengthLabel.textContent = level.label;
  });

  /* =========================================================
     FORMULAIRE INFORMATIONS : validation avant envoi réel au serveur
     (POST natif vers /modifier_profil défini dans le <form>)
     ========================================================= */
  const infoForm = document.getElementById('cvtInfoForm');
  infoForm && infoForm.addEventListener('submit', (e) => {
    const email = document.getElementById('cvtEmail').value.trim();
    const lastName = document.getElementById('cvtLastName').value.trim();

    if (!email || !lastName){
      e.preventDefault();
      showToast('Veuillez renseigner au moins le nom et l\'email');
    }
    // Sinon : laisser le formulaire se soumettre normalement vers Flask.
  });

  /* =========================================================
     FORMULAIRE SECURITE : validation avant envoi réel au serveur
     (POST natif vers /changer_mot_de_passe défini dans le <form>)
     ========================================================= */
  const securityForm = document.getElementById('cvtSecurityForm');
  securityForm && securityForm.addEventListener('submit', (e) => {
    const newPwd = document.getElementById('cvtNewPwd').value;
    const confirmPwd = document.getElementById('cvtConfirmPwd').value;

    if (newPwd && newPwd !== confirmPwd){
      e.preventDefault();
      showToast('Les mots de passe ne correspondent pas');
      return;
    }
    // Sinon : laisser le formulaire se soumettre normalement vers Flask.
    // Flask redirige ensuite avec un message de succès ou d'erreur réel.
  });

  /* =========================================================
     NOTIFICATIONS / PREFERENCES
     Aucune colonne en base pour stocker ces réglages : action non
     connectée, on informe clairement l'utilisateur au lieu de
     simuler une sauvegarde qui n'existe pas réellement.
     ========================================================= */
  const saveNotifsBtn = document.getElementById('cvtSaveNotifs');
  saveNotifsBtn && saveNotifsBtn.addEventListener('click', () => {
    showToast('Fonctionnalité non disponible pour le moment');
  });

  const savePrefsBtn = document.getElementById('cvtSavePrefs');
  savePrefsBtn && savePrefsBtn.addEventListener('click', () => {
    showToast('Fonctionnalité non disponible pour le moment');
  });

});
