# src/core/file_hasher.py
from pathlib import Path
import hashlib
import logging
from pathlib import Path
import hashlib
from typing import Optional

class FileHasher:
    @staticmethod
    def get_content_hash(file_path: Path) -> Optional[str]:
        """Calculate SHA-256 hash of file contents"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating content hash for {file_path}: {e}")
            return None

    @staticmethod
    def get_quick_hash(file_path: Path) -> Optional[str]:
        """Quick hash of first and last megabyte"""
        SAMPLE_SIZE = 1024 * 1024  # 1MB
        
        try:
            if not file_path.is_file():
                return None
                
            file_size = file_path.stat().st_size
            if file_size == 0:
                return None

            with open(file_path, 'rb') as f:
                # Read first MB
                start = f.read(SAMPLE_SIZE)
                
                # Read last MB if file is large enough
                if file_size > SAMPLE_SIZE * 2:
                    f.seek(-SAMPLE_SIZE, 2)
                    end = f.read()
                else:
                    end = b''

                return hashlib.md5(start + end).hexdigest()
        except Exception as e:
            logging.error(f"Error calculating quick hash for {file_path}: {e}")
            return None

    @staticmethod
    def are_files_identical(file1: Path, file2: Path) -> bool:
        """Compare two files using both quick and full hashes"""
        try:
            # First check quick hash
            if FileHasher.get_quick_hash(file1) != FileHasher.get_quick_hash(file2):
                return False
            
            # If quick hash matches, verify with full hash
            return FileHasher.get_content_hash(file1) == FileHasher.get_content_hash(file2)
        except Exception as e:
            logging.error(f"Error comparing files {file1} and {file2}: {e}")
            return False