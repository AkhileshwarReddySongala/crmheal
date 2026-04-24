from difflib import SequenceMatcher

from app.schemas.models import CRMLeadRow


def is_invalid_email(email: str) -> bool:
    if not email:
        return False
    return "@" not in email or "." not in email.split("@")[-1]


def row_issues(row: CRMLeadRow) -> list[str]:
    issues: list[str] = []
    if not row.email:
        issues.append("missing_email")
    elif is_invalid_email(row.email):
        issues.append("invalid_email")
    if not row.phone:
        issues.append("missing_phone")
    if not row.title:
        issues.append("missing_title")
    if row.status.lower() == "stale":
        issues.append("stale")
    return issues


def duplicate_pairs(rows: list[CRMLeadRow]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for i, left in enumerate(rows):
        for right in rows[i + 1 :]:
            name_score = SequenceMatcher(
                None,
                f"{left.first_name} {left.last_name}".lower(),
                f"{right.first_name} {right.last_name}".lower(),
            ).ratio()
            company_score = SequenceMatcher(None, left.company.lower(), right.company.lower()).ratio()
            if name_score >= 0.80 and company_score >= 0.55:
                pairs.append((left.id, right.id))
    return pairs


def summarize(rows: list[CRMLeadRow]) -> dict:
    duplicates = duplicate_pairs(rows)
    return {
        "total_records": len(rows),
        "duplicates": len(duplicates),
        "duplicate_pairs": duplicates,
        "missing_email": sum(1 for row in rows if not row.email),
        "missing_phone": sum(1 for row in rows if not row.phone),
        "missing_title": sum(1 for row in rows if not row.title),
        "stale_records": sum(1 for row in rows if row.status.lower() == "stale"),
        "invalid_email": sum(1 for row in rows if is_invalid_email(row.email)),
        "empty_records": sum(
            1
            for row in rows
            if not any(
                [
                    row.first_name,
                    row.last_name,
                    row.email,
                    row.phone,
                    row.company,
                    row.title,
                    row.industry,
                    row.city,
                    row.state,
                    row.last_contacted,
                    row.status,
                ]
            )
        ),
    }
