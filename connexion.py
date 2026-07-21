import mysql.connector  
try:
    connexion = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "",
        database = "gestion_fichiers_convertis" 
    )
    print("connexion reussit")
except mysql.connector.Error as err :
    print("Erreur :", err) 