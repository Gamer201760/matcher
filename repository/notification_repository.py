"""
NotificationRepository stub implementation.

This is a placeholder implementation that logs notifications instead
of actually sending them. In a production environment, this would
integrate with email, SMS, push notification services, etc.
"""

from uuid import UUID
import logging

# Setup logger
logger = logging.getLogger("notification_service")
logger.setLevel(logging.INFO)

# Add console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class NotificationRepository:
    """
    Stub repository for notification operations.
    
    This implementation logs notifications instead of sending them.
    Replace with actual notification service integration in production.
    """
    
    def notify_owner_of_new_request(
        self,
        group_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Notify the group owner about a new join request.
        
        In a real implementation, this would:
        - Look up the owner's contact information
        - Send an email/push notification
        - Create an in-app notification
        
        Args:
            group_id: Group that received the request
            user_id: User who sent the request
        """
        logger.info(
            f"📬 NOTIFICATION: Group {group_id} owner notified of join request from user {user_id}"
        )
        logger.debug(
            f"Would send email/push notification to group {group_id} owner "
            f"about request from user {user_id}"
        )
    
    def notify_user_of_decision(
        self,
        user_id: UUID,
        group_id: UUID,
        accepted: bool,
    ) -> None:
        """
        Notify a user about the decision on their join request.
        
        In a real implementation, this would:
        - Look up the user's contact information
        - Send an email/push notification
        - Create an in-app notification
        - Include group details if accepted
        
        Args:
            user_id: User who sent the request
            group_id: Group that made the decision
            accepted: True if request was accepted, False if rejected
        """
        status = "✅ ACCEPTED" if accepted else "❌ REJECTED"
        logger.info(
            f"📬 NOTIFICATION: User {user_id} notified that their request "
            f"to join group {group_id} was {status}"
        )
        logger.debug(
            f"Would send email/push notification to user {user_id} "
            f"about {'acceptance into' if accepted else 'rejection from'} group {group_id}"
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

