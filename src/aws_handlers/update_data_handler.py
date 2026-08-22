"""Thin scheduled Lambda adapter for the existing update service."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.aws_database.dynamodb_repository import DynamoDataRepository
from src.aws_runtime.world_bank_client import WorldBankS3Client
from src.config import Settings
from src.services.data_service import DataUpdateService


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    settings = Settings.from_env({"DATABASE_PATH": "/tmp/not-used.db"})
    repository = DynamoDataRepository(os.environ["DATA_TABLE_NAME"])
    client = WorldBankS3Client(
        base_url=settings.api_base_url,
        raw_bucket_name=os.environ["RAW_BUCKET_NAME"],
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        backoff_factor=settings.backoff_factor,
        request_interval=settings.request_interval,
        user_agent=settings.user_agent,
    )
    result = DataUpdateService(settings, repository, client=client).update()
    LOGGER.info("Data update completed: %s", json.dumps(result.to_dict()))
    if result.status == "failed":
        raise RuntimeError("World Bank update failed; see the structured result in CloudWatch Logs")
    if result.status == "partial":
        LOGGER.warning("World Bank update completed partially")
    return result.to_dict()
