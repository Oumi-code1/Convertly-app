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

    clearError();

    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
        showError("Veuillez remplir tous les champs.");
        event.preventDefault();
        return;
    }

    if (!isValidEmail(email)) {
        showError("Adresse e-mail invalide.");
        event.preventDefault();
        return;
    }

    if (password.length < 6) {
        showError("Le mot de passe doit contenir au moins 6 caractères.");
        event.preventDefault();
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Connexion...";
    }

    // Ma tdir ta event.preventDefault() hna
    // Khalli Flask yst9bel POST
});

});