import mysql.connector  
def get_db_connection() :
    try:
        connexion = mysql.connector.connect(
            host = "localhost",
            user = "root",
            password = "",
            database = "gestion_fichiers_convertis" 
        )
        return connexion
    except mysql.connector.Error as err :
        print("Erreur :", err) 
        return None 