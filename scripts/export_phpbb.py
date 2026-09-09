#!/usr/bin/env python3
"""
Export phpBB 3.0.x data to JSON format.

Usage:
    python export_phpbb.py --source ../Input --output ./data/export --verbose
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
import pymysql
from dotenv import load_dotenv
from tqdm import tqdm

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load .env if exists
load_dotenv()


class PhpBBExporter:
    """Export phpBB 3.0.x forum data."""
    
    def __init__(self, source_path, output_path, verbose=False, debug=False):
        self.source_path = Path(source_path)
        self.output_path = Path(output_path)
        self.verbose = verbose
        self.debug = debug
        
        if verbose or debug:
            logger.setLevel(logging.DEBUG)
        
        # Create output directories
        self.output_path.mkdir(parents=True, exist_ok=True)
        (self.output_path / 'files').mkdir(parents=True, exist_ok=True)
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        file_handler = logging.FileHandler('data/logs/export_phpbb.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        self.db_connection = None
        self.config = None
    
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
        except pymysql.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def export_users(self):
        """Export all users from phpBB."""
        logger.info("Exporting users...")
        
        cursor = self.db_connection.cursor()
        table = f"{self.config['prefix']}users"
        
        cursor.execute(f"SELECT * FROM {table} WHERE user_id > 1 ORDER BY user_id")
        users = cursor.fetchall()
        
        users_data = []
        for user in users:
            users_data.append({
                'user_id': user.get('user_id'),
                'username': user.get('username'),
                'user_email': user.get('user_email'),
                'user_joined': user.get('user_regdate'),
                'user_avatar': user.get('user_avatar'),
                'user_posts': user.get('user_posts'),
                'user_website': user.get('user_website'),
                'user_from': user.get('user_from'),
                'user_birthday': user.get('user_birthday'),
                'user_lastvisit': user.get('user_lastvisit'),
            })
        
        output_file = self.output_path / 'users.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(users_data)} users to {output_file}")
        return users_data
    
    def export_categories(self):
        """Export all forums/categories from phpBB."""
        logger.info("Exporting categories...")
        
        cursor = self.db_connection.cursor()
        table = f"{self.config['prefix']}forums"
        
        cursor.execute(f"""
            SELECT * FROM {table}
            WHERE parent_id != 0 OR parent_id = 0
            ORDER BY left_id
        """)
        forums = cursor.fetchall()
        
        categories = []
        for forum in forums:
            categories.append({
                'forum_id': forum.get('forum_id'),
                'forum_name': forum.get('forum_name'),
                'forum_desc': forum.get('forum_desc'),
                'parent_id': forum.get('parent_id'),
                'forum_topics': forum.get('forum_topics'),
                'forum_posts': forum.get('forum_posts'),
                'forum_type': forum.get('forum_type'),
            })
        
        output_file = self.output_path / 'categories.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, default=str)
        
        logger.info(f"Exported {len(categories)} categories to {output_file}")
        return categories
    
    def export_topics(self):
        """Export all topics from phpBB."""
        logger.info("Exporting topics...")
        
        cursor = self.db_connection.cursor()
        table = f"{self.config['prefix']}topics"
        
        cursor.execute(f"""
            SELECT * FROM {table}
            ORDER BY topic_id
        """)
        topics = cursor.fetchall()
        
        topics_data = []
        for topic in topics:
            topics_data.append({
                'topic_id': topic.get('topic_id'),
                'forum_id': topic.get('forum_id'),
                'topic_title': topic.get('topic_title'),
                'topic_poster': topic.get('topic_poster'),
                'topic_time': topic.get('topic_time'),
                'topic_views': topic.get('topic_views'),
                'topic_posts': topic.get('topic_posts_approved'),
                'topic_status': topic.get('topic_status'),
                'topic_type': topic.get('topic_type'),
                'topic_last_post_id': topic.get('topic_last_post_id'),
            })
        
        output_file = self.output_path / 'topics.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(topics_data)} topics to {output_file}")
        return topics_data
    
    def export_posts(self):
        """Export all posts from phpBB."""
        logger.info("Exporting posts...")
        
        cursor = self.db_connection.cursor()
        table = f"{self.config['prefix']}posts"
        
        cursor.execute(f"""
            SELECT * FROM {table}
            ORDER BY post_id
        """)
        posts = cursor.fetchall()
        
        posts_data = []
        for post in posts:
            posts_data.append({
                'post_id': post.get('post_id'),
                'topic_id': post.get('topic_id'),
                'forum_id': post.get('forum_id'),
                'poster_id': post.get('poster_id'),
                'post_time': post.get('post_time'),
                'post_text': post.get('post_text'),
                'post_subject': post.get('post_subject'),
                'post_edit_time': post.get('post_edit_time'),
                'post_edit_reason': post.get('post_edit_reason'),
                'post_edit_user': post.get('post_edit_user'),
            })
        
        output_file = self.output_path / 'posts.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(posts_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(posts_data)} posts to {output_file}")
        return posts_data
    
    def export_files(self):
        """Export uploaded files."""
        logger.info("Exporting uploaded files...")
        
        files_dir = self.source_path / 'files'
        if not files_dir.exists():
            logger.warning(f"Files directory not found: {files_dir}")
            return
        
        import shutil
        
        target_dir = self.output_path / 'files'
        files = [item for item in files_dir.rglob('*') if item.is_file()]
        progress = tqdm(files, desc="Export fichiers", unit="fichier")
        try:
            for item in progress:
                rel_path = item.relative_to(files_dir)
                progress.set_postfix_str(str(rel_path)[-50:])
                target_file = target_dir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_file)
        except Exception as e:
            logger.error(f"Error exporting files: {e}")
        finally:
            progress.close()
        logger.info(f"Exported {len(files)} files to {target_dir}")
    
    def run(self, files_only=False, db_only=False):
        """Run complete export."""
        logger.info("Starting phpBB export...")
        
        try:
            if not files_only:
                self.connect_db()
                self.export_users()
                self.export_categories()
                self.export_topics()
                self.export_posts()
                self.db_connection.close()
            
            if not db_only:
                self.export_files()
            
            logger.info("Export completed successfully!")
            return True
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Export phpBB 3.0.x forum data to JSON format'
    )
    parser.add_argument(
        '--source',
        default='../Input',
        help='Path to phpBB directory (default: ../Input)'
    )
    parser.add_argument(
        '--output',
        default='./data/export',
        help='Output directory for exported data (default: ./data/export)'
    )
    parser.add_argument(
        '--db-only',
        action='store_true',
        help='Export database only, skip files'
    )
    parser.add_argument(
        '--files-only',
        action='store_true',
        help='Export files only, skip database'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging with stack traces'
    )
    
    args = parser.parse_args()
    
    exporter = PhpBBExporter(
        args.source,
        args.output,
        verbose=args.verbose,
        debug=args.debug
    )
    
    success = exporter.run(
        files_only=args.files_only,
        db_only=args.db_only
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
