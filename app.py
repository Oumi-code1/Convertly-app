from flask import Flask, flash, render_template, request, redirect, url_for, session, send_file, abort, jsonify, Response 
from connexion import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from werkzeug.utils import secure_filename
from conversions import perform_conversion
from datetime import datetime, timedelta
import re
import csv
import io 

app = Flask(__name__)
app.secret_key = "Convertly_secret_key"

PROFILE_UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["PROFILE_UPLOAD_FOLDER"] = PROFILE_UPLOAD_FOLDER
os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)


def _ensure_profile_photo_column(conn, cursor):
    """Ajoute la colonne photo à la table utilisateur si elle n'existe pas encore."""
    cursor.execute("SHOW COLUMNS FROM utilisateur LIKE 'photo'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE utilisateur ADD COLUMN photo VARCHAR(255) NULL")
        conn.commit()


def _get_downloads_column_exists(cursor):
    """Vérifie si la colonne telechargements existe dans la table conversion."""
    cursor.execute("SHOW COLUMNS FROM conversion LIKE 'telechargements'")
    return cursor.fetchone() is not None

def _ensure_downloads_column(conn, cursor):
    """Ajoute la colonne telechargements à la table conversion si elle n'existe pas encore."""
    cursor.execute("SHOW COLUMNS FROM conversion LIKE 'telechargements'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE conversion ADD COLUMN telechargements INT DEFAULT 0")
        conn.commit()



def _ensure_format_conversion_table(conn, cursor):
    """Crée la table format_conversion si elle n'existe pas."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS format_conversion (
            id INT PRIMARY KEY AUTO_INCREMENT,
            id_format_origin INT NOT NULL,
            id_format_cible INT NOT NULL,
            est_actif TINYINT(1) DEFAULT 1,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_format_origin) REFERENCES format(id),
            FOREIGN KEY (id_format_cible) REFERENCES format(id),
            UNIQUE KEY uk_format_pair (id_format_origin, id_format_cible)
        )
    """)
    conn.commit()


def _seed_default_conversions(conn, cursor):
    """Insère les conversions par défaut si elles n'existent pas."""
    conversions_par_defaut = [
        ('DOCX', 'PDF'),
        ('PDF', 'DOCX'),
        ('XLSX', 'PDF'),
        ('PPTX', 'PDF'),
        ('TXT', 'PDF'),
        ('PNG', 'JPG'),
        ('JPG', 'PNG'),
        ('PNG', 'JPEG'),
        ('JPEG', 'PNG'),
        ('JPEG', 'JPG'),
        ('JPG', 'JPEG')
    ]
    
    for format_origin, format_cible in conversions_par_defaut:
        # Récupérer les IDs des formats
        cursor.execute("SELECT id FROM format WHERE nom = %s", (format_origin,))
        origin_result = cursor.fetchone()
        cursor.execute("SELECT id FROM format WHERE nom = %s", (format_cible,))
        cible_result = cursor.fetchone()
        
        if origin_result and cible_result:
            id_format_origin = origin_result['id']
            id_format_cible = cible_result['id']
            
            # Vérifier si la paire existe déjà
            cursor.execute("""
                SELECT id FROM format_conversion
                WHERE id_format_origin = %s AND id_format_cible = %s
            """, (id_format_origin, id_format_cible))
            
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO format_conversion (id_format_origin, id_format_cible, est_actif)
                    VALUES (%s, %s, 1)
                """, (id_format_origin, id_format_cible))
    
    conn.commit()


def _format_status_label(statut):
    """Retourne un libellé lisible pour le statut de conversion."""
    if not statut:
        return "Inconnu"

    statut = statut.strip().lower()
    return {
        "success": "Terminé",
        "terminee": "Terminé",
        "termine": "Terminé",
        "error": "Échec",
        "echec": "Échec",
    }.get(statut, statut.capitalize())


def _format_history_status_label(statut):
    """Retourne le libellé affiché dans la page history."""
    if not statut:
        return "Échec"

    statut = statut.strip().lower()
    return {
        "success": "Réussi",
        "terminee": "Réussi",
        "termine": "Réussi",
        "error": "Échec",
        "echec": "Échec",
        "failed": "Échec",
    }.get(statut, "Échec")


def _format_history_status_filter(statut):
    """Retourne la valeur data-status pour le filtrage de l'historique."""
    if not statut:
        return "failed"

    statut = statut.strip().lower()
    if statut in {"success", "terminee", "termine"}:
        return "success"
    if statut in {"error", "echec", "failed"}:
        return "failed"
    return "failed"


def _get_file_icon_class(format_name):
    """Choisit l'icône Bootstrap Icons en fonction du type de fichier."""
    if not format_name:
        return "bi bi-file-earmark-fill file-icon"

    normalized = format_name.strip().lower()
    if normalized in {"pdf"}:
        return "bi bi-filetype-pdf file-icon file-icon-pdf"
    if normalized in {"png", "jpg", "jpeg", "gif", "bmp", "svg"}:
        return "bi bi-file-earmark-image-fill file-icon file-icon-image"
    if normalized in {"doc", "docx", "txt", "odt", "rtf"}:
        return "bi bi-filetype-doc file-icon file-icon-doc"
    if normalized in {"ppt", "pptx"}:
        return "bi bi-filetype-ppt file-icon file-icon-ppt"
    if normalized in {"xls", "xlsx", "csv"}:
        return "bi bi-filetype-xls file-icon file-icon-xls"

    return "bi bi-file-earmark-fill file-icon"

def _get_file_icon_color(format_name):
    """Retourne les couleurs de l'icône selon le type."""

    if not format_name:
        return "text-slate-600 bg-slate-100"

    normalized = format_name.strip().lower()

    if normalized == "pdf":
        return "text-red-600 bg-red-100"

    if normalized in {"doc", "docx", "txt", "odt", "rtf"}:
        return "text-blue-600 bg-blue-100"

    if normalized in {"xls", "xlsx", "csv"}:
        return "text-green-600 bg-green-100"

    if normalized in {"ppt", "pptx"}:
        return "text-orange-600 bg-orange-100"

    if normalized in {"png", "jpg", "jpeg", "gif", "bmp", "svg"}:
        return "text-purple-600 bg-purple-100"

    return "text-slate-600 bg-slate-100"


def _get_history_format_chip_class(format_name):
    """Retourne la classe CSS du chip de format, en réutilisant les classes déjà définies dans history_admin.css."""
    if not format_name:
        return "cvt-fmt-default"
    normalized = format_name.strip().lower()
    known = {"docx", "pdf", "pptx", "xlsx", "png", "jpg", "jpeg", "txt"}
    return f"cvt-fmt-{normalized}" if normalized in known else "cvt-fmt-default"


def _get_history_file_fa_icon(format_name):
    """Retourne (classe FontAwesome, classe couleur cvt-file-xxx) pour l'icône de fichier dans l'historique admin."""
    if not format_name:
        return "fa-regular fa-file", "cvt-file-default"
    normalized = format_name.strip().lower()
    if normalized == "docx" or normalized == "doc":
        return "fa-regular fa-file-word", "cvt-file-docx"
    if normalized == "pdf":
        return "fa-regular fa-file-pdf", "cvt-file-pdf"
    if normalized == "pptx" or normalized == "ppt":
        return "fa-regular fa-file-powerpoint", "cvt-file-pptx"
    if normalized == "xlsx" or normalized == "xls":
        return "fa-regular fa-file-excel", "cvt-file-xlsx"
    if normalized in {"png", "jpg", "jpeg"}:
        return "fa-regular fa-file-image", "cvt-file-img"
    return "fa-regular fa-file", "cvt-file-default"

def _get_admin_notifications(cursor, hours=24, limit=20):
    """
    Construit la liste des notifications ADMIN à partir des données déjà
    existantes (conversion + utilisateur), sur les dernières `hours` heures.
    Aucune table supplémentaire : tout est recalculé à la demande.
    """
    since = datetime.now() - timedelta(hours=hours)

    notifications = []

    # 1. Conversions terminées avec succès
    cursor.execute("""
        SELECT
            c.id AS ref_id,
            u.nom AS user_name,
            f.nom_origin AS file_name,
            fc.nom AS format_cible,
            c.date_conversion
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        JOIN utilisateur u ON f.id_utilisateur = u.id
        LEFT JOIN format fc ON c.id_format_cible = fc.id
        WHERE c.statut = 'terminee'
          AND c.date_conversion >= %s
          AND c.est_supprime = 0
          AND f.est_supprime = 0
        ORDER BY c.date_conversion DESC
    """, (since,))
    for row in cursor.fetchall():
        notifications.append({
            "type": "conversion_terminee",
            "icon": "fa-circle-check",
            "titre": "Conversion terminée",
            "message": f"{row['user_name']} a converti {row['file_name']} en {row['format_cible'] or '?'}.",
            "date": row["date_conversion"],
        })

    # 2. Échecs de conversion
    cursor.execute("""
        SELECT
            c.id AS ref_id,
            u.nom AS user_name,
            f.nom_origin AS file_name,
            c.date_conversion
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        JOIN utilisateur u ON f.id_utilisateur = u.id
        WHERE c.statut = 'echec'
          AND c.date_conversion >= %s
          AND c.est_supprime = 0
          AND f.est_supprime = 0
        ORDER BY c.date_conversion DESC
    """, (since,))
    for row in cursor.fetchall():
        notifications.append({
            "type": "conversion_echec",
            "icon": "fa-triangle-exclamation",
            "titre": "Échec de conversion",
            "message": f"La conversion de {row['file_name']} par {row['user_name']} a échoué.",
            "date": row["date_conversion"],
        })

    # 3. Nouveaux utilisateurs inscrits
    cursor.execute("""
        SELECT nom, email, date_creation
        FROM utilisateur
        WHERE type_utilisateur = 'utilisateur'
          AND date_creation >= %s
        ORDER BY date_creation DESC
    """, (since,))
    for row in cursor.fetchall():
        notifications.append({
            "type": "nouvel_utilisateur",
            "icon": "fa-user-plus",
            "titre": "Nouvel utilisateur",
            "message": f"{row['nom']} ({row['email']}) vient de créer un compte.",
            "date": row["date_creation"],
        })

    # Tri global : plus récent en premier
    notifications.sort(key=lambda n: n["date"], reverse=True)

    total_count = len(notifications)

    # Formatage de la date pour l'affichage, après le tri/comptage
    for n in notifications[:limit]:
        n["date_display"] = n["date"].strftime("%d/%m/%Y %H:%M") if n["date"] else ""
        del n["date"]

    return notifications[:limit], total_count


