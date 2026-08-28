#!/usr/bin/env python3
"""
Validate migration from phpBB to Discourse.

Usage:
    python validate_migration.py --phpbb ../Input --discourse http://localhost:3000 --verbose
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
import requests
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validate phpBB → Discourse migration."""
    
    def __init__(self, phpbb_path, discourse_url, verbose=False):
        self.phpbb_path = Path(phpbb_path)
        self.discourse_url = discourse_url.rstrip('/')
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Setup logging
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler('data/logs/validation.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        self.session = requests.Session()
        self.issues = defaultdict(list)
        self.stats = {}
    
    def load_export_json(self, filename):
        """Load exported JSON data."""
        filepath = Path('data/export') / filename
        if not filepath.exists():
            logger.warning(f"Export file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def get_discourse_data(self, endpoint):
        """Get data from Discourse API."""
        try:
            response = self.session.get(f"{self.discourse_url}/api/{endpoint}.json")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch {endpoint}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return None
    
    def validate_users(self):
        """Validate user migration."""
        logger.info("\n=== Validating Users ===")
        
        phpbb_users = self.load_export_json('users.json')
        discourse_data = self.get_discourse_data('users')
        
        if not discourse_data:
            self.issues['users'].append("Cannot fetch Discourse users")
            return False
        
        discourse_users = discourse_data.get('users', [])
        
        phpbb_count = len(phpbb_users)
        discourse_count = len(discourse_users)
        
        self.stats['users'] = {
            'phpbb': phpbb_count,
            'discourse': discourse_count,
            'match': phpbb_count == discourse_count
        }
        
        logger.info(f"phpBB users: {phpbb_count}")
        logger.info(f"Discourse users: {discourse_count}")
        
        if phpbb_count != discourse_count:
            self.issues['users'].append(
                f"User count mismatch: phpBB={phpbb_count}, Discourse={discourse_count}"
            )
        
        # Check for missing emails
        no_email = [u for u in discourse_users if not u.get('email')]
        if no_email:
            self.issues['users'].append(f"{len(no_email)} users without email")
        
        return len(self.issues['users']) == 0
    
    def validate_categories(self):
        """Validate category migration."""
        logger.info("\n=== Validating Categories ===")
        
        phpbb_categories = self.load_export_json('categories.json')
        discourse_data = self.get_discourse_data('categories')
        
        if not discourse_data:
            self.issues['categories'].append("Cannot fetch Discourse categories")
            return False
        
        discourse_categories = discourse_data.get('category_list', {}).get('categories', [])
        
        phpbb_count = len([c for c in phpbb_categories if c.get('parent_id') == 0])
        discourse_count = len(discourse_categories)
        
        self.stats['categories'] = {
            'phpbb': phpbb_count,
            'discourse': discourse_count,
            'match': phpbb_count == discourse_count
        }
        
        logger.info(f"phpBB categories: {phpbb_count}")
        logger.info(f"Discourse categories: {discourse_count}")
        
        if phpbb_count != discourse_count:
            self.issues['categories'].append(
                f"Category count mismatch: phpBB={phpbb_count}, Discourse={discourse_count}"
            )
        
        return len(self.issues['categories']) == 0
    
    def validate_topics(self):
        """Validate topic migration."""
        logger.info("\n=== Validating Topics ===")
        
        phpbb_topics = self.load_export_json('topics.json')
        discourse_data = self.get_discourse_data('latest')
        
        if not discourse_data:
            self.issues['topics'].append("Cannot fetch Discourse topics")
            return False
        
        discourse_topics = discourse_data.get('topic_list', {}).get('topics', [])
        
        phpbb_count = len(phpbb_topics)
        discourse_count = len(discourse_topics)
        
        self.stats['topics'] = {
            'phpbb': phpbb_count,
            'discourse': discourse_count,
            'match': phpbb_count <= discourse_count  # Discourse might have system topics
        }
        
        logger.info(f"phpBB topics: {phpbb_count}")
        logger.info(f"Discourse topics: {discourse_count}")
        
        if phpbb_count > discourse_count:
            self.issues['topics'].append(
                f"Topic count mismatch: phpBB={phpbb_count}, Discourse={discourse_count}"
            )
        
        return len(self.issues['topics']) == 0
    
    def validate_posts(self):
        """Validate post migration."""
        logger.info("\n=== Validating Posts ===")
        
        phpbb_posts = self.load_export_json('posts.json')
        
        phpbb_count = len(phpbb_posts)
        # Note: Difficult to get total posts from Discourse API without iterating
        
        self.stats['posts'] = {
            'phpbb': phpbb_count,
            'discourse': 'N/A (requires detailed API calls)',
        }
        
        logger.info(f"phpBB posts: {phpbb_count}")
        logger.info(f"Discourse posts: Counting...")
        
        # Check for empty posts
        empty_posts = [p for p in phpbb_posts if not p.get('post_text', '').strip()]
        if empty_posts:
            self.issues['posts'].append(f"{len(empty_posts)} empty posts in phpBB")
        
        return len(self.issues['posts']) == 0
    
    def validate_files(self):
        """Validate file migration."""
        logger.info("\n=== Validating Files ===")
        
        source_files = self.phpbb_path / 'files'
        converted_files = Path('data/converted/files')
        
        if not source_files.exists():
            logger.warning("No source files directory")
            return True
        
        if not converted_files.exists():
            self.issues['files'].append("Converted files directory not found")
            return False
        
        source_count = sum(1 for _ in source_files.rglob('*') if _.is_file())
        converted_count = sum(1 for _ in converted_files.rglob('*') if _.is_file())
        
        self.stats['files'] = {
            'source': source_count,
            'converted': converted_count,
            'match': source_count == converted_count
        }
        
        logger.info(f"Source files: {source_count}")
        logger.info(f"Converted files: {converted_count}")
        
        if source_count != converted_count:
            self.issues['files'].append(
                f"File count mismatch: source={source_count}, converted={converted_count}"
            )
        
        return len(self.issues['files']) == 0
    
    def generate_html_report(self, output_file='data/logs/validation.html'):
        """Generate HTML validation report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Migration Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #0088cc; padding-bottom: 10px; }}
        h2 {{ color: #0088cc; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
        .stat-box {{ padding: 15px; background: #f9f9f9; border-left: 4px solid #0088cc; }}
        .stat-box.pass {{ border-left-color: #008000; }}
        .stat-box.fail {{ border-left-color: #ff0000; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .issues {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .issue {{ color: #856404; margin: 10px 0; padding-left: 20px; }}
        .issue:before {{ content: "⚠ "; font-weight: bold; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; color: #155724; }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Migration Validation Report</h1>
        <p>phpBB 3.0.x → Discourse</p>
        <p class="timestamp">Generated: {datetime.now().isoformat()}</p>
        
        <h2>Summary</h2>
        <div class="stats">
"""
        
        for category, stats in self.stats.items():
            if isinstance(stats, dict):
                match = stats.get('match', False)
                phpbb = stats.get('phpbb', 'N/A')
                discourse = stats.get('discourse', 'N/A')
                status = 'pass' if match else 'fail'
                
                html += f"""
            <div class="stat-box {status}">
                <div class="stat-label">{category.upper()}</div>
                <div class="stat-value">{phpbb} → {discourse}</div>
            </div>
                """
        
        html += "</div>"
        
        if any(self.issues.values()):
            html += "<div class='issues'><h2>Issues Found</h2>"
            for category, issues_list in self.issues.items():
                for issue in issues_list:
                    html += f'<div class="issue">[{category}] {issue}</div>'
            html += "</div>"
        else:
            html += '<div class="success">✓ All validations passed!</div>'
        
        html += """
        <h2>Details</h2>
        <pre>
"""
        
        for category, stats in self.stats.items():
            html += f"{category.upper()}:\n"
            if isinstance(stats, dict):
                for key, value in stats.items():
                    html += f"  {key}: {value}\n"
            html += "\n"
        
        html += """
        </pre>
    </div>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Report saved to {output_file}")
    
    def run(self, output_file='data/logs/validation.html'):
        """Run all validations."""
        logger.info("Starting migration validation...")
        
        self.validate_users()
        self.validate_categories()
        self.validate_topics()
        self.validate_posts()
        self.validate_files()
        
        self.generate_html_report(output_file)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        if total_issues == 0:
            logger.info("\n✓ All validations passed!")
            return True
        else:
            logger.warning(f"\n⚠ Found {total_issues} issues")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Validate phpBB to Discourse migration'
    )
    parser.add_argument(
        '--phpbb',
        default='../Input',
        help='Path to phpBB directory (default: ../Input)'
    )
    parser.add_argument(
        '--discourse',
        default='http://localhost:3000',
        help='Discourse URL (default: http://localhost:3000)'
    )
    parser.add_argument(
        '--output',
        default='data/logs/validation.html',
        help='Output report file (default: data/logs/validation.html)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    validator = MigrationValidator(
        args.phpbb,
        args.discourse,
        verbose=args.verbose
    )
    
    success = validator.run(args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
