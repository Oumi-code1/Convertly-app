document.addEventListener('DOMContentLoaded', () => {

    /* =========================================================
       SIDEBAR : mobile open / close
       ========================================================= */

    const sidebar = document.getElementById('cvtSidebar');
    const overlay = document.getElementById('cvtOverlay');
    const burger = document.getElementById('cvtBurger');
    const closeBtn = document.getElementById('cvtSidebarClose');

    function openSidebar() {
        sidebar?.classList.add('cvt-open');
        overlay?.classList.add('cvt-visible');
    }

    function closeSidebar() {
        sidebar?.classList.remove('cvt-open');
        overlay?.classList.remove('cvt-visible');
    }

    burger?.addEventListener('click', openSidebar);
    closeBtn?.addEventListener('click', closeSidebar);
    overlay?.addEventListener('click', closeSidebar);


    /* =========================================================
       NAVIGATION
       ========================================================= */

    document.querySelectorAll('.cvt-nav-link').forEach(link => {

        link.addEventListener('click', () => {

            document
                .querySelectorAll('.cvt-nav-link')
                .forEach(item => item.classList.remove('active'));

            link.classList.add('active');

            closeSidebar();
        });

    });


    /* =========================================================
       FILTRE : ACTIF / INACTIF
       =========================================================
       
       Le filtrage est maintenant fait par Flask/MySQL.
       JavaScript sert seulement à envoyer le filtre au backend.
       ========================================================= */

    const statusFilter = document.getElementById('cvtStatusFilter');

    if (statusFilter) {

        statusFilter.addEventListener('change', () => {

            const statut = statusFilter.value;

            const url = new URL(window.location.href);

            // Revenir à la page 1 après changement de filtre
            url.searchParams.delete('page');

            if (statut) {
                url.searchParams.set('statut', statut);
            } else {
                url.searchParams.delete('statut');
            }

            window.location.href = url.toString();
        });

    }


    /* =========================================================
       BOUTON EXPORTER
       =========================================================
       
       Pour l'instant aucune logique ici.
       Il sera connecté plus tard à une route Flask
       d'export CSV/Excel.
       ========================================================= */

    const exportBtn = document.getElementById('cvtExportBtn');

    if (exportBtn) {

        exportBtn.addEventListener('click', () => {

            const url = new URL('/users_admin/export', window.location.origin);

            const statut = statusFilter?.value || '';

            if (statut) {
                url.searchParams.set('statut', statut);
            }

            // Route Flask à créer plus tard
            window.location.href = url.toString();

        });

    }


    /* =========================================================
       ACTIONS : MODIFIER / SUPPRIMER
       =========================================================
       
       Les boutons existent déjà dans le tableau.
       Pour l'instant on récupère seulement l'action.
       
       La modification réelle dans MySQL sera ajoutée
       quand on créera les routes Flask correspondantes.
       ========================================================= */

    document.querySelectorAll('.cvt-row-actions button').forEach(button => {

        button.addEventListener('click', () => {

            const action = button.dataset.action;
            const userId = button.dataset.id;

            if (!action || !userId) {
                return;
            }

            if (action === 'edit') {

                const modal = document.getElementById('cvtUserModalOverlay');

                const nameInput = document.getElementById('cvtUserName');
                const emailInput = document.getElementById('cvtUserEmail');
                const statusInput = document.getElementById('cvtUserStatus');

                const modalTitle = document.getElementById('cvtUserModalTitle');
                const modalSubmit = document.getElementById('cvtUserModalSubmit');
                const pwdField = document.getElementById('cvtUserPwdField');

                // Remplir le formulaire avec les données de l'utilisateur
                nameInput.value = button.dataset.name || '';
                emailInput.value = button.dataset.email || '';
                statusInput.value = button.dataset.status || 'actif';

                // Mode modification
                modalTitle.textContent = 'Modifier l’utilisateur';

                modalSubmit.innerHTML =
                    '<i class="fa-solid fa-check"></i> Enregistrer les modifications';

                // Pas besoin de mot de passe pour modifier
                if (pwdField) {
                    pwdField.style.display = 'none';
                }

                // Stocker l'ID pour le submit
                document.getElementById('cvtUserForm').dataset.editId = userId;

                // Ouvrir le modal
                modal.classList.add('cvt-visible');
            }

            if (action === 'delete') {
                const userId = button.dataset.id;
                const userName = button.dataset.name;

                const confirmation = confirm(
                    `Voulez-vous vraiment supprimer ${userName} ?`
                );

                if (!confirmation) {
                    return;
                }

                window.location.href = `/users_admin/delete/${userId}`;
            }

        });

    });

    /* =========================================================
    MODAL : AJOUTER UN UTILISATEUR
    ========================================================= */
    const addUserBtn = document.getElementById('cvtAddUserBtn');
    const userModal = document.getElementById('cvtUserModalOverlay');
    const userModalClose = document.getElementById('cvtUserModalClose');
    const userModalCancel = document.getElementById('cvtUserModalCancel');
    /* Ouvrir le modal */
    addUserBtn?.addEventListener('click', () => {

        userModal?.classList.add('cvt-visible');

    });
    /* Fermer avec X */
    userModalClose?.addEventListener('click', () => {

        userModal?.classList.remove('cvt-visible');

    });
    /* Fermer avec Annuler */
    userModalCancel?.addEventListener('click', () => {

        userModal?.classList.remove('cvt-visible');

    });
    /* Fermer en cliquant sur l'arrière-plan */
    userModal?.addEventListener('click', (event) => {

        if (event.target === userModal) {
            userModal.classList.remove('cvt-visible');
        }

    });

});