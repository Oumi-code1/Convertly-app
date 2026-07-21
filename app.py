from flask import Flask, render_template

app = Flask(__name__)

# ===== PAGE ACCUEIL =====
@app.route("/")
def accueil():
    return render_template("acceuil.html")

@app.route("/login")
def login():
    return render_template("login.html")


# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

