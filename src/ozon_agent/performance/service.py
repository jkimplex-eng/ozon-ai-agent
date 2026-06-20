from __future__ import annotations

import logging
from pathlib import Path

from ozon_agent.performance.client import PerformanceClient
from ozon_agent.performance.csv_parser import parse_performance_csv
from ozon_agent.performance.models import (
    PerformanceCampaign,
    PerformanceCampaignsResult,
    PerformanceReportRequest,
    PerformanceReportResult,
    PerformanceReportStatus,
    utc_now_iso,
)
from ozon_agent.performance.store import (
    save_normalized_campaigns,
    save_normalized_stats,
    save_raw_campaigns,
    save_raw_stats,
)

logger = logging.getLogger(__name__)


def fetch_campaigns(
    *,
    client: PerformanceClient | None = None,
    max_pages: int = 1,
    page_delay: float = 0.0,
    dry_run: bool = False,
    save: bool = True,
    storage_root: Path | None = None,
) -> PerformanceCampaignsResult:
    if dry_run:
        return PerformanceCampaignsResult(
            warnings=["dry_run: request built but HTTP call skipped"],
        )
    active_client = client or PerformanceClient.from_env()
    close_client = client is None
    try:

        all_campaigns: list[PerformanceCampaign] = []
        total_pages = 1
        raw_response: dict[str, object] = {}
        for page_num in range(1, max_pages + 1):
            response_data = active_client.get_campaigns_page(page=page_num)
            result = active_client.parse_campaigns_response(response_data)
            all_campaigns.extend(result.campaigns)
            total_pages = result.total_pages
            raw_response = response_data
            logger.info(
                "Page %d/%d: fetched %d campaigns (total pages: %d)",
                page_num,
                max_pages,
                len(result.campaigns),
                total_pages,
            )
            if page_num >= total_pages:
                break
            if page_delay > 0:
                import time
                time.sleep(page_delay)

        result = PerformanceCampaignsResult(
            campaigns=all_campaigns,
            raw_response=raw_response,
            page=1,
            total_pages=total_pages,
        )

        if save:
            requested_at = utc_now_iso()
            save_raw_campaigns(
                all_campaigns,
                storage_root=storage_root,
                requested_at=requested_at,
            )
            save_normalized_campaigns(
                all_campaigns,
                storage_root=storage_root,
                requested_at=requested_at,
            )

        return result
    finally:
        if close_client:
            active_client.close()


def fetch_stats(
    request: PerformanceReportRequest,
    *,
    client: PerformanceClient | None = None,
    poll_interval: float = 60.0,
    timeout: float = 900.0,
    dry_run: bool = False,
    save: bool = True,
    storage_root: Path | None = None,
) -> PerformanceReportResult:
    if dry_run:
        return PerformanceReportResult(
            report_id="dry-run",
            status=PerformanceReportStatus.CREATED,
            warnings=["dry_run: request built but HTTP call skipped"],
        )
    active_client = client or PerformanceClient.from_env()
    close_client = client is None
    try:

        body = active_client.create_stats_report(request)
        result_data = body.get("result", body)
        report_id = str(
            body.get("UUID", "")
            or result_data.get("report_id", "")
            or result_data.get("id", "")
        )

        status = active_client.poll_report_until_done(
            report_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        if status == PerformanceReportStatus.FAILED:
            return PerformanceReportResult(
                report_id=report_id,
                status=status,
                warnings=[f"Report {report_id} failed on server"],
            )

        if status != PerformanceReportStatus.DONE:
            return PerformanceReportResult(
                report_id=report_id,
                status=status,
                warnings=[f"Report {report_id} did not complete within timeout"],
            )

        csv_text = active_client.download_report_csv(report_id)
        rows = parse_performance_csv(csv_text)

        result = PerformanceReportResult(
            report_id=report_id,
            status=status,
            rows=rows,
            raw_csv=csv_text,
        )

        if save:
            requested_at = utc_now_iso()
            save_raw_stats(
                csv_text,
                storage_root=storage_root,
                requested_at=requested_at,
                report_id=report_id,
            )
            save_normalized_stats(
                rows,
                storage_root=storage_root,
                requested_at=requested_at,
                report_id=report_id,
            )

        return result
    finally:
        if close_client:
            active_client.close()


def download_report(
    report_id: str,
    *,
    client: PerformanceClient | None = None,
    save: bool = True,
    storage_root: Path | None = None,
) -> PerformanceReportResult:
    active_client = client or PerformanceClient.from_env()
    close_client = client is None
    try:
        csv_text = active_client.download_report_csv(report_id)
        rows = parse_performance_csv(csv_text)

        result = PerformanceReportResult(
            report_id=report_id,
            status=PerformanceReportStatus.DONE,
            rows=rows,
            raw_csv=csv_text,
        )

        if save:
            requested_at = utc_now_iso()
            save_raw_stats(
                csv_text,
                storage_root=storage_root,
                requested_at=requested_at,
                report_id=report_id,
            )
            save_normalized_stats(
                rows,
                storage_root=storage_root,
                requested_at=requested_at,
                report_id=report_id,
            )

        return result
    finally:
        if close_client:
            active_client.close()
