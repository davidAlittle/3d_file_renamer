# src/database/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from .models import Base, File, Tag, ProcessedArchive
from pathlib import Path
from datetime import datetime 
import json

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "file_renamer.db"
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.Session()

    def update_file_status(self, file_id: int, new_name: str, status: str):
        with self.get_session() as session:
            file = session.query(File).get(file_id)
            if file:
                file.new_name = new_name
                file.status = status
                file.last_modified = datetime.utcnow()
                session.commit()

    def get_file_by_hash(self, content_hash: str) -> File:
        with self.get_session() as session:
            return session.query(File).filter_by(content_hash=content_hash).first()

    def add_tag(self, name: str, category: str = None) -> Tag:
        with self.get_session() as session:
            tag = session.query(Tag).filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name, category=category)
                session.add(tag)
                session.commit()
            return tag

    def add_tags_to_file(self, file_id: int, tag_names: list[str]):
        with self.get_session() as session:
            file = session.query(File).get(file_id)
            if file:
                for name in tag_names:
                    tag = self.add_tag(name)
                    if tag not in file.tags:
                        file.tags.append(tag)
                session.commit()

    def record_processed_archive(self, filepath: Path, content_hash: str, 
                               file_list: list, analysis_data: dict):
        with self.get_session() as session:
            archive = ProcessedArchive(
                file_path=str(filepath),
                content_hash=content_hash,
                file_list=json.dumps(file_list),
                analysis_data=json.dumps(analysis_data)
            )
            session.add(archive)
            session.commit()
            
    def add_file(self, filepath: Path, quick_hash: str = None, content_hash: str = None) -> File: 
            with self.get_session() as session:
                file = File(
                    original_name=filepath.name,
                    original_path=str(filepath),
                    quick_hash=quick_hash,
                    content_hash=content_hash,
                    status='pending'
        )
                
            session.add(file)
            session.commit()
            return file

# Add to database.py
def ensure_indexes(self):
    """Ensure all indexes exist in the database"""
    try:
        with self.get_session() as session:
            # Get database engine connection
            connection = session.connection()
            
            # Check each index and create if missing
            for table in Base.metadata.tables.values():
                for index in table.indexes:
                    if not index.exists(connection):
                        index.create(connection)
                        logging.info(f"Created index: {index.name}")
                        
    except Exception as e:
        logging.error(f"Error ensuring indexes: {e}")
        raise

# Update __init__ method
def __init__(self, db_path: str = None):
    if db_path is None:
        db_path = Path(__file__).parent.parent / "data" / "file_renamer.db"
    self.engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(self.engine)
    self.Session = sessionmaker(bind=self.engine)
    self.ensure_indexes()  # Add this line    