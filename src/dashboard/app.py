"""
GitHub Trend Analyzer - Flask Dashboard Backend
=================================================
Serves the analysis results from the output/ directory
to the frontend visualization dashboard.
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import requests
from collections import Counter

app = Flask(__name__)

# Path to the output directory
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "output"))


def load_json(filename):
    """Safely load a JSON file from the output directory."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/language-popularity')
def language_popularity():
    return jsonify(load_json("1_language_popularity.json"))


@app.route('/api/top-repos')
def top_repos():
    return jsonify(load_json("2_top_repos_by_stars.json"))


@app.route('/api/topic-trends')
def topic_trends():
    return jsonify(load_json("3_topic_trends.json"))


@app.route('/api/yoy-growth')
def yoy_growth():
    return jsonify(load_json("4_yoy_growth.json"))


@app.route('/api/star-distribution')
def star_distribution():
    return jsonify(load_json("5_star_distribution.json"))


@app.route('/api/activity-index')
def activity_index():
    return jsonify(load_json("6_activity_index.json"))


@app.route('/api/ecosystem-health')
def ecosystem_health():
    return jsonify(load_json("7_ecosystem_health.json"))


@app.route('/api/performance')
def performance():
    return jsonify(load_json("performance_timing.json"))


@app.route('/api/user-profiles')
def user_profiles():
    return jsonify(load_json("8_user_profiles.json"))


@app.route('/api/github-user/<username>')
def github_user_lookup(username):
    """Fetch real GitHub user profile + repos + events via the GitHub API."""
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        # 1. User profile
        user_resp = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=10)
        if user_resp.status_code == 404:
            return jsonify({"error": f"User '{username}' not found on GitHub."}), 404
        if user_resp.status_code == 403:
            return jsonify({"error": "GitHub API rate limit reached. Try again in a minute."}), 429
        user_resp.raise_for_status()
        user = user_resp.json()

        # 2. Public repos (up to 100)
        repos_resp = requests.get(
            f"https://api.github.com/users/{username}/repos?per_page=100&sort=stars&direction=desc",
            headers=headers, timeout=10
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        # 3. Recent public events (up to 100)
        events_resp = requests.get(
            f"https://api.github.com/users/{username}/events?per_page=100",
            headers=headers, timeout=10
        )
        events = events_resp.json() if events_resp.status_code == 200 else []

        # ---- Analyze ----
        languages = [r.get("language") for r in repos if r.get("language")]
        lang_counts = Counter(languages)
        favorite_language = lang_counts.most_common(1)[0][0] if lang_counts else "N/A"

        event_types = [e.get("type", "") for e in events]
        event_counts = Counter(event_types)
        primary_activity = event_counts.most_common(1)[0][0] if event_counts else "N/A"

        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)

        # Top repos
        top_repos_list = []
        for r in repos[:10]:
            top_repos_list.append({
                "name": r.get("full_name", ""),
                "language": r.get("language", "N/A"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "description": (r.get("description") or "")[:100],
                "topics": r.get("topics", [])[:5],
            })

        # Language breakdown for chart
        lang_breakdown = [{"language": lang, "count": cnt} for lang, cnt in lang_counts.most_common(10)]

        # Activity breakdown for chart
        activity_breakdown = [{"event_type": evt, "count": cnt} for evt, cnt in event_counts.most_common(10)]

        profile = {
            "username": user.get("login", username),
            "name": user.get("name", ""),
            "avatar_url": user.get("avatar_url", ""),
            "bio": user.get("bio", ""),
            "location": user.get("location", ""),
            "company": user.get("company", ""),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "created_at": user.get("created_at", ""),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "favorite_language": favorite_language,
            "primary_activity": primary_activity,
            "languages_used": len(lang_counts),
            "top_repos": top_repos_list,
            "language_breakdown": lang_breakdown,
            "activity_breakdown": activity_breakdown,
        }
        return jsonify(profile)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to GitHub API: {str(e)}"}), 500


if __name__ == '__main__':
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Starting dashboard at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
