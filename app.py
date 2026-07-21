from flask import Flask, render_template , request 

app = Flask(__name__)

# ===== PAGE ACCUEIL =====
@app.route("/")
def accueil():
    return render_template("acceuil.html")

@app.route("/login",methods=["GET", "POST"])
def login():
    if request.method == "POST":
        
        email = request.form["email"]
        password = request.form["password"]
        
        print(email)
        print(password)

    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")


# ===== LANCER LE SERVEUR =====
if __name__ == "__main__":
    app.run(debug=True)