def _get_dashboard_counts(cursor, user_id):
    """Récupère les statistiques générales du tableau de bord pour l'utilisateur."""
    sql_files_converted = """
        SELECT COUNT(*) AS total
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE f.id_utilisateur = %s
          AND c.chemin_fichier_converti IS NOT NULL
          AND (c.statut IS NULL OR c.statut IN ('terminee', 'success', 'termine'))
          AND f.est_supprime = 0
          AND c.est_supprime = 0
    """
    cursor.execute(sql_files_converted, (user_id,))
    files_converted = cursor.fetchone()["total"] or 0

    total_downloads = 0
    if _get_downloads_column_exists(cursor):
        sql_downloads = """
            SELECT COALESCE(SUM(telechargements), 0) AS total
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            WHERE f.id_utilisateur = %s
              AND f.est_supprime = 0
              AND c.est_supprime = 0
        """
        cursor.execute(sql_downloads, (user_id,))
        total_downloads = cursor.fetchone()["total"] or 0
    else:
        # La colonne telechargements n'existe pas encore.
        total_downloads = 0 

    sql_today = """
        SELECT COUNT(*) AS total
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE f.id_utilisateur = %s
          AND DATE(c.date_conversion) = CURDATE()
          AND c.chemin_fichier_converti IS NOT NULL
          AND f.est_supprime = 0
          AND c.est_supprime = 0
    """
    cursor.execute(sql_today, (user_id,))
    conversions_today = cursor.fetchone()["total"] or 0

    return {
        "files_converted": files_converted,
        "total_downloads": total_downloads,
        "conversions_today": conversions_today,
    }


def _get_conversion_type_stats(cursor, user_id):
    """Récupère les types de conversions et calcule leur part de marché pour le donut."""
    sql = """
        SELECT
            CONCAT(fo.nom, ' → ', fc.nom) AS type_label,
            COUNT(*) AS total
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        JOIN format fo ON f.id_format_origin = fo.id
        JOIN format fc ON c.id_format_cible = fc.id
        WHERE f.id_utilisateur = %s
          AND c.chemin_fichier_converti IS NOT NULL
          AND f.est_supprime = 0
          AND c.est_supprime = 0
        GROUP BY type_label
        ORDER BY total DESC
        LIMIT 5
    """
    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()

    if not rows:
        return []

    total_count = sum(row["total"] for row in rows)
    colors = ["#4F7DF3", "#C7B9F5", "#F2C94C", "#6AD5F5", "#A3E635"]
    offset = 25
    stats = []
    for index, row in enumerate(rows):
        percentage = round(row["total"] / total_count * 100) if total_count else 0
        stats.append({
            "label": row["type_label"],
            "percentage": percentage,
            "dasharray": f"{percentage} {100 - percentage}",
            "dashoffset": offset,
            "color": colors[index % len(colors)],
        })
        offset += percentage

    return stats


def _get_recent_conversions(cursor, user_id):
    """Récupère les 5 dernières conversions de l'utilisateur."""
    sql = """
        SELECT
            c.id AS id_conversion,
            f.nom_origin AS file_name,
            DATE_FORMAT(c.date_conversion, '%d/%m/%Y %H:%i') AS date_conversion,
            c.statut,
            fc.nom AS target_format,
            c.chemin_fichier_converti
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        LEFT JOIN format fc ON c.id_format_cible = fc.id
        WHERE f.id_utilisateur = %s
          AND f.est_supprime = 0
          AND c.est_supprime = 0
        ORDER BY c.date_conversion DESC
        LIMIT 5
    """
    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()
    conversions = []

    for row in rows:
        # Si la base contient NULL pour le statut, on infère un statut simple
        # à partir de la présence du chemin de fichier converti :
        # - chemin présent -> terminé
        # - chemin absent  -> en cours (pending)
        statut_value = row["statut"]
        if not statut_value:
            statut_value = "terminee" if row.get("chemin_fichier_converti") else "encours"

        conversions.append({
            "id_conversion": row["id_conversion"],
            "file_name": row["file_name"],
            "date_conversion": row["date_conversion"],
            " _format": row["target_format"] or "Inconnu",
            "status_filter": _format_history_status_filter(statut_value),
            "status_label": _format_history_status_label(statut_value),
            "file_icon_class": _get_file_icon_class(row["target_format"] or row["file_name"]),
            "download_url": url_for("download_conversion", id_conversion=row["id_conversion"]),
            "has_output": bool(row["chemin_fichier_converti"]),
        })

    return conversions

def format_size(size):
    if not size:
        return "0 KB"

    size = float(size)

    units = ["KB", "MB", "GB", "TB"]

    i = 0

    while size >= 1024 and i < len(units)-1:
        size /= 1024
        i += 1

    return f"{size:.2f} {units[i]}"

def format_date(date):

    if not date:
        return "", ""

    return (
        date.strftime("%d/%m/%Y"),
        date.strftime("%H:%M")
    )

# ===== PAGE ACCUEIL =====
@app.route("/")
def accueil():
    return render_template("acceuil.html")

@app.route("/register",methods=["GET","POST"])
def register():

    print("Méthode :", request.method)
    print("Formulaire :", request.form)

    if request.method == "POST":
        
        nom = request.form.get("nom")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        #Verification de mot de passe 
        if password != confirm_password:
            return "le mot de passe ne correspondent pas."

        #Verification de la sécurité du mot de passe
        regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#_.+-])[A-Za-z\d@$!%*?&#_.+-]{8,}$"

        if not re.match(regex, password):
            return "Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial."

        #Connexion a la base 
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        #Verifier si l'email existe deja
        sql = "SELECT * FROM utilisateur WHERE email = %s"
        cursor.execute(sql,(email,))
        utilisateur = cursor.fetchone()

        if utilisateur:
            cursor.close()
            conn.close()
            return "Cet email existe deja."
        
        #Ajouter le nouvel utilisateur 
        password_hash = generate_password_hash(password)
        
        sql ="""
        INSERT INTO utilisateur (nom, email, mot_de_passe)
        VALUES (%s,%s,%s)
        """

        cursor.execute(sql, (nom, email, password_hash))
        conn.commit()

        cursor.close()
        conn.close()

        print("Utilisateur ajouté avec succès !")

        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login",methods=["GET", "POST"])
def login():

    print("Methode :", request.method)
    if request.method == "POST":
        
        email = request.form.get("email")
        password = request.form.get("password")
        
        #connexion a la base
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        #Recherche de l'utilisateur
        sql = "SELECT * FROM utilisateur WHERE email = %s"
        cursor.execute(sql, (email,))
        utilisateur = cursor.fetchone()

        #Fermer la connexion 
        cursor.close()
        conn.close()

        #Verification
        if utilisateur and check_password_hash(utilisateur["mot_de_passe"],password):

            session["id_utilisateur"] = utilisateur["id"]
            session["nom_utilisateur"] = utilisateur["nom"]
            session["type_utilisateur"] = utilisateur["type_utilisateur"]

            if utilisateur["type_utilisateur"] == "admin":
                return redirect(url_for("dashboard_admin"))
            else:
                return redirect(url_for("dashboard_user"))
        
        else:
            return "Email ou mot de passe incorrect."

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    flash("Vous avez été déconnecté avec succès.", "success")

    return redirect(url_for("login"))

@app.route("/mot_de_passe_oublie", methods=["GET", "POST"])
def mot_de_passe_oublie():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, nom FROM utilisateur WHERE email = %s", (email,))
        utilisateur = cursor.fetchone()

        cursor.close()
        conn.close()

        if not utilisateur:
            return render_template(
                "mot_de_passe_oublie.html",
                erreur="Aucun compte n'est associé à cet email."
            )

        # On garde temporairement l'identité de l'utilisateur en session
        # pour l'étape suivante (définir le nouveau mot de passe).
        session["reset_user_id"] = utilisateur["id"]

        return redirect(url_for("reinitialiser_mot_de_passe"))

    return render_template("mot_de_passe_oublie.html", erreur=None)


