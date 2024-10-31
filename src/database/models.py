from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Table, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

file_tags = Table(
    'file_tags', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('tag_id', Integer, ForeignKey('tags.id')),
    Index('idx_file_tags_file_id', 'file_id'),
    Index('idx_file_tags_tag_id', 'tag_id')
)

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    original_name = Column(String, nullable=False)
    new_name = Column(String)
    original_path = Column(String, nullable=False)
    content_hash = Column(String)
    quick_hash = Column(String)
    first_seen = Column(
        DateTime, default=lambda: datetime.now(datetime.timezone.utc)
    )
    last_modified = Column(
        DateTime, default=lambda: datetime.now(datetime.timezone.utc)
    )
    status = Column(String)
    tags = relationship('Tag', secondary=file_tags, back_populates='files')

    __table_args__ = (
        Index('idx_files_content_hash', 'content_hash'),
        Index('idx_files_quick_hash', 'quick_hash'),
        Index('idx_files_status', 'status'),
        Index('idx_files_original_name', 'original_name'),
    )

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String)
    files = relationship('File', secondary=file_tags, back_populates='tags')

    __table_args__ = (
        Index('idx_tags_name', 'name'),
        Index('idx_tags_category', 'category'),
    )

class ProcessedArchive(Base):
    __tablename__ = 'processed_archives'
    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    content_hash = Column(String)
    file_list = Column(String)
    analysis_data = Column(String)
    processed_date = Column(
        DateTime, default=lambda: datetime.now(datetime.timezone.utc)
    )

    __table_args__ = (
        Index('idx_processed_archives_content_hash', 'content_hash'),
        Index('idx_processed_archives_file_path', 'file_path'),
        Index('idx_processed_archives_date', 'processed_date'),
    )
