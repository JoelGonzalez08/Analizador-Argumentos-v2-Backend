"""
Database Migration Script - Add paragraph_analyses table

This script adds the new paragraph_analyses table to the existing database
without affecting existing data.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine
from app.models.models import ParagraphAnalysisDB

def migrate():
    """Run database migration"""
    print("🔄 Starting database migration...")
    
    try:
        # Create only the paragraph_analyses table if it doesn't exist
        ParagraphAnalysisDB.__table__.create(engine, checkfirst=True)
        print("✅ Table 'paragraph_analyses' created successfully")
        print("✅ Migration completed!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