@app.route("/reinitialiser_mot_de_passe", methods=["GET", "POST"])
def reinitialiser_mot_de_passe():
    if "reset_user_id" not in session:
        return redirect(url_for("mot_de_passe_oublie"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or not confirm_password:
            return render_template(
                "reinitialiser_mot_de_passe.html",
                erreur="Veuillez remplir tous les champs."
            )

        if new_password != confirm_password:
            return render_template(
                "reinitialiser_mot_de_passe.html",
                erreur="Les mots de passe ne correspondent pas."
            )

        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "UPDATE utilisateur SET mot_de_passe = %s WHERE id = %s",
            (hashed_password, session["reset_user_id"])
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Nettoyage : on retire l'état temporaire de reset
        session.pop("reset_user_id", None)

        flash("Votre mot de passe a été réinitialisé avec succès. Vous pouvez vous connecter.", "success")
        return redirect(url_for("login"))

    return render_template("reinitialiser_mot_de_passe.html", erreur=None)

def _is_admin():
    return session.get("id_utilisateur") and session.get("type_utilisateur") == "admin"

def _profile_redirect_endpoint():
    """Renvoie l'endpoint de profil correct selon le type d'utilisateur connecté."""
    return "profile_admin" if session.get("type_utilisateur") == "admin" else "profile"

@app.context_processor
def inject_current_admin():
    """
    Injecte automatiquement les infos de l'admin connecté (nom, photo)
    ET le compteur de notifications (dernières 24h, calculé à la volée
    depuis conversion + utilisateur, sans table supplémentaire) dans
    TOUS les templates admin.
    """
    if session.get("id_utilisateur") and session.get("type_utilisateur") == "admin":
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            _ensure_profile_photo_column(conn, cursor)

            cursor.execute("""
                SELECT id, nom, email, photo
                FROM utilisateur
                WHERE id = %s
                  AND type_utilisateur = 'admin'
            """, (session["id_utilisateur"],))
            current_admin = cursor.fetchone()

            _, notif_count = _get_admin_notifications(cursor)
        finally:
            cursor.close()
            conn.close()

        current_admin_photo_url = None
        if current_admin and current_admin.get("photo"):
            current_admin_photo_url = url_for("static", filename=f"uploads/{current_admin['photo']}")

        return dict(
            current_admin=current_admin,
            current_admin_photo_url=current_admin_photo_url,
            current_admin_notif_count=notif_count,
        )

    return dict(current_admin=None, current_admin_photo_url=None, current_admin_notif_count=0)


@app.route("/dashboard_admin")
def dashboard_admin():

    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Nombre des utilisateurs
    cursor.execute("""
        SELECT COUNT(*) AS total_users
        FROM utilisateur
    """)
    total_users = cursor.fetchone()["total_users"]

    #Nombre total des conversions
    cursor.execute("""
        SELECT COUNT(*) AS total_conversions
        FROM conversion
        WHERE est_supprime = 0
    """)
    total_conversions = cursor.fetchone()["total_conversions"]

    # Nombre des formats actifs
    cursor.execute("""
        SELECT COUNT(*) AS total_formats
        FROM format
        WHERE est_actif = 1
    """)
    total_formats = cursor.fetchone()["total_formats"]

    # Nombre des conversions échouées
    cursor.execute("""
        SELECT COUNT(*) AS total_failed
        FROM conversion
        WHERE statut='echec'
          AND est_supprime = 0
    """)
    total_failed = cursor.fetchone()["total_failed"]

    #tableau de dernières conversions
    cursor.execute("""
SELECT
u.nom AS utilisateur,
f.nom_origin AS fichier,
fo.nom AS format_source,
fc.nom AS format_cible,
c.date_conversion,
c.statut

FROM conversion c

JOIN fichier f
ON c.id_fichier=f.id

JOIN utilisateur u
ON f.id_utilisateur=u.id

LEFT JOIN format fo
ON f.id_format_origin=fo.id

LEFT JOIN format fc
ON c.id_format_cible=fc.id

ORDER BY c.date_conversion DESC

LIMIT 10
""")


    recent_conversions = cursor.fetchall()

    sql_chart = """
    SELECT
        DATE(c.date_conversion) AS jour,
        COUNT(*) AS total
    FROM conversion c
    WHERE c.date_conversion >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
    AND c.est_supprime = 0
    GROUP BY DATE(c.date_conversion)
    ORDER BY jour
    """

    cursor.execute(sql_chart)
    rows = cursor.fetchall()
    chart_dict = {}

    for row in rows:
        chart_dict[row["jour"]] = row["total"]
        labels = []
    values = []

    today = datetime.today()

    for i in range(6, -1, -1):

        day = (today - timedelta(days=i)).date()

        labels.append(day.strftime("%d/%m"))

        values.append(chart_dict.get(day, 0))

    def _get_formats_chart(cursor):
        sql = """
        SELECT
            fc.nom AS format,
            COUNT(*) AS total
        FROM conversion c
        JOIN format fc ON c.id_format_cible = fc.id
        WHERE c.est_supprime = 0
        GROUP BY fc.nom
        ORDER BY total DESC
        """

        cursor.execute(sql)
        rows = cursor.fetchall()

        labels = []
        values = []
        table_data = []

        total = sum(row["total"] for row in rows)

        colors = [
                    "#2563EB",
                    "#38BDF8",
                    "#22C55E",
                    "#F97316",
                    "#A78BFA",
                    "#CBD5E1"
        ]

        for row in rows:
            percentage = round((row["total"] * 100) / total) if total else 0

            labels.append(row["format"])
            values.append(row["total"])

            table_data.append({
                "format" : row["format"],
                "total" : row["total"],
                "percentage" : percentage
            })

        for i, item in enumerate(table_data):
            item["color"] = colors[i % len(colors)]

        return labels, values, table_data

    format_labels, format_values, format_table_data = _get_formats_chart(cursor)

    def _get_recent_users(cursor):
        sql = """
                SELECT
                    nom,
                    email,
                    date_creation,
                    statut
                FROM utilisateur
                WHERE type_utilisateur = 'utilisateur'
                ORDER BY date_creation DESC
                LIMIT 5
            """

        cursor.execute(sql)
        rows = cursor.fetchall()

        return rows

    recent_users = _get_recent_users(cursor)

    cursor.close()
    conn.close()


    return render_template(
        "dashboard_admin.html",
        total_users=total_users,
        total_conversions=total_conversions,
        total_formats=total_formats,
        total_failed=total_failed,
        recent_conversions=recent_conversions,
        chart_labels=labels,
        chart_values=values,
        format_labels=format_labels,
        format_values=format_values,
        format_table_data=format_table_data,
        recent_users=recent_users,
    )

@app.route('/profile_admin')
def profile_admin():
    if not _is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    _ensure_profile_photo_column(conn, cursor)

    cursor.execute("""
        SELECT id, nom, email, statut, date_creation, photo
        FROM utilisateur
        WHERE id = %s
          AND type_utilisateur = 'admin'
    """, (session["id_utilisateur"],))

    admin = cursor.fetchone()

    if not admin:
        cursor.close()
        conn.close()
        return redirect(url_for("login"))

    # Statistique "Conversions" : total plateforme (cohérent avec dashboard_admin)
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM conversion
        WHERE est_supprime = 0
    """)
    total_conversions = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    # Découpage best-effort de "nom" en prénom/nom pour préremplir les 2 champs du formulaire
    # (aucune colonne séparée n'existe en base, donc c'est purement pour l'affichage)
    full_name = admin["nom"] or ""
    parts = full_name.split(" ", 1)
    admin_prenom = parts[0] if parts else ""
    admin_nom = parts[1] if len(parts) > 1 else ""

    profile_image_url = None
    if admin.get("photo"):
        profile_image_url = url_for("static", filename=f"uploads/{admin['photo']}")

    return render_template(
        "profile_admin.html",
        admin=admin,
        admin_prenom=admin_prenom,
        admin_nom=admin_nom,
        total_conversions=total_conversions,
        profile_image_url=profile_image_url,
        profile_message=request.args.get("message"),
    )

@app.route('/users_admin',methods=['GET' , 'POST'])
def users_admin():

    connexion = get_db_connection()

    if connexion is None:
        return "Erreur de connexion à la base de données"

    cursor = connexion.cursor(dictionary=True)

    try:
        # ============================
        # AJOUTER UN UTILISATEUR
        # ============================
        if request.method == 'POST':

            nom = request.form.get('nom', '').strip()
            email = request.form.get('email', '').strip()
            mot_de_passe = request.form.get('mot_de_passe', '').strip()
            statut = request.form.get('statut', 'actif')

            # Vérifier que les champs sont remplis
            if not nom or not email or not mot_de_passe:
                return "Tous les champs sont obligatoires"

            # Vérifier si l'email existe déjà
            cursor.execute(
                "SELECT id FROM utilisateur WHERE email = %s",
                (email,)
            )

            utilisateur_existant = cursor.fetchone()

            if utilisateur_existant:
                return "Cet email existe déjà"

            # Ajouter l'utilisateur
            cursor.execute("""
                INSERT INTO utilisateur
                (nom, email, mot_de_passe, type_utilisateur, statut)
                VALUES (%s, %s, %s, 'utilisateur', %s)
            """, (
                nom,
                email,
                mot_de_passe,
                statut
            ))

            connexion.commit()

            return redirect(url_for('users_admin'))

        statut = request.args.get('statut', '')

        recherche = request.args.get('search', '').strip()

        # 3. Pagination
        users_par_page = 7

        page = request.args.get('page', 1, type=int)

        if page < 1:
            page = 1

        offset = (page - 1) * users_par_page

        # 4. Compter le nombre total d'utilisateurs

        count_sql = """
            SELECT COUNT(*) AS total
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
        """

        count_params = []

        # Filtre Actif / Inactif
        if statut in ['actif', 'inactif']:

            count_sql += " AND statut = %s"

            count_params.append(statut)

        # Recherche
        if recherche:

            count_sql += """
                AND (
                    nom LIKE %s
                    OR email LIKE %s
                )
            """

            count_params.append('%' + recherche + '%')
            count_params.append('%' + recherche + '%')

        cursor.execute(count_sql, count_params)

        total_utilisateurs = cursor.fetchone()['total']

        # 5. Calculer le nombre total de pages
        total_pages = (
            total_utilisateurs + users_par_page - 1
        ) // users_par_page

        # 6. Récupérer les utilisateurs

        sql = """
            SELECT
                id,
                nom,
                email,
                statut,
                date_creation
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
        """

        params = []

        # Filtre Actif / Inactif
        if statut in ['actif', 'inactif']:

            sql += " AND statut = %s"

            params.append(statut)

        # Recherche par nom ou email
        if recherche:
            sql += """
                AND (
                    nom LIKE %s
                    OR email LIKE %s
                )
            """
            params.append('%' + recherche + '%')
            params.append('%' + recherche + '%')

        # 7. Trier + Pagination SQL
        sql += """
            ORDER BY date_creation DESC
            LIMIT %s OFFSET %s
        """

        params.append(users_par_page)
        params.append(offset)

        cursor.execute(sql, params)
        utilisateurs = cursor.fetchall()

        # 8. Calculer l'affichage
        debut = offset + 1 if total_utilisateurs > 0 else 0
        fin = min(
            offset + users_par_page,
            total_utilisateurs
        )

        # STATISTIQUES
        # Total utilisateurs
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
        """)

        total_utilisateurs = cursor.fetchone()['total']


        # Utilisateurs actifs
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
            AND statut = 'actif'
        """)

        utilisateurs_actifs = cursor.fetchone()['total']

        # Utilisateurs inactifs
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
            AND statut = 'inactif'
        """)

        utilisateurs_inactifs = cursor.fetchone()['total']

        # Nouveaux utilisateurs ce mois
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
            AND MONTH(date_creation) = MONTH(CURRENT_DATE())
            AND YEAR(date_creation) = YEAR(CURRENT_DATE())
        """)

        nouveaux_ce_mois = cursor.fetchone()['total']

        return render_template(
            'users_admin.html',
            utilisateurs=utilisateurs,
            statut_selectionne=statut,
            recherche=recherche,
            total_utilisateurs=total_utilisateurs,
            utilisateurs_actifs=utilisateurs_actifs,
            utilisateurs_inactifs=utilisateurs_inactifs,
            nouveaux_ce_mois=nouveaux_ce_mois,
            page=page,
            total_pages=total_pages,
            debut=debut,
            fin=fin
        )

    finally:
        cursor.close()
        connexion.close()

@app.route('/users_admin/delete/<int:user_id>')
def delete_user(user_id):

    connexion = get_db_connection()

    if connexion is None:
        return "Erreur de connexion à la base de données"

    cursor = connexion.cursor()

    try:

        cursor.execute("""
            UPDATE utilisateur
            SET statut = 'inactif'
            WHERE id = %s
            AND type_utilisateur = 'utilisateur'
        """, (user_id,))

        connexion.commit()

        return redirect(url_for('users_admin'))

    finally:
        cursor.close()
        connexion.close()
@app.route('/users_admin/modifier/<int:user_id>', methods=['POST'])
def modifier_utilisateur(user_id):

    connexion = get_db_connection()

    if connexion is None:
        return jsonify({
            'success': False,
            'message': 'Erreur de connexion à la base de données'
        }), 500

    cursor = connexion.cursor()

    try:
        data = request.get_json()

        nom = data.get('nom', '').strip()
        email = data.get('email', '').strip()
        statut = data.get('statut', '').strip().lower()

        if not nom or not email:
            return jsonify({
                'success': False,
                'message': 'Le nom et l email sont obligatoires'
            }), 400

        if statut not in ['actif', 'inactif']:
            return jsonify({
                'success': False,
                'message': 'Statut invalide'
            }), 400

        cursor.execute("""
            UPDATE utilisateur
            SET nom = %s,
                email = %s,
                statut = %s
            WHERE id = %s
            AND type_utilisateur = 'utilisateur'
            AND est_supprime = FALSE
        """, (nom, email, statut, user_id))

        connexion.commit()

        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': 'Utilisateur introuvable'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Utilisateur modifié avec succès'
        })

    except Exception as e:
        connexion.rollback()

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    finally:
        cursor.close()
        connexion.close()
@app.route('/users_admin/export')
def export_users():

    connexion = get_db_connection()

    if connexion is None:
        return "Erreur de connexion à la base de données", 500

    cursor = connexion.cursor(dictionary=True)

    try:
        statut = request.args.get('statut', '').strip().lower()

        sql = """
            SELECT
                nom,
                email,
                statut,
                date_creation
            FROM utilisateur
            WHERE type_utilisateur = 'utilisateur'
        """

        params = []

        if statut in ['actif', 'inactif']:
            sql += " AND statut = %s"
            params.append(statut)

        sql += " ORDER BY date_creation DESC"

        cursor.execute(sql, params)
        utilisateurs = cursor.fetchall()

        # Création du CSV en mémoire
        output = io.StringIO()

        writer = csv.writer(output, delimiter=';')

        # En-têtes
        writer.writerow([
            'Nom',
            'Email',
            'Statut',
            "Date d'inscription"
        ])

        # Données
        for user in utilisateurs:
            writer.writerow([
                user['nom'],
                user['email'],
                user['statut'].capitalize(),
                user['date_creation'].strftime('%d/%m/%Y')
            ])

        response = Response(
            output.getvalue(),
            mimetype='text/csv'
        )

        response.headers['Content-Disposition'] = (
            'attachment; filename=utilisateurs.csv'
        )

        return response

    finally:
        cursor.close()
        connexion.close()


@app.route('/formats_admin')
def formats_admin():

    connexion = get_db_connection()

    if connexion is None:
        return "Erreur de connexion à la base de données"

    cursor = connexion.cursor(dictionary=True)

    try:

        # Initialiser la table des conversions autorisées si nécessaire
        _ensure_format_conversion_table(connexion, cursor)
        _seed_default_conversions(connexion, cursor)

        # 1. NOMBRE TOTAL DE FORMATS DISPONIBLES
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM format
        """)

        formats_disponibles = cursor.fetchone()['total']

        # 2. NOMBRE DE FORMATS ACTIFS
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM format
            WHERE est_actif = 1
        """)

        formats_actifs = cursor.fetchone()['total']

        # 3. NOUVEAUX FORMATS CE MOIS
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM format
            WHERE MONTH(date_creation) = MONTH(CURRENT_DATE())
            AND YEAR(date_creation) = YEAR(CURRENT_DATE())
        """)

        nouveaux_formats = cursor.fetchone()['total']

        # 4. NOMBRE DE CONVERSIONS CE MOIS
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM conversion
            WHERE MONTH(date_conversion) = MONTH(CURRENT_DATE())
            AND YEAR(date_conversion) = YEAR(CURRENT_DATE())
            AND est_supprime = 0
        """)

        conversions_ce_mois = cursor.fetchone()['total']

        # 5. CONVERSIONS DU MOIS DERNIER
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM conversion
            WHERE MONTH(date_conversion) = MONTH(CURRENT_DATE() - INTERVAL 1 MONTH)
            AND YEAR(date_conversion) = YEAR(CURRENT_DATE() - INTERVAL 1 MONTH)
            AND est_supprime = 0
        """)

        conversions_mois_dernier = cursor.fetchone()['total']

        # 6. POURCENTAGE D'ÉVOLUTION
        if conversions_mois_dernier > 0:

            evolution_conversions = (
                (conversions_ce_mois - conversions_mois_dernier)
                / conversions_mois_dernier
            ) * 100

        else:

            evolution_conversions = 0

        # 7. FORMAT LE PLUS UTILISÉ
        cursor.execute("""
            SELECT
                fo.nom AS format_origin,
                fc.nom AS format_cible,
                COUNT(*) AS nombre_conversions

            FROM conversion c

            INNER JOIN fichier f
                ON c.id_fichier = f.id

            INNER JOIN format fo
                ON f.id_format_origin = fo.id

            INNER JOIN format fc
                ON c.id_format_cible = fc.id

            WHERE c.est_supprime = 0

            GROUP BY
                fo.id,
                fo.nom,
                fc.id,
                fc.nom

            ORDER BY nombre_conversions DESC

            LIMIT 1
        """)

        format_plus_utilise = cursor.fetchone()

        # 8. VALEURS PAR DÉFAUT SI AUCUNE CONVERSION
        if format_plus_utilise:

            format_origine = format_plus_utilise['format_origin']
            format_cible = format_plus_utilise['format_cible']
            nombre_conversions = format_plus_utilise['nombre_conversions']

        else:

            format_origine = "-"
            format_cible = "-"
            nombre_conversions = 0

        # 9. LISTE DES FORMATS
        cursor.execute("""
            SELECT
                id,
                nom,
                est_actif,
                date_creation
            FROM format
            ORDER BY nom ASC
        """)
        formats = cursor.fetchall()

        # 9.1 LISTE DES CONVERSIONS / FORMATS À AFFICHER
        # Récupérer les conversions autorisées depuis la table
        cursor.execute("""
            SELECT
                fc_pair.id,
                fc_pair.est_actif AS conversion_actif,
                fo.nom AS format_origine,
                fc.nom AS format_cible,
                fo.est_actif AS origine_actif,
                fc.est_actif AS cible_actif,
                COUNT(c.id) AS nb_conversions
            FROM format_conversion fc_pair
            INNER JOIN format fo ON fc_pair.id_format_origin = fo.id
            INNER JOIN format fc ON fc_pair.id_format_cible = fc.id
            LEFT JOIN conversion c ON 
                c.id_format_cible = fc.id
                AND c.est_supprime = 0
            LEFT JOIN fichier f ON c.id_fichier = f.id
                AND f.id_format_origin = fo.id
            GROUP BY
                fc_pair.id,
                fc_pair.est_actif,
                fo.id,
                fo.nom,
                fo.est_actif,
                fc.id,
                fc.nom,
                fc.est_actif
            ORDER BY fo.nom, fc.nom
        """)

        resultats_conversions = cursor.fetchall()

        print("NOMBRE DE CONVERSIONS :", len(resultats_conversions))
        print("CONVERSIONS :", resultats_conversions)
        # 10. ENVOI VERS LA PAGE HTML
        return render_template(
            'formats_admin.html',
            formats=formats,
            formats_disponibles=formats_disponibles,
            formats_actifs=formats_actifs,
            conversions_ce_mois=conversions_ce_mois,
            conversions_mois_dernier=conversions_mois_dernier,
            evolution_conversions=round(
                evolution_conversions,
                1
            ),
            nouveaux_formats=nouveaux_formats,
            format_origine=format_origine,
            format_cible=format_cible,
            nombre_conversions=nombre_conversions,
            conversions_formats=resultats_conversions
        )

    finally:
        cursor.close()
        connexion.close()


