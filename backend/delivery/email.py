import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from config import settings
from db.models import NudgeLog, Story, UserStoryState

logger = logging.getLogger(__name__)


def _count_new_high_unread(db: Session) -> tuple[int, Story | None]:
    last = db.query(NudgeLog).order_by(NudgeLog.sent_at.desc()).first()
    since = last.sent_at if last else datetime.fromtimestamp(0, tz=timezone.utc)

    stories = (
        db.query(Story)
        .outerjoin(
            UserStoryState,
            (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == "me"),
        )
        .filter(
            Story.relevance_label == "high",
            Story.processed_at >= since,
            UserStoryState.story_id.is_(None),
        )
        .order_by(Story.relevance_score.desc())
        .all()
    )
    return len(stories), (stories[0] if stories else None)


def send_nudge(db: Session) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.info("SMTP not configured — skipping nudge.")
        return

    count, top = _count_new_high_unread(db)
    if count < settings.nudge_min_stories:
        logger.info("Only %d new high stories — below threshold of %d.",
                    count, settings.nudge_min_stories)
        return

    body = (
        f"{count} new AI/ML reads in your queue.\n\n"
        f"{top.title}\n"
        f"→ {top.what_to_do}\n\n"
        f"Open dashboard: {settings.dashboard_url}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{count} new AI/ML reads in your queue"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.email_to
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.email_to, msg.as_string())
        db.add(NudgeLog(stories_count=count, top_story_id=top.id if top else None))
        db.commit()
        logger.info("Nudge sent: %d stories to %s", count, settings.email_to)
    except Exception as exc:
        logger.error("Nudge send failed: %s", exc)
