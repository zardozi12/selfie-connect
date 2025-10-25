"""
Audit logging service for PhotoVault
Tracks important user actions and system events
"""

import uuid
from tortoise import Tortoise


async def audit(
    user_id: str | None, 
    action: str, 
    subject_type: str | None = None, 
    subject_id: str | None = None, 
    ip: str | None = None, 
    ua: str | None = None
):
    """
    Log an audit event to the database.
    
    Args:
        user_id: ID of the user performing the action (None for system events)
        action: Action being performed (e.g., 'upload_image', 'create_share', 'login')
        subject_type: Type of object being acted upon (e.g., 'image', 'album', 'share')
        subject_id: ID of the object being acted upon
        ip: IP address of the client
        ua: User agent string
    """
    try:
        await Tortoise.get_connection("default").execute_query(
            """
            INSERT INTO audit_events (id, user_id, action, subject_type, subject_id, ip, ua)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            [str(uuid.uuid4()), user_id, action, subject_type, subject_id, ip, ua],
        )
    except Exception as e:
        print(f"Failed to log audit event: {e}")


async def get_audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Retrieve audit logs with optional filtering.
    
    Args:
        user_id: Filter by user ID
        action: Filter by action type
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        List of audit events
    """
    try:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            query += f" AND user_id = ${param_count}"
            params.append(user_id)
        
        if action:
            param_count += 1
            query += f" AND action = ${param_count}"
            params.append(action)
        
        query += " ORDER BY created_at DESC"
        
        param_count += 1
        query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        query += f" OFFSET ${param_count}"
        params.append(offset)
        
        result = await Tortoise.get_connection("default").execute_query_dict(query, params)
        return result
        
    except Exception as e:
        print(f"Failed to retrieve audit logs: {e}")
        return []


# Common audit actions
class AuditActions:
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD_IMAGE = "upload_image"
    DELETE_IMAGE = "delete_image"
    CREATE_ALBUM = "create_album"
    DELETE_ALBUM = "delete_album"
    CREATE_SHARE = "create_share"
    REVOKE_SHARE = "revoke_share"
    VIEW_SHARE = "view_share"
    ADMIN_ACTION = "admin_action"
    SYSTEM_EVENT = "system_event"


# Common subject types
class SubjectTypes:
    USER = "user"
    IMAGE = "image"
    ALBUM = "album"
    SHARE = "share"
    SYSTEM = "system"
