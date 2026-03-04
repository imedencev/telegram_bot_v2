"""
Database models for order bot.
Extended with all required fields for production.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model - customers using the bot"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Privacy consent (152-ФЗ compliance)
    consent_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    consent_revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Order(Base):
    """Order model - customer orders"""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    
    # Order details
    order_type: Mapped[str] = mapped_column(String(20))  # 'cake' or 'dessert'
    cake_flavor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For cakes
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For desserts
    
    # Cake-specific fields
    decor_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Decoration type
    inscription: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Text on cake
    
    # Addons (paid extras)
    addon_topper: Mapped[bool] = mapped_column(Boolean, default=False)  # Топпер +200₽
    addon_sparkler: Mapped[bool] = mapped_column(Boolean, default=False)  # Свеча-фейерверк +150₽
    addon_photo_print: Mapped[bool] = mapped_column(Boolean, default=False)  # Фотопечать (free)
    
    # Pickup details
    pickup_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    issue_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Contact
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Calendar import (for orders imported from external calendar)
    calendar_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Notifications
    notify_ready_early: Mapped[bool] = mapped_column(Boolean, default=False)  # Notify when ready early
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, confirmed, completed
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CatalogCake(Base):
    """Catalog of available cakes and desserts"""
    __tablename__ = "catalog_cakes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)  # 'cake' or 'dessert'
    availability: Mapped[str] = mapped_column(String(50), default="available")
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    image_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationState(Base):
    """Conversation state - tracks where user is in order flow"""
    __tablename__ = "conversation_states"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    
    # Current state in order flow
    current_state: Mapped[str] = mapped_column(String(50))
    
    # Active order being created
    active_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Context data (JSON stored as text)
    context_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Settings(Base):
    """Settings - key-value configuration storage"""
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    
    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Admin(Base):
    """Admin - users who can manage bot and view statistics"""
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    added_by: Mapped[int] = mapped_column(Integer)  # Telegram ID of who added them
    
    # Timestamp
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