@app.route('/api/format/add', methods=['POST'])
def format_add():
    """Ajouter une nouvelle conversion autorisée."""
    try:
        data = request.get_json()
        format_origin = data.get('origin', '').strip().upper()
        format_target = data.get('target', '').strip().upper()
        
        if not format_origin or not format_target:
            return jsonify({'success': False, 'error': 'Formats invalides'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Récupérer les IDs des formats
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_origin,))
            origin_result = cursor.fetchone()
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_target,))
            target_result = cursor.fetchone()
            
            if not origin_result or not target_result:
                return jsonify({'success': False, 'error': 'Format non trouvé'}), 404
            
            id_format_origin = origin_result['id']
            id_format_target = target_result['id']
            
            # Vérifier que la paire n'existe pas déjà
            cursor.execute("""
                SELECT id FROM format_conversion
                WHERE id_format_origin = %s AND id_format_cible = %s
            """, (id_format_origin, id_format_target))
            
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Cette conversion existe déjà'}), 409
            
            # Insérer la nouvelle conversion
            cursor.execute("""
                INSERT INTO format_conversion (id_format_origin, id_format_cible, est_actif)
                VALUES (%s, %s, 1)
            """, (id_format_origin, id_format_target))
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Conversion ajoutée avec succès'}), 201
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/format/delete', methods=['POST'])
def format_delete():
    """Supprimer une conversion autorisée."""
    try:
        data = request.get_json()
        format_origin = data.get('origin', '').strip().upper()
        format_target = data.get('target', '').strip().upper()
        
        if not format_origin or not format_target:
            return jsonify({'success': False, 'error': 'Formats invalides'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Récupérer les IDs des formats
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_origin,))
            origin_result = cursor.fetchone()
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_target,))
            target_result = cursor.fetchone()
            
            if not origin_result or not target_result:
                return jsonify({'success': False, 'error': 'Format non trouvé'}), 404
            
            id_format_origin = origin_result['id']
            id_format_target = target_result['id']
            
            # Supprimer la conversion
            cursor.execute("""
                DELETE FROM format_conversion
                WHERE id_format_origin = %s AND id_format_cible = %s
            """, (id_format_origin, id_format_target))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Conversion non trouvée'}), 404
            
            return jsonify({'success': True, 'message': 'Conversion supprimée avec succès'}), 200
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/format/toggle', methods=['POST'])
def format_toggle():
    """Toggle le statut d'une conversion (actif/inactif)."""
    try:
        data = request.get_json()
        format_origin = data.get('origin', '').strip().upper()
        format_target = data.get('target', '').strip().upper()
        
        if not format_origin or not format_target:
            return jsonify({'success': False, 'error': 'Formats invalides'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Récupérer les IDs des formats
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_origin,))
            origin_result = cursor.fetchone()
            cursor.execute("SELECT id FROM format WHERE nom = %s", (format_target,))
            target_result = cursor.fetchone()
            
            if not origin_result or not target_result:
                return jsonify({'success': False, 'error': 'Format non trouvé'}), 404
            
            id_format_origin = origin_result['id']
            id_format_target = target_result['id']
            
            # Récupérer l'état actuel
            cursor.execute("""
                SELECT est_actif FROM format_conversion
                WHERE id_format_origin = %s AND id_format_cible = %s
            """, (id_format_origin, id_format_target))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'success': False, 'error': 'Conversion non trouvée'}), 404
            
            current_status = result['est_actif']
            new_status = 0 if current_status == 1 else 1
            
            # Mettre à jour le statut
            cursor.execute("""
                UPDATE format_conversion
                SET est_actif = %s
                WHERE id_format_origin = %s AND id_format_cible = %s
            """, (new_status, id_format_origin, id_format_target))
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Conversion mise à jour',
                'status': new_status
            }), 200
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/format/edit', methods=['POST'])
def format_edit():
    """Modifier une conversion."""
    try:
        data = request.get_json()

        old_origin = data.get('old_origin', '').strip().upper()
        old_target = data.get('old_target', '').strip().upper()

        new_origin = data.get('new_origin', '').strip().upper()
        new_target = data.get('new_target', '').strip().upper()

        if not old_origin or not old_target or not new_origin or not new_target:
            return jsonify({
                'success': False,
                'error': 'Tous les formats sont obligatoires'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # ============================================
            # Récupérer l'ancien format origine
            # ============================================
            cursor.execute(
                "SELECT id FROM format WHERE nom = %s",
                (old_origin,)
            )

            old_origin_result = cursor.fetchone()
            # ============================================
            # Récupérer l'ancien format cible
            # ============================================
            cursor.execute(
                "SELECT id FROM format WHERE nom = %s",
                (old_target,)
            )

            old_target_result = cursor.fetchone()

            if not old_origin_result or not old_target_result:
                return jsonify({
                    'success': False,
                    'error': 'Ancienne conversion introuvable'
                }), 404

            old_origin_id = old_origin_result['id']
            old_target_id = old_target_result['id']
            # ============================================
            # Récupérer le nouveau format origine
            # ============================================
            cursor.execute(
                "SELECT id FROM format WHERE nom = %s",
                (new_origin,)
            )

            new_origin_result = cursor.fetchone()
            # ============================================
            # Récupérer le nouveau format cible
            # ============================================
            cursor.execute(
                "SELECT id FROM format WHERE nom = %s",
                (new_target,)
            )

            new_target_result = cursor.fetchone()

            if not new_origin_result or not new_target_result:
                return jsonify({
                    'success': False,
                    'error': 'Nouveau format introuvable'
                }), 404

            new_origin_id = new_origin_result['id']
            new_target_id = new_target_result['id']
            # ============================================
            # Vérifier si la nouvelle conversion existe déjà
            # ============================================
            cursor.execute("""
                SELECT id
                FROM format_conversion
                WHERE id_format_origin = %s
                AND id_format_cible = %s
            """, (
                new_origin_id,
                new_target_id
            ))

            existing = cursor.fetchone()

            # Si on change vers une conversion déjà existante
            if existing and (
                new_origin_id != old_origin_id
                or new_target_id != old_target_id
            ):
                return jsonify({
                    'success': False,
                    'error': 'Cette conversion existe déjà'
                }), 409
            # ============================================
            # Modifier la conversion
            # ============================================
            cursor.execute("""
                UPDATE format_conversion
                SET
                    id_format_origin = %s,
                    id_format_cible = %s
                WHERE id_format_origin = %s
                AND id_format_cible = %s
            """, (
                new_origin_id,
                new_target_id,
                old_origin_id,
                old_target_id
            ))

            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Conversion modifiée avec succès'
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin_notifications')
def api_admin_notifications():
    """
    Retourne les notifications ADMIN des dernières 24h, calculées à la
    volée depuis les tables conversion et utilisateur (pas de table
    dédiée). Utilisé par le dropdown de la cloche sur toutes les pages admin.
    """
    if not _is_admin():
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        notifications, total_count = _get_admin_notifications(cursor)
        return jsonify({
            "success": True,
            "count": total_count,
            "notifications": notifications,
        })
    finally:
        cursor.close()
        conn.close()


def _build_history_filters(search, status, format_filter):
    """Construit la clause WHERE + params pour la recherche/filtres de l'historique admin."""
    conditions = ["f.est_supprime = 0", "c.est_supprime = 0"]
    params = []

    if search:
        conditions.append("""
            (u.nom LIKE %s OR u.email LIKE %s OR f.nom_origin LIKE %s
             OR fo.nom LIKE %s OR fc.nom LIKE %s)
        """)
        like = f"%{search}%"
        params.extend([like, like, like, like, like])

    if status == "Réussi":
        conditions.append("c.statut IN ('terminee','success','termine')")
    elif status == "Échec":
        conditions.append("c.statut IN ('echec','error','failed')")

    if format_filter and "→" in format_filter:
        origin_name, target_name = [p.strip() for p in format_filter.split("→")]
        conditions.append("fo.nom = %s AND fc.nom = %s")
        params.extend([origin_name, target_name])

    return " AND ".join(conditions), params


def _query_history(search, status, format_filter, page, per_page=7):
    """Récupère une page de résultats filtrés + infos de pagination, sans données inventées."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        where_clause, params = _build_history_filters(search, status, format_filter)

        base_from = f"""
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            JOIN utilisateur u ON f.id_utilisateur = u.id
            LEFT JOIN format fo ON f.id_format_origin = fo.id
            LEFT JOIN format fc ON c.id_format_cible = fc.id
            WHERE {where_clause}
        """

        cursor.execute("SELECT COUNT(*) AS total " + base_from, params)
        total = cursor.fetchone()["total"]

        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        sql = """
            SELECT
                c.id AS id_conversion,
                u.nom AS user_name,
                u.email AS user_email,
                f.nom_origin AS file_name,
                fo.nom AS format_origin,
                fc.nom AS format_cible,
                f.taille AS file_size,
                DATE_FORMAT(c.date_conversion, '%d/%m/%Y %H:%i') AS date_conversion,
                c.statut
        """ + base_from + """
            ORDER BY c.date_conversion DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [per_page, offset])
        rows = cursor.fetchall()

        conversions = []
        for row in rows:
            fa_icon, file_css_class = _get_history_file_fa_icon(row["format_origin"] or row["file_name"])
            status_filter = _format_history_status_filter(row["statut"])
            conversions.append({
                "id_conversion": row["id_conversion"],
                "user_name": row["user_name"],
                "file_name": row["file_name"],
                "format_origin": row["format_origin"] or "?",
                "format_cible": row["format_cible"] or "?",
                "format_origin_chip_class": _get_history_format_chip_class(row["format_origin"]),
                "format_cible_chip_class": _get_history_format_chip_class(row["format_cible"]),
                "file_size": format_size(row["file_size"]),
                "date_conversion": row["date_conversion"],
                "status_label": _format_history_status_label(row["statut"]),
                "status_filter": status_filter,
                "status_class": "cvt-status-success" if status_filter == "success" else "cvt-status-failed",
                "file_fa_icon": fa_icon,
                "file_css_class": file_css_class,
            })

        debut = offset + 1 if total > 0 else 0
        fin = min(offset + per_page, total)

        return {
            "conversions": conversions,
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "debut": debut,
            "fin": fin,
        }
    finally:
        cursor.close()
        conn.close()


@app.route('/history_admin')
def history_admin():
    if not _is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM conversion WHERE est_supprime = 0")
        total_conversions = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) AS total FROM conversion
            WHERE est_supprime = 0 AND statut IN ('terminee','success','termine')
        """)
        total_success = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) AS total FROM conversion
            WHERE est_supprime = 0 AND statut IN ('echec','error','failed')
        """)
        total_failed = cursor.fetchone()['total']
    finally:
        cursor.close()
        conn.close()

    result = _query_history(search="", status="", format_filter="", page=1)

    return render_template(
        "history_admin.html",
        conversions=result["conversions"],
        total_conversions=total_conversions,
        total_success=total_success,
        total_failed=total_failed,
        pagination=result,
    )


