import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# UUID хранятся как String(36): клиенты генерируют их сами,
# формат одинаково работает на PostgreSQL и SQLite (тесты).
def uuid_pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True,
                         default=lambda: str(uuid.uuid4()))


class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = uuid_pk()
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # привязка к аккаунту основного сайта (SSO); null — локально созданные
    external_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Board(Base):
    __tablename__ = 'boards'

    id: Mapped[str] = uuid_pk()
    owner_id: Mapped[str] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False
    )


class BoardMember(Base):
    __tablename__ = 'board_members'

    board_id: Mapped[str] = mapped_column(
        ForeignKey('boards.id', ondelete='CASCADE'), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # 'editor' | 'viewer'

    __table_args__ = (UniqueConstraint('board_id', 'user_id'),)


class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[str] = uuid_pk()  # генерирует клиент
    board_id: Mapped[str] = mapped_column(
        ForeignKey('boards.id', ondelete='CASCADE'), nullable=False
    )
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=200)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    text: Mapped[str] = mapped_column(Text, nullable=False, default='')
    color: Mapped[str] = mapped_column(String(9), nullable=False, default='#FFF3B1')
    updated_by: Mapped[str] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False
    )


class Zone(Base):
    """Зона-подложка на доске: фон для группировки тикетов, с заголовком."""

    __tablename__ = 'zones'

    id: Mapped[str] = uuid_pk()  # генерирует клиент
    board_id: Mapped[str] = mapped_column(
        ForeignKey('boards.id', ondelete='CASCADE'), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default='')
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=420)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=280)
    updated_by: Mapped[str] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False
    )


class Edge(Base):
    __tablename__ = 'edges'

    id: Mapped[str] = uuid_pk()  # генерирует клиент
    board_id: Mapped[str] = mapped_column(
        ForeignKey('boards.id', ondelete='CASCADE'), nullable=False
    )
    source_ticket_id: Mapped[str] = mapped_column(
        ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False
    )
    target_ticket_id: Mapped[str] = mapped_column(
        ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False
    )
