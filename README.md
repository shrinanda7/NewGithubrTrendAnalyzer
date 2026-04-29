# GitHub Repository Trend Analysis — Big Data Project

A comprehensive Big Data analytics project that processes **1GB+ of GitHub event data** using **Apache Spark** to uncover programming language trends, popular repositories, and ecosystem health.

## 🔑 Key Features

- **7 Spark Analyses** with Mapper/Reducer phase timing
- **1.1GB realistic dataset** with unbiased language distributions (based on GitHub Octoverse 2015-2024)
- **Premium interactive dashboard** with 15+ charts
- **Performance profiling** showing Map-Reduce timings

## 📊 The 7 Analyses

| # | Analysis | Description |
|---|----------|-------------|
| 1 | **Language Popularity** | Events per language per year, ranked |
| 2 | **Top Repos by Stars** | Most starred repositories with forks and activity |
| 3 | **Trending Topics** | Topic keyword frequency, year-wise evolution |
| 4 | **YoY Growth Rate** | Growth % using LAG window function |
| 5 | **Star Distribution** | Avg, Median, Max, StdDev of stars per language |
| 6 | **Activity Index** | Composite score: events × event_types × years_active |
| 7 | **Ecosystem Health** | Normalized composite: repos + stars + forks + events + topics |

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Step 1: Generate 1.1GB of realistic data (~5 min)
python src/data_generator.py

# Step 2: Run all 7 Spark analyses (~2-5 min)
python src/spark_analyzer.py

# Step 3: Launch the dashboard
python src/dashboard/app.py
# Open http://127.0.0.1:5000
```

## 📂 Project Structure

```
github-trend-analyzer/
├── data/                  # 1GB+ JSON dataset
├── output/                # Spark analysis results (JSON)
├── src/
│   ├── data_generator.py  # Realistic data generator
│   ├── data_collector.py  # GH Archive downloader (alternative)
│   ├── spark_analyzer.py  # 7 Spark analyses with timing
│   └── dashboard/
│       ├── app.py         # Flask backend
│       ├── templates/
│       │   └── index.html # Dashboard page
│       └── static/
│           ├── style.css  # Premium dark-mode design
│           └── dashboard.js # Chart rendering logic
├── requirements.txt
└── README.md
```

## 🔬 Data Pipeline

The data generator uses **real GitHub Octoverse distributions** (2015-2024) to ensure unbiased analysis:
- Language weights shift year-over-year (e.g., Python rises from 10% → 22.5%)
- Stars follow a power-law distribution (most repos have <10 stars)
- Topics are correlated with languages (not random)
- Event volume increases over years (reflecting GitHub's growth)
