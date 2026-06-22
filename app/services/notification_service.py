from datetime import UTC, datetime

from app.core.extensions import db
from app.core.models import Notification, NotificationType


class NotificationService:
    @staticmethod
    def create_notification(
        user_id: str,
        title: str,
        message: str | None = None,
        type: str = NotificationType.INFO.value,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def mark_as_read(notification_id: str, user_id: str) -> bool:
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()
        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        db.session.commit()
        return True

    @staticmethod
    def mark_all_as_read(user_id: str) -> bool:
        Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.now(UTC)}
        )
        db.session.commit()
        return True

    @staticmethod
    def get_user_notifications(user_id: str, limit: int = 50, unread_only: bool = False) -> list[Notification]:
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def bulk_create(notifications: list[dict]) -> list[Notification]:
        objs = []
        for n in notifications:
            notification = Notification(
                user_id=n["user_id"],
                type=n.get("type", NotificationType.INFO.value),
                title=n["title"],
                message=n.get("message"),
                link=n.get("link"),
            )
            db.session.add(notification)
            objs.append(notification)
        db.session.commit()
        return objs
