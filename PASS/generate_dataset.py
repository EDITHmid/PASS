"""
PASS — Synthetic Dataset Generator
====================================
Generates realistic CSV datasets for testing and demonstration.

Produces submission records for 200 students across 3 courses
with varied behavioral profiles to showcase system capabilities.

Usage:
    python generate_dataset.py
    python generate_dataset.py --students 50 --assignments 8
"""

import csv
import os
import sys
import random
import argparse
from datetime import datetime, timedelta, timezone

# Behavioral profiles with realistic parameters
PROFILES = {
    "excellent": {
        "description": "Consistently early submitters",
        "weight": 0.15,
        "mean_dt_hours": 28,
        "std_dt_hours": 8,
        "miss_rate": 0.02,
        "drift": 0,  # No drift over time
    },
    "good": {
        "description": "Generally on-time with occasional delays",
        "weight": 0.25,
        "mean_dt_hours": 12,
        "std_dt_hours": 10,
        "miss_rate": 0.05,
        "drift": 0,
    },
    "average": {
        "description": "Mixed submission pattern",
        "weight": 0.25,
        "mean_dt_hours": 3,
        "std_dt_hours": 14,
        "miss_rate": 0.08,
        "drift": 0,
    },
    "struggling": {
        "description": "Frequently late, low consistency",
        "weight": 0.15,
        "mean_dt_hours": -6,
        "std_dt_hours": 16,
        "miss_rate": 0.12,
        "drift": 0,
    },
    "at_risk": {
        "description": "Severely delayed, high miss rate",
        "weight": 0.08,
        "mean_dt_hours": -18,
        "std_dt_hours": 20,
        "miss_rate": 0.25,
        "drift": 0,
    },
    "declining": {
        "description": "Initially good but progressively worsening",
        "weight": 0.07,
        "mean_dt_hours": 20,
        "std_dt_hours": 10,
        "miss_rate": 0.03,
        "drift": -4.5,  # Lose 4.5 hours per assignment period
    },
    "improving": {
        "description": "Initially struggling but getting better",
        "weight": 0.05,
        "mean_dt_hours": -10,
        "std_dt_hours": 15,
        "miss_rate": 0.15,
        "drift": 3.0,  # Gain 3 hours per assignment period
    },
}

# Indian student names for realistic data
FIRST_NAMES = [
    "Aarav", "Aditi", "Arjun", "Aisha", "Bhavesh", "Charvi", "Deepak",
    "Divya", "Eshan", "Falguni", "Gaurav", "Harini", "Ishaan", "Jaya",
    "Karthik", "Kavya", "Lakshmi", "Manoj", "Meghna", "Nikhil", "Nandini",
    "Omkar", "Priya", "Pranav", "Rithika", "Rohan", "Sneha", "Suresh",
    "Swathi", "Tanvi", "Uday", "Varun", "Vidya", "Vikram", "Yamini",
    "Sanjay", "Pooja", "Rahul", "Ananya", "Harsh", "Trisha", "Siddharth",
    "Bhavana", "Rajesh", "Kavitha", "Amit", "Nithya", "Vivek", "Shruti",
    "Aditya",
]

LAST_NAMES = [
    "Agarwal", "Banerjee", "Choudhary", "Desai", "Ghosh", "Gupta", "Iyer",
    "Joshi", "Khan", "Krishnan", "Kumar", "Malhotra", "Mehta", "Menon",
    "Mishra", "Nair", "Patel", "Pawar", "Pillai", "Rao", "Raghavan",
    "Reddy", "Shah", "Sharma", "Singh", "Srinivasan", "Sundaram", "Tiwari",
    "Verma", "Yadav",
]

COURSES = [
    ("CS501", "Data Structures & Algorithms"),
    ("CS502", "Database Management Systems"),
    ("CS503", "Software Engineering"),
]


def generate_student_name(index):
    """Generate a unique student name."""
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index * 7 + 3) % len(LAST_NAMES)]
    return f"{first} {last}"


def assign_profile(index, total):
    """Assign a behavioral profile based on weighted distribution."""
    cumulative = 0
    threshold = (index / total)
    for name, config in PROFILES.items():
        cumulative += config["weight"]
        if threshold < cumulative:
            return name
    return "average"


