"""
Schedule Service - syncs staff data from pythonbotk13 database.
Used for staff scheduling and management.
"""
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

PYTHONBOTK13_DB_PATH = "/opt/pythonbotk13/data/bakery_bot.db"


class ScheduleService:
    """Service for managing staff schedules and syncing from pythonbotk13"""
    
    @staticmethod
    def sync_staff_from_database() -> int:
        """
        Sync staff data from pythonbotk13 database.
        Returns number of staff members synced.
        """
        try:
            conn = sqlite3.connect(PYTHONBOTK13_DB_PATH)
            cursor = conn.cursor()
            
            # Query staff data from pythonbotk13 employees table
            cursor.execute("""
                SELECT id, first_name, last_name, role, branch
                FROM employees
            """)
            
            staff_members = cursor.fetchall()
            conn.close()
            
            logger.info(f"Synced {len(staff_members)} staff members from pythonbotk13 database")
            return len(staff_members)
            
        except sqlite3.Error as e:
            logger.error(f"Error syncing from database: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error syncing staff: {e}")
            return 0
    
    @staticmethod
    def get_staff_list() -> List[Dict]:
        """
        Get list of staff members from pythonbotk13 database.
        Returns list of staff dictionaries.
        """
        try:
            conn = sqlite3.connect(PYTHONBOTK13_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, first_name, last_name, role, branch
                FROM employees
                ORDER BY first_name, last_name
            """)
            
            staff_data = []
            for row in cursor.fetchall():
                staff_data.append({
                    'id': row[0],
                    'name': f"{row[1]} {row[2]}".strip(),
                    'first_name': row[1],
                    'last_name': row[2],
                    'role': row[3],
                    'branch': row[4]
                })
            
            conn.close()
            return staff_data
            
        except Exception as e:
            logger.error(f"Error getting staff list: {e}")
            return []
    
    @staticmethod
    def get_staff_by_id(staff_id: int) -> Optional[Dict]:
        """
        Get staff member by ID.
        Returns staff dictionary or None.
        """
        try:
            conn = sqlite3.connect(PYTHONBOTK13_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, first_name, last_name, role, branch
                FROM employees
                WHERE id = ?
            """, (staff_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'name': f"{row[1]} {row[2]}".strip(),
                    'first_name': row[1],
                    'last_name': row[2],
                    'role': row[3],
                    'branch': row[4]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting staff by id: {e}")
            return None
