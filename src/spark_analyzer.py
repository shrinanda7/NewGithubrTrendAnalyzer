"""
GitHub Repository Trend Analysis - Spark Engine
=================================================
Performs 7 comprehensive analyses on 1GB+ GitHub event data.

Each analysis includes:
  - Detailed timing (Mapper/Transformer phase + Reducer/Action phase)
  - Logic explanation printed to console
  - Results saved as JSON for the dashboard

Analyses:
  1. Language Popularity by Year
  2. Top Repositories by Stars
  3. Trending Topics by Year
  4. Year-over-Year Language Growth Rate
  5. Star Distribution Across Languages
  6. Repository Activity Index (Most Active Repos)
  7. Language Ecosystem Health Score
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, year, month, count, desc, asc, sum as spark_sum,
    avg, max as spark_max, min as spark_min,
    explode, lower, size, when, lit, round as spark_round,
    countDistinct, collect_list, struct, dense_rank, row_number,
    percentile_approx, stddev, lag, coalesce, array_contains
)
from pyspark.sql.window import Window
import os
import json
import time


class AnalysisTimer:
    """Track mapper (transformation) and reducer (action) phases separately."""

    def __init__(self, name):
        self.name = name
        self.mapper_start = None
        self.mapper_end = None
        self.reducer_start = None
        self.reducer_end = None

    def start_mapper(self):
        self.mapper_start = time.time()
        return self

    def end_mapper(self):
        self.mapper_end = time.time()
        return self

    def start_reducer(self):
        self.reducer_start = time.time()
        return self

    def end_reducer(self):
        self.reducer_end = time.time()
        return self

    @property
    def mapper_duration(self):
        if self.mapper_start and self.mapper_end:
            return self.mapper_end - self.mapper_start
        return 0

    @property
    def reducer_duration(self):
        if self.reducer_start and self.reducer_end:
            return self.reducer_end - self.reducer_start
        return 0

    @property
    def total_duration(self):
        return self.mapper_duration + self.reducer_duration

    def summary(self):
        return {
            "analysis": self.name,
            "mapper_phase_seconds": round(self.mapper_duration, 3),
            "reducer_phase_seconds": round(self.reducer_duration, 3),
            "total_seconds": round(self.total_duration, 3)
        }


def print_analysis_header(number, name, logic):
    """Print a formatted header with analysis explanation."""
    print(f"\n{'='*70}")
    print(f"  ANALYSIS {number}: {name}")
    print(f"{'='*70}")
    print(f"  Logic: {logic}")
    print(f"{'='*70}")


def save_results(data, output_path, filename):
    """Save analysis results as JSON."""
    filepath = os.path.join(output_path, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"  [OK] Saved: {filepath} ({len(data)} records)")


def run_all_analyses(input_path, output_path):
    """Run all 7 analyses with detailed timing."""

    # ========================================================================
    # SPARK SESSION SETUP
    # ========================================================================
    spark = SparkSession.builder \
        .appName("GitHub Repository Trend Analysis") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .config("spark.default.parallelism", "8") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    all_timings = []
    total_start = time.time()

    # ========================================================================
    # DATA LOADING & INITIAL CLEANING
    # ========================================================================
    print(f"\n{'#'*70}")
    print(f"  LOADING DATA")
    print(f"{'#'*70}")

    load_timer = AnalysisTimer("Data Loading & Cleaning")
    load_timer.start_mapper()

    print(f"  Reading from: {input_path}")
    df = spark.read.json(input_path)

    # CLEANING PHASE
    # 1. Remove nulls in critical columns
    # 2. Extract year from created_at
    # 3. Filter out invalid years
    # 4. Cache for reuse across all analyses
    df_clean = df.filter(
        col("repo.language").isNotNull() &
        col("created_at").isNotNull() &
        col("repo.name").isNotNull()
    ).withColumn("event_year", year(col("created_at"))) \
     .filter((col("event_year") >= 2015) & (col("event_year") <= 2026))

    load_timer.end_mapper()
    load_timer.start_reducer()

    # Force materialization to measure actual load time
    total_records = df.count()
    clean_records = df_clean.count()
    df_clean.cache()
    df_clean.count()  # Trigger cache

    load_timer.end_reducer()
    all_timings.append(load_timer.summary())

    print(f"  Total raw records: {total_records:,}")
    print(f"  After cleaning:    {clean_records:,}")
    print(f"  Records removed:   {total_records - clean_records:,} ({((total_records - clean_records) / max(total_records,1)) * 100:.1f}%)")
    print(f"  [TIME] Mapper (transformations): {load_timer.mapper_duration:.3f}s")
    print(f"  [TIME] Reducer (actions):        {load_timer.reducer_duration:.3f}s")
    print(f"  [TIME] Total:                    {load_timer.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 1: Language Popularity by Year
    # ========================================================================
    print_analysis_header(1, "Language Popularity by Year",
        "MAP: Extract (year, language) pairs from each event.\n"
        "           REDUCE: GroupBy (year, language) -> COUNT events.\n"
        "           This shows how many events each language generated per year,\n"
        "           revealing which languages are most actively used over time.")

    t1 = AnalysisTimer("Language Popularity by Year")
    t1.start_mapper()

    lang_popularity = df_clean.select(
        col("event_year").alias("year"),
        col("repo.language").alias("language")
    ).groupBy("year", "language") \
     .agg(count("*").alias("event_count"))

    # Add rank within each year
    year_window = Window.partitionBy("year").orderBy(desc("event_count"))
    lang_popularity = lang_popularity.withColumn("rank", dense_rank().over(year_window))

    t1.end_mapper()
    t1.start_reducer()

    result1 = lang_popularity.filter(col("rank") <= 20) \
        .orderBy("year", "rank") \
        .toPandas().to_dict(orient="records")
    save_results(result1, output_path, "1_language_popularity.json")

    t1.end_reducer()
    all_timings.append(t1.summary())
    print(f"  [TIME] Mapper: {t1.mapper_duration:.3f}s | Reducer: {t1.reducer_duration:.3f}s | Total: {t1.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 2: Top Repositories by Stars
    # ========================================================================
    print_analysis_header(2, "Top Repositories by Stars",
        "MAP: Extract (repo_name, language, stars, forks) from each event.\n"
        "           REDUCE: GroupBy repo_name -> MAX(stars), MAX(forks), COUNT(events).\n"
        "           This identifies the most popular repositories by their star count,\n"
        "           along with their primary language and fork count.")

    t2 = AnalysisTimer("Top Repositories by Stars")
    t2.start_mapper()

    top_repos = df_clean.select(
        col("repo.name").alias("repo_name"),
        col("repo.language").alias("language"),
        col("repo.stars").alias("stars"),
        col("repo.forks").alias("forks")
    ).groupBy("repo_name", "language") \
     .agg(
        spark_max("stars").alias("max_stars"),
        spark_max("forks").alias("max_forks"),
        count("*").alias("total_events")
    ).orderBy(desc("max_stars"))

    t2.end_mapper()
    t2.start_reducer()

    result2 = top_repos.limit(100).toPandas().to_dict(orient="records")
    save_results(result2, output_path, "2_top_repos_by_stars.json")

    t2.end_reducer()
    all_timings.append(t2.summary())
    print(f"  [TIME] Mapper: {t2.mapper_duration:.3f}s | Reducer: {t2.reducer_duration:.3f}s | Total: {t2.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 3: Trending Topics by Year
    # ========================================================================
    print_analysis_header(3, "Trending Topics by Year",
        "MAP: Explode the topics array -> one row per (year, topic) pair.\n"
        "           REDUCE: GroupBy (year, topic) -> COUNT occurrences.\n"
        "           This reveals which development topics (e.g., 'machine-learning',\n"
        "           'kubernetes') are gaining or losing traction each year.")

    t3 = AnalysisTimer("Trending Topics by Year")
    t3.start_mapper()

    topic_trends = df_clean.select(
        col("event_year").alias("year"),
        explode(col("repo.topics")).alias("topic")
    ).filter(col("topic").isNotNull() & (col("topic") != "")) \
     .withColumn("topic", lower(col("topic"))) \
     .groupBy("year", "topic") \
     .agg(count("*").alias("count"))

    topic_window = Window.partitionBy("year").orderBy(desc("count"))
    topic_trends = topic_trends.withColumn("rank", dense_rank().over(topic_window))

    t3.end_mapper()
    t3.start_reducer()

    result3 = topic_trends.filter(col("rank") <= 15) \
        .orderBy("year", "rank") \
        .toPandas().to_dict(orient="records")
    save_results(result3, output_path, "3_topic_trends.json")

    t3.end_reducer()
    all_timings.append(t3.summary())
    print(f"  [TIME] Mapper: {t3.mapper_duration:.3f}s | Reducer: {t3.reducer_duration:.3f}s | Total: {t3.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 4: Year-over-Year Language Growth Rate
    # ========================================================================
    print_analysis_header(4, "Year-over-Year Language Growth Rate",
        "MAP: Count events per (year, language).\n"
        "           REDUCE: Use LAG window function to get previous year's count,\n"
        "           then calculate growth_rate = ((current - previous) / previous) * 100.\n"
        "           This shows which languages are growing fastest or declining.")

    t4 = AnalysisTimer("YoY Language Growth Rate")
    t4.start_mapper()

    lang_yearly = df_clean.select(
        col("event_year").alias("year"),
        col("repo.language").alias("language")
    ).groupBy("year", "language") \
     .agg(count("*").alias("event_count"))

    # Calculate YoY growth using LAG
    lang_window = Window.partitionBy("language").orderBy("year")
    growth = lang_yearly.withColumn(
        "prev_year_count", lag("event_count", 1).over(lang_window)
    ).filter(col("prev_year_count").isNotNull()) \
     .withColumn(
        "growth_rate",
        spark_round(((col("event_count") - col("prev_year_count")) / col("prev_year_count")) * 100, 2)
    ).withColumn(
        "absolute_change", col("event_count") - col("prev_year_count")
    )

    t4.end_mapper()
    t4.start_reducer()

    result4 = growth.orderBy("year", desc("growth_rate")) \
        .toPandas().to_dict(orient="records")
    save_results(result4, output_path, "4_yoy_growth.json")

    t4.end_reducer()
    all_timings.append(t4.summary())
    print(f"  [TIME] Mapper: {t4.mapper_duration:.3f}s | Reducer: {t4.reducer_duration:.3f}s | Total: {t4.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 5: Star Distribution Across Languages
    # ========================================================================
    print_analysis_header(5, "Star Distribution Across Languages",
        "MAP: Extract (language, stars) from each unique repository.\n"
        "           REDUCE: GroupBy language -> AVG(stars), MEDIAN(stars), MAX(stars),\n"
        "           STDDEV(stars), total_stars, repo_count.\n"
        "           This reveals which languages attract the most stars on average\n"
        "           and the distribution shape (skewed by mega-repos or uniform).")

    t5 = AnalysisTimer("Star Distribution Across Languages")
    t5.start_mapper()

    # Deduplicate repos (take max stars per repo)
    unique_repos = df_clean.select(
        col("repo.name").alias("repo_name"),
        col("repo.language").alias("language"),
        col("repo.stars").alias("stars")
    ).groupBy("repo_name", "language") \
     .agg(spark_max("stars").alias("stars"))

    star_dist = unique_repos.groupBy("language").agg(
        count("*").alias("repo_count"),
        spark_round(avg("stars"), 2).alias("avg_stars"),
        percentile_approx("stars", 0.5).alias("median_stars"),
        spark_max("stars").alias("max_stars"),
        spark_sum("stars").alias("total_stars"),
        spark_round(stddev("stars"), 2).alias("stddev_stars")
    ).orderBy(desc("total_stars"))

    t5.end_mapper()
    t5.start_reducer()

    result5 = star_dist.toPandas().to_dict(orient="records")
    save_results(result5, output_path, "5_star_distribution.json")

    t5.end_reducer()
    all_timings.append(t5.summary())
    print(f"  [TIME] Mapper: {t5.mapper_duration:.3f}s | Reducer: {t5.reducer_duration:.3f}s | Total: {t5.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 6: Repository Activity Index
    # ========================================================================
    print_analysis_header(6, "Repository Activity Index (Most Active Repos)",
        "MAP: Extract (repo_name, event_type, year) from each event.\n"
        "           REDUCE: GroupBy repo -> COUNT total events, COUNT DISTINCT event types,\n"
        "           COUNT DISTINCT years active.\n"
        "           Activity Score = total_events x distinct_event_types x years_active.\n"
        "           This identifies the most consistently active repositories.")

    t6 = AnalysisTimer("Repository Activity Index")
    t6.start_mapper()

    activity = df_clean.select(
        col("repo.name").alias("repo_name"),
        col("repo.language").alias("language"),
        col("repo.stars").alias("stars"),
        col("type").alias("event_type"),
        col("event_year")
    ).groupBy("repo_name", "language") \
     .agg(
        count("*").alias("total_events"),
        countDistinct("event_type").alias("distinct_event_types"),
        countDistinct("event_year").alias("years_active"),
        spark_max("stars").alias("max_stars")
    ).withColumn(
        "activity_score",
        spark_round(col("total_events") * col("distinct_event_types") * col("years_active"), 0)
    ).orderBy(desc("activity_score"))

    t6.end_mapper()
    t6.start_reducer()

    result6 = activity.limit(100).toPandas().to_dict(orient="records")
    save_results(result6, output_path, "6_activity_index.json")

    t6.end_reducer()
    all_timings.append(t6.summary())
    print(f"  [TIME] Mapper: {t6.mapper_duration:.3f}s | Reducer: {t6.reducer_duration:.3f}s | Total: {t6.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 7: Language Ecosystem Health Score
    # ========================================================================
    print_analysis_header(7, "Language Ecosystem Health Score",
        "MAP: Extract (language, stars, forks, topics_count, events) per repo.\n"
        "           REDUCE: GroupBy language -> Aggregate total_repos, total_stars,\n"
        "           total_forks, avg_topics, total_events.\n"
        "           Health Score = normalize(repos) + normalize(stars) + normalize(forks)\n"
        "                        + normalize(events) + normalize(avg_topics).\n"
        "           This composite metric measures overall ecosystem vitality.")

    t7 = AnalysisTimer("Language Ecosystem Health Score")
    t7.start_mapper()

    # Get unique repos with their metrics
    repo_metrics = df_clean.select(
        col("repo.name").alias("repo_name"),
        col("repo.language").alias("language"),
        col("repo.stars").alias("stars"),
        col("repo.forks").alias("forks"),
        size(col("repo.topics")).alias("topic_count")
    ).groupBy("repo_name", "language") \
     .agg(
        spark_max("stars").alias("stars"),
        spark_max("forks").alias("forks"),
        spark_max("topic_count").alias("topic_count"),
        count("*").alias("events")
    )

    ecosystem = repo_metrics.groupBy("language").agg(
        count("*").alias("total_repos"),
        spark_sum("stars").alias("total_stars"),
        spark_sum("forks").alias("total_forks"),
        spark_round(avg("topic_count"), 2).alias("avg_topics"),
        spark_sum("events").alias("total_events"),
        spark_round(avg("stars"), 2).alias("avg_stars_per_repo"),
        spark_round(avg("forks"), 2).alias("avg_forks_per_repo")
    ).orderBy(desc("total_repos"))

    t7.end_mapper()
    t7.start_reducer()

    eco_pd = ecosystem.toPandas()

    # Calculate normalized health score (0-100)
    if not eco_pd.empty:
        for metric_col in ["total_repos", "total_stars", "total_forks", "total_events", "avg_topics"]:
            max_val = eco_pd[metric_col].max()
            if max_val > 0:
                eco_pd[f"{metric_col}_norm"] = (eco_pd[metric_col] / max_val) * 20  # Each metric worth 20 pts

        score_cols = [c for c in eco_pd.columns if c.endswith("_norm")]
        eco_pd["health_score"] = eco_pd[score_cols].sum(axis=1).round(2)
        eco_pd = eco_pd.drop(columns=score_cols)
        eco_pd = eco_pd.sort_values("health_score", ascending=False)

    result7 = eco_pd.to_dict(orient="records")
    save_results(result7, output_path, "7_ecosystem_health.json")

    t7.end_reducer()
    all_timings.append(t7.summary())
    print(f"  [TIME] Mapper: {t7.mapper_duration:.3f}s | Reducer: {t7.reducer_duration:.3f}s | Total: {t7.total_duration:.3f}s")

    # ========================================================================
    # ANALYSIS 8: User Activity Profiles
    # ========================================================================
    print_analysis_header(8, "User Activity Profiles",
        "MAP: Extract (actor_login, language, repo, event_type, year) per event.\n"
        "           REDUCE: GroupBy actor_login -> COUNT events, COLLECT languages,\n"
        "           COUNT DISTINCT repos, COUNT DISTINCT years.\n"
        "           This builds a searchable profile for each user.")

    t8 = AnalysisTimer("User Activity Profiles")
    t8.start_mapper()

    user_profiles = df_clean.select(
        col("actor.login").alias("username"),
        col("repo.language").alias("language"),
        col("repo.name").alias("repo_name"),
        col("repo.stars").alias("stars"),
        col("type").alias("event_type"),
        col("event_year")
    ).groupBy("username") \
     .agg(
        count("*").alias("total_events"),
        countDistinct("repo_name").alias("repos_contributed"),
        countDistinct("language").alias("languages_used"),
        countDistinct("event_year").alias("years_active"),
        spark_max("stars").alias("max_repo_stars"),
        collect_list("language").alias("all_languages"),
        collect_list("event_type").alias("all_event_types")
    ).orderBy(desc("total_events"))

    t8.end_mapper()
    t8.start_reducer()

    user_pd = user_profiles.limit(5000).toPandas()

    # Calculate favorite language (mode) and favorite event type for each user
    def get_mode(lst):
        if not lst:
            return "Unknown"
        from collections import Counter
        return Counter(lst).most_common(1)[0][0]

    user_pd["favorite_language"] = user_pd["all_languages"].apply(get_mode)
    user_pd["primary_activity"] = user_pd["all_event_types"].apply(get_mode)
    user_pd = user_pd.drop(columns=["all_languages", "all_event_types"])

    result8 = user_pd.to_dict(orient="records")
    save_results(result8, output_path, "8_user_profiles.json")

    t8.end_reducer()
    all_timings.append(t8.summary())
    print(f"  [TIME] Mapper: {t8.mapper_duration:.3f}s | Reducer: {t8.reducer_duration:.3f}s | Total: {t8.total_duration:.3f}s")

    # ========================================================================
    # TIMING SUMMARY
    # ========================================================================
    total_end = time.time()
    total_time = total_end - total_start

    print(f"\n{'#'*70}")
    print(f"  PERFORMANCE SUMMARY")
    print(f"{'#'*70}")
    print(f"  {'Phase':<45} {'Mapper':>8} {'Reducer':>8} {'Total':>8}")
    print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*8}")
    for t in all_timings:
        print(f"  {t['analysis']:<45} {t['mapper_phase_seconds']:>7.3f}s {t['reducer_phase_seconds']:>7.3f}s {t['total_seconds']:>7.3f}s")
    print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*8}")
    print(f"  {'GRAND TOTAL':<45} {'':>8} {'':>8} {total_time:>7.3f}s")
    print(f"{'#'*70}\n")

    # Save timing data for the dashboard
    timing_summary = {
        "analyses": all_timings,
        "total_pipeline_seconds": round(total_time, 3),
        "total_records_processed": clean_records,
        "records_removed_in_cleaning": total_records - clean_records
    }
    save_results(timing_summary, output_path, "performance_timing.json")

    spark.stop()
    print("Spark session stopped. All analyses complete!")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, "..", "data", "github_events.json")
    output_dir = os.path.join(base_dir, "..", "output")
    run_all_analyses(input_dir, output_dir)
