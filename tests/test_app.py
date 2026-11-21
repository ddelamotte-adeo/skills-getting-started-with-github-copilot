from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(app_module.activities))
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_root_redirects_to_index(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    activity = response.json()[activity_name]
    assert activity["description"] == "Learn strategies and compete in chess tournaments"
    assert activity["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
    assert activity["max_participants"] == 12
    assert activity["participants"] == ["michael@mergington.edu", "daniel@mergington.edu"]


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activities[activity_name]["participants"].count(email) == 1


def test_unregister_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants", params={"email": email}
    )
    activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert email not in activities[activity_name]["participants"]
    assert "daniel@mergington.edu" in activities[activity_name]["participants"]


def test_unregister_rejects_absent_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "absent@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants", params={"email": email}
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/activities/Unknown Club/signup"),
        ("DELETE", "/activities/Unknown Club/participants"),
    ],
)
def test_unknown_activity_returns_not_found(client, method, path):
    # Arrange
    email = "student@mergington.edu"

    # Act
    response = client.request(method, path, params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/activities/Chess Club/signup"),
        ("DELETE", "/activities/Chess Club/participants"),
    ],
)
def test_participant_endpoints_require_email(client, method, path):
    # Arrange
    expected_location = ["query", "email"]

    # Act
    response = client.request(method, path)

    # Assert
    assert response.status_code == 422
    assert any(error["loc"] == expected_location for error in response.json()["detail"])
