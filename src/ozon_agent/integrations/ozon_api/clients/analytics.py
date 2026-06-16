from __future__ import annotations

from ozon_agent.integrations.ozon_api.clients.base import BaseOzonClient
from ozon_agent.skills.ozon_api.swagger_models import EndpointCategory


class AnalyticsClient(BaseOzonClient):
    category = EndpointCategory.ANALYTICS
