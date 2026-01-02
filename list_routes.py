from website_server import app

print("Registered Routes:")
print("=" * 60)
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint:30s} {str(rule.methods):30s} {rule.rule}")
