// ==========================================================
// Convertly - register.js
// Validation du formulaire d'inscription
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {

    const registerForm = document.querySelector(".register-form");
    if (!registerForm) return;

    const nameInput = registerForm.querySelector('input[name="nom"]');
    const emailInput = registerForm.querySelector('input[name="email"]');
    const passwordInput = registerForm.querySelector('input[name="password"]');
    const confirmInput = registerForm.querySelector('input[name="confirm_password"]');

    registerForm.addEventListener("submit", function(event) {

        const nom = nameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        const confirmPassword = confirmInput.value.trim();

        // Vérifier les champs vides
        if (!nom || !email || !password || !confirmPassword) {
            alert("Veuillez remplir tous les champs.");
            event.preventDefault();
            return;
        }

        // Vérifier l'email
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!regex.test(email)) {
            alert("Adresse e-mail invalide.");
            event.preventDefault();
            return;
        }

        // Vérifier le mot de passe
        if (password.length < 6) {
            alert("Le mot de passe doit contenir au moins 6 caractères.");
            event.preventDefault();
            return;
        }

        // Vérifier la confirmation
        if (password !== confirmPassword) {
            alert("Les mots de passe ne correspondent pas.");
            event.preventDefault();
            return;
        }

        // Si tout est correct, Flask reçoit le POST
        console.log("Formulaire valide, envoi vers Flask...");
    });

});

