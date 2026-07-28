from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort
from connexion import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from werkzeug.utils import secure_filename
from conversions import perform_conversion
from datetime import datetime, timedelta

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


def _format_status_label(statut):
    """Retourne un libellé lisible pour le statut de conversion."""
    if not statut:
        return "Inconnu"

    statut = statut.strip().lower()
    return {
        "success": "Terminé",
        "terminee": "Terminé",
        "termine": "Terminé",
        "encours": "En cours",
        "error": "Échec",
        "echec": "Échec",
    }.get(statut, statut.capitalize())


def _format_history_status_label(statut):
    """Retourne le libellé affiché dans la page history."""
    if not statut:
        return "Inconnu"

    statut = statut.strip().lower()
    return {
        "success": "Réussi",
        "terminee": "Réussi",
        "termine": "Réussi",
        "encours": "En attente",
        "en cours": "En attente",
        "pending": "En attente",
        "error": "Échec",
        "echec": "Échec",
        "failed": "Échec",
    }.get(statut, statut.capitalize())


def _format_history_status_filter(statut):
    """Retourne la valeur data-status pour le filtrage de l'historique."""
    if not statut:
        return "unknown"

    statut = statut.strip().lower()
    if statut in {"success", "terminee", "termine"}:
        return "success"
    if statut in {"encours", "en cours", "pending"}:
        return "pending"
    if statut in {"error", "echec", "failed"}:
        return "failed"
    return "unknown"


def _get_file_icon_class(format_name):
    """Choisit l'icône Bootstrap Icons en fonction du type de fichier."""
    if not format_name:
        return "bi bi-file-earmark-fill file-icon"

    normalized = format_name.strip().lower()
    if normalized in {"pdf"}:
        return "bi bi-filetype-pdf file-icon file-icon-pdf"
    if normalized in {"png", "jpg", "jpeg", "gif", "bmp", "svg"}:
        return "bi bi-filetype-image file-icon file-icon-image"
    if normalized in {"doc", "docx", "txt", "odt", "rtf"}:
        return "bi bi-filetype-doc file-icon file-icon-doc"
    if normalized in {"ppt", "pptx"}:
        return "bi bi-filetype-ppt file-icon file-icon-ppt"
    if normalized in {"xls", "xlsx", "csv"}:
        return "bi bi-filetype-xls file-icon file-icon-xls"

    return "bi bi-file-earmark-fill file-icon"


