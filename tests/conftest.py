
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app, db


@pytest.fixture()
def test_app():
    app.config.update(
        TESTING=True,
    )

    with app.app_context():
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(test_app):
    return test_app.test_client()