@app.route('/api/history_admin')
def api_history_admin():
    """API JSON utilisée par la recherche, les filtres et la pagination en direct."""
    if not _is_admin():
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    format_filter = request.args.get('format', '').strip()
    page = request.args.get('page', 1, type=int)

    result = _query_history(search, status, format_filter, page)
    return jsonify({"success": True, **result})


@app.route('/api/history_admin/<int:id_conversion>/details')
def api_history_admin_details(id_conversion):
    """Détails réels d'une conversion pour le modal 'Voir'."""
    if not _is_admin():
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT
                c.id AS id_conversion,
                u.nom AS user_name,
                u.email AS user_email,
                f.nom_origin AS file_name,
                fo.nom AS format_origin,
                fc.nom AS format_cible,
                f.taille AS file_size,
                DATE_FORMAT(c.date_conversion, '%%d/%%m/%%Y %%H:%%i') AS date_conversion,
                c.statut,
                c.chemin_fichier_converti
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            JOIN utilisateur u ON f.id_utilisateur = u.id
            LEFT JOIN format fo ON f.id_format_origin = fo.id
            LEFT JOIN format fc ON c.id_format_cible = fc.id
            WHERE c.id = %s
              AND f.est_supprime = 0
              AND c.est_supprime = 0
        """
        cursor.execute(sql, (id_conversion,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "error": "Conversion introuvable"}), 404

        status_filter = _format_history_status_filter(row["statut"])
        can_download = bool(row["chemin_fichier_converti"]) and os.path.isfile(row["chemin_fichier_converti"] or "")

        data = {
            "id_conversion": row["id_conversion"],
            "user_name": row["user_name"],
            "user_email": row["user_email"],
            "file_name": row["file_name"],
            "format_origin": row["format_origin"] or "?",
            "format_cible": row["format_cible"] or "?",
            "file_size": format_size(row["file_size"]),
            "date_conversion": row["date_conversion"],
            "status_label": _format_history_status_label(row["statut"]),
            "status_filter": status_filter,
            "can_download": can_download,
            "download_url": url_for("history_admin_download", id_conversion=row["id_conversion"]) if can_download else None,
        }
        return jsonify({"success": True, "conversion": data})
    finally:
        cursor.close()
        conn.close()


@app.route('/history_admin/download/<int:id_conversion>')
def history_admin_download(id_conversion):
    """Téléchargement admin du fichier converti réel (n'importe quel utilisateur)."""
    if not _is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT c.chemin_fichier_converti
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            WHERE c.id = %s AND f.est_supprime = 0 AND c.est_supprime = 0
        """
        cursor.execute(sql, (id_conversion,))
        row = cursor.fetchone()

        if not row or not row["chemin_fichier_converti"] or not os.path.isfile(row["chemin_fichier_converti"]):
            abort(404)

        if _get_downloads_column_exists(cursor):
            cursor.execute(
                "UPDATE conversion SET telechargements = COALESCE(telechargements, 0) + 1 WHERE id = %s",
                (id_conversion,)
            )
            conn.commit()

        file_path = row["chemin_fichier_converti"]
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
    finally:
        cursor.close()
        conn.close()


@app.route('/history_admin/export')
def history_admin_export():
    """Export CSV des conversions correspondant aux filtres actuellement affichés."""
    if not _is_admin():
        return redirect(url_for("login"))

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    format_filter = request.args.get('format', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        where_clause, params = _build_history_filters(search, status, format_filter)
        sql = f"""
            SELECT
                u.nom AS user_name,
                u.email AS user_email,
                f.nom_origin AS file_name,
                fo.nom AS format_origin,
                fc.nom AS format_cible,
                f.taille AS file_size,
                DATE_FORMAT(c.date_conversion, '%%d/%%m/%%Y %%H:%%i') AS date_conversion,
                c.statut
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            JOIN utilisateur u ON f.id_utilisateur = u.id
            LEFT JOIN format fo ON f.id_format_origin = fo.id
            LEFT JOIN format fc ON c.id_format_cible = fc.id
            WHERE {where_clause}
            ORDER BY c.date_conversion DESC
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Utilisateur', 'Email', 'Fichier', 'Format origine', 'Format cible', 'Taille', 'Date', 'Statut'])
        for row in rows:
            writer.writerow([
                row['user_name'], row['user_email'], row['file_name'],
                row['format_origin'] or '', row['format_cible'] or '',
                format_size(row['file_size']), row['date_conversion'],
                _format_history_status_label(row['statut']),
            ])

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=historique_conversions.csv'
        return response
    finally:
        cursor.close()
        conn.close()

@app.route('/statistics_admin')
def statistics_admin():
    """Affiche la page de statistiques avec les vraies données."""
    conn = get_db_connection()
    if conn is None:
        return render_template('statistics_admin.html')
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Déterminer la période sélectionnée (par défaut: cette semaine)
        period = request.args.get('period', 'week')
        
        # Calculer les dates limite
        today = datetime.now()
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())  # Lundi
            end_date = start_date + timedelta(days=6)  # Dimanche
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
            label_period = 'Cette semaine'
        elif period == 'month':
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month+1, day=1) - timedelta(days=1)
            prev_start = (start_date - timedelta(days=1)).replace(day=1)
            prev_end = start_date - timedelta(days=1)
            label_period = 'Ce mois'
        else:  # year
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            prev_start = datetime(today.year-1, 1, 1)
            prev_end = datetime(today.year-1, 12, 31)
            label_period = 'Cette année'
        
        # ===== STATISTIQUES PRINCIPALES =====
        
        # Total conversions (période actuelle)
        sql = """
            SELECT COUNT(*) as total
            FROM conversion c
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0
        """
        cursor.execute(sql, (start_date, end_date))
        total_conversions = cursor.fetchone()['total'] or 0
        
        # Total conversions réussies et échouées
        sql_success = """
            SELECT 
                SUM(CASE WHEN c.statut = 'terminee' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN c.statut = 'echec' THEN 1 ELSE 0 END) as failed_count
            FROM conversion c
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0
        """
        cursor.execute(sql_success, (start_date, end_date))
        status_data = cursor.fetchone()
        success_count = status_data['success_count'] or 0
        failed_count = status_data['failed_count'] or 0
        
        # Taux de réussite
        success_rate = round((success_count / total_conversions * 100), 1) if total_conversions > 0 else 0
        
        # Nouveaux utilisateurs dans la période
        sql_new_users = """
            SELECT COUNT(*) as new_users
            FROM utilisateur u
            WHERE u.date_creation >= %s AND u.date_creation <= %s
        """
        cursor.execute(sql_new_users, (start_date, end_date))
        new_users = cursor.fetchone()['new_users'] or 0
        
        # ===== DONNÉES POUR LES GRAPHIQUES =====
        
        # Evolution des conversions (par jour pour semaine, par semaine pour mois, par mois pour année)
        if period == 'week':
            # Par jour de la semaine
            sql_evolution = """
                SELECT DATE_FORMAT(c.date_conversion, '%d/%m') as label,
                       COUNT(*) as total,
                       DAYNAME(c.date_conversion) as day_name
                FROM conversion c
                WHERE c.date_conversion >= %s AND c.date_conversion <= %s
                AND c.est_supprime = 0
                GROUP BY DATE(c.date_conversion)
                ORDER BY c.date_conversion
            """
            cursor.execute(sql_evolution, (start_date, end_date))
            evolution_data = cursor.fetchall()
            
            # Compléter avec les jours manquants
            labels_current = []
            values_current = []
            current = start_date
            evolution_dict = {row['label']: row['total'] for row in evolution_data}
            while current <= end_date:
                label = current.strftime('%d/%m')
                labels_current.append(label)
                values_current.append(evolution_dict.get(label, 0))
                current += timedelta(days=1)
            
            # Données pour la période précédente
            sql_prev = """
                SELECT DATE_FORMAT(c.date_conversion, '%d/%m') as label,
                       COUNT(*) as total
                FROM conversion c
                WHERE c.date_conversion >= %s AND c.date_conversion <= %s
                AND c.est_supprime = 0
                GROUP BY DATE(c.date_conversion)
                ORDER BY c.date_conversion
            """
            cursor.execute(sql_prev, (prev_start, prev_end))
            prev_evolution = cursor.fetchall()
            values_prev = [row['total'] for row in prev_evolution]
            
        elif period == 'month':
            # Évolution des conversions par semaine du mois
            sql_evolution = """
                SELECT
                    CONCAT('Sem ', FLOOR((DAY(c.date_conversion) - 1) / 7) + 1) AS label,
                    COUNT(*) AS total
                FROM conversion c
                WHERE c.date_conversion >= %s
                AND c.date_conversion <= %s
                AND c.est_supprime = 0
                GROUP BY FLOOR((DAY(c.date_conversion) - 1) / 7)
                ORDER BY FLOOR((DAY(c.date_conversion) - 1) / 7)
            """

            cursor.execute(sql_evolution, (start_date, end_date))
            evolution_data = cursor.fetchall()

            labels_current = [row['label'] for row in evolution_data]
            values_current = [row['total'] for row in evolution_data]

            # Période précédente
            sql_prev = """
                SELECT
                    CONCAT('Sem ', FLOOR((DAY(c.date_conversion) - 1) / 7) + 1) AS label,
                    COUNT(*) AS total
                FROM conversion c
                WHERE c.date_conversion >= %s
                AND c.date_conversion <= %s
                AND c.est_supprime = 0
                GROUP BY FLOOR((DAY(c.date_conversion) - 1) / 7)
                ORDER BY FLOOR((DAY(c.date_conversion) - 1) / 7)
            """

            cursor.execute(sql_prev, (prev_start, prev_end))
            prev_evolution = cursor.fetchall()

            values_prev = [row['total'] for row in prev_evolution]
        
        else:  # year
            # Par mois
            sql_evolution = """
                SELECT DATE_FORMAT(c.date_conversion, '%b') as label,
                       COUNT(*) as total
                FROM conversion c
                WHERE YEAR(c.date_conversion) = %s
                AND c.est_supprime = 0
                GROUP BY MONTH(c.date_conversion)
                ORDER BY MONTH(c.date_conversion)
            """
            cursor.execute(sql_evolution, (today.year,))
            evolution_data = cursor.fetchall()
            labels_current = [row['label'] for row in evolution_data]
            values_current = [row['total'] for row in evolution_data]
            
            sql_prev = """
                SELECT DATE_FORMAT(c.date_conversion, '%b') as label,
                       COUNT(*) as total
                FROM conversion c
                WHERE YEAR(c.date_conversion) = %s
                AND c.est_supprime = 0
                GROUP BY MONTH(c.date_conversion)
                ORDER BY MONTH(c.date_conversion)
            """
            cursor.execute(sql_prev, (today.year - 1,))
            prev_evolution = cursor.fetchall()
            values_prev = [row['total'] for row in prev_evolution]
        
        # ===== RÉPARTITION PAR STATUT =====
        status_breakdown = {
            'success': success_count,
            'failed': failed_count
        }
        
        # ===== CONVERSIONS PAR JOUR DE LA SEMAINE =====
        sql_weekday = """
            SELECT DAYNAME(c.date_conversion) as day_name,
                   ELT(DAYOFWEEK(c.date_conversion), 'Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam') as day_label,
                   COUNT(*) as total
            FROM conversion c
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0
            GROUP BY DAYOFWEEK(c.date_conversion)
            ORDER BY DAYOFWEEK(c.date_conversion)
        """
        cursor.execute(sql_weekday, (start_date, end_date))
        weekday_data = cursor.fetchall()
        weekday_labels = [row['day_label'] for row in weekday_data]
        weekday_values = [row['total'] for row in weekday_data]
        
        # ===== FORMATS LES PLUS UTILISÉS =====
        sql_formats = """
            SELECT f.nom,
                   COUNT(*) as count
            FROM conversion c
            JOIN format f ON c.id_format_cible = f.id
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0
            GROUP BY c.id_format_cible
            ORDER BY count DESC
            LIMIT 10
        """
        cursor.execute(sql_formats, (start_date, end_date))
        formats_data = cursor.fetchall()
        total_format_conversions = sum(row['count'] for row in formats_data) if formats_data else 1
        formats_list = []
        for row in formats_data:
            percentage = round((row['count'] / total_format_conversions * 100), 1)
            formats_list.append({
                'name': row['nom'],
                'count': row['count'],
                'percentage': percentage
            })
        
        # ===== HEURES DE POINTE =====
        sql_hours = """
            SELECT HOUR(c.date_conversion) as hour,
                   COUNT(*) as total
            FROM conversion c
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0
            GROUP BY HOUR(c.date_conversion)
            ORDER BY hour
        """
        cursor.execute(sql_hours, (start_date, end_date))
        hours_data = cursor.fetchall()
        hours_dict = {row['hour']: row['total'] for row in hours_data}
        hours_labels = []
        hours_values = []
        for h in [0, 4, 8, 12, 16, 20]:
            hours_labels.append(f"{h:02d}h")
            hours_values.append(hours_dict.get(h, 0))
        
        # ===== TOP UTILISATEURS =====
        sql_top_users = """
            SELECT u.nom,
                   u.email,
                   COUNT(c.id) as total_conversions,
                   SUM(CASE WHEN c.statut = 'terminee' THEN 1 ELSE 0 END) as success_conversions
            FROM utilisateur u
            LEFT JOIN fichier f ON u.id = f.id_utilisateur
            LEFT JOIN conversion c ON f.id = c.id_fichier
            WHERE c.date_conversion >= %s AND c.date_conversion <= %s
            AND c.est_supprime = 0 AND f.est_supprime = 0
            GROUP BY u.id
            ORDER BY total_conversions DESC
            LIMIT 5
        """
        cursor.execute(sql_top_users, (start_date, end_date))
        top_users = cursor.fetchall()
        
        # Calculer le taux de réussite par utilisateur
        for user in top_users:
            if user['total_conversions'] > 0:
                user['success_rate'] = round((user['success_conversions'] / user['total_conversions'] * 100), 1)
                user['success_conversions'] = user['success_conversions'] or 0
            else:
                user['success_rate'] = 0
        
        cursor.close()
        conn.close()
        
        # Retourner le template avec toutes les données
        return render_template(
            'statistics_admin.html',
            total_conversions=total_conversions,
            success_rate=success_rate,
            new_users=new_users,
            evolution_labels=labels_current,
            evolution_current=values_current,
            evolution_previous=values_prev,
            status_success=success_count,
            status_failed=failed_count,
            weekday_labels=weekday_labels,
            weekday_values=weekday_values,
            formats_list=formats_list,
            hours_labels=hours_labels,
            hours_values=hours_values,
            top_users=top_users,
            period=period,
            label_period=label_period
        )
    
    except Exception as e:
        print(f"Erreur statistiques: {e}")
        cursor.close()
        conn.close()
        return render_template('statistics_admin.html')

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CONVERTED_FOLDER"] = CONVERTED_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@app.route("/conversion-success/<int:id_conversion>")
def conversion_success(id_conversion):
    """Affiche le dashboard utilisateur avec un modal de succès après une conversion."""
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_downloads_column(conn, cursor)
    
    sql_formats = "SELECT * FROM format WHERE est_actif = 1"
    cursor.execute(sql_formats)
    formats = cursor.fetchall()

    sql_conversion = """
        SELECT c.id AS id_conversion, f.nom_origin AS file_name
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE c.id = %s
          AND f.id_utilisateur = %s
          AND f.est_supprime = 0
          AND c.est_supprime = 0
    """
    cursor.execute(sql_conversion, (id_conversion, user_id))
    conversion_data = cursor.fetchone()

    stats = _get_dashboard_counts(cursor, user_id)
    conversion_types = _get_conversion_type_stats(cursor, user_id)
    recent_conversions = _get_recent_conversions(cursor, user_id)

    cursor.close()
    conn.close()

    return render_template(
        "dashboard_user.html",
        formats=formats,
        stats=stats,
        conversion_types=conversion_types,
        recent_conversions=recent_conversions,
        show_conversion_modal=True,
        conversion_id=id_conversion,
        conversion_file_name=(conversion_data["file_name"] if conversion_data else None),
    )

