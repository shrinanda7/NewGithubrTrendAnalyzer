# Source Code Directory (`src/`)

This directory contains the core logic for the GitHub Trend Analyzer. It handles everything from data generation to distributed processing and web serving.

## Files

### `data_generator.py`
This script synthesizes the 1GB+ dataset required for our Big Data analysis. It ensures realistic distributions of languages, topics, and events over time.

**Key Snippet:**
```python
def generate_event(date_str: str) -> dict:
    # Randomly select a language based on realistic weights
    lang = random.choices(languages, weights=lang_weights)[0]
    
    # Create realistic event structure mimicking GitHub REST API
    return {
        "id": str(random.randint(10000000000, 99999999999)),
        "type": random.choices(event_types, weights=event_weights)[0],
        "actor": {"login": f"user{random.randint(1, 50000)}"},
        "repo": {
            "name": f"{lang.lower()}-repo-{random.randint(1, 1000)}",
            "language": lang,
            "stars": random.randint(0, 10000),
            "forks": random.randint(0, 2000),
            "topics": random.sample(topics_pool, k=random.randint(0, 4))
        },
        "created_at": date_str
    }
```

### `spark_analyzer.py`
This is the heart of the Big Data processing pipeline. It utilizes PySpark to perform MapReduce operations on our dataset.

**Key Snippet (YoY Growth Logic):**
```python
# MAP Phase: Count events per language per year
df_yearly = df_clean.groupBy("event_year", "repo.language") \
    .agg(count("*").alias("yearly_events"))

# REDUCE Phase: Calculate Year-over-Year Growth using Window Functions
window_spec = Window.partitionBy("language").orderBy("event_year")
df_growth = df_yearly.withColumn("prev_year_events", lag("yearly_events", 1).over(window_spec)) \
    .withColumn("growth_rate", 
                when(col("prev_year_events").isNotNull(),
                     spark_round(((col("yearly_events") - col("prev_year_events")) / col("prev_year_events")) * 100, 2))
                .otherwise(lit(0.0)))
```

### `data_collector.py`
A utility script intended to connect to a MongoDB instance to fetch actual historical data (used as a reference or alternative data source).

## Subdirectories
*   `dashboard/`: Contains the Flask server and frontend files.
