#!/usr/bin/env python3
"""
Local Database Manager for License System
Uses JSON file as a simple database - can be migrated to SQL later
"""
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Import blacklist function from license_manager
try:
    from license_manager import add_to_blacklist
    BLACKLIST_ENABLED = True
except ImportError:
    BLACKLIST_ENABLED = False

DB_FILE = Path(__file__).parent / '.database.json'


def _load_db() -> dict:
    """Load database from file."""
    default_db = {
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'customers': [],  # List of customers
        'licenses': [],   # List of licenses
        'activations': [], # License activations history
        'stats': {
            'total_customers': 0,
            'total_licenses': 0,
            'active_licenses': 0,
            'expired_licenses': 0,
            'total_revenue': 0
        }
    }
    try:
        if DB_FILE.exists():
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading database: {e}")
    return default_db


def _save_db(db: dict) -> bool:
    """Save database to file."""
    try:
        db['updated_at'] = datetime.now().isoformat()
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving database: {e}")
        return False


def _update_stats(db: dict):
    """Update statistics."""
    now = datetime.now()
    
    db['stats']['total_customers'] = len(db['customers'])
    db['stats']['total_licenses'] = len(db['licenses'])
    
    active = 0
    expired = 0
    for lic in db['licenses']:
        if lic.get('validity_hours') == -1:
            active += 1
        elif lic.get('status') == 'revoked':
            expired += 1
        else:
            try:
                expiry = datetime.fromisoformat(lic['expiry_iso'])
                if now < expiry:
                    active += 1
                else:
                    expired += 1
            except:
                pass
    
    db['stats']['active_licenses'] = active
    db['stats']['expired_licenses'] = expired


# ============ CUSTOMER MANAGEMENT ============

def create_customer(name: str, email: str = '', phone: str = '', 
                   company: str = '', notes: str = '') -> dict:
    """Create a new customer."""
    db = _load_db()
    
    # Generate unique customer ID
    customer_id = f"CUS-{uuid.uuid4().hex[:8].upper()}"
    
    customer = {
        'id': customer_id,
        'name': name,
        'email': email,
        'phone': phone,
        'company': company,
        'notes': notes,
        'created_at': datetime.now().isoformat(),
        'licenses': [],  # List of license IDs
        'status': 'active'  # active, suspended, deleted
    }
    
    db['customers'].append(customer)
    _update_stats(db)
    _save_db(db)
    
    return customer


def get_customer(customer_id: str) -> Optional[dict]:
    """Get customer by ID."""
    db = _load_db()
    for customer in db['customers']:
        if customer['id'] == customer_id:
            return customer
    return None


def get_customer_by_email(email: str) -> Optional[dict]:
    """Get customer by email."""
    db = _load_db()
    for customer in db['customers']:
        if customer.get('email', '').lower() == email.lower():
            return customer
    return None


def list_customers(include_deleted: bool = False) -> List[dict]:
    """List all customers with license counts."""
    db = _load_db()
    customers = db['customers'] if include_deleted else [c for c in db['customers'] if c.get('status') != 'deleted']
    
    # Add license count for each customer
    for customer in customers:
        customer['license_count'] = len(customer.get('licenses', []))
    
    return customers


def update_customer(customer_id: str, updates: dict = None, **kwargs) -> Optional[dict]:
    """Update customer details. Returns updated customer or None if not found."""
    db = _load_db()
    # Merge updates dict and kwargs
    if updates is None:
        updates = kwargs
    else:
        updates.update(kwargs)
    
    for customer in db['customers']:
        if customer['id'] == customer_id:
            for key, value in updates.items():
                if key in ['name', 'email', 'phone', 'company', 'notes', 'status']:
                    customer[key] = value
            customer['updated_at'] = datetime.now().isoformat()
            _save_db(db)
            return customer
    return None


def delete_customer(customer_id: str, hard_delete: bool = False) -> bool:
    """Delete a customer (soft delete by default)."""
    db = _load_db()
    for i, customer in enumerate(db['customers']):
        if customer['id'] == customer_id:
            if hard_delete:
                db['customers'].pop(i)
            else:
                customer['status'] = 'deleted'
                customer['deleted_at'] = datetime.now().isoformat()
            _update_stats(db)
            _save_db(db)
            return True
    return False


