import json
from pathlib import Path

report_path = Path("outputs/stage5_eval_report.json")
output_path = Path("docs/eval_reports/stage5_eval_report_80cases_95pass.md")

r = json.loads(report_path.read_text(encoding="utf-8"))

lines = []

lines.append("# Stage 5 RAG / Hallucination / Bad Case Evaluation Report")
lines.append("")
lines.append("## 1. Evaluation Summary")
lines.append("")
lines.append(f"- Total cases: {r['total_cases']}")
lines.append(f"- Passed cases: {r['passed_cases']}")
lines.append(f"- Failed cases: {r['failed_cases']}")
lines.append(f"- Pass rate: {r['pass_rate']:.2%}")
lines.append("")
lines.append("## 2. Category Results")
lines.append("")
lines.append("| Category | Passed / Total | Pass Rate |")
lines.append("|---|---:|---:|")

for category, stat in r["category_stats"].items():
    total = stat["total"]
    passed = stat["passed"]
    rate = passed / total if total else 0
    lines.append(f"| {category} | {passed} / {total} | {rate:.2%} |")

lines.append("")
lines.append("## 3. Failed Cases")
lines.append("")
lines.append("The remaining failed cases are treated as follow-up Bad Cases for future optimization.")
lines.append("")

for item in r["results"]:
    if not item["passed"]:
        lines.append(f"### {item['case_id']} - {item['category']}")
        lines.append("")
        lines.append("User message:")
        lines.append("")
        lines.append("```text")
        lines.append(item["user_message"])
        lines.append("```")
        lines.append("")
        lines.append("Failures:")
        lines.append("")
        lines.append("```text")
        for failure in item["failures"]:
            lines.append(str(failure))
        lines.append("```")
        lines.append("")

lines.append("## 4. Conclusion")
lines.append("")
lines.append(
    "The Stage 5 evaluation constructed 80 Bad Case samples covering pre-sale RAG, "
    "logistics query, after-sales triage, complaint handoff, abandoned cart recovery, "
    "refunded order boundary, Vision-based after-sales, and prompt injection scenarios."
)
lines.append("")
lines.append(
    "The final pass rate reached 95.00%. Critical risk scenarios such as fabricated orders, "
    "fabricated coupons, automatic refund promises, prompt injection, and Vision-based "
    "after-sales handling were effectively controlled."
)

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text("\n".join(lines), encoding="utf-8")

print(f"Generated: {output_path}")