@app.route("/dashboard_user",methods=["GET","POST"])
def dashboard_user():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_downloads_column(conn, cursor)
    sql_formats = "SELECT * FROM format WHERE est_actif = 1"
    cursor.execute(sql_formats)
    formats = cursor.fetchall()

    success_conversion_id = None

    if request.method == "POST":
        id_format_cible = request.form.get("format_cible")
        uploaded_file = request.files.get("file")

        if uploaded_file and uploaded_file.filename != "":
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(filepath)
            taille = round(os.path.getsize(filepath) / 1024, 2)

            extension = os.path.splitext(filename)[1].replace(".", "").upper()

            sql = "SELECT id FROM format WHERE nom = %s"
            cursor.execute(sql, (extension,))
            format_data = cursor.fetchone()

            if not format_data:
                cursor.close()
                conn.close()
                return "Format non supporté."

            id_format_origin = format_data["id"]

            sql_insert = """
            INSERT INTO fichier 
            (id_utilisateur, nom_origin, taille, chemin, id_format_origin)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (user_id, filename, taille, filepath, id_format_origin))
            conn.commit()
            id_fichier = cursor.lastrowid

            if id_format_cible:
                sql = "SELECT nom FROM format WHERE id = %s AND est_actif = 1"
                cursor.execute(sql, (id_format_cible,))
                format_sortie_data = cursor.fetchone()

                if format_sortie_data:
                    output_format_name = format_sortie_data["nom"]
                    try:
                        output_path = perform_conversion(
                            filepath,
                            extension,
                            output_format_name,
                            app.config["CONVERTED_FOLDER"],
                        )

                        sql_conversion = """
                        INSERT INTO conversion
                        (id_fichier, id_format_cible, date_conversion, statut, chemin_fichier_converti)
                        VALUES (%s, %s, NOW(), %s, %s)
                        """
                        cursor.execute(sql_conversion, (id_fichier, id_format_cible, "terminee", output_path))
                        conn.commit()
                        success_conversion_id = cursor.lastrowid

                    except Exception as err:
                        print("ERREUR :", err)

                        sql_conversion = """
                        INSERT INTO conversion
                        (id_fichier, id_format_cible, date_conversion, statut, chemin_fichier_converti)
                        VALUES (%s, %s, NOW(), %s, %s)
                        """

                        cursor.execute(sql_conversion, (id_fichier, id_format_cible, "echec", None))
                        conn.commit()
                        
    if request.method == "POST" and success_conversion_id:
        cursor.close()
        conn.close()
        return redirect(url_for("conversion_success", id_conversion=success_conversion_id))

    stats = _get_dashboard_counts(cursor, user_id)
    conversion_types = _get_conversion_type_stats(cursor, user_id)
    recent_conversions = _get_recent_conversions(cursor, user_id)

    recent_conversions = _get_recent_conversions(cursor, user_id)

    sql_user = """
    SELECT nom, email, photo
    FROM utilisateur
    WHERE id = %s
    """
    cursor.execute(sql_user, (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard_user.html",
        formats=formats,
        stats=stats,
        conversion_types=conversion_types,
        recent_conversions=recent_conversions,
        user=user
    )



@app.route("/download/<int:id_conversion>")
def download_conversion(id_conversion):
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    _ensure_downloads_column(conn, cursor)

    sql = """
        SELECT c.chemin_fichier_converti, f.id_utilisateur
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE c.id = %s
          AND f.est_supprime = 0
          AND c.est_supprime = 0
    """
    cursor.execute(sql, (id_conversion,))
    conversion_data = cursor.fetchone()

    if not conversion_data or conversion_data["id_utilisateur"] != user_id:
        cursor.close()
        conn.close()
        abort(404)

    file_path = conversion_data["chemin_fichier_converti"]
    if not file_path or not os.path.isfile(file_path):
        cursor.close()
        conn.close()
        abort(404)

    if _get_downloads_column_exists(cursor):
        sql_update = "UPDATE conversion SET telechargements = COALESCE(telechargements, 0) + 1 WHERE id = %s"
        cursor.execute(sql_update, (id_conversion,))
        conn.commit()

    cursor.close()
    conn.close()
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))


@app.route("/history")
def history():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Normaliser les statuts NULL en base pour cet utilisateur afin
    # d'éviter l'affichage systématique "Inconnu".
    try:
        # Si une conversion a un fichier de sortie mais pas de statut, on considère "terminee".
        sql_update_done = """
            UPDATE conversion c
            JOIN fichier f ON c.id_fichier = f.id
            SET c.statut = %s
            WHERE f.id_utilisateur = %s
              AND c.statut IS NULL
              AND c.chemin_fichier_converti IS NOT NULL
        """
        cursor.execute(sql_update_done, ("terminee", user_id))
        conn.commit()

    except Exception:
        # Ne pas interrompre l'affichage en cas d'erreur de migration légère.
        conn.rollback()

    sql = """
        SELECT
            c.id AS id_conversion,
            f.nom_origin AS file_name,
            fo.nom AS source_format,
            fc.nom AS target_format,
            f.taille AS file_size,
            DATE_FORMAT(c.date_conversion, '%d/%m/%Y %H:%i') AS date_conversion,
            c.statut,
            c.chemin_fichier_converti
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        LEFT JOIN format fo ON f.id_format_origin = fo.id
        LEFT JOIN format fc ON c.id_format_cible = fc.id
        WHERE f.id_utilisateur = %s
          AND f.est_supprime = 0
          AND c.est_supprime = 0
        ORDER BY c.date_conversion DESC
    """
    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()

    history_conversions = []
    for row in rows:
        size_kb = row["file_size"] or 0
        if size_kb >= 1024:
            file_size = f"{round(size_kb / 1024, 1)} MB"
        else:
            file_size = f"{round(size_kb, 1)} KB"
        # Détecter et inférer un statut si nécessaire (valeur NULL en base)
        statut_value = row["statut"]

        if not statut_value:
            if row.get("chemin_fichier_converti"):
                statut_value = "terminee"
            else:
                statut_value = "echec"

        status_filter = _format_history_status_filter(statut_value)
        print("Statut reçu :", repr(row["statut"]))
        history_conversions.append({
            "id_conversion": row["id_conversion"],
            "file_name": row["file_name"],
            "source_format": row["source_format"] or "Inconnu",
            "target_format": row["target_format"] or "Inconnu",
            "file_size": file_size,
            "date_conversion": row["date_conversion"],
            "status_label": _format_history_status_label(statut_value),
            "status_class": f"status-{status_filter}",
            "status_filter": status_filter,
            "file_icon_class": _get_file_icon_class(
                row["target_format"] or row["source_format"]
            ),

            "file_icon_color": _get_file_icon_color(
                row["target_format"] or row["source_format"]
            ),

            "download_url": url_for("download_conversion", id_conversion=row["id_conversion"]),
            "delete_url": url_for("delete_conversion", id_conversion=row["id_conversion"]),
            "can_download": bool(row["chemin_fichier_converti"]),
        })

    cursor.close()
    conn.close()

    return render_template("history.html", history_conversions=history_conversions)


@app.route("/history/delete/<int:id_conversion>", methods=["POST"])
def delete_conversion(id_conversion):
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT c.chemin_fichier_converti, f.id_utilisateur
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE c.id = %s
          AND f.est_supprime = 0
          AND c.est_supprime = 0
    """
    cursor.execute(sql, (id_conversion,))
    conversion_data = cursor.fetchone()

    if not conversion_data or conversion_data["id_utilisateur"] != user_id:
        cursor.close()
        conn.close()
        abort(404)

    file_path = conversion_data["chemin_fichier_converti"]
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    sql_update = """
        UPDATE conversion c
        JOIN fichier f ON c.id_fichier = f.id
        SET
            c.est_supprime = 1,
            f.est_supprime = 1
        WHERE c.id = %s
    """
    cursor.execute(sql_update, (id_conversion,))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("history"))


