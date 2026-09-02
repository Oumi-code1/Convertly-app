import pytest

import connexion


def test_get_db_connection_success(monkeypatch):
    """Teste que la connexion à la base est renvoyée lorsqu'elle réussit."""
    connection = object()
    monkeypatch.setattr(connexion.mysql.connector, "connect", lambda **kwargs: connection)

    result = connexion.get_db_connection()

    assert result is connection


def test_get_db_connection_failure(monkeypatch):
    """Teste que None est renvoyé quand la connexion échoue."""

    def raise_error(**kwargs):
        raise connexion.mysql.connector.Error("Erreur de connexion")

    monkeypatch.setattr(connexion.mysql.connector, "connect", raise_error)

    result = connexion.get_db_connection()

    assert result is None
