#!/usr/bin/env python3
"""
Detect phpBB version automatically.

Usage:
    python detect_version.py --source ../Input --output config/version.json --verbose
"""

import os
import sys
import json
import argparse
import logging
import re
from pathlib import Path
import pymysql
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class PhpBBVersionDetector:
    """Detect phpBB version and configuration."""
    
    # Version patterns
    VERSION_PATTERNS = {
        r'\$this->version\s*=\s*["\']([0-9.]+)': 'version.php method 1',
        r'\$this->version_update_from\s*=\s*["\']([0-9.]+)': 'version.php method 2',
        r'define\(["\']PHPBB_VERSION["\'],\s*["\']([0-9.]+)': 'constants.php',
    }
    
    # Column mappings per version
    COLUMN_MAPPINGS = {
        '2.0': {
            'user_table': 'users',
            'post_column': 'post_text',
            'post_approved_column': None,
            'topic_table': 'topics',
            'forum_table': 'forums',
            'has_post_approved': False,
            'encoding': 'utf8',
        },
        '3.0': {
            'user_table': 'users',
            'post_column': 'post_text',
            'post_approved_column': 'post_approved',
            'topic_table': 'topics',
            'forum_table': 'forums',
            'has_post_approved': True,
            'encoding': 'utf8mb4',
        },
        '3.1': {
            'user_table': 'users',
            'post_column': 'post_text',
            'post_approved_column': 'post_approved',
            'topic_table': 'topics',
            'forum_table': 'forums',
            'has_post_approved': True,
            'encoding': 'utf8mb4',
        },
        '3.2': {
            'user_table': 'users',
            'post_column': 'post_text',
            'post_approved_column': 'post_approved',
            'topic_table': 'topics',
            'forum_table': 'forums',
            'has_post_approved': True,
            'encoding': 'utf8mb4',
        },
    }
    
    def __init__(self, source_path, verbose=False):
        self.source_path = Path(source_path)
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.version = None
        self.config = {}
        self.db_connection = None
    
    def detect_from_file(self):
        """Detect version from phpBB files."""
        logger.info("Detecting version from files...")
        
        # Try version.php first
        version_file = self.source_path / 'includes' / 'version.php'
        if version_file.exists():
            try:
                with open(version_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    for pattern, method in self.VERSION_PATTERNS.items():
                        match = re.search(pattern, content)
                        if match:
                            self.version = match.group(1)
                            logger.info(f"✓ Found version {self.version} via {method}")
                            return True
            except Exception as e:
                logger.warning(f"Error reading version.php: {e}")
        
        # Try README
        readme_file = self.source_path / 'README.txt'
        if readme_file.exists():
            try:
                with open(readme_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f.readlines()[:20]:
                        if 'phpbb' in line.lower() and 'version' in line.lower():
                            match = re.search(r'([0-9]+\.[0-9]+\.[0-9]+)', line)
                            if match:
                                self.version = match.group(1)
                                logger.info(f"✓ Found version {self.version} via README.txt")
                                return True
            except Exception as e:
                logger.warning(f"Error reading README.txt: {e}")
        
        logger.warning("Could not detect version from files")
        return False
    
    def load_phpbb_config(self):
        """Load phpBB configuration from config.php."""
        config_file = self.source_path / 'config.php'
        
        if not config_file.exists():
            raise FileNotFoundError(f"config.php not found at {config_file}")
        
        logger.info(f"Loading config from {config_file}")
        
        self.config = {}
        with open(config_file, 'r') as f:
            for line in f:
                if "$dbhost" in line:
                    self.config['host'] = self._extract_value(line)
                elif "$dbname" in line:
                    self.config['database'] = self._extract_value(line)
                elif "$dbuser" in line:
                    self.config['user'] = self._extract_value(line)
                elif "$dbpasswd" in line:
                    self.config['password'] = self._extract_value(line)
                elif "$table_prefix" in line:
                    self.config['prefix'] = self._extract_value(line)
        
        if not all(k in self.config for k in ['host', 'database', 'user', 'password', 'prefix']):
            raise ValueError("Incomplete phpBB config")
        
        logger.info(f"Config loaded: {self.config['host']}/{self.config['database']}")
        return self.config
    
    @staticmethod
    def _extract_value(line):
        """Extract value from phpBB config line."""
        try:
            return line.split("'")[1]
        except IndexError:
            return line.split('"')[1]
    
    def connect_db(self):
        """Connect to phpBB database."""
        if not self.config:
            self.load_phpbb_config()
        
        try:
            self.db_connection = pymysql.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Database connection established")
            return True
        except pymysql.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def detect_from_db(self):
        """Detect version from database structure."""
        logger.info("Detecting version from database...")
        
        if not self.connect_db():
            logger.warning("Could not connect to database")
            return False
        
        try:
            cursor = self.db_connection.cursor()
            
            # Check for version table
            table = f"{self.config['prefix']}config"
            cursor.execute(f"SELECT config_value FROM {table} WHERE config_name = 'dbms_version' LIMIT 1")
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Database version: {result.get('config_value')}")
            
            # Check table structures
            cursor.execute(f"DESCRIBE {self.config['prefix']}posts")
            columns = [row['Field'] for row in cursor.fetchall()]
            
            has_post_approved = 'post_approved' in columns
            
            # Infer version from features
            if has_post_approved:
                self.version = '3.0'  # 3.0.x, 3.1.x, 3.2.x all have this
                logger.info("✓ Detected phpBB 3.x (has post_approved column)")
            else:
                self.version = '2.0'
                logger.info("✓ Detected phpBB 2.0.x (no post_approved column)")
            
            return True
        
        except Exception as e:
            logger.error(f"Error detecting from database: {e}")
            return False
        
        finally:
            if self.db_connection:
                self.db_connection.close()
    
    def get_column_mapping(self):
        """Get column mapping for detected version."""
        if not self.version:
            return None
        
        # Get major.minor version
        version_parts = self.version.split('.')
        major_minor = f"{version_parts[0]}.{version_parts[1]}"
        
        if major_minor in self.COLUMN_MAPPINGS:
            return self.COLUMN_MAPPINGS[major_minor]
        elif version_parts[0] == '3':
            # Default to 3.0 if not found
            return self.COLUMN_MAPPINGS['3.0']
        else:
            return self.COLUMN_MAPPINGS.get('2.0')
    
    def save_config(self, output_file):
        """Save detected configuration to JSON."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            'detected_version': self.version,
            'detection_method': 'file and database',
            'php_version_min': '.'.join(self.version.split('.')[:2]) + '.0',
            'php_version_max': '.'.join(self.version.split('.')[:2]) + '.99',
            'features': self.get_column_mapping() or {},
            'database_config': {
                'host': self.config.get('host'),
                'database': self.config.get('database'),
                'prefix': self.config.get('prefix'),
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration saved to {output_file}")
        return config
    
    def detect(self):
        """Run complete detection."""
        logger.info("Starting phpBB version detection...")
        
        # Try file-based detection first
        if self.detect_from_file():
            # Try to load config
            try:
                self.load_phpbb_config()
            except:
                logger.warning("Could not load database config")
                pass
            return True
        
        # Try database detection
        if self.detect_from_db():
            return True
        
        logger.error("Could not detect phpBB version")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Detect phpBB version and generate configuration'
    )
    parser.add_argument(
        '--source',
        default='../Input',
        help='Path to phpBB directory (default: ../Input)'
    )
    parser.add_argument(
        '--output',
        default='config/version.json',
        help='Output configuration file (default: config/version.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    detector = PhpBBVersionDetector(args.source, verbose=args.verbose)
    
    if detector.detect():
        config = detector.save_config(args.output)
        print(f"\n✓ phpBB version detected: {config['detected_version']}")
        print(f"✓ Configuration saved to: {args.output}")
        sys.exit(0)
    else:
        print(f"\n✗ Could not detect phpBB version")
        sys.exit(1)


if __name__ == '__main__':
    main()
