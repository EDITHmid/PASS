"""
PASS AI Query Engine
======================
Natural-language query processor for instructor & principal dashboards.
Parses plain-English questions about students, scores, alerts, and
class-wide metrics, then returns structured data + a conversational reply.
"""

import re
from statistics import mean

from models import Student, Submission, Alert, Course


class AIQueryEngine:
    """Converts natural-language queries into DB queries + formatted replies."""

    def __init__(self, db_session):
        self.db = db_session

    # ── Public entry point ──────────────────────────────────────────────────

    def process(self, query: str):
        q = query.strip()
        if not q:
            return self._reply("Please type a question.")

        handlers = [
            ("help", self._handle_help),
            ("student_info", self._handle_student_info),
            ("student_marks", self._handle_student_marks),
            ("student_alerts", self._handle_student_alerts),
            ("attendance", self._handle_attendance),
            ("count_below", self._handle_count_below),
            ("count_above", self._handle_count_above),
            ("count_range", self._handle_count_range),
            ("comparison", self._handle_comparison),
            ("top_students", self._handle_top_students),
            ("bottom_students", self._handle_bottom_students),
            ("tier_list", self._handle_tier_list),
            ("average_score", self._handle_average),
            ("alerts", self._handle_alerts),
            ("distribution", self._handle_distribution),
            ("summary", self._handle_summary),
            ("late_submissions", self._handle_late_submissions),
            ("improving_declining", self._handle_trend),
            ("course_query", self._handle_course_query),
        ]

        for intent, handler in handlers:
            if intent == "help" and self._match_help(q):
                return handler()
            params = self._match_intent(intent, q)
            if params is not None:
                return handler(**params)

        return self._reply(
            "I didn't understand that. Try asking about a student's marks, "
            "how many students are below a score, active alerts, or "
            "type 'help' for examples."
        )

    # ── Intent matching ────────────────────────────────────────────────────

    def _match_intent(self, intent, q):
        matchers = {
            "student_info": [
                r"(?:show|tell|get|find|display|what(?:\s+is|\'s))?\s*(?:me|about)?\s*(?:student)?\s*(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:details|info|information|data|profile)?\s*$",
                r"(?:what\s+is|show|tell)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:credibility\s*)?score",
                r"(?:details|info)\s+(?:of|for|about)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
                r"who\s+is\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
            ],
            "student_marks": [
                r"(?:show|what\s+is|tell|get|display)\s+(?:me\s+)?(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:'s)?\s*(?:marks|scores|exam\s*scores|mid\s*scores|grades)",
                r"(?:marks|scores|exam)\s+(?:of|for)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
            ],
            "student_alerts": [
                r"(?:show|list|get|what\s+are)\s+(?:alerts|flags?|warnings?)\s+(?:for|of|about)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
                r"(?:why\s+is|why\s+are)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:flagged|at\s+risk|in\s+danger)?",
                r"(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:'s)?\s*(?:alerts?|flags?|issues)",
            ],
            "attendance": [
                r"(?:what\s+is|show|tell)\s+(?:the\s+)?attendance\s+(?:of|for)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
                r"(\w+(?:\s+\w+)?(?:\s+\w+)?)\s*(?:'s)?\s*attendance",
                r"students?\s+with\s+(?:low\s+)?attendance\s+(?:below|less\s+than)\s+(\d+)",
                r"who\s+has\s+(?:low|poor)\s+attendance",
            ],
            "count_below": [
                r"(?:how\s+many\s+)?students?\s+(?:are\s+)?(?:with\s+)?(?:scores?\s+)?(?:below|less\s+than|under|<\s*)\s*(\d+)",
                r"(?:count|number\s+of)\s+students?\s+(?:below|under|less\s+than)\s+(\d+)",
                r"(\d+)\s*(?:below|under)\s*(?:credibility\s*)?(?:score\s*)?(\d+)",
            ],
            "count_above": [
                r"(?:how\s+many\s+)?students?\s+(?:are\s+)?(?:with\s+)?(?:scores?\s+)?(?:above|more\s+than|greater\s+than|>\s*)\s*(\d+)",
                r"(?:count|number\s+of)\s+students?\s+(?:above|over|more\s+than)\s+(\d+)",
            ],
            "count_range": [
                r"(?:students?\s+)?(?:between|in\s+(?:the\s+)?range)\s+(\d+)\s*(?:and|to|-)\s*(\d+)",
                r"(?:how\s+many\s+)?students?\s+(?:with\s+)?scores?\s+(?:between|from)\s+(\d+)\s+(?:to|and)\s+(\d+)",
            ],
            "comparison": [
                r"(?:compare|difference|who\s+is\s+better)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)\s+(?:and|vs|versus|or)\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
                r"(\w+(?:\s+\w+)?(?:\s+\w+)?)\s+vs\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)",
            ],
            "top_students": [
                r"(?:top|best|highest|highest\s+scoring)\s+(\d+)?\s*(?:students?)?",
                r"(?:top|best)\s+(?:\d+\s+)?performers?",
            ],
            "bottom_students": [
                r"(?:bottom|worst|lowest|lowest\s+scoring|at\s+risk)\s+(\d+)?\s*(?:students?)?",
                r"(?:most\s+)?at\s*risk\s+(?:students?)?",
            ],
            "tier_list": [
                r"(?:show|list|get|all)\s+(excellent|good|warning|critical)\s+students?",
                r"students?\s+(?:in|with)\s+(?:the\s+)?(excellent|good|warning|critical)\s+(?:tier|level|category)?",
                r"(?:list|show)\s+students?\s+(?:by\s+)?(?:tier|level|category)",
            ],
            "average_score": [
                r"(?:average|mean|avg)\s+(?:credibility\s*)?(?:score|scores)?",
                r"(?:class|overall)\s+(?:average|mean)\s*(?:credibility\s*)?(?:score)?",
                r"what\s+is\s+(?:the\s+)?average",
            ],
            "alerts": [
                r"(?:show|list|get|display|how\s+many)\s+(?:active\s+)?alerts?",
                r"(?:active|unresolved)\s+alerts?",
                r"(?:how\s+many\s+)?alerts?\s+(?:are\s+)?(?:active|there|exist)",
            ],
            "distribution": [
                r"(?:credibility\s*)?(?:distribution|breakdown|tiers?)",
                r"(?:how\s+many\s+)?students?\s+in\s+(?:each\s+)?(?:tier|level|category)",
                r"(?:excellent|good|warning|critical)\s+(?:students?|tier|count)",
            ],
            "summary": [
                r"(?:class|dashboard|overall)\s*(?:summary|overview|stats|statistics)",
                r"(?:summary|overview)\s+(?:of|for)\s+(?:class|all\s+students)",
                r"how\s+(?:are|is)\s+(?:things|the\s+class|everyone)",
            ],
            "late_submissions": [
                r"(?:who\s+has|which\s+students?\s+have|most)\s+(?:the\s+most\s+)?(?:late|missing)\s+submissions?",
                r"(?:late|missing)\s+(?:submissions?|assignments?)\s+(?:rate|count|stats?)",
                r"(?:submission|assignment)\s+(?:status|statistics|overview)",
            ],
            "improving_declining": [
                r"(?:who\s+is|students?\s+|which\s+students?\s+are)\s+(improving|declining|dropping|rising|trending\s+(?:up|down))",
                r"(?:positive|negative|upward|downward)\s+(?:trend|trajectory)",
                r"recent\s+(?:improvements|declines|changes)",
            ],
            "course_query": [
                r"(?:students?\s+(?:in|from|of|enrolled\s+in)\s+)?(?:course|class|section)\s+([A-Za-z]{2,4}\s*\d{3,4})",
                r"(?:course|class|section)\s+([A-Za-z]{2,4}\s*\d{3,4})\s+(?:students?|details?)",
                r"(?:show|list|get)\s+(?:course|class|section)\s+([A-Za-z]{2,4}\s*\d{3,4})",
                r"which\s+(?:course|class)\s+has\s+(?:the\s+most|highest|lowest)\s+(?:students?|scores?)",
            ],
        }

        patterns = matchers.get(intent, [])
        for pat in patterns:
            m = re.search(pat, q, re.IGNORECASE)
            if m:
                return m.groups()
        return None

    def _match_help(self, q):
        return bool(re.search(
            r"^(?:help|commands?|what\s+can\s+(?:you\s+)?(?:do|ask)|"
            r"how\s+(?:to|do\s+I)|examples?|guide)",
            q, re.IGNORECASE
        ))

    # ── Student name resolution ────────────────────────────────────────────

    def _resolve_student(self, name_hint):
        """Find a student by name hint — exact or partial match."""
        if not name_hint:
            return None
        students = Student.query.filter(
            Student.status == "active"
        ).all()

        hint_lower = name_hint.strip().lower()
        matches = [s for s in students if hint_lower in s.name.lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            exact = [s for s in matches if s.name.lower() == hint_lower]
            return exact[0] if exact else None
        from models import User
        users = User.query.filter(
            User.role == "student", User.is_active == True
        ).all()
        for u in users:
            if hint_lower in u.full_name.lower() and u.student_profile:
                return u.student_profile
        return None

    def _resolve_students(self, hints):
        results = []
        for h in hints:
            s = self._resolve_student(h)
            if s:
                results.append(s)
        return results

    # ── Handlers ───────────────────────────────────────────────────────────

    def _handle_student_info(self, *args):
        name_hint = args[0] if args else None
        student = self._resolve_student(name_hint) if name_hint else None
        if not student:
            return self._reply(f"I couldn't find a student matching '{name_hint}'.")
        tier = self._tier_label(student.credibility_score)
        lines = [
            f"**{student.name}** ({student.student_id})",
            f"- Credibility Score: **{student.credibility_score:.1f}** ({tier})",
            f"- Attendance: **{student.attendance_pct:.1f}%**",
            f"- On-Time Rate: **{student.on_time_rate:.1f}%**",
            f"- Submissions: **{student.total_submissions}**",
            f"- Active Alerts: **{student.active_alerts_count}**",
        ]
        if student.course:
            lines.append(f"- Course: **{student.course.course_name}** ({student.course.course_id})")
        return self._reply("\n".join(lines), data=student.to_dict())

    def _handle_student_marks(self, *args):
        name_hint = args[0] if args else None
        student = self._resolve_student(name_hint) if name_hint else None
        if not student:
            return self._reply(f"I couldn't find a student matching '{name_hint}'.")
        lines = [f"**{student.name}** — Exam Scores"]
        mids = []
        for label, val in [("Mid-1", student.mid1_score), ("Mid-2", student.mid2_score), ("Mid-3", student.mid3_score)]:
            if val is not None:
                mids.append(f"  {label}: **{val:.1f}**")
        if mids:
            lines.extend(mids)
            bta = student.best_two_mid_avg
            if bta:
                lines.append(f"  Best 2 Avg: **{bta:.1f}**")
        else:
            lines.append("  No exam scores recorded yet.")
        lines.append(f"  Attendance: **{student.attendance_pct:.1f}%**")
        lines.append(f"  Credibility Score: **{student.credibility_score:.1f}**")
        return self._reply("\n".join(lines), data=student.to_dict())

    def _handle_student_alerts(self, *args):
        name_hint = args[0] if args else None
        student = self._resolve_student(name_hint) if name_hint else None
        if not student:
            return self._reply(f"I couldn't find a student matching '{name_hint}'.")
        alerts = Alert.query.filter_by(
            student_id=student.id, resolved=False
        ).order_by(Alert.created_at.desc()).all()
        if not alerts:
            return self._reply(
                f"**{student.name}** has no active alerts. All clear!",
                data=student.to_dict()
            )
        lines = [f"**{student.name}** — {len(alerts)} Active Alert(s):"]
        for a in alerts:
            lines.append(
                f"  - [{a.severity.upper()}] {a.description}"
            )
        return self._reply("\n".join(lines), data=[a.to_dict() for a in alerts])

    def _handle_attendance(self, *args):
        name_hint = args[0] if args else None
        if name_hint and name_hint.isdigit():
            threshold = float(name_hint)
            students = Student.query.filter(
                Student.status == "active",
                Student.attendance_pct < threshold
            ).order_by(Student.attendance_pct.asc()).all()
            if not students:
                return self._reply(f"No active students have attendance below {threshold:.0f}%.")
            names = "\n".join(f"  - {s.name}: **{s.attendance_pct:.1f}%**" for s in students[:20])
            return self._reply(f"**{len(students)}** student(s) with attendance below {threshold:.0f}%:\n{names}",
                               data=[s.to_dict() for s in students[:20]])

        student = self._resolve_student(name_hint) if name_hint else None
        if student:
            return self._reply(f"**{student.name}** attendance: **{student.attendance_pct:.1f}%**")

        low_pct = Student.query.filter(
            Student.status == "active",
            Student.attendance_pct < 75.0
        ).count()
        return self._reply(
            f"**{low_pct}** active student(s) have attendance below 75%."
        )

    def _handle_count_below(self, *args):
        threshold = float(args[0]) if args and args[0] else 50.0
        students = Student.query.filter(
            Student.status == "active",
            Student.credibility_score < threshold
        ).order_by(Student.credibility_score.asc()).all()
        count = len(students)
        names = "\n".join(f"  - {s.name}: **{s.credibility_score:.1f}**" for s in students[:20])
        if count == 0:
            return self._reply(f"No active students have a credibility score below {threshold:.0f}.")
        msg = f"**{count}** active student(s) with scores below {threshold:.0f}.\n{names}"
        if count > 20:
            msg += f"\n  … and {count - 20} more."
        return self._reply(msg, data=[s.to_dict() for s in students[:20]])

    def _handle_count_above(self, *args):
        threshold = float(args[0]) if args and args[0] else 80.0
        students = Student.query.filter(
            Student.status == "active",
            Student.credibility_score >= threshold
        ).order_by(Student.credibility_score.desc()).all()
        count = len(students)
        names = "\n".join(f"  - {s.name}: **{s.credibility_score:.1f}**" for s in students[:20])
        if count == 0:
            return self._reply(f"No active students have a credibility score of {threshold:.0f} or above.")
        msg = f"**{count}** active student(s) with scores {threshold:.0f} or above.\n{names}"
        if count > 20:
            msg += f"\n  … and {count - 20} more."
        return self._reply(msg, data=[s.to_dict() for s in students[:20]])

    def _handle_count_range(self, *args):
        if not args or len(args) < 2:
            return self._reply("Please specify a range, e.g. 'students between 30 and 60'.")
        lo, hi = float(args[0]), float(args[1])
        students = Student.query.filter(
            Student.status == "active",
            Student.credibility_score >= lo,
            Student.credibility_score <= hi
        ).order_by(Student.credibility_score.asc()).all()
        count = len(students)
        names = "\n".join(f"  - {s.name}: **{s.credibility_score:.1f}**" for s in students[:20])
        if count == 0:
            return self._reply(f"No active students have scores between {lo:.0f} and {hi:.0f}.")
        msg = f"**{count}** active student(s) with scores between {lo:.0f}–{hi:.0f}.\n{names}"
        if count > 20:
            msg += f"\n  … and {count - 20} more."
        return self._reply(msg, data=[s.to_dict() for s in students[:20]])

    def _handle_comparison(self, *args):
        if not args or len(args) < 2:
            return self._reply("Please name two students to compare, e.g. 'compare Arjun and Sita'.")
        s1, s2 = self._resolve_student(args[0]), self._resolve_student(args[1])
        if not s1 or not s2:
            missing = " or ".join(
                n for n, s in zip(args, [s1, s2]) if s is None
            )
            return self._reply(f"Could not find student(s): {missing}.")

        def fmt(stu):
            return (
                f"  **{stu.name}** — Score: **{stu.credibility_score:.1f}** "
                f"(Attendance: {stu.attendance_pct:.1f}%, "
                f"On-Time: {stu.on_time_rate:.1f}%, "
                f"Alerts: {stu.active_alerts_count})"
            )

        better = s1 if s1.credibility_score >= s2.credibility_score else s2
        return self._reply(
            f"**Comparison:**\n{fmt(s1)}\n{fmt(s2)}\n\n"
            f"**{better.name}** has the higher credibility score."
        )

    def _handle_top_students(self, *args):
        n = int(args[0]) if args and args[0] else 5
        n = min(max(n, 1), 50)
        students = Student.query.filter(
            Student.status == "active"
        ).order_by(Student.credibility_score.desc()).limit(n).all()
        if not students:
            return self._reply("No active students found.")
        names = "\n".join(
            f"  {i + 1}. {s.name}: **{s.credibility_score:.1f}**"
            for i, s in enumerate(students)
        )
        return self._reply(f"**Top {n} Students by Credibility Score:**\n{names}",
                           data=[s.to_dict() for s in students])

    def _handle_bottom_students(self, *args):
        n = int(args[0]) if args and args[0] else 5
        n = min(max(n, 1), 50)
        students = Student.query.filter(
            Student.status == "active"
        ).order_by(Student.credibility_score.asc()).limit(n).all()
        if not students:
            return self._reply("No active students found.")
        names = "\n".join(
            f"  {i + 1}. {s.name}: **{s.credibility_score:.1f}**"
            for i, s in enumerate(students)
        )
        return self._reply(f"**Bottom {n} Students by Credibility Score:**\n{names}",
                           data=[s.to_dict() for s in students])

    def _handle_tier_list(self, *args):
        tier_name = args[0].lower() if args and args[0] else None
        tier_map = {
            "excellent": (80, 101),
            "good": (60, 80),
            "warning": (40, 60),
            "critical": (0, 40),
        }
        if tier_name not in tier_map:
            return self._reply("Please specify a tier: excellent, good, warning, or critical.")
        lo, hi = tier_map[tier_name]
        students = Student.query.filter(
            Student.status == "active",
            Student.credibility_score >= lo,
            Student.credibility_score < hi
        ).order_by(Student.credibility_score.desc()).all()
        if not students:
            return self._reply(f"No active students in the **{tier_name.title()}** tier.")
        names = "\n".join(
            f"  - {s.name}: **{s.credibility_score:.1f}**"
            for s in students[:30]
        )
        msg = f"**{len(students)}** student(s) in the {tier_name.title()} tier:\n{names}"
        if len(students) > 30:
            msg += f"\n  … and {len(students) - 30} more."
        return self._reply(msg, data=[s.to_dict() for s in students[:30]])

    def _handle_average(self, *args):
        students = Student.query.filter(Student.status == "active").all()
        if not students:
            return self._reply("No active students to compute average.")
        scores = [s.credibility_score for s in students]
        avg = mean(scores)
        median = sorted(scores)[len(scores) // 2]
        return self._reply(
            f"**Class-Wide Credibility:**\n"
            f"- Average: **{avg:.1f}**\n"
            f"- Median: **{median:.1f}**\n"
            f"- Range: **{min(scores):.1f}** to **{max(scores):.1f}**\n"
            f"- Based on **{len(students)}** active students.",
            data={"average": round(avg, 2), "median": round(median, 2), "count": len(students)}
        )

    def _handle_alerts(self, *args):
        alerts = Alert.query.filter(
            Alert.resolved == False
        ).order_by(Alert.created_at.desc()).limit(20).all()
        count = len(alerts)
        if count == 0:
            return self._reply("No active alerts. Everything looks good!")
        critical = sum(1 for a in alerts if a.severity == "critical")
        warning = sum(1 for a in alerts if a.severity == "warning")
        info = sum(1 for a in alerts if a.severity == "info")
        lines = [
            f"**{count} Active Alerts** (Critical: {critical}, Warning: {warning}, Info: {info})",
        ]
        for a in alerts[:10]:
            student_name = a.student.name if a.student else "Unknown"
            lines.append(
                f"  - [{a.severity.upper()}] {student_name}: "
                f"{a.description[:80]}{'…' if len(a.description) > 80 else ''}"
            )
        if count > 10:
            lines.append(f"  … and {count - 10} more.")
        return self._reply("\n".join(lines), data=[a.to_dict() for a in alerts])

    def _handle_distribution(self, *args):
        students = Student.query.filter(Student.status == "active").all()
        if not students:
            return self._reply("No active students.")
        counts = {"Excellent (≥80)": 0, "Good (60–79)": 0, "Warning (40–59)": 0, "Critical (<40)": 0}
        for s in students:
            sc = s.credibility_score
            if sc >= 80:
                counts["Excellent (≥80)"] += 1
            elif sc >= 60:
                counts["Good (60–79)"] += 1
            elif sc >= 40:
                counts["Warning (40–59)"] += 1
            else:
                counts["Critical (<40)"] += 1
        lines = ["**Credibility Distribution:**"]
        for label, cnt in counts.items():
            bar = "█" * min(cnt, 30)
            pct = cnt / len(students) * 100
            lines.append(f"  {label}: {cnt} ({pct:.1f}%) {bar}")
        return self._reply("\n".join(lines), data=counts)

    def _handle_summary(self, *args):
        students = Student.query.filter(Student.status == "active").all()
        alerts = Alert.query.filter(Alert.resolved == False).count()
        total = len(students)
        if total == 0:
            return self._reply("No active students in the system.")
        avg = mean(s.credibility_score for s in students) if students else 0
        at_risk = sum(1 for s in students if s.credibility_score < 40)
        excellent = sum(1 for s in students if s.credibility_score >= 80)
        total_subs = sum(s.total_submissions for s in students)
        late_subs = sum(
            1 for s in students
            for sub in s.submissions if sub.submission_status == "late"
        )
        return self._reply(
            f"**Class Summary**\n"
            f"- Total Students: **{total}**\n"
            f"- Average Credibility: **{avg:.1f}**\n"
            f"- Excellent (≥80): **{excellent}**\n"
            f"- At-Risk (<40): **{at_risk}**\n"
            f"- Active Alerts: **{alerts}**\n"
            f"- Submissions: **{total_subs}** ({late_subs} late)",
            data={"total_students": total, "avg_credibility": round(avg, 2), "alerts": alerts}
        )

    def _handle_late_submissions(self, *args):
        students = Student.query.filter(Student.status == "active").all()
        if not students:
            return self._reply("No active students.")

        ranked = sorted(
            students,
            key=lambda s: sum(1 for sub in s.submissions if sub.submission_status == "late"),
            reverse=True
        )
        lines = ["**Late Submission Report:**"]
        total_late = 0
        total_subs = 0
        shown = 0
        for s in ranked:
            late = sum(1 for sub in s.submissions if sub.submission_status == "late")
            total = s.total_submissions
            total_late += late
            total_subs += total
            if late > 0 and shown < 10:
                rate = (late / total * 100) if total else 0
                lines.append(f"  - {s.name}: {late}/{total} late ({rate:.0f}%)")
                shown += 1

        overall_rate = (total_late / total_subs * 100) if total_subs else 0
        lines.insert(1, f"  Overall: **{total_late}/{total_subs}** submissions late ({overall_rate:.1f}%)")
        return self._reply("\n".join(lines))

    def _handle_trend(self, *args):
        direction = args[0].lower() if args and args[0] else None
        from engine.metrics import MetricComputer
        mc = MetricComputer()

        students = Student.query.filter(Student.status == "active").all()
        if not students:
            return self._reply("No active students.")

        results = []
        for s in students:
            if not s.submissions:
                continue
            vals = [sub.delta_t for sub in s.submissions]
            trend = mc.compute_trend_direction(vals)
            results.append((s, trend))

        if direction and direction.startswith("declin"):
            filtered = [(s, t) for s, t in results if t.get("direction") == "worsening"]
            label = "Declining"
        elif direction and direction.startswith("improv"):
            filtered = [(s, t) for s, t in results if t.get("direction") == "improving"]
            label = "Improving"
        else:
            filtered = [(s, t) for s, t in results if t.get("direction") != "stable"]
            label = "Notable Trends"

        filtered.sort(key=lambda x: abs(x[1].get("pct_change", 0)), reverse=True)

        if not filtered:
            return self._reply(f"No students show a clear trend right now.")

        lines = [f"**{label}:**"]
        for s, t in filtered[:10]:
            dir_symbol = "📈" if t.get("direction") == "improving" else "📉"
            lines.append(
                f"  {dir_symbol} {s.name}: score {s.credibility_score:.1f} "
                f"(Δt {t.get('direction', 'stable')}, {t.get('pct_change', 0):+.1f}%)"
            )
        if len(filtered) > 10:
            lines.append(f"  … and {len(filtered) - 10} more.")
        return self._reply("\n".join(lines))

    def _handle_course_query(self, *args):
        import re as _re
        course_code = args[0] if args else None
        if course_code:
            course_code = course_code.strip().upper()
            course_code = _re.sub(r"\s+", "", course_code)
            course = Course.query.filter(
                Course.course_id == course_code
            ).first()
            if not course:
                return self._reply(f"Could not find course **{course_code}**.")
            students = Student.query.filter(
                Student.course_id == course.id,
                Student.status == "active"
            ).all()
            if not students:
                return self._reply(f"**{course.course_name}** has no active students enrolled.")
            avg = mean(s.credibility_score for s in students)
            names = "\n".join(
                f"  - {s.name}: **{s.credibility_score:.1f}**"
                for s in sorted(students, key=lambda x: x.credibility_score, reverse=True)[:20]
            )
            lines = [
                f"**{course.course_name}** ({course.course_id})",
                f"- Enrolled: **{len(students)}** students",
                f"- Average Credibility: **{avg:.1f}**",
                f"",
                names,
            ]
            if len(students) > 20:
                lines.append(f"  … and {len(students) - 20} more.")
            return self._reply("\n".join(lines), data=[s.to_dict() for s in students[:20]])

        # "which course has the most/highest/lowest" variant
        courses = Course.query.all()
        if not courses:
            return self._reply("No courses found.")
        best = max(
            courses,
            key=lambda c: len([s for s in c.students if s.status == "active"]) if c.students else 0
        )
        return self._reply(
            f"**{best.course_name}** ({best.course_id}) has the most active students."
        )

    def _handle_help(self):
        return self._reply(
            "**What I Can Do** — Examples:\n\n"
            "📌 **Student Lookup**\n"
            "  \"Show Arjun's details\"\n"
            "  \"What is Sita's credibility score?\"\n"
            "  \"Show alerts for Arjun\"\n"
            "  \"Why is Sita flagged?\"\n\n"
            "📊 **Marks & Attendance**\n"
            "  \"Show Arjun's marks\"\n"
            "  \"What is Sita's attendance?\"\n"
            "  \"Students with attendance below 75\"\n\n"
            "🔢 **Counts**\n"
            "  \"How many students below 40?\"\n"
            "  \"Students above 80\"\n"
            "  \"Students between 30 and 60\"\n\n"
            "🏆 **Rankings & Tiers**\n"
            "  \"Top 10 students\"\n"
            "  \"Bottom 5 students\"\n"
            "  \"Show excellent students\"\n"
            "  \"List critical students\"\n\n"
            "🔔 **Alerts & Trends**\n"
            "  \"Show active alerts\"\n"
            "  \"Who is improving?\"\n"
            "  \"Who is declining?\"\n"
            "  \"Late submission report\"\n\n"
            "📖 **Course Queries**\n"
            "  \"Students in course CS101\"\n"
            "  \"Which course has most students?\"\n\n"
            "📈 **Class Overview**\n"
            "  \"Class average\"\n"
            "  \"Credibility distribution\"\n"
            "  \"Class summary\"\n\n"
            "⚖️ **Comparison**\n"
            "  \"Compare Arjun and Sita\""
        )

    # ── Utilities ──────────────────────────────────────────────────────────

    @staticmethod
    def _tier_label(score):
        if score >= 80:
            return "🌟 Excellent"
        if score >= 60:
            return "✅ Good"
        if score >= 40:
            return "⚠️ Warning"
        return "🔴 Critical"

    @staticmethod
    def _reply(text, data=None):
        return {"response": text, "data": data}