def _get_dashboard_counts(cursor, user_id):
    """Récupère les statistiques générales du tableau de bord pour l'utilisateur."""
    sql_files_converted = """
        SELECT COUNT(*) AS total
        FROM conversion c
        JOIN fichier f ON c.id_fichier = f.id
        WHERE f.id_utilisateur = %s
          AND c.chemin_fichier_converti IS NOT NULL
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
        # Si la colonne telechargements n'existe pas dans la base, on affiche un total de conversions.
        sql_downloads = """
            SELECT COUNT(*) AS total
            FROM conversion c
            JOIN fichier f ON c.id_fichier = f.id
            WHERE f.id_utilisateur = %s
              AND c.chemin_fichier_converti IS NOT NULL
              AND f.est_supprime = 0
              AND c.est_supprime = 0
        """
        cursor.execute(sql_downloads, (user_id,))
        total_downloads = cursor.fetchone()["total"] or 0

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
            "target_format": row["target_format"] or "Inconnu",
            "status_filter": _format_history_status_filter(statut_value),
            "status_label": _format_history_status_label(statut_value),
            "file_icon_class": _get_file_icon_class(row["target_format"] or row["file_name"]),
            "download_url": url_for("download_conversion", id_conversion=row["id_conversion"]),
            "has_output": bool(row["chemin_fichier_converti"]),
        })

    return conversions

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
            est_actif
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
        recent_users=recent_users
    )

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CONVERTED_FOLDER"] = CONVERTED_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@app.route("/dashboard_user",methods=["GET","POST"])
def dashboard_user():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    sql_formats = "SELECT * FROM format WHERE est_actif = 1"
    cursor.execute(sql_formats)
    formats = cursor.fetchall()

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
                    except Exception as err:
                        sql_conversion = """
                        INSERT INTO conversion
                        (id_fichier, id_format_cible, date_conversion, statut, chemin_fichier_converti)
                        VALUES (%s, %s, NOW(), %s, %s)
                        """

                        cursor.execute(sql_conversion, (id_fichier, id_format_cible, "echec", None))
                        conn.commit()
                        

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
    )

@app.route("/download/<int:id_conversion>")
def download_conversion(id_conversion):
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

@app.route("/documents_user")
def documents_user():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        f.nom_origin,
        f.taille,
        f.date_creation,
        fo.nom AS format
    FROM fichier f
    JOIN format fo
    ON f.id_format_origin = fo.id
    WHERE f.id_utilisateur = %s;
    """,(session["id_utilisateur"],))

    fichiers = cursor.fetchall()
    print("Fichiers récupérés :", fichiers)

    cursor.close()
    conn.close()

    return render_template("documents_user.html", fichiers=fichiers)


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

        # Si une conversion n'a pas de fichier de sortie et pas de statut, on marque "encours" (pending).
        sql_update_pending = """
            UPDATE conversion c
            JOIN fichier f ON c.id_fichier = f.id
            SET c.statut = %s
            WHERE f.id_utilisateur = %s
              AND c.statut IS NULL
              AND c.chemin_fichier_converti IS NULL
        """
        cursor.execute(sql_update_pending, ("encours", user_id))
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
            statut_value = "terminee" if row.get("chemin_fichier_converti") else "encours"

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
            "file_icon_class": _get_file_icon_class(row["target_format"] or row["source_format"]),
            "download_url": url_for("download_conversion", id_conversion=row["id_conversion"]),
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

    sql_delete = "DELETE FROM conversion WHERE id = %s"
    cursor.execute(sql_delete, (id_conversion,))
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
        return redirect(url_for("profile"))

    user_id = session["id_utilisateur"]
    nom = request.form.get("nom", "").strip()
    email = request.form.get("email", "").strip()
    uploaded_file = request.files.get("photo_profil")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_profile_photo_column(conn, cursor)

    if not nom or not email:
        cursor.close()
        conn.close()
        return redirect(url_for("profile", message="Veuillez renseigner votre nom et votre email."))

    cursor.execute("SELECT id, photo FROM utilisateur WHERE email = %s AND id != %s", (email, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return redirect(url_for("profile", message="Cet email est déjà utilisé."))

    photo_filename = None
    if uploaded_file and uploaded_file.filename:
        allowed_extensions = {".jpg", ".jpeg", ".png"}
        extension = os.path.splitext(uploaded_file.filename)[1].lower()
        if extension not in allowed_extensions:
            cursor.close()
            conn.close()
            return redirect(url_for("profile", message="Seules les images JPG, JPEG et PNG sont acceptées."))

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
    return redirect(url_for("profile", message="Profil mis à jour avec succès."))


# ===== CHANGEMENT DE MOT DE PASSE =====
@app.route("/changer_mot_de_passe", methods=["GET", "POST"])
def changer_mot_de_passe():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    if request.method != "POST":
        return redirect(url_for("profile"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        return redirect(url_for("profile", message="Veuillez remplir tous les champs du mot de passe."))

    if new_password != confirm_password:
        return redirect(url_for("profile", message="La confirmation du mot de passe ne correspond pas."))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT mot_de_passe FROM utilisateur WHERE id = %s", (session["id_utilisateur"],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user["mot_de_passe"], current_password):
        cursor.close()
        conn.close()
        return redirect(url_for("profile", message="Le mot de passe actuel est incorrect."))

    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE utilisateur SET mot_de_passe = %s WHERE id = %s", (hashed_password, session["id_utilisateur"]))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("profile", message="Mot de passe modifié avec succès."))


# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

