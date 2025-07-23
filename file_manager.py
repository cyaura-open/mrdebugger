import os
from typing import List, Dict


class FileManager:
    """Handles all file I/O operations and codebase scanning"""
    
    @staticmethod
    def read_file(filename: str) -> str:
        """Read a file and return its contents"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filename}")
        except UnicodeDecodeError:
            # Try reading as binary and decoding with error handling
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    print(f"Warning: {filename} contains non-UTF-8 characters, some may be lost")
                    return content
            except Exception as e:
                raise Exception(f"Error reading file {filename}: {e}")
        except Exception as e:
            raise Exception(f"Error reading file {filename}: {e}")
    
    @staticmethod
    def write_file(filename: str, content: str) -> None:
        """Write content to a file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise Exception(f"Error writing file {filename}: {e}")
    
    @staticmethod
    def scan_codebase_folder(codebase_folder: str, supported_extensions: List[str]) -> List[str]:
        """Scan codebase folder for supported files"""
        if not os.path.exists(codebase_folder):
            raise FileNotFoundError(f"Codebase folder not found: {codebase_folder}")
        
        if not os.path.isdir(codebase_folder):
            raise Exception(f"Codebase path is not a directory: {codebase_folder}")
        
        found_files = []
        
        # Walk through all subdirectories
        for root, dirs, files in os.walk(codebase_folder):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                      ['node_modules', '__pycache__', 'build', 'dist', 'target', 'bin', 'obj']]
            
            for file in files:
                # Check if file has supported extension
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in supported_extensions:
                    full_path = os.path.join(root, file)
                    # Use relative path from codebase folder
                    relative_path = os.path.relpath(full_path, codebase_folder)
                    found_files.append(os.path.join(codebase_folder, relative_path))
        
        # Sort for consistent ordering
        found_files.sort()
        return found_files
    
    @staticmethod
    def read_codebase_folder(codebase_folder: str, supported_extensions: List[str]) -> str:
        """Read entire codebase folder and combine into structured text"""
        file_paths = FileManager.scan_codebase_folder(codebase_folder, supported_extensions)
        
        if not file_paths:
            print(f"Warning: No supported files found in {codebase_folder}")
            return f"# No supported files found in {codebase_folder}\n"
        
        print(f"Found {len(file_paths)} files in codebase:")
        for file_path in file_paths:
            file_size = os.path.getsize(file_path)
            print(f"   - {file_path} ({file_size:,} bytes)")
        
        combined_content = f"# CODEBASE ANALYSIS - {len(file_paths)} files from {codebase_folder}\n\n"
        
        for file_path in file_paths:
            try:
                content = FileManager.read_file(file_path)
                relative_path = os.path.relpath(file_path, codebase_folder)
                
                combined_content += f"# ===== {relative_path} =====\n"
                combined_content += f"# File: {file_path}\n"
                combined_content += f"# Size: {len(content):,} characters\n\n"
                combined_content += content
                combined_content += "\n\n"
                
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")
                combined_content += f"# ===== {relative_path} =====\n"
                combined_content += f"# ERROR: Could not read file - {e}\n\n"
        
        return combined_content
    
    @staticmethod
    def read_codebase_files(filenames: List[str]) -> str:
        """Read multiple specific codebase files and combine them (legacy method)"""
        combined_content = ""
        
        for filename in filenames:
            try:
                content = FileManager.read_file(filename)
                combined_content += f"\n# ===== {filename} =====\n{content}\n"
            except FileNotFoundError:
                print(f"Warning: Codebase file {filename} not found, skipping.")
                continue
        
        return combined_content
    
    @staticmethod
    def get_codebase_stats(codebase_folder: str, supported_extensions: List[str]) -> Dict:
        """Get statistics about the codebase"""
        try:
            file_paths = FileManager.scan_codebase_folder(codebase_folder, supported_extensions)
            
            stats = {
                'total_files': len(file_paths),
                'total_size_bytes': 0,
                'total_size_chars': 0,
                'file_types': {},
                'largest_file': None,
                'largest_size': 0
            }
            
            for file_path in file_paths:
                # File size in bytes
                file_size_bytes = os.path.getsize(file_path)
                stats['total_size_bytes'] += file_size_bytes
                
                # File size in characters
                try:
                    content = FileManager.read_file(file_path)
                    char_count = len(content)
                    stats['total_size_chars'] += char_count
                    
                    if char_count > stats['largest_size']:
                        stats['largest_size'] = char_count
                        stats['largest_file'] = file_path
                        
                except Exception:
                    pass  # Skip files we can't read
                
                # File type counting
                file_ext = os.path.splitext(file_path)[1].lower()
                stats['file_types'][file_ext] = stats['file_types'].get(file_ext, 0) + 1
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def file_exists(filename: str) -> bool:
        """Check if a file exists"""
        return os.path.isfile(filename)
    
    @staticmethod
    def folder_exists(folder_path: str) -> bool:
        """Check if a folder exists"""
        return os.path.isdir(folder_path)
    
    @staticmethod
    def ensure_file_exists(filename: str, default_content: str = "") -> None:
        """Create file if it doesn't exist"""
        if not FileManager.file_exists(filename):
            FileManager.write_file(filename, default_content)