def generate_dataset(num_students=200, num_assignments=10, output_dir="data"):
    """
    Generate a complete synthetic CSV dataset.

    Args:
        num_students: Number of students to generate (default: 200)
        num_assignments: Number of assignments per course (default: 10)
        output_dir: Output directory for CSV files
    """
    random.seed(42)  # Reproducible results

    os.makedirs(output_dir, exist_ok=True)

    # Setup deadlines (weekly over the semester)
    base_deadline = datetime(2025, 1, 13, 23, 59, 0, tzinfo=timezone.utc)
    assignments = []
    for i in range(num_assignments):
        assignments.append({
            "id": f"A{str(i + 1).zfill(2)}",
            "deadline": base_deadline + timedelta(weeks=i),
        })

    records = []
    profile_stats = {name: 0 for name in PROFILES}

    for s_idx in range(num_students):
        student_name = generate_student_name(s_idx)
        student_id = f"1RV22CS{str(s_idx + 1).zfill(3)}"
        course_id = COURSES[s_idx % len(COURSES)][0]
        profile_name = assign_profile(s_idx, num_students)
        profile = PROFILES[profile_name]
        profile_stats[profile_name] += 1

        for a_idx, assignment in enumerate(assignments):
            # Check if student misses this assignment
            miss_probability = profile["miss_rate"]
            # For declining students, increase miss rate over time
            if profile_name == "declining":
                miss_probability += a_idx * 0.02

            if random.random() < miss_probability:
                continue

            # Compute Δt with drift
            base_mean = profile["mean_dt_hours"] + (profile["drift"] * a_idx)
            dt_hours = random.gauss(base_mean, profile["std_dt_hours"])

            # Add some weekend effect (submissions due Monday tend to be later)
            if assignment["deadline"].weekday() == 0:  # Monday
                dt_hours -= random.uniform(0, 4)

            # Clamp to realistic bounds
            dt_hours = max(min(dt_hours, 96), -72)

            submitted_at = assignment["deadline"] - timedelta(hours=dt_hours)

            records.append({
                "student_id": student_id,
                "student_name": student_name,
                "assignment_id": assignment["id"],
                "submitted_at": submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                "deadline": assignment["deadline"].strftime("%Y-%m-%d %H:%M:%S"),
                "course_id": course_id,
            })

    # Write main dataset
    main_file = os.path.join(output_dir, "submissions.csv")
    with open(main_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "student_id", "student_name", "assignment_id",
            "submitted_at", "deadline", "course_id",
        ])
        writer.writeheader()
        writer.writerows(records)

    # Write a smaller test dataset (first 50 submissions)
    test_file = os.path.join(output_dir, "test_submissions.csv")
    with open(test_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "student_id", "student_name", "assignment_id",
            "submitted_at", "deadline", "course_id",
        ])
        writer.writeheader()
        writer.writerows(records[:50])

    # Summary
    print("═══════════════════════════════════════════════════")
    print("  PASS — Synthetic Dataset Generator")
    print("═══════════════════════════════════════════════════")
    print(f"  Students:       {num_students}")
    print(f"  Assignments:    {num_assignments}")
    print(f"  Total Records:  {len(records)}")
    print(f"  Courses:        {len(COURSES)}")
    print()
    print("  Profile Distribution:")
    for name, count in profile_stats.items():
        pct = count / num_students * 100
        desc = PROFILES[name]["description"]
        print(f"    {name:12s}: {count:3d} ({pct:5.1f}%)  — {desc}")
    print()
    print(f"  Output Files:")
    print(f"    {main_file} ({len(records)} records)")
    print(f"    {test_file} (50 records)")
    print("═══════════════════════════════════════════════════")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PASS Synthetic Dataset Generator")
    parser.add_argument("--students", type=int, default=200, help="Number of students")
    parser.add_argument("--assignments", type=int, default=10, help="Assignments per course")
    parser.add_argument("--output", type=str, default="data", help="Output directory")

    args = parser.parse_args()
    generate_dataset(
        num_students=args.students,
        num_assignments=args.assignments,
        output_dir=args.output,
    )
