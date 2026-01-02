#!/usr/bin/env python3
"""
Script to add HTML routes to website_server.py
"""

# Read the current file
with open('/usr/src/app/website_server.py', 'r') as f:
    content = f.read()

# Check if routes already exist
if '@app.route(\'/register_tenant.html\')' in content:
    print("Routes already exist!")
    exit(0)

# Find the position to insert new routes (after health_check)
health_check_end = content.find('if __name__ == "__main__":')

if health_check_end == -1:
    print("Could not find insertion point!")
    exit(1)

# New routes to add
new_routes = """
# HTML Pages Routes
@app.route('/')
def index():
    \"\"\"صفحه اصلی\"\"\"
    return send_from_directory('website', 'index.html')

@app.route('/register_tenant.html')
def register_tenant():
    \"\"\"صفحه ثبت‌نام مشتری جدید\"\"\"
    return send_from_directory('website', 'register_tenant.html')

@app.route('/admin_panel.html')
def admin_panel():
    \"\"\"پنل مدیریت مشتریان\"\"\"
    return send_from_directory('website', 'admin_panel.html')

# Serve all static files from website folder
@app.route('/<path:filename>')
def serve_static(filename):
    \"\"\"Serve static files\"\"\"
    return send_from_directory('website', filename)

"""

# Insert new routes
new_content = content[:health_check_end] + new_routes + content[health_check_end:]

# Write back
with open('/usr/src/app/website_server.py', 'w') as f:
    f.write(new_content)

print("Routes added successfully!")
print("Please restart the application: liara restart --app odoomaster")
