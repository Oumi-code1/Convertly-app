// ==========================================================
// Convertly - profile.js
// Logique spécifique à la page profil utilisateur
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  /* ---------- 1. Changer la photo de profil ---------- */
  const avatarEditBtn = document.querySelector('.avatar-edit');
  const avatarInput = document.querySelector('.avatar-input');
  const avatarIcon = document.querySelector('.avatar-icon');

  if (avatarEditBtn && avatarInput) {
    avatarEditBtn.addEventListener('click', () => avatarInput.click());

    avatarInput.addEventListener('change', () => {
      const file = avatarInput.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        if (avatarIcon) {
          avatarIcon.outerHTML = `<img src="${event.target.result}" class="avatar-icon avatar-img" alt="Photo de profil">`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  /* ---------- 2. Barre de progression du profil ---------- */
  const progressBar = document.querySelector('.profile-progress .progress-bar');
  if (progressBar) {
    const target = parseInt(progressBar.dataset.value, 10) || 0;
    requestAnimationFrame(() => {
      progressBar.style.width = target + '%';
      progressBar.textContent = target + '%';
      progressBar.setAttribute('aria-valuenow', target);
    });
  }

  /* ---------- 3. Enregistrer les modifications du profil ---------- */
  const profileForm = document.querySelector('.profile-form');
  const editBtn = document.querySelector('.btn-edit-profile');

  if (profileForm) {
    profileForm.addEventListener('submit', (event) => {
      event.preventDefault();

      const isEditing = editBtn ? editBtn.classList.contains('btn-editing') : true;
      if (!isEditing) return;

      const emailField = profileForm.querySelector('input[type="email"]');
      if (emailField && emailField.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailField.value.trim())) {
        alert('Adresse e-mail invalide.');
        return;
      }

      // À remplacer par un véritable appel API (fetch/axios) vers le backend
      console.log('Profil enregistré :', new FormData(profileForm));

      if (editBtn) {
        const fields = document.querySelectorAll('.profile-editable');
        fields.forEach((field) => field.setAttribute('disabled', 'true'));
        editBtn.classList.remove('btn-editing');
      }

      const savedMsg = document.querySelector('.profile-saved-msg');
      if (savedMsg) {
        savedMsg.classList.add('visible');
        setTimeout(() => savedMsg.classList.remove('visible'), 2500);
      }
    });
  }

  /* ---------- 4. Suppression du compte ---------- */
  const deleteBtn = document.querySelector('.btn-delete-account');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => {
      const confirmDelete = confirm('Voulez-vous vraiment supprimer votre compte ? Cette action est irréversible.');
      if (confirmDelete) {
        // À remplacer par un véritable appel API de suppression
        console.log('Suppression du compte demandée.');
        window.location.href = 'login.html';
      }
    });
  }

  const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {

    logoutBtn.addEventListener("click", function () {

        const modal = new bootstrap.Modal(
            document.getElementById("logoutModal")
        );

        modal.show();

    });

}

});
