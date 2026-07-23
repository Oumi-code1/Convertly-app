from flask import Flask, render_template , request , redirect, url_for
from connexion import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)

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

        #Verification
        if utilisateur and check_password_hash(utilisateur["mot_de_passe"],password):
            print("connexion réussie !")
            print("Bienvenue", utilisateur["nom"])
        
            cursor.close()
            conn.close()

            return "Connexion réussie !"
        else:

            cursor.close()
            conn.close()

            return "Email ou mot de passe incorrect."

    return render_template("login.html")

# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

