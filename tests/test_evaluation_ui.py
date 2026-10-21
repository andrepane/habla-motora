"""Navigation aliases must never trigger acoustic analysis."""
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.mark.parametrize("url,module", [
    ("/", "evaluation-ui.js"),
    ("/evaluation?evaluation_id=example", "evaluation-ui.js"),
    ("/vocal", "app.js"),
    ("/?attempt_id=legacy&evaluation_id=example", "app.js"),
    ("/?standalone=1", "app.js"),
    ("/ddk", "ddk.js"),
    ("/phrase", "phrase.js"),
    ("/profile", "motor-profile-ui.js"),
])
def test_navigation_pages(url, module):
    response = TestClient(app).get(url)
    assert response.status_code == 200
    assert f'/static/{module}' in response.text
