// ==========================================================
// Convertly - login.js
// Logique spécifique à la page de connexion
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  const loginForm = document.querySelector('.login-form');
  if (!loginForm) return;

  const emailInput = loginForm.querySelector('input[type="email"]');
  const passwordInput = loginForm.querySelector('input[type="password"]');
  const errorBox = loginForm.querySelector('.form-error');
  const submitBtn = loginForm.querySelector('button[type="submit"]');

  /* ---------- Validation d'un email simple ---------- */
  const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  /* ---------- Afficher un message d'erreur ---------- */
  const showError = (message) => {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.classList.add('visible');
  };

  /* ---------- Masquer le message d'erreur ---------- */
  const clearError = () => {
    if (!errorBox) return;
    errorBox.textContent = '';
    errorBox.classList.remove('visible');
  };

  /* ---------- Effacer l'erreur dès que l'utilisateur retape ---------- */
  [emailInput, passwordInput].forEach((input) => {
    if (input) input.addEventListener('input', clearError);
  });

  /* ---------- Soumission du formulaire ---------- */
  loginForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearError();

    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';

    if (!email || !password) {
      showError('Veuillez remplir tous les champs.');
      return;
    }

    if (!isValidEmail(email)) {
      showError('Adresse e-mail invalide.');
      return;
    }

    if (password.length < 6) {
      showError('Le mot de passe doit contenir au moins 6 caractères.');
      return;
    }

    /* ---------- Simulation d'une requête de connexion ---------- */
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Connexion...';
    }

    setTimeout(() => {
      // À remplacer par un véritable appel API (fetch/axios) vers le backend
      console.log('Connexion tentée avec :', { email });
      window.location.href = 'dashboard.html';
    }, 800);
  });

});