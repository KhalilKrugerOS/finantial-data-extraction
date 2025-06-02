#!/usr/bin/env python3

import os
import sqlite3
from pathlib import Path

def setup_fresh_database():
    """Setup a fresh database with all tables"""
    
    db_file = "invoice_database.db"
    
    # Remove existing database
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️ Removed existing database")
    
    # Create fresh database
    conn = sqlite3.connect(db_file)
    
    # Create invoices table
    conn.execute("""
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT,
            supplier_address TEXT,
            supplier_email TEXT,
            supplier_phone_number TEXT,
            supplier_vat_number TEXT,
            supplier_website TEXT,
            expense_date DATE,
            invoice_number TEXT,
            currency TEXT,
            total_net REAL,
            total_tax REAL,
            total_amount REAL,
            original_ocr_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    
    conn.commit()
    conn.close()
    
    print(f"✅ Fresh database created: {db_file}")

if __name__ == "__main__":
    setup_fresh_database()