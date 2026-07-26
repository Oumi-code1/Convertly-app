from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort
from connexion import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from conversions import perform_conversion

app = Flask(__name__)
app.secret_key = "Convertly_secret_key"


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
        return "bi bi-filetype-png file-icon file-icon-png"
    if normalized in {"doc", "docx", "txt", "odt", "rtf", "ppt", "pptx"}:
        return "bi bi-file-earmark-text-fill file-icon file-icon-doc"
    if normalized in {"xls", "xlsx", "csv"}:
        return "bi bi-file-earmark-spreadsheet-fill file-icon"

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
            DATE_FORMAT(c.date_conversion, '%%d/%%m/%%Y %%H:%%i') AS date_conversion,
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
        conversions.append({
            "id_conversion": row["id_conversion"],
            "file_name": row["file_name"],
            "date_conversion": row["date_conversion"],
            "target_format": row["target_format"] or "Inconnu",
            "status_filter": _format_history_status_filter(row["statut"]),
            "status_label": _format_history_status_label(row["statut"]),
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
    return render_template("dashboard_admin.html")

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


@app.route("/history")
def history():
    if "id_utilisateur" not in session:
        return redirect(url_for("login"))

    user_id = session["id_utilisateur"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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

        status_filter = _format_history_status_filter(row["statut"])
        print("Statut reçu :", repr(row["statut"]))
        history_conversions.append({
            "id_conversion": row["id_conversion"],
            "file_name": row["file_name"],
            "source_format": row["source_format"] or "Inconnu",
            "target_format": row["target_format"] or "Inconnu",
            "file_size": file_size,
            "date_conversion": row["date_conversion"],
            "status_label": _format_history_status_label(row["statut"]),
            "status_class": f"status-{status_filter}",
            "status_filter": status_filter,
            "file_icon_class": _get_file_icon_class(row["target_format"] or row["source_format"]),
            "download_url": url_for("download_conversion", id_conversion=row["id_conversion"]),
            "can_download": bool(row["chemin_fichier_converti"]),
            "delete_url": url_for("delete_conversion", id_conversion=row["id_conversion"]),
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
    return render_template("profile.html")



# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

