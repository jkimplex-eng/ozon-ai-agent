from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from ozon_agent.performance.models import (
    PERFORMANCE_BASE_URL,
    PerformanceCampaign,
    PerformanceCampaignsResult,
    PerformanceCredentials,
    PerformanceReportRequest,
    PerformanceReportStatus,
)

logger = logging.getLogger(__name__)


class PerformanceCredentialsError(ValueError):
    pass


class PerformanceClient:
    def __init__(
        self,
        credentials: PerformanceCredentials,
        *,
        base_url: str = PERFORMANCE_BASE_URL,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not credentials.client_id or not credentials.client_secret:
            raise PerformanceCredentialsError(
                "OZON_PERFORMANCE_CLIENT_ID and "
                "OZON_PERFORMANCE_CLIENT_SECRET are required"
            )
        self.credentials = credentials
        self.base_url = base_url
        self._client = http_client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
        )

    @classmethod
    def from_env(cls) -> PerformanceClient:
        return cls(
            PerformanceCredentials(
                client_id=os.environ.get("OZON_PERFORMANCE_CLIENT_ID", ""),
                client_secret=os.environ.get(
                    "OZON_PERFORMANCE_CLIENT_SECRET", ""
                ),
            )
        )

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {self.credentials.client_secret}"
            ),
            "Content-Type": "application/json",
        }

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                response = self._client.get(
                    path,
                    params=params,
                    headers=self._auth_headers(),
                )
                if response.status_code == 429:
                    default_wait = backoff * (2 ** attempt)
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", default_wait
                        )
                    )
                    logger.warning(
                        "Rate limited (429), retrying in %.1fs",
                        retry_after,
                    )
                    time.sleep(retry_after)
                    continue
                return response
            except httpx.TimeoutException as exc:
                last_exc = exc
                wait = backoff * (2 ** attempt)
                logger.warning(
                    "Timeout on attempt %d, retrying in %.1fs",
                    attempt + 1,
                    wait,
                )
                time.sleep(wait)
        if last_exc:
            raise last_exc
        raise httpx.HTTPError("Request failed after retries")

    def _post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        *,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                response = self._client.post(
                    path,
                    json=json_data,
                    headers=self._auth_headers(),
                )
                if response.status_code == 429:
                    default_wait = backoff * (2 ** attempt)
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", default_wait
                        )
                    )
                    logger.warning(
                        "Rate limited (429), retrying in %.1fs",
                        retry_after,
                    )
                    time.sleep(retry_after)
                    continue
                return response
            except httpx.TimeoutException as exc:
                last_exc = exc
                wait = backoff * (2 ** attempt)
                logger.warning(
                    "Timeout on attempt %d, retrying in %.1fs",
                    attempt + 1,
                    wait,
                )
                time.sleep(wait)
        if last_exc:
            raise last_exc
        raise httpx.HTTPError("Request failed after retries")

    def get_campaigns_page(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        response = self._get(
            "/api/client/campaign",
            params={"page": page, "page_size": page_size},
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body

    def parse_campaigns_response(
        self, data: dict[str, Any]
    ) -> PerformanceCampaignsResult:
        result_data = data.get("result", data)
        campaigns_raw = result_data.get("list", [])
        pagination = result_data.get("pagination", {})
        campaigns: list[PerformanceCampaign] = []
        for item in campaigns_raw:
            campaigns.append(
                PerformanceCampaign(
                    id=int(item.get("id", 0)),
                    name=str(item.get("title", "")),
                    status=str(item.get("status", "")),
                    campaign_type=str(item.get("type", "")),
                    budget=float(item.get("budget", 0) or 0),
                    daily_budget=float(
                        item.get("daily_budget", 0) or 0
                    ),
                    start_date=str(item.get("start_date", "")),
                    end_date=str(item.get("end_date", "")),
                )
            )
        return PerformanceCampaignsResult(
            campaigns=campaigns,
            raw_response=data,
            page=int(pagination.get("page", 1)),
            total_pages=int(pagination.get("total_pages", 1)),
        )

    def create_stats_report(
        self,
        request: PerformanceReportRequest,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "date_from": request.date_from,
            "date_to": request.date_to,
            "limit": request.limit,
        }
        if request.campaign_ids:
            payload["campaign_ids"] = request.campaign_ids
        response = self._post(
            "/api/client/statistics/report",
            json_data=payload,
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body

    def get_report_status(self, report_id: str) -> dict[str, Any]:
        response = self._get(
            f"/api/client/statistics/report/{report_id}",
        )
        body: dict[str, Any] = response.json()
        return body

    def download_report_csv(self, report_id: str) -> str:
        response = self._get(
            f"/api/client/statistics/report/download/{report_id}",
        )
        response.raise_for_status()
        result: str = response.text
        return result

    def poll_report_until_done(
        self,
        report_id: str,
        *,
        poll_interval: float = 60.0,
        timeout: float = 900.0,
    ) -> PerformanceReportStatus:
        elapsed = 0.0
        while elapsed < timeout:
            body = self.get_report_status(report_id)
            result_data = body.get("result", body)
            status_str = str(
                result_data.get("status", "")
            ).upper()
            try:
                status = PerformanceReportStatus(status_str)
            except ValueError:
                status = PerformanceReportStatus.PENDING

            if status == PerformanceReportStatus.DONE:
                return status
            if status == PerformanceReportStatus.FAILED:
                return status

            logger.info(
                "Report %s status: %s, waiting %.0fs...",
                report_id,
                status_str,
                poll_interval,
            )
            time.sleep(poll_interval)
            elapsed += poll_interval

        return PerformanceReportStatus.PENDING

    def close(self) -> None:
        self._client.close()
