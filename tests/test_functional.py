def test_home_page(test_client):
    """
    GIVEN a Flask application
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"Expense Tracker" in response.data

def test_login_logout(test_client, init_database):
    """
    GIVEN a registered user
    WHEN we try to login and logout
    THEN check that it works
    """
    # 1. Einloggen
    response = test_client.post('/auth/login', data=dict(
        email='test@example.com',
        password='password123'
    ), follow_redirects=True)
    
    # Prüfen ob wir eingeloggt sind (Logout Button sichtbar?)
    assert response.status_code == 200
    assert b"Logout" in response.data

    # 2. Ausloggen
    response = test_client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data

def test_create_category(test_client, init_database):
    """
    GIVEN a logged in user
    WHEN adding a category
    THEN check if it exists in the list
    """
    # Erst einloggen (jeder Test ist isoliert, session merkt sich das aber im Client)
    test_client.post('/auth/login', data=dict(
        email='test@example.com',
        password='password123'
    ), follow_redirects=True)

    # Kategorie erstellen
    response = test_client.post('/categories/new', data=dict(
        name='TestKategorie'
    ), follow_redirects=True)
    
    assert response.status_code == 200
    assert b"TestKategorie" in response.data
    assert b"Kategorie erstellt!" in response.data