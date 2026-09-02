import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app import (
    app,
    _ensure_profile_photo_column,
    _format_history_status_filter,
    _format_history_status_label,
    _format_status_label,
    _get_conversion_type_stats,
    _get_dashboard_counts,
    _get_file_icon_class,
    _get_file_icon_color,
    _get_recent_conversions,
    _get_downloads_column_exists,
    format_date,
    format_size,
)


def test_home_route(client):
    """Teste que la page d'accueil renvoie bien une réponse HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_register_get_route(client):
    """Teste l'accès à la page d'inscription en GET."""
    response = client.get("/register")
    assert response.status_code == 200


def test_login_get_route(client):
    """Teste l'accès à la page de connexion en GET."""
    response = client.get("/login")
    assert response.status_code == 200


def test_register_post_password_mismatch(client):
    """Teste l'affichage d'une erreur quand les mots de passe ne correspondent pas."""
    response = client.post(
        "/register",
        data={
            "nom": "Test",
            "email": "test@example.com",
            "password": "abc123",
            "confirm_password": "wrong",
        },
    )
    assert response.status_code == 200
    assert b"mot de passe ne correspondent pas" in response.data


def test_login_post_invalid_credentials(client, monkeypatch):
    """Teste le message d'erreur lorsque les identifiants sont incorrects."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr("app.get_db_connection", lambda: mock_conn)

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "badpass"},
    )

    assert response.status_code == 200
    assert b"Email ou mot de passe incorrect" in response.data


def test_login_post_admin_redirects(client, monkeypatch):
    """Teste la redirection vers le tableau de bord admin après connexion réussie."""
    password_hash = generate_password_hash("secret")
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "nom": "Admin",
        "mot_de_passe": password_hash,
        "type_utilisateur": "admin",
    }
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr("app.get_db_connection", lambda: mock_conn)

    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "secret"},
    )

    assert response.status_code == 302
    assert "/dashboard_admin" in response.headers["Location"]


def test_logout_route_clears_session(client):
    """Teste que la déconnexion fonctionne et redirige vers la page de connexion."""
    with client.session_transaction() as sess:
        sess["id_utilisateur"] = 1
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Connexion" in response.data or b"login" in response.data.lower()


def test_format_helpers():
    """Teste les utilitaires de format de texte et de taille."""
    assert _format_status_label("success") == "Terminé"
    assert _format_status_label("echec") == "Échec"
    assert _format_status_label(None) == "Inconnu"

    assert _format_history_status_label("success") == "Réussi"
    assert _format_history_status_label("failed") == "Échec"

    assert _format_history_status_filter("terminee") == "success"
    assert _format_history_status_filter("en cours") == "failed"
    assert _format_history_status_filter("failed") == "failed"

    assert _get_file_icon_class("pdf").startswith("bi bi-filetype-pdf")
    assert _get_file_icon_color("docx").startswith("text-blue")

    assert format_size(0) == "0 KB"
    assert format_size(1024) == "1.00 MB"

    date_str, time_str = format_date(datetime(2024, 1, 2, 15, 30))
    assert date_str == "02/01/2024"
    assert time_str == "15:30"


def test_get_downloads_column_exists_true_and_false():
    """Teste la détection de l'existence de la colonne telechargements."""
    cursor = MagicMock()
    cursor.fetchone.return_value = {"Field": "telechargements"}
    assert _get_downloads_column_exists(cursor) is True

    cursor.fetchone.return_value = None
    assert _get_downloads_column_exists(cursor) is False


def test_get_dashboard_counts_with_and_without_downloads(monkeypatch):
    """Teste le calcul des statistiques du tableau de bord selon la présence de la colonne téléchargements."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"total": 2},  # files converted
        {"total": 5},  # downloads
        {"total": 1},  # today
    ]
    monkeypatch.setattr("app._get_downloads_column_exists", lambda cursor: True)

    stats = _get_dashboard_counts(cursor, 1)
    assert stats == {"files_converted": 2, "total_downloads": 5, "conversions_today": 1}

    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"total": 2},
        {"total": 4},
        {"total": 1},
    ]
    monkeypatch.setattr("app._get_downloads_column_exists", lambda cursor: False)

    stats = _get_dashboard_counts(cursor, 1)
    assert stats == {"files_converted": 2, "total_downloads": 0, "conversions_today": 4}


def test_get_conversion_type_stats_returns_percentages():
    """Teste le calcul des parts de marché de conversion."""
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"type_label": "PDF → DOCX", "total": 1},
        {"type_label": "PNG → JPG", "total": 3},
    ]

    stats = _get_conversion_type_stats(cursor, 1)

    assert len(stats) == 2
    assert stats[0]["percentage"] == 25
    assert stats[1]["percentage"] == 75


def test_get_recent_conversions_infers_status_and_builds_url():
    """Teste la lecture des conversions récentes et la génération de l'URL de téléchargement."""
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {
            "id_conversion": 1,
            "file_name": "doc.pdf",
            "date_conversion": "01/01/2024 12:00",
            "statut": None,
            "target_format": "DOCX",
            "chemin_fichier_converti": "/tmp/doc.docx",
        }
    ]

    with app.test_request_context():
        recent = _get_recent_conversions(cursor, 1)

    assert recent[0]["status_label"] == "Réussi"
    assert "/download/1" in recent[0]["download_url"]


def test_ensure_profile_photo_column_executes_alter_when_missing(monkeypatch):
    """Teste l'ajout de la colonne photo si elle n'existe pas dans la base."""
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()

    _ensure_profile_photo_column(conn, cursor)

    cursor.execute.assert_any_call("SHOW COLUMNS FROM utilisateur LIKE 'photo'")
    cursor.execute.assert_any_call("ALTER TABLE utilisateur ADD COLUMN photo VARCHAR(255) NULL")
    conn.commit.assert_called_once()


def test_conversion_success_route_shows_modal(client, monkeypatch):
    """Teste que la route de succès affiche bien le modal de conversion terminée."""

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr("app.get_db_connection", lambda: mock_conn)

    with client.session_transaction() as sess:
        sess["id_utilisateur"] = 1

    response = client.get("/conversion-success/42")

    assert response.status_code == 200
    assert b"Conversion termin\xc3\xa9e avec succ\xc3\xa8s !" in response.data


def test_dashboard_admin_requires_login(client):
    """Teste que l'accès à /dashboard_admin redirige vers la page de connexion sans session."""
    response = client.get("/dashboard_admin")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
