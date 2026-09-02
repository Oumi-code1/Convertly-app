// ==========================================================
// Convertly - dashboard_user.js
// Logique spécifique au tableau de bord utilisateur
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {

  /* ---------- 1. Zone de dépôt de fichiers (drag & drop) ---------- */
  const dropZone = document.querySelector('.upload-dropzone');
  const fileInput = document.querySelector('.upload-input');
  const convertBtn = document.querySelector('.btn-convert');
  const fileNameLabel = document.querySelector('.upload-filename');
  const formatSelect = document.getElementById("format_cible");
  const allowedFormats = {
      PDF: ["DOCX"],
      DOCX: ["PDF"],
      XLSX: ["PDF"],
      PPTX: ["PDF"],
      TXT: ["PDF"],
      PNG: ["JPG", "JPEG"],
      JPG: ["PNG", "JPEG"],
      JPEG: ["PNG", "JPG"],
  };
  
  Array.from(formatSelect.options).forEach(option => {
    if (option.value !== "") {
        option.hidden = true;
    }
  });

  if (dropZone && fileInput) {

    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add('dragging');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove('dragging');
      });
    });

    dropZone.addEventListener('drop', (event) => {
      const files = event.dataTransfer.files;
      if (files.length) {
        fileInput.files = files;
        handleSelectedFile(files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) {
        handleSelectedFile(fileInput.files[0]);
      }
    });
  }

  function updateFormats(extension) {

    Array.from(formatSelect.options).forEach(option => {

        if (option.value === "") {
            option.hidden = false;
            return;
        }

        if (allowedFormats[extension]) {
            option.hidden = !allowedFormats[extension].includes(option.text);
        } else {
            option.hidden = true;
        }

    });

    formatSelect.value = "";
  }

  function handleSelectedFile(file) {
    if (fileNameLabel) fileNameLabel.textContent = file.name;
    
    const extension = file.name.split(".").pop().toUpperCase();
    
    updateFormats(extension);
    
    if (convertBtn) convertBtn.disabled = false;
  }


  /* ---------- 3. Lancer la conversion (simulation) ---------- */
 /* ---------- 3. Envoyer le formulaire à Flask ---------- */

const uploadForm = document.querySelector(".upload-form");

if (convertBtn && uploadForm) {

    convertBtn.addEventListener("click", () => {

        if (!fileInput.files.length) {
            alert("Veuillez sélectionner un fichier.");
            return;
        }

        uploadForm.submit();

    });

}

  /* ---------- 4. Ajouter une entrée dans "Conversions récentes" ---------- */
  function addToRecentConversions(fileName, format) {
    const list = document.querySelector('.recent-conversions-list');
    if (!list) return;

    const item = document.createElement('li');
    item.classList.add('recent-conversion-item');
    item.innerHTML = `
      <span class="file-name">${fileName}</span>
      <span class="file-format">${format}</span>
      <span class="file-date">${new Date().toLocaleDateString('fr-FR')}</span>
    `;
    list.prepend(item);
  }

  /* ---------- 5. Compteurs de statistiques (animation) ---------- */
  const statNumbers = document.querySelectorAll('.stat-number');
  statNumbers.forEach((el) => {
    const target = parseInt(el.dataset.value, 10) || 0;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 40));

    const counter = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(counter);
      }
      el.textContent = current;
    }, 25);
  });

});
 