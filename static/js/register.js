// ==========================================================
// Convertly - register.js
// Logique spécifique à la page d'inscription
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  const registerForm = document.querySelector('.register-form');
  if (!registerForm) return;

  const nameInput = registerForm.querySelector('input[type="text"]');
  const emailInput = registerForm.querySelector('input[type="email"]');
  const passwordInput = registerForm.querySelector('input[name="password"]');
  const confirmInput = registerForm.querySelector('input[name="confirm-password"]');
  const termsCheckbox = registerForm.querySelector('input[type="checkbox"]');
  const errorBox = registerForm.querySelector('.form-error');
  const submitBtn = registerForm.querySelector('button[type="submit"]');

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
  [nameInput, emailInput, passwordInput, confirmInput].forEach((input) => {
    if (input) input.addEventListener('input', clearError);
  });
  if (termsCheckbox) termsCheckbox.addEventListener('change', clearError);

  /* ---------- Soumission du formulaire ---------- */
  registerForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearError();

    const name = nameInput ? nameInput.value.trim() : '';
    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';
    const confirmPassword = confirmInput ? confirmInput.value.trim() : '';

    if (!name || !email || !password || !confirmPassword) {
      showError('Veuillez remplir tous les champs.');
      return;
    }

    if (name.length < 2) {
      showError('Le nom doit contenir au moins 2 caractères.');
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

    if (password !== confirmPassword) {
      showError('Les mots de passe ne correspondent pas.');
      return;
    }

    if (termsCheckbox && !termsCheckbox.checked) {
      showError('Vous devez accepter les conditions d\'utilisation.');
      return;
    }

    /* ---------- Simulation d'une requête d'inscription ---------- */
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Inscription...';
    }

    setTimeout(() => {
      // À remplacer par un véritable appel API (fetch/axios) vers le backend
      console.log('Inscription tentée avec :', { name, email });
      window.location.href = 'login.html';
    }, 800);
  });

});
