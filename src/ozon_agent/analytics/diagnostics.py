"""Data quality diagnostics."""
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class DiagnosticResult:
    check: str
    status: str  # pass, warn, fail
    message: str
    details: dict[str, Any] | None = None


def check_missing_data(df: pd.DataFrame, required_columns: list[str]) -> list[DiagnosticResult]:
    """Check for missing data in required columns."""
    results = []

    for col in required_columns:
        if col not in df.columns:
            results.append(DiagnosticResult(
                check=f"column_exists:{col}",
                status="fail",
                message=f"Column '{col}' not found",
            ))
            continue

        missing = df[col].isna().sum()
        total = len(df)
        pct = missing / total * 100 if total > 0 else 0

        if pct > 50:
            status = "fail"
            msg = f"Column '{col}' has {pct:.1f}% missing values"
        elif pct > 20:
            status = "warn"
            msg = f"Column '{col}' has {pct:.1f}% missing values"
        else:
            status = "pass"
            msg = f"Column '{col}' OK ({pct:.1f}% missing)"

        results.append(DiagnosticResult(
            check=f"missing_data:{col}",
            status=status,
            message=msg,
            details={"missing": int(missing), "total": total, "percentage": round(pct, 2)},
        ))

    return results


def check_duplicates(df: pd.DataFrame, key_columns: list[str]) -> list[DiagnosticResult]:
    """Check for duplicate records."""
    results: list[DiagnosticResult] = []

    available_keys = [col for col in key_columns if col in df.columns]
    if not available_keys:
        return results

    duplicates = df.duplicated(subset=available_keys, keep=False).sum()
    total = len(df)
    pct = duplicates / total * 100 if total > 0 else 0

    if pct > 10:
        status = "fail"
    elif pct > 5:
        status = "warn"
    else:
        status = "pass"

    results.append(DiagnosticResult(
        check="duplicates",
        status=status,
        message=f"Found {duplicates} duplicate records ({pct:.1f}%)",
        details={"duplicates": int(duplicates), "total": total, "percentage": round(pct, 2)},
    ))

    return results


def check_date_continuity(df: pd.DataFrame, date_column: str) -> list[DiagnosticResult]:
    """Check for gaps in date series."""
    results: list[DiagnosticResult] = []

    if date_column not in df.columns:
        return results

    dates = pd.to_datetime(df[date_column]).dropna().sort_values()
    if len(dates) < 2:
        return results

    date_range = pd.date_range(start=dates.min(), end=dates.max(), freq="D")
    missing_dates = set(date_range) - set(dates)

    if len(missing_dates) > 7:
        status = "fail"
    elif len(missing_dates) > 0:
        status = "warn"
    else:
        status = "pass"

    results.append(DiagnosticResult(
        check="date_continuity",
        status=status,
        message=f"Found {len(missing_dates)} missing dates",
        details={"missing_dates": [d.isoformat() for d in sorted(missing_dates)[:10]]},
    ))

    return results


def check_outliers(
    df: pd.DataFrame, columns: list[str], threshold: float = 3.0
) -> list[DiagnosticResult]:
    """Check for outliers using z-score."""
    results = []

    for col in columns:
        if col not in df.columns:
            continue

        values = df[col].dropna()
        if len(values) < 10:
            continue

        mean = values.mean()
        std = values.std()
        if std == 0:
            continue

        z_scores = ((values - mean) / std).abs()
        outliers = (z_scores > threshold).sum()
        pct = outliers / len(values) * 100

        if pct > 5:
            status = "warn"
        else:
            status = "pass"

        results.append(DiagnosticResult(
            check=f"outliers:{col}",
            status=status,
            message=f"Column '{col}' has {outliers} outliers ({pct:.1f}%)",
            details={
                "outliers": int(outliers),
                "mean": round(mean, 2),
                "std": round(std, 2),
                "threshold": threshold,
            },
        ))

    return results


def check_negative_values(df: pd.DataFrame, columns: list[str]) -> list[DiagnosticResult]:
    """Check for unexpected negative values."""
    results = []

    for col in columns:
        if col not in df.columns:
            continue

        negatives = (df[col] < 0).sum()
        if negatives > 0:
            results.append(DiagnosticResult(
                check=f"negative_values:{col}",
                status="warn",
                message=f"Column '{col}' has {negatives} negative values",
                details={"count": int(negatives)},
            ))

    return results


def run_full_diagnostics(df: pd.DataFrame, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run full data quality diagnostics."""
    config = config or {}

    required_columns = config.get("required_columns", [
        "date", "product_id", "quantity", "revenue",
    ])

    key_columns = config.get("key_columns", ["date", "product_id"])
    date_column = config.get("date_column", "date")
    numeric_columns = config.get(
        "numeric_columns", ["quantity", "revenue", "spend", "price"]
    )
    positive_columns = config.get(
        "positive_columns", ["quantity", "revenue", "impressions", "clicks"]
    )

    all_results = []
    all_results.extend(check_missing_data(df, required_columns))
    all_results.extend(check_duplicates(df, key_columns))
    all_results.extend(check_date_continuity(df, date_column))
    all_results.extend(check_outliers(df, numeric_columns))
    all_results.extend(check_negative_values(df, positive_columns))

    summary = {
        "total_checks": len(all_results),
        "passed": sum(1 for r in all_results if r.status == "pass"),
        "warnings": sum(1 for r in all_results if r.status == "warn"),
        "failed": sum(1 for r in all_results if r.status == "fail"),
        "checks": [
            {
                "check": r.check,
                "status": r.status,
                "message": r.message,
                "details": r.details,
            }
            for r in all_results
        ],
    }

    return summary