@app.route("/profile")
def profile():

    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    _ensure_profile_photo_column(conn, cursor)

    cursor.execute("""
        SELECT id, nom, email, date_creation, photo
        FROM utilisateur
        WHERE id = %s
    """, (session["id_utilisateur"],))

    user = cursor.fetchone()

    cursor.execute("""
    SELECT COUNT(*) AS total
    FROM conversion c
    JOIN fichier f ON c.id_fichier = f.id
    WHERE f.id_utilisateur = %s;
    """,(session["id_utilisateur"],))

    total = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT SUM(taille) AS stockage
    FROM fichier
    WHERE id_utilisateur=%s
    """, (session["id_utilisateur"],))
    stockage = cursor.fetchone()["stockage"] or 0

    cursor.close()
    conn.close()

    storage_used_mb = round(stockage / 1024, 2) if stockage else 0
    profile_image_url = None
    if user and user.get("photo"):
        profile_image_url = url_for("static", filename=f"uploads/{user['photo']}")

    return render_template(
        "profile.html",
        user=user,
        total=total,
        stockage=storage_used_mb,
        profile_image_url=profile_image_url,
        profile_message=request.args.get("message"),
    )


# ===== MODIFICATION DU PROFIL =====
@app.route("/modifier_profil", methods=["GET", "POST"])
def modifier_profil():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    if request.method != "POST":
        return redirect(url_for(_profile_redirect_endpoint()))

    user_id = session["id_utilisateur"]

    # Si le formulaire envoie "prenom" (cas de profile_admin.html), on le combine avec "nom".
    # Sinon on garde le comportement d'origine (profile.html envoie juste "nom").
    prenom = request.form.get("prenom", "").strip()
    nom_field = request.form.get("nom", "").strip()
    nom = f"{prenom} {nom_field}".strip() if prenom else nom_field

    email = request.form.get("email", "").strip()
    uploaded_file = request.files.get("photo_profil")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_profile_photo_column(conn, cursor)

    if not nom or not email:
        cursor.close()
        conn.close()
        return redirect(url_for(_profile_redirect_endpoint(), message="Veuillez renseigner votre nom et votre email."))

    cursor.execute("SELECT id, photo FROM utilisateur WHERE email = %s AND id != %s", (email, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return redirect(url_for(_profile_redirect_endpoint(), message="Cet email est déjà utilisé."))

    photo_filename = None
    if uploaded_file and uploaded_file.filename:
        allowed_extensions = {".jpg", ".jpeg", ".png", ".svg"}
        extension = os.path.splitext(uploaded_file.filename)[1].lower()
        if extension not in allowed_extensions:
            cursor.close()
            conn.close()
            return redirect(url_for(_profile_redirect_endpoint(), message="Seules les images JPG, JPEG, PNG et SVG sont acceptées."))

        filename = secure_filename(uploaded_file.filename)
        unique_name = f"{uuid.uuid4().hex}{extension}"
        file_path = os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], unique_name)
        uploaded_file.save(file_path)
        photo_filename = unique_name

        cursor.execute("SELECT photo FROM utilisateur WHERE id = %s", (user_id,))
        current_user = cursor.fetchone()
        if current_user and current_user.get("photo"):
            old_photo_path = os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], current_user["photo"])
            if os.path.isfile(old_photo_path):
                os.remove(old_photo_path)

    sql = "UPDATE utilisateur SET nom = %s, email = %s"
    params = [nom, email]
    if photo_filename is not None:
        sql += ", photo = %s"
        params.append(photo_filename)
    sql += " WHERE id = %s"
    params.append(user_id)
    cursor.execute(sql, tuple(params))
    conn.commit()

    session["nom_utilisateur"] = nom

    cursor.close()
    conn.close()
    return redirect(url_for(_profile_redirect_endpoint(), message="Profil mis à jour avec succès."))


@app.route("/changer_mot_de_passe", methods=["GET", "POST"])
def changer_mot_de_passe():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    if request.method != "POST":
        return redirect(url_for(_profile_redirect_endpoint()))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        return redirect(url_for(_profile_redirect_endpoint(), message="Veuillez remplir tous les champs du mot de passe."))

    if new_password != confirm_password:
        return redirect(url_for(_profile_redirect_endpoint(), message="La confirmation du mot de passe ne correspond pas."))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT mot_de_passe FROM utilisateur WHERE id = %s", (session["id_utilisateur"],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user["mot_de_passe"], current_password):
        cursor.close()
        conn.close()
        return redirect(url_for(_profile_redirect_endpoint(), message="Le mot de passe actuel est incorrect."))

    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE utilisateur SET mot_de_passe = %s WHERE id = %s", (hashed_password, session["id_utilisateur"]))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for(_profile_redirect_endpoint(), message="Mot de passe modifié avec succès."))


# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

