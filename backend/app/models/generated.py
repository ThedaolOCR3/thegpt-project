from typing import Any, Optional
import datetime
import uuid

from pgvector.sqlalchemy.vector import VECTOR
from sqlalchemy import Boolean, DateTime, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class EmailVerifications(Base):
    __tablename__ = 'email_verifications'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='email_verifications_pkey'),
        Index('idx_email_verifications_email', 'email'),
        {'schema': 'app_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('email', name='users_email_key'),
        {'schema': 'app_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    auth_provider: Mapped[Optional[str]] = mapped_column(String(30), server_default=text("'local'::character varying"))
    is_email_verified: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    conversations: Mapped[list['Conversations']] = relationship('Conversations', back_populates='user')
    admin_documents: Mapped[list['AdminDocuments']] = relationship('AdminDocuments', back_populates='users')


class Conversations(Base):
    __tablename__ = 'conversations'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['app_db.users.id'], ondelete='CASCADE', name='conversations_user_id_fkey'),
        PrimaryKeyConstraint('id', name='conversations_pkey'),
        Index('idx_conversations_category', 'category'),
        Index('idx_conversations_user_id', 'user_id'),
        {'schema': 'app_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    is_title_custom: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    user: Mapped['Users'] = relationship('Users', back_populates='conversations')
    messages: Mapped[list['Messages']] = relationship('Messages', back_populates='conversation')


class AdminDocuments(Base):
    __tablename__ = 'admin_documents'
    __table_args__ = (
        ForeignKeyConstraint(['uploaded_by'], ['app_db.users.id'], name='admin_documents_uploaded_by_fkey'),
        PrimaryKeyConstraint('id', name='admin_documents_pkey'),
        {'schema': 'vector_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    original_file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    ocr_extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    ocr_status: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'pending'::character varying"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='admin_documents')
    document_chunks: Mapped[list['DocumentChunks']] = relationship('DocumentChunks', back_populates='document')


class Messages(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        ForeignKeyConstraint(['conversation_id'], ['app_db.conversations.id'], ondelete='CASCADE', name='messages_conversation_id_fkey'),
        PrimaryKeyConstraint('id', name='messages_pkey'),
        Index('idx_messages_conversation_id', 'conversation_id'),
        {'schema': 'app_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    conversation: Mapped['Conversations'] = relationship('Conversations', back_populates='messages')
    message_attachments: Mapped[list['MessageAttachments']] = relationship('MessageAttachments', back_populates='message')


class DocumentChunks(Base):
    __tablename__ = 'document_chunks'
    __table_args__ = (
        ForeignKeyConstraint(['document_id'], ['vector_db.admin_documents.id'], ondelete='CASCADE', name='document_chunks_document_id_fkey'),
        PrimaryKeyConstraint('id', name='document_chunks_pkey'),
        Index('idx_document_chunks_document_id', 'document_id'),
        {'schema': 'vector_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR(1024))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    document: Mapped['AdminDocuments'] = relationship('AdminDocuments', back_populates='document_chunks')
    chunk_embeddings: Mapped[list['ChunkEmbeddings']] = relationship('ChunkEmbeddings', back_populates='chunk')


class ChunkEmbeddings(Base):
    """RAG(팀원이 임베딩 모델을 정하는 중)용 정규화된 임베딩 저장 테이블. 청크 하나당
    provider(모델)별로 행이 하나씩 생긴다 — 모델을 몇 개/어떤 걸 쓰든 스키마 변경이
    필요 없다. 기존 document_chunks.embedding(Gemini 파이프라인용)과는 별개다."""

    __tablename__ = 'chunk_embeddings'
    __table_args__ = (
        ForeignKeyConstraint(['chunk_id'], ['vector_db.document_chunks.id'], ondelete='CASCADE', name='chunk_embeddings_chunk_id_fkey'),
        PrimaryKeyConstraint('id', name='chunk_embeddings_pkey'),
        UniqueConstraint('chunk_id', 'provider_name', name='chunk_embeddings_chunk_id_provider_name_key'),
        Index('idx_chunk_embeddings_chunk_id', 'chunk_id'),
        Index('idx_chunk_embeddings_provider_name', 'provider_name'),
        {'schema': 'vector_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    # 컬럼 폭은 2048로 넓게 잡고(마이그레이션 참고) 실제로 쓰는 길이는 dimension에 별도
    # 기록한다 — 짧은 벡터는 0으로 패딩해서 저장한다(코사인 유사도에 영향 없음).
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR(2048))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    chunk: Mapped['DocumentChunks'] = relationship('DocumentChunks', back_populates='chunk_embeddings')


class MessageAttachments(Base):
    __tablename__ = 'message_attachments'
    __table_args__ = (
        ForeignKeyConstraint(['message_id'], ['app_db.messages.id'], ondelete='CASCADE', name='message_attachments_message_id_fkey'),
        PrimaryKeyConstraint('id', name='message_attachments_pkey'),
        Index('idx_message_attachments_message_id', 'message_id'),
        {'schema': 'app_db'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    message_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(50))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    message: Mapped['Messages'] = relationship('Messages', back_populates='message_attachments')