# ============ LICENSE MANAGEMENT ============

def create_license(hardware_id: str, validity_hours: int, 
                  customer_id: Optional[str] = None,
                  license_key: str = '', price: float = 0,
                  notes: str = '', customer_name: str = '',
                  user_id: Optional[str] = None) -> dict:
    """Create a new license record."""
    db = _load_db()
    
    # Generate unique license ID
    license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
    
    # Calculate expiry
    if validity_hours == -1:
        expiry_text = "نامحدود"
        from datetime import timedelta
        expiry_iso = (datetime.now() + timedelta(days=365*100)).isoformat()
    else:
        from datetime import timedelta
        expiry_dt = datetime.now() + timedelta(hours=validity_hours)
        expiry_iso = expiry_dt.isoformat()
        
        if validity_hours < 24:
            expiry_text = f"{validity_hours} ساعت"
        elif validity_hours < 720:
            expiry_text = f"{validity_hours // 24} روز"
        elif validity_hours < 8760:
            expiry_text = f"{validity_hours // 720} ماه"
        else:
            expiry_text = f"{validity_hours // 8760} سال"
    
    # Get customer name from database if customer_id provided and name not given
    if customer_id and not customer_name:
        customer = get_customer(customer_id)
        if customer:
            customer_name = customer.get('name', '')
    
    license_record = {
        'id': license_id,
        'hardware_id': hardware_id,
        'license_key': license_key,
        'customer_id': customer_id,
        'customer_name': customer_name,
        'user_id': user_id,
        'validity_hours': validity_hours,
        'validity_text': expiry_text,
        'expiry_iso': expiry_iso,
        'expiry_date': datetime.fromisoformat(expiry_iso).strftime('%Y-%m-%d %H:%M'),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'price': price,
        'notes': notes,
        'status': 'active',  # active, expired, revoked
        'activations': 0,
        'last_activation': None
    }
    
    db['licenses'].append(license_record)
    
    # Link to customer if provided
    if customer_id:
        for customer in db['customers']:
            if customer['id'] == customer_id:
                customer['licenses'].append(license_id)
                break
    
    # Update revenue
    db['stats']['total_revenue'] = db['stats'].get('total_revenue', 0) + price
    
    _update_stats(db)
    _save_db(db)
    
    return license_record


def get_license(license_id: str) -> Optional[dict]:
    """Get license by ID."""
    db = _load_db()
    for lic in db['licenses']:
        if lic['id'] == license_id:
            return lic
    return None


def get_license_by_key(license_key: str) -> Optional[dict]:
    """Get license by license key."""
    db = _load_db()
    for lic in db['licenses']:
        if lic.get('license_key') == license_key:
            return lic
    return None


def get_licenses_by_hardware(hardware_id: str) -> List[dict]:
    """Get all licenses for a hardware ID."""
    db = _load_db()
    return [lic for lic in db['licenses'] if lic['hardware_id'] == hardware_id]


def get_licenses_by_customer(customer_id: str) -> List[dict]:
    """Get all licenses for a customer."""
    db = _load_db()
    return [lic for lic in db['licenses'] if lic.get('customer_id') == customer_id]


def list_licenses(status: Optional[str] = None) -> List[dict]:
    """List all licenses, optionally filtered by status."""
    db = _load_db()
    licenses = db['licenses']
    
    # Update status based on expiry
    now = datetime.now()
    for lic in licenses:
        if lic.get('status') != 'revoked':
            if lic.get('validity_hours') == -1:
                lic['status'] = 'active'
            else:
                try:
                    expiry = datetime.fromisoformat(lic['expiry_iso'])
                    lic['status'] = 'active' if now < expiry else 'expired'
                except:
                    pass
    
    if status:
        return [lic for lic in licenses if lic.get('status') == status]
    return licenses


