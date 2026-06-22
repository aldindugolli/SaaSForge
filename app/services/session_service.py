from datetime import UTC, datetime
from uuid import uuid4

from flask import request
from flask import session as flask_session

from app.core.extensions import db
from app.core.models import UserSession
from app.services.base import NotFoundError


class SessionService:
    @staticmethod
    def _parse_user_agent(ua: str | None) -> dict:
        if not ua:
            return {"browser": None, "os": None, "device": None}
        ua_lower = ua.lower()
        browser = "Unknown"
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "Chrome"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "Safari"
        elif "edg" in ua_lower:
            browser = "Edge"
        os_name = "Unknown"
        if "windows" in ua_lower:
            os_name = "Windows"
        elif "mac" in ua_lower:
            os_name = "macOS"
        elif "linux" in ua_lower:
            os_name = "Linux"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            os_name = "iOS"
        device = "Desktop"
        if "mobile" in ua_lower or "iphone" in ua_lower or "android" in ua_lower:
            device = "Mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device = "Tablet"
        return {"browser": browser, "os": os_name, "device": device}

    @staticmethod
    def create_session(user_id: str) -> UserSession:
        flask_session.permanent = True
        session_id = flask_session.sid or str(uuid4())
        flask_session["user_session_id"] = session_id

        ua_info = SessionService._parse_user_agent(request.user_agent.string if request.user_agent else None)

        UserSession.query.filter_by(user_id=user_id).update({"is_current": False})

        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            browser=ua_info["browser"],
            os=ua_info["os"],
            device_name=ua_info["device"],
            is_current=True,
            last_activity_at=datetime.now(UTC),
        )
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def get_user_sessions(user_id: str) -> list:
        return UserSession.query.filter_by(user_id=user_id).order_by(UserSession.last_activity_at.desc()).all()

    @staticmethod
    def revoke_session(session_id: str, user_id: str) -> bool:
        session = UserSession.query.filter_by(id=session_id, user_id=user_id).first()
        if not session:
            raise NotFoundError("Session not found.")
        if session.is_current:
            return False
        db.session.delete(session)
        db.session.commit()
        return True

    @staticmethod
    def revoke_all_sessions(user_id: str, exclude_current: bool = True) -> int:
        query = UserSession.query.filter_by(user_id=user_id)
        if exclude_current:
            query = query.filter_by(is_current=False)
        count = query.delete()
        db.session.commit()
        return count

    @staticmethod
    def touch_session():
        session_id = flask_session.get("user_session_id")
        if session_id:
            session = UserSession.query.filter_by(session_id=session_id).first()
            if session:
                session.last_activity_at = datetime.now(UTC)
                db.session.commit()
