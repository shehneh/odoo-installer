from website_server import app

with app.test_client() as c:
    print("Testing /api/health:")
    r = c.get('/api/health')
    print(f"Status: {r.status_code}")
    print(f"Response: {r.get_json()}")
    
    print("\nTesting /api/list-customers:")
    r = c.get('/api/list-customers')
    print(f"Status: {r.status_code}")
    print(f"Response: {r.get_json()}")
