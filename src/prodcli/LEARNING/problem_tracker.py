import json
import os
import webbrowser
from collections import defaultdict
from datetime import datetime

DATA_FILE = "src/data/problems.json"

os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def _load_problems():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {DATA_FILE} is empty or corrupted. Starting with empty list.")
            return []
    return []

def _save_problems(problems):
    with open(DATA_FILE, 'w') as f:
        json.dump(problems, f, indent=4)

def add_problem(platform, url, name, difficulty, status, notes, tags_str):
    problems = _load_problems()
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    new_problem = {
        "platform": platform,
        "url": url,
        "name": name,
        "difficulty": difficulty,
        "status": status,
        "notes": notes,
        "tags": tags,
        "added_date": datetime.now().isoformat() # Automatically adds current date
    }
    problems.append(new_problem)
    _save_problems(problems)

def list_problems(platform=None, status=None, tag=None):
    problems = _load_problems()
    filtered_problems = []
    for problem in problems:
        match = True
        if platform and problem['platform'].lower() != platform.lower():
            match = False
        if status and problem['status'].lower() != status.lower():
            match = False
        if tag and tag.lower() not in [t.lower() for t in problem.get('tags', [])]:
            match = False
        if match:
            filtered_problems.append(problem)
    return filtered_problems

def update_problem(name, new_status=None, new_notes=None, new_difficulty=None, new_tags_str=None):
    problems = _load_problems()
    found = False
    for problem in problems:
        if problem['name'].lower() == name.lower():
            if new_status:
                problem['status'] = new_status
            if new_notes is not None: # Allow empty string to clear notes
                problem['notes'] = new_notes
            if new_difficulty:
                problem['difficulty'] = new_difficulty
            if new_tags_str is not None:
                problem['tags'] = [t.strip() for t in new_tags_str.split(',') if t.strip()] if new_tags_str else []
            # Optionally update last_modified_date
            problem['last_modified_date'] = datetime.now().isoformat()
            found = True
            break
    if found:
        _save_problems(problems)
    return found

def open_problem_in_browser(name):
    problems = _load_problems()
    for problem in problems:
        if problem['name'].lower() == name.lower() and problem.get('url'):
            webbrowser.open(problem['url'])
            return True
    return False

def get_problem_stats():
    problems = _load_problems()
    stats = {
        "total_problems": len(problems),
        "problems_by_platform": defaultdict(int),
        "problems_by_status": defaultdict(int),
        "problems_by_difficulty": defaultdict(int),
    }
    for problem in problems:
        stats['problems_by_platform'][problem['platform']] += 1
        stats['problems_by_status'][problem['status']] += 1
        stats['problems_by_difficulty'][problem['difficulty']] += 1
    return stats