def revoke_license(license_id: str, reason: str = '') -> bool:
    """Revoke a license and add to blacklist."""
    db = _load_db()
    for lic in db['licenses']:
        if lic['id'] == license_id:
            lic['status'] = 'revoked'
            lic['revoked_at'] = datetime.now().isoformat()
            lic['revoke_reason'] = reason
            _update_stats(db)
            _save_db(db)
            
            # Add to blacklist so client-side check also fails
            if BLACKLIST_ENABLED:
                license_key = lic.get('license_key', '')
                hardware_id = lic.get('hardware_id', '')
                add_to_blacklist(license_key, hardware_id, reason)
            
            return True
    return False


def record_activation(license_id: str, hardware_id: str, ip_address: str = '') -> bool:
    """Record a license activation."""
    db = _load_db()
    
    activation = {
        'license_id': license_id,
        'hardware_id': hardware_id,
        'ip_address': ip_address,
        'activated_at': datetime.now().isoformat()
    }
    
    db['activations'].append(activation)
    
    # Update license activation count
    for lic in db['licenses']:
        if lic['id'] == license_id:
            lic['activations'] = lic.get('activations', 0) + 1
            lic['last_activation'] = datetime.now().isoformat()
            break
    
    _save_db(db)
    return True


# ============ STATISTICS ============

def get_stats() -> dict:
    """Get database statistics."""
    db = _load_db()
    _update_stats(db)
    return db['stats']


def get_dashboard_data() -> dict:
    """Get data for admin dashboard."""
    db = _load_db()
    _update_stats(db)
    
    # Recent licenses (last 10)
    recent_licenses = sorted(
        db['licenses'], 
        key=lambda x: x.get('created_at', ''), 
        reverse=True
    )[:10]
    
    # Recent customers (last 10)
    recent_customers = sorted(
        db['customers'], 
        key=lambda x: x.get('created_at', ''), 
        reverse=True
    )[:10]
    
    return {
        'stats': db['stats'],
        'recent_licenses': recent_licenses,
        'recent_customers': recent_customers,
        'total_activations': len(db['activations'])
    }


# ============ SEARCH ============

def search_customers(query: str) -> List[dict]:
    """Search customers by name, email, phone, or company."""
    db = _load_db()
    query = query.lower()
    results = []
    
    for customer in db['customers']:
        if customer.get('status') == 'deleted':
            continue
        if (query in customer.get('name', '').lower() or
            query in customer.get('email', '').lower() or
            query in customer.get('phone', '').lower() or
            query in customer.get('company', '').lower()):
            results.append(customer)
    
    return results


def search_licenses(query: str) -> List[dict]:
    """Search licenses by hardware ID, customer ID, or license ID."""
    db = _load_db()
    query = query.lower()
    results = []
    
    for lic in db['licenses']:
        if (query in lic.get('hardware_id', '').lower() or
            query in lic.get('id', '').lower() or
            query in lic.get('customer_id', '').lower() if lic.get('customer_id') else False):
            results.append(lic)
    
    return results


# ============ EXPORT/BACKUP ============

def export_database(filepath: str = None) -> str:
    """Export database to JSON file."""
    db = _load_db()
    
    if filepath is None:
        filepath = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    return filepath


def import_database(filepath: str) -> bool:
    """Import database from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            db = json.load(f)
        return _save_db(db)
    except Exception as e:
        print(f"Error importing database: {e}")
        return False


# Test/Demo
if __name__ == '__main__':
    print("=" * 60)
    print("📦 Database Manager - Test")
    print("=" * 60)
    
    # Create a test customer
    customer = create_customer(
        name="تست کاربر",
        email="test@example.com",
        phone="09121234567",
        company="شرکت آزمایشی"
    )
    print(f"\n✅ Customer created: {customer['id']}")
    
    # Create a test license
    license_rec = create_license(
        hardware_id="abc123def456",
        validity_hours=8760,  # 1 year
        customer_id=customer['id'],
        license_key="TEST_LICENSE_KEY",
        price=500000
    )
    print(f"✅ License created: {license_rec['id']}")
    
    # Get stats
    stats = get_stats()
    print(f"\n📊 Stats:")
    print(f"   Customers: {stats['total_customers']}")
    print(f"   Licenses: {stats['total_licenses']}")
    print(f"   Active: {stats['active_licenses']}")
    print(f"   Revenue: {stats['total_revenue']:,} تومان")
    
    print("\n" + "=" * 60)
