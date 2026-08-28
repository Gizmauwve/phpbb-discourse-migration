#!/usr/bin/env python3
"""
Convert phpBB exported data to Discourse NDJSON format.

Usage:
    python convert_data.py --input ./data/export --output ./data/converted --verbose
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
import hashlib
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhpBBToDiscourseConverter:
    """Convert phpBB data to Discourse format."""
    
    def __init__(self, input_path, output_path, verbose=False, mapping_file=None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.verbose = verbose
        self.mapping_file = mapping_file
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Create output directories
        self.output_path.mkdir(parents=True, exist_ok=True)
        (self.output_path / 'files').mkdir(parents=True, exist_ok=True)
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        file_handler = logging.FileHandler('data/logs/convert_data.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        self.user_mapping = {}  # phpBB user_id -> Discourse username
        self.forum_mapping = {}  # phpBB forum_id -> Discourse category_id
        self.topic_mapping = {}  # phpBB topic_id -> Discourse topic_id
    
    def load_json(self, filename):
        """Load JSON file from input directory."""
        filepath = self.input_path / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def save_ndjson(self, filename, data):
        """Save data as NDJSON (one JSON object per line)."""
        filepath = self.output_path / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, default=str) + '\n')
            logger.info(f"Saved {len(data)} items to {filename}")
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
    
    def convert_phpbb_to_markdown(self, text):
        """Convert phpBB BBCode to Discourse Markdown."""
        if not text:
            return ""
        
        # Basic conversions
        text = re.sub(r'\[b\](.*?)\[/b\]', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'\[i\](.*?)\[/i\]', r'*\1*', text, flags=re.DOTALL)
        text = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', text, flags=re.DOTALL)
        text = re.sub(r'\[s\](.*?)\[/s\]', r'~~\1~~', text, flags=re.DOTALL)
        
        # Links
        text = re.sub(r'\[url=(.*?)\](.*?)\[/url\]', r'[\2](\1)', text, flags=re.DOTALL)
        text = re.sub(r'\[url\](.*?)\[/url\]', r'[\1](\1)', text, flags=re.DOTALL)
        
        # Images
        text = re.sub(r'\[img\](.*?)\[/img\]', r'![image](\1)', text, flags=re.DOTALL)
        
        # Code
        text = re.sub(r'\[code\](.*?)\[/code\]', r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'\[code=(\w+)\](.*?)\[/code\]', r'```\1\n\2\n```', text, flags=re.DOTALL)
        
        # Quotes
        text = re.sub(r'\[quote="(.*?)"\](.*?)\[/quote\]', r'> **\1** wrote:\n> \2', text, flags=re.DOTALL)
        text = re.sub(r'\[quote\](.*?)\[/quote\]', r'> \1', text, flags=re.DOTALL)
        
        # Lists
        text = re.sub(r'\[list\]', '', text)
        text = re.sub(r'\[\*\]', '* ', text)
        text = re.sub(r'\[/list\]', '', text)
        
        return text.strip()
    
    def convert_timestamp(self, phpbb_timestamp):
        """Convert phpBB timestamp to ISO 8601."""
        if not phpbb_timestamp or phpbb_timestamp <= 0:
            return datetime.utcnow().isoformat() + 'Z'
        
        try:
            dt = datetime.utcfromtimestamp(int(phpbb_timestamp))
            return dt.isoformat() + 'Z'
        except (ValueError, OSError):
            return datetime.utcnow().isoformat() + 'Z'
    
    def convert_users(self):
        """Convert phpBB users to Discourse users."""
        logger.info("Converting users...")
        
        users = self.load_json('users.json')
        discourse_users = []
        
        for user in users:
            if not user.get('username') or user['username'] == 'Anonymous':
                continue
            
            # Map user
            user_id = user.get('user_id')
            username = user.get('username', '').strip()
            self.user_mapping[user_id] = username
            
            discourse_user = {
                'id': user_id,
                'username': username.lower()[:20],  # Discourse has max 20 chars
                'email': user.get('user_email', f'user{user_id}@forum.local'),
                'name': username,
                'created_at': self.convert_timestamp(user.get('user_joined')),
                'last_seen_at': self.convert_timestamp(user.get('user_lastvisit')),
                'active': True,
                'admin': False,  # Set later if needed
                'moderator': False,  # Set later if needed
            }
            
            discourse_users.append(discourse_user)
        
        self.save_ndjson('users.ndjson', discourse_users)
        return discourse_users
    
    def convert_categories(self):
        """Convert phpBB forums to Discourse categories."""
        logger.info("Converting categories...")
        
        categories = self.load_json('categories.json')
        discourse_categories = []
        
        # Filter only top-level categories
        root_categories = [c for c in categories if c.get('parent_id') == 0]
        
        for idx, category in enumerate(root_categories, start=1):
            forum_id = category.get('forum_id')
            self.forum_mapping[forum_id] = idx
            
            discourse_category = {
                'id': idx,
                'name': category.get('forum_name', 'Uncategorized')[:50],
                'description': self.convert_phpbb_to_markdown(category.get('forum_desc', '')),
                'color': self._generate_color(forum_id),
                'text_color': '000000',
            }
            
            discourse_categories.append(discourse_category)
        
        self.save_ndjson('categories.ndjson', discourse_categories)
        return discourse_categories
    
    def convert_topics(self):
        """Convert phpBB topics to Discourse topics."""
        logger.info("Converting topics...")
        
        topics = self.load_json('topics.json')
        discourse_topics = []
        
        for topic in topics:
            topic_id = topic.get('topic_id')
            forum_id = topic.get('forum_id')
            
            # Map to category
            category_id = self.forum_mapping.get(forum_id, 1)
            
            # Get creator
            poster_id = topic.get('topic_poster')
            username = self.user_mapping.get(poster_id, 'system')
            
            self.topic_mapping[topic_id] = topic_id
            
            discourse_topic = {
                'id': topic_id,
                'title': topic.get('topic_title', 'Untitled')[:255],
                'category_id': category_id,
                'user_id': poster_id,
                'username': username,
                'created_at': self.convert_timestamp(topic.get('topic_time')),
                'views': topic.get('topic_views', 0),
                'reply_count': topic.get('topic_posts', 0) - 1,
                'closed': topic.get('topic_status') == 1,
                'pinned': topic.get('topic_type') in [1, 2, 3],  # phpBB sticky types
            }
            
            discourse_topics.append(discourse_topic)
        
        self.save_ndjson('topics.ndjson', discourse_topics)
        return discourse_topics
    
    def convert_posts(self):
        """Convert phpBB posts to Discourse posts."""
        logger.info("Converting posts...")
        
        posts = self.load_json('posts.json')
        discourse_posts = []
        
        for post in posts:
            topic_id = post.get('topic_id')
            poster_id = post.get('poster_id')
            
            # Get username
            username = self.user_mapping.get(poster_id, 'system')
            
            discourse_post = {
                'id': post.get('post_id'),
                'topic_id': topic_id,
                'user_id': poster_id,
                'username': username,
                'raw': self.convert_phpbb_to_markdown(post.get('post_text', '')),
                'cooked': self.convert_phpbb_to_markdown(post.get('post_text', '')),
                'created_at': self.convert_timestamp(post.get('post_time')),
                'updated_at': self.convert_timestamp(post.get('post_edit_time')),
                'post_number': 1,  # Will be set by Discourse
            }
            
            # Add edit info if available
            if post.get('post_edit_reason'):
                discourse_post['edit_reason'] = post.get('post_edit_reason')
            
            discourse_posts.append(discourse_post)
        
        self.save_ndjson('posts.ndjson', discourse_posts)
        return discourse_posts
    
    def convert_files(self, skip_files=False):
        """Copy and organize uploaded files."""
        if skip_files:
            logger.info("Skipping file conversion")
            return
        
        logger.info("Converting files...")
        
        import shutil
        
        source_files = self.input_path / 'files'
        if not source_files.exists():
            logger.warning(f"Source files directory not found: {source_files}")
            return
        
        try:
            for item in source_files.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(source_files)
                    target_file = self.output_path / 'files' / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_file)
        except Exception as e:
            logger.error(f"Error converting files: {e}")
    
    @staticmethod
    def _generate_color(seed):
        """Generate a consistent color based on ID."""
        colors = [
            '0088cc', 'cc0000', '00cc00', 'cc8800', '8800cc',
            '00cccc', 'cccc00', 'ff6600', '00ff00', '0066cc',
        ]
        return colors[seed % len(colors)]
    
    def run(self, skip_files=False):
        """Run complete conversion."""
        logger.info("Starting data conversion...")
        
        try:
            self.convert_users()
            self.convert_categories()
            self.convert_topics()
            self.convert_posts()
            self.convert_files(skip_files=skip_files)
            
            logger.info("Conversion completed successfully!")
            return True
        
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert phpBB exported data to Discourse format'
    )
    parser.add_argument(
        '--input',
        default='./data/export',
        help='Input directory from phpBB export (default: ./data/export)'
    )
    parser.add_argument(
        '--output',
        default='./data/converted',
        help='Output directory for converted data (default: ./data/converted)'
    )
    parser.add_argument(
        '--mapping-file',
        help='Custom mapping file (JSON)'
    )
    parser.add_argument(
        '--skip-files',
        action='store_true',
        help='Skip file conversion'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    converter = PhpBBToDiscourseConverter(
        args.input,
        args.output,
        verbose=args.verbose,
        mapping_file=args.mapping_file
    )
    
    success = converter.run(skip_files=args.skip_files)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
