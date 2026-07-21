document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const label = btn.textContent.trim();
    console.log('Bouton cliqué :', label);
  });
});
