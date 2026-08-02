"""Notification inbox, preference, and delivery log APIs."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notifications import (
    NotificationDeliveryRead,
    NotificationItem,
    NotificationList,
    NotificationPreferences,
    UnreadCount,
)
from app.services.notifications import (
    delivery_logs,
    get_preferences,
    get_user_notification,
    list_user_notifications,
    mark_all_read,
    mark_read,
    masked_address,
    soft_delete,
    total_pages,
    unread_notifications_count,
    update_preferences,
)
from app.services.security import AuthContext, add_audit_log, require_permission

router = APIRouter(tags=["notifications"])


def _item(notification) -> NotificationItem:
    return NotificationItem(
        id=notification.public_id,
        type=notification.notification_type,
        category=notification.category,
        priority=notification.priority,
        title=notification.title,
        body=notification.body,
        short_body=notification.short_body,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        pilot_id=notification.pilot_id,
        action_url=notification.action_url,
        payload=notification.payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.get("/notifications", response_model=NotificationList)
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=200),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(read|unread)$"),
    category: str | None = None,
    priority: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    context: AuthContext = Depends(require_permission("notifications.read")),
    db: Session = Depends(get_db),
) -> NotificationList:
    items, total, unread_count = list_user_notifications(
        db,
        user=context.user,
        page=page,
        page_size=page_size,
        status=status_filter,
        category=category,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
    )
    return NotificationList(
        items=[_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages(total, page_size),
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count", response_model=UnreadCount)
def unread_count(
    context: AuthContext = Depends(require_permission("notifications.read")),
    db: Session = Depends(get_db),
) -> UnreadCount:
    return UnreadCount(unread_count=unread_notifications_count(db, context.user))


@router.get(
    "/notifications/delivery-logs",
    response_model=list[NotificationDeliveryRead],
)
def list_delivery_logs(
    _: AuthContext = Depends(require_permission("notifications.delivery_logs.read")),
    db: Session = Depends(get_db),
) -> list[NotificationDeliveryRead]:
    return [
        NotificationDeliveryRead(
            id=delivery.id,
            notification_id=delivery.notification_id,
            notification_public_id=delivery.notification.public_id,
            channel=delivery.channel,
            recipient_address=masked_address(delivery),
            provider=delivery.provider,
            template_code=delivery.template_code,
            status=delivery.status,
            provider_message_id=delivery.provider_message_id,
            attempt_count=delivery.attempt_count,
            sent_at=delivery.sent_at,
            delivered_at=delivery.delivered_at,
            failed_at=delivery.failed_at,
            failure_code=delivery.failure_code,
            failure_reason=delivery.failure_reason,
            created_at=delivery.created_at,
        )
        for delivery in delivery_logs(db)
    ]


@router.get("/notifications/{notification_id}", response_model=NotificationItem)
def get_notification(
    notification_id: str,
    context: AuthContext = Depends(require_permission("notifications.read")),
    db: Session = Depends(get_db),
) -> NotificationItem:
    return _item(get_user_notification(db, context.user, notification_id))


@router.patch("/notifications/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(
    notification_id: str,
    context: AuthContext = Depends(require_permission("notifications.mark_read")),
    db: Session = Depends(get_db),
) -> NotificationItem:
    notification = get_user_notification(db, context.user, notification_id)
    mark_read(notification)
    db.commit()
    db.refresh(notification)
    return _item(notification)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    context: AuthContext = Depends(require_permission("notifications.mark_read")),
    db: Session = Depends(get_db),
) -> None:
    mark_all_read(db, context.user)
    db.commit()


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    context: AuthContext = Depends(require_permission("notifications.mark_read")),
    db: Session = Depends(get_db),
) -> None:
    soft_delete(get_user_notification(db, context.user, notification_id))
    db.commit()


@router.get("/notification-preferences", response_model=NotificationPreferences)
def read_notification_preferences(
    context: AuthContext = Depends(require_permission("notifications.read")),
) -> NotificationPreferences:
    return get_preferences(context.user)


@router.put("/notification-preferences", response_model=NotificationPreferences)
def put_notification_preferences(
    payload: NotificationPreferences,
    context: AuthContext = Depends(require_permission("notifications.manage_preferences")),
    db: Session = Depends(get_db),
) -> NotificationPreferences:
    old_data = get_preferences(context.user).model_dump()
    update_preferences(db, context.user, payload)
    add_audit_log(
        db,
        action="notifications.preferences_updated",
        entity_type="UserPreference",
        entity_id=context.user.id,
        actor_user_id=context.user.id,
        old_data=old_data,
        new_data=payload.model_dump(),
        session_id=context.session.id,
    )
    db.commit()
    return payload
