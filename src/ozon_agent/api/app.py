"""FastAPI foundation — read-only API skeleton for future migration."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ozon AI Agent API",
    description="Read-only API for Ozon AI Agent analytics",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    """System status endpoint."""
    return {
        "status": "operational",
        "timestamp": datetime.now(UTC).isoformat(),
        "modules": {
            "sheets": "operational",
            "learning": "operational",
            "intelligence": "operational",
            "quality": "operational",
        },
    }


@app.get("/recommendations")
async def recommendations() -> dict[str, Any]:
    """List recent recommendations."""
    return {
        "recommendations": [],
        "total": 0,
        "message": "Recommendations endpoint - data loaded from approval repository",
    }


@app.get("/sku/{sku_id}")
async def sku_info(sku_id: str) -> dict[str, Any]:
    """Get SKU information."""
    return {
        "sku": sku_id,
        "metrics": {},
        "risk": {},
        "opportunity": {},
        "message": f"SKU info endpoint for {sku_id}",
    }


@app.get("/quality")
async def data_quality() -> dict[str, Any]:
    """Get data quality report."""
    return {
        "overall_status": "UNKNOWN",
        "metrics": [],
        "message": "Data quality endpoint - run quality report first",
    }


@app.get("/cockpit")
async def management_cockpit() -> dict[str, Any]:
    """Get management cockpit data."""
    return {
        "revenue": [],
        "profit": [],
        "advertising": [],
        "risks": [],
        "opportunities": [],
        "actions": [],
        "message": "Management cockpit endpoint - build cockpit first",
    }


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app
