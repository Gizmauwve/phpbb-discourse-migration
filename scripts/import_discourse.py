#!/usr/bin/env python3
"""
Import converted Discourse data into a running Discourse instance.

Usage:
    python import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key YOUR_KEY --admin-email admin@example.com
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscourseImporter:
    """Import converted data into Discourse."""
    
    def __init__(self, source_path, target_url, api_key, admin_email, verbose=False):
        self.source_path = Path(source_path)
        self.target_url = target_url.rstrip('/')
        self.api_key = api_key
        self.admin_email = admin_email
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Setup logging
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler('data/logs/import_discourse.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Api-Key': api_key,
            'Api-Username': 'system',
        })
        
        self.id_mapping = {}  # Track ID mappings
    
    def check_connection(self):
        """Verify connection to Discourse."""
        logger.info(f"Checking connection to {self.target_url}")
        
        try:
            response = self.session.get(f"{self.target_url}/api/users/system.json")
            if response.status_code == 200:
                logger.info("✓ Connected to Discourse")
                return True
            else:
                logger.error(f"Connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def load_ndjson(self, filename):
        """Load NDJSON file."""
        filepath = self.source_path / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        data = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            logger.info(f"Loaded {len(data)} items from {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
        
        return data
    
    def create_user(self, user):
        """Create a user in Discourse."""
        payload = {
            'name': user['name'][:20],
            'email': user['email'],
            'username': user['username'],
            'password': 'temp_password_123',  # Temp, user will reset
            'user_fields': {
                '1': user.get('created_at', '')
            }
        }
        
        try:
            response = self.session.post(
                f"{self.target_url}/users.json",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                user_id = result.get('user', {}).get('id')
                self.id_mapping[user['id']] = user_id
                return user_id
            else:
                logger.warning(f"Failed to create user {user['username']}: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def create_category(self, category):
        """Create a category in Discourse."""
        payload = {
            'name': category['name'],
            'description': category.get('description', ''),
            'color': category.get('color', '0088cc'),
            'text_color': category.get('text_color', '000000'),
            'parent_category_id': category.get('parent_id', None),
        }
        
        try:
            response = self.session.post(
                f"{self.target_url}/categories.json",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                category_id = result.get('category', {}).get('id')
                self.id_mapping[category['id']] = category_id
                return category_id
            else:
                logger.warning(f"Failed to create category {category['name']}: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None
    
    def create_topic(self, topic):
        """Create a topic in Discourse."""
        category_id = self.id_mapping.get(topic['category_id'], 1)
        username = topic.get('username', 'system')
        
        payload = {
            'title': topic['title'],
            'raw': '(Original post will be added via post import)',
            'category': category_id,
            'created_at': topic.get('created_at'),
        }
        
        try:
            response = self.session.post(
                f"{self.target_url}/posts.json",
                json=payload,
                headers={'Api-Username': username}
            )
            
            if response.status_code == 200:
                result = response.json()
                topic_id = result.get('topic_id')
                self.id_mapping[topic['id']] = topic_id
                return topic_id
            else:
                logger.warning(f"Failed to create topic {topic['title']}: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            return None
    
    def create_post(self, post):
        """Create a post in Discourse."""
        topic_id = self.id_mapping.get(post['topic_id'])
        username = post.get('username', 'system')
        
        if not topic_id:
            logger.warning(f"Topic {post['topic_id']} not mapped")
            return None
        
        payload = {
            'topic_id': topic_id,
            'raw': post.get('raw', ''),
            'created_at': post.get('created_at'),
        }
        
        try:
            response = self.session.post(
                f"{self.target_url}/posts.json",
                json=payload,
                headers={'Api-Username': username}
            )
            
            if response.status_code == 200:
                result = response.json()
                post_id = result.get('id')
                return post_id
            else:
                logger.warning(f"Failed to create post in topic {topic_id}: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return None
    
    def import_users(self, batch_size=100):
        """Import all users."""
        logger.info("\n=== Importing Users ===")
        
        users = self.load_ndjson('users.ndjson')
        success_count = 0
        
        with tqdm(total=len(users), desc="Users") as pbar:
            for user in users:
                if self.create_user(user):
                    success_count += 1
                pbar.update(1)
        
        logger.info(f"Imported {success_count}/{len(users)} users")
        return success_count == len(users)
    
    def import_categories(self):
        """Import all categories."""
        logger.info("\n=== Importing Categories ===")
        
        categories = self.load_ndjson('categories.ndjson')
        success_count = 0
        
        with tqdm(total=len(categories), desc="Categories") as pbar:
            for category in categories:
                if self.create_category(category):
                    success_count += 1
                pbar.update(1)
        
        logger.info(f"Imported {success_count}/{len(categories)} categories")
        return success_count == len(categories)
    
    def import_topics(self, batch_size=100):
        """Import all topics."""
        logger.info("\n=== Importing Topics ===")
        
        topics = self.load_ndjson('topics.ndjson')
        success_count = 0
        
        with tqdm(total=len(topics), desc="Topics") as pbar:
            for topic in topics:
                if self.create_topic(topic):
                    success_count += 1
                pbar.update(1)
        
        logger.info(f"Imported {success_count}/{len(topics)} topics")
        return success_count
    
    def import_posts(self, batch_size=100):
        """Import all posts."""
        logger.info("\n=== Importing Posts ===")
        
        posts = self.load_ndjson('posts.ndjson')
        success_count = 0
        
        with tqdm(total=len(posts), desc="Posts") as pbar:
            for post in posts:
                if self.create_post(post):
                    success_count += 1
                pbar.update(1)
        
        logger.info(f"Imported {success_count}/{len(posts)} posts")
        return success_count
    
    def run(self, dry_run=False):
        """Run complete import."""
        logger.info("Starting Discourse import...")
        
        if not self.check_connection():
            logger.error("Cannot connect to Discourse")
            return False
        
        if dry_run:
            logger.info("DRY RUN MODE - No data will be imported")
            logger.info(f"Would import users from: {self.source_path}/users.ndjson")
            logger.info(f"Would import categories from: {self.source_path}/categories.ndjson")
            logger.info(f"Would import topics from: {self.source_path}/topics.ndjson")
            logger.info(f"Would import posts from: {self.source_path}/posts.ndjson")
            return True
        
        try:
            self.import_users()
            self.import_categories()
            self.import_topics()
            self.import_posts()
            
            logger.info("\n✓ Import completed successfully!")
            return True
        
        except Exception as e:
            logger.error(f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Import converted data into Discourse'
    )
    parser.add_argument(
        '--source',
        default='./data/converted',
        help='Source directory with converted data (default: ./data/converted)'
    )
    parser.add_argument(
        '--target',
        default='http://localhost:3000',
        help='Discourse URL (default: http://localhost:3000)'
    )
    parser.add_argument(
        '--api-key',
        required=True,
        help='Discourse API key (required)'
    )
    parser.add_argument(
        '--admin-email',
        default='admin@example.com',
        help='Admin email for import operations'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for imports (default: 100)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulation without actual import'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    importer = DiscourseImporter(
        args.source,
        args.target,
        args.api_key,
        args.admin_email,
        verbose=args.verbose
    )
    
    success = importer.run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
