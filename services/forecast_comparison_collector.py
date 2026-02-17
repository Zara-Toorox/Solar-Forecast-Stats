# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Solar Forecast Stats x86 DB-Version part of Solar Forecast ML DB
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/ha-solar-forecast-ml/blob/main/LICENSE
# ******************************************************************************

"""Forecast comparison collector for SFML Stats (DB-only). @zara"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING, AsyncIterator

import aiosqlite

from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from ..storage.db_connection_manager import DatabaseConnectionManager

from ..const import (
    DOMAIN,
    SOLAR_FORECAST_DB,
    FORECAST_COMPARISON_RETENTION_DAYS,
    CONF_FORECAST_ENTITY_1,
    CONF_FORECAST_ENTITY_2,
    CONF_FORECAST_ENTITY_1_NAME,
    CONF_FORECAST_ENTITY_2_NAME,
    DEFAULT_FORECAST_ENTITY_1_NAME,
    DEFAULT_FORECAST_ENTITY_2_NAME,
)
from ..sfml_data_reader import SFMLDataReader

_LOGGER = logging.getLogger(__name__)


def _compute_accuracy(actual: float | None, forecast: float | None) -> float | None:
    """Compute accuracy percent from actual and forecast values. @zara"""
    if actual is None or forecast is None:
        return None
    if actual <= 0 and forecast <= 0:
        return 100.0
    if actual <= 0 or forecast <= 0:
        return 0.0
    return round(max(0, min(100, 100 - abs((actual - forecast) / actual) * 100)), 1)


def _determine_best_source(
    sfml_acc: float | None,
    ext1_acc: float | None,
    ext2_acc: float | None,
) -> str | None:
    """Determine best forecast source by accuracy. @zara"""
    candidates: dict[str, float] = {}
    if sfml_acc is not None and sfml_acc > 0:
        candidates["sfml"] = sfml_acc
    if ext1_acc is not None and ext1_acc > 0:
        candidates["external_1"] = ext1_acc
    if ext2_acc is not None and ext2_acc > 0:
        candidates["external_2"] = ext2_acc
    if not candidates:
        return None
    return max(candidates, key=candidates.get)


class ForecastComparisonCollector:
    """Collect and store forecast comparison data directly in DB. @zara"""

    _db_manager: DatabaseConnectionManager | None = None

    def __init__(self, hass: HomeAssistant, config_path: Path, db_manager: DatabaseConnectionManager | None = None) -> None:
        """Initialize the collector. @zara"""
        self._hass = hass
        self._config_path = config_path
        self._db_path = config_path / SOLAR_FORECAST_DB
        if db_manager is not None:
            ForecastComparisonCollector._db_manager = db_manager

    def _get_config(self) -> dict[str, Any]:
        """Get current configuration. @zara"""
        entries = self._hass.data.get(DOMAIN, {})
        for entry_id, entry_data in entries.items():
            if isinstance(entry_data, dict) and "config" in entry_data:
                return entry_data["config"]

        config_entries = self._hass.config_entries.async_entries(DOMAIN)
        if config_entries:
            return dict(config_entries[0].data)
        return {}

    def _get_sensor_value(self, entity_id: str | None) -> float | None:
        """Read current value from a sensor. @zara"""
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    @asynccontextmanager
    async def _get_db_connection(self) -> AsyncIterator[aiosqlite.Connection | None]:
        """Get a database connection via the centralized manager. @zara"""
        from ..storage.db_connection_manager import get_manager

        manager = get_manager()
        if manager is not None and manager.is_connected:
            try:
                _LOGGER.debug("ForecastComparisonCollector: Using database connection manager")
                yield await manager.get_connection()
                return
            except Exception as err:
                _LOGGER.warning("Error getting connection from manager: %s", err)

        _LOGGER.warning("ForecastComparisonCollector: Database manager not available, using direct connection")
        if not self._db_path.exists():
            _LOGGER.debug("SFML database not found: %s", self._db_path)
            yield None
            return

        try:
            conn = await aiosqlite.connect(str(self._db_path))
            conn.row_factory = aiosqlite.Row
            try:
                yield conn
            finally:
                await conn.close()
        except Exception as err:
            _LOGGER.error("Error connecting to SFML database: %s", err)
            yield None

    async def _get_existing_day(self, conn: aiosqlite.Connection, day_str: str) -> dict[str, Any] | None:
        """Read existing row from stats_forecast_comparison for a day. @zara"""
        try:
            async with conn.execute(
                """SELECT date, actual_kwh, sfml_forecast_kwh, sfml_accuracy_percent,
                          external_1_kwh, external_1_accuracy_percent,
                          external_2_kwh, external_2_accuracy_percent, best_source
                   FROM stats_forecast_comparison WHERE date = ?""",
                (day_str,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as err:
            _LOGGER.warning("Error reading existing day %s: %s", day_str, err)
        return None

    async def _upsert_day(
        self,
        conn: aiosqlite.Connection,
        day_str: str,
        actual_kwh: float | None = None,
        sfml_forecast_kwh: float | None = None,
        sfml_accuracy_percent: float | None = None,
        external_1_kwh: float | None = None,
        external_1_accuracy_percent: float | None = None,
        external_2_kwh: float | None = None,
        external_2_accuracy_percent: float | None = None,
        best_source: str | None = None,
    ) -> bool:
        """Insert or update a row in stats_forecast_comparison. @zara"""
        try:
            await conn.execute(
                """INSERT INTO stats_forecast_comparison
                       (date, actual_kwh, sfml_forecast_kwh, sfml_accuracy_percent,
                        external_1_kwh, external_1_accuracy_percent,
                        external_2_kwh, external_2_accuracy_percent,
                        best_source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                   ON CONFLICT(date) DO UPDATE SET
                       actual_kwh = COALESCE(excluded.actual_kwh, actual_kwh),
                       sfml_forecast_kwh = COALESCE(excluded.sfml_forecast_kwh, sfml_forecast_kwh),
                       sfml_accuracy_percent = COALESCE(excluded.sfml_accuracy_percent, sfml_accuracy_percent),
                       external_1_kwh = COALESCE(excluded.external_1_kwh, external_1_kwh),
                       external_1_accuracy_percent = COALESCE(excluded.external_1_accuracy_percent, external_1_accuracy_percent),
                       external_2_kwh = COALESCE(excluded.external_2_kwh, external_2_kwh),
                       external_2_accuracy_percent = COALESCE(excluded.external_2_accuracy_percent, external_2_accuracy_percent),
                       best_source = COALESCE(excluded.best_source, best_source),
                       updated_at = CURRENT_TIMESTAMP""",
                (day_str, actual_kwh, sfml_forecast_kwh, sfml_accuracy_percent,
                 external_1_kwh, external_1_accuracy_percent,
                 external_2_kwh, external_2_accuracy_percent, best_source),
            )
            await conn.commit()
            return True
        except Exception as err:
            _LOGGER.error("Error upserting forecast comparison for %s: %s", day_str, err)
            return False

    async def _get_sfml_forecast(self, day_str: str) -> float | None:
        """Get SFML forecast for a specific day from database. @zara"""
        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

        async with self._get_db_connection() as conn:
            if not conn:
                return None

            try:
                if day_str in (today_str, tomorrow_str):
                    if day_str == today_str:
                        async with conn.execute(
                            """SELECT prediction_kwh FROM daily_forecasts
                               WHERE forecast_type = 'today'
                               ORDER BY created_at DESC LIMIT 1"""
                        ) as cursor:
                            row = await cursor.fetchone()
                            if row and row["prediction_kwh"] is not None:
                                prediction = row["prediction_kwh"]
                                _LOGGER.debug("SFML forecast for today from DB: %.2f kWh", prediction)
                                return prediction

                    elif day_str == tomorrow_str:
                        async with conn.execute(
                            """SELECT prediction_kwh FROM daily_forecasts
                               WHERE forecast_type = 'tomorrow'
                               ORDER BY created_at DESC LIMIT 1"""
                        ) as cursor:
                            row = await cursor.fetchone()
                            if row and row["prediction_kwh"] is not None:
                                prediction = row["prediction_kwh"]
                                _LOGGER.debug("SFML forecast for tomorrow from DB: %.2f kWh", prediction)
                                return prediction

                async with conn.execute(
                    """SELECT predicted_total_kwh FROM daily_summaries
                       WHERE date = ?""",
                    (day_str,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row["predicted_total_kwh"] is not None:
                        return row["predicted_total_kwh"]

                _LOGGER.debug("No SFML forecast found for %s", day_str)
                return None

            except Exception as err:
                _LOGGER.warning("Error reading SFML forecast from database: %s", err)
                return None

    async def _cleanup_old_entries(self, conn: aiosqlite.Connection) -> None:
        """Remove entries older than retention period from DB. @zara"""
        cutoff_date = date.today() - timedelta(days=FORECAST_COMPARISON_RETENTION_DAYS)
        cutoff_str = cutoff_date.isoformat()

        try:
            async with conn.execute(
                "DELETE FROM stats_forecast_comparison WHERE date < ?",
                (cutoff_str,),
            ) as cursor:
                deleted = cursor.rowcount
            await conn.commit()
            if deleted and deleted > 0:
                _LOGGER.debug("Removed %d old forecast comparison entries", deleted)
        except Exception as err:
            _LOGGER.warning("Error cleaning up old forecast entries: %s", err)

    async def async_collect_morning_forecasts(self) -> bool:
        """Collect forecast values for today at morning time. @zara"""
        config = self._get_config()
        today_str = date.today().isoformat()

        _LOGGER.info("Collecting morning forecast values for %s", today_str)

        external_1_entity = config.get(CONF_FORECAST_ENTITY_1)
        external_2_entity = config.get(CONF_FORECAST_ENTITY_2)

        external_1_kwh = self._get_sensor_value(external_1_entity) if external_1_entity else None
        external_2_kwh = self._get_sensor_value(external_2_entity) if external_2_entity else None

        sfml_forecast_kwh = await self._get_sfml_forecast(today_str)

        async with self._get_db_connection() as conn:
            if not conn:
                _LOGGER.error("No DB connection for morning forecast collection")
                return False

            # Read existing row to avoid overwriting evening data
            existing = await self._get_existing_day(conn, today_str)

            # Only set values if not already present
            sfml = sfml_forecast_kwh if (not existing or existing.get("sfml_forecast_kwh") is None) else None
            ext1 = external_1_kwh if (not existing or existing.get("external_1_kwh") is None) else None
            ext2 = external_2_kwh if (not existing or existing.get("external_2_kwh") is None) else None

            success = await self._upsert_day(
                conn,
                today_str,
                sfml_forecast_kwh=sfml,
                external_1_kwh=ext1,
                external_2_kwh=ext2,
            )

        if success:
            _LOGGER.info(
                "Morning forecasts saved to DB for %s: SFML=%.2f kWh, Ext1=%s, Ext2=%s",
                today_str,
                sfml_forecast_kwh or 0,
                f"{external_1_kwh:.2f} kWh" if external_1_kwh else "N/A",
                f"{external_2_kwh:.2f} kWh" if external_2_kwh else "N/A",
            )

        return success

    async def async_collect_evening_actual(self) -> bool:
        """Collect actual production for today at evening time. @zara"""
        today_str = date.today().isoformat()

        _LOGGER.info("Collecting evening actual production for %s", today_str)

        sfml_reader = SFMLDataReader(self._hass)
        actual_kwh = sfml_reader.get_live_yield()

        # Always get authoritative SFML forecast from daily_summaries/daily_forecasts
        sfml_forecast_kwh = await self._get_sfml_forecast(today_str)

        async with self._get_db_connection() as conn:
            if not conn:
                _LOGGER.error("No DB connection for evening actual collection")
                return False

            # Read existing row to get external forecasts
            existing = await self._get_existing_day(conn, today_str)

            ext1_kwh = (existing or {}).get("external_1_kwh")
            ext2_kwh = (existing or {}).get("external_2_kwh")

            # Only fall back to existing SFML value if authoritative source unavailable
            if sfml_forecast_kwh is None:
                sfml_forecast_kwh = (existing or {}).get("sfml_forecast_kwh")
                if sfml_forecast_kwh is not None:
                    _LOGGER.debug("Using existing SFML forecast for %s: %.2f kWh", today_str, sfml_forecast_kwh)
            else:
                existing_sfml = (existing or {}).get("sfml_forecast_kwh")
                if existing_sfml is not None and abs(existing_sfml - sfml_forecast_kwh) > 0.01:
                    _LOGGER.info(
                        "Correcting SFML forecast for %s: %.2f → %.2f kWh (from authoritative source)",
                        today_str, existing_sfml, sfml_forecast_kwh,
                    )

            # Compute accuracies
            sfml_acc = _compute_accuracy(actual_kwh, sfml_forecast_kwh)
            ext1_acc = _compute_accuracy(actual_kwh, ext1_kwh)
            ext2_acc = _compute_accuracy(actual_kwh, ext2_kwh)

            best = _determine_best_source(sfml_acc, ext1_acc, ext2_acc)

            success = await self._upsert_day(
                conn,
                today_str,
                actual_kwh=actual_kwh,
                sfml_forecast_kwh=sfml_forecast_kwh,
                sfml_accuracy_percent=sfml_acc,
                external_1_accuracy_percent=ext1_acc,
                external_2_accuracy_percent=ext2_acc,
                best_source=best,
            )

            # Cleanup old entries
            await self._cleanup_old_entries(conn)

        if success:
            _LOGGER.info(
                "Evening actual saved to DB for %s: Actual=%.2f kWh, SFML=%s, Ext1=%s, Ext2=%s",
                today_str,
                actual_kwh or 0,
                f"{sfml_forecast_kwh:.2f} kWh" if sfml_forecast_kwh else "N/A",
                f"{ext1_kwh:.2f} kWh" if ext1_kwh else "N/A",
                f"{ext2_kwh:.2f} kWh" if ext2_kwh else "N/A",
            )

        return success

    async def _get_all_sfml_summaries(self) -> dict[str, dict[str, Any]]:
        """Load all SFML summaries from database. @zara"""
        async with self._get_db_connection() as conn:
            if not conn:
                return {}

            try:
                async with conn.execute(
                    """SELECT date, predicted_total_kwh, actual_total_kwh, accuracy_percent
                       FROM daily_summaries
                       ORDER BY date DESC"""
                ) as cursor:
                    rows = await cursor.fetchall()

                result = {}
                for row in rows:
                    day_str = row["date"]
                    if day_str:
                        result[day_str] = {
                            "predicted_kwh": row["predicted_total_kwh"],
                            "actual_kwh": row["actual_total_kwh"],
                            "accuracy_percent": row["accuracy_percent"],
                        }

                _LOGGER.debug("Loaded %d SFML summaries from database", len(result))
                return result

            except Exception as err:
                _LOGGER.warning("Error reading SFML summaries from database: %s", err)
                return {}

    async def _get_sensor_history_from_recorder(
        self, entity_id: str, days: int
    ) -> dict[str, float | None]:
        """Get historical values from HA Recorder. @zara"""
        result: dict[str, float | None] = {}

        if not entity_id:
            return result

        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.history import state_changes_during_period

            start_time = datetime.now() - timedelta(days=days)

            states = await get_instance(self._hass).async_add_executor_job(
                state_changes_during_period,
                self._hass,
                start_time,
                None,
                entity_id,
                False,
                True,
                1000,
            )

            if entity_id not in states:
                _LOGGER.debug("No recorder data found for %s", entity_id)
                return result

            daily_values: dict[str, list[float]] = {}

            for state in states[entity_id]:
                if state.state in ("unknown", "unavailable"):
                    continue

                try:
                    value = float(state.state)
                    day_str = state.last_changed.date().isoformat()

                    if day_str not in daily_values:
                        daily_values[day_str] = []
                    daily_values[day_str].append(value)
                except (ValueError, TypeError):
                    continue

            for day_str, values in daily_values.items():
                if values:
                    result[day_str] = max(values)

            _LOGGER.debug(
                "Loaded %d days of history for %s", len(result), entity_id
            )

        except ImportError:
            _LOGGER.warning("Recorder not available for historical data")
        except Exception as err:
            _LOGGER.warning("Error reading recorder history for %s: %s", entity_id, err)

        return result

    async def async_collect_historical(self, days: int = 7) -> bool:
        """Collect historical data for the last N days into DB. @zara"""
        config = self._get_config()

        _LOGGER.info("Collecting historical forecast comparison data for last %d days", days)

        sfml_data = await self._get_all_sfml_summaries()

        sfml_reader = SFMLDataReader(self._hass)
        actual_entity = sfml_reader.get_yield_entity_id()
        external_1_entity = config.get(CONF_FORECAST_ENTITY_1)
        external_2_entity = config.get(CONF_FORECAST_ENTITY_2)

        actual_history = await self._get_sensor_history_from_recorder(actual_entity, days)
        external_1_history = await self._get_sensor_history_from_recorder(external_1_entity, days)
        external_2_history = await self._get_sensor_history_from_recorder(external_2_entity, days)

        async with self._get_db_connection() as conn:
            if not conn:
                _LOGGER.error("No DB connection for historical collection")
                return False

            end_date = date.today()
            start_date = end_date - timedelta(days=days - 1)

            current = start_date
            days_added = 0

            while current <= end_date:
                day_str = current.isoformat()

                # Check existing data and fill gaps
                existing = await self._get_existing_day(conn, day_str)

                sfml_info = sfml_data.get(day_str, {})
                sfml_forecast = sfml_info.get("predicted_kwh")
                actual_kwh = actual_history.get(day_str) or sfml_info.get("actual_kwh")
                external_1_kwh = external_1_history.get(day_str)
                external_2_kwh = external_2_history.get(day_str)

                # Skip only if ALL fields are already populated
                if existing and existing.get("actual_kwh") is not None:
                    has_gaps = (
                        (existing.get("sfml_forecast_kwh") is None and sfml_forecast is not None)
                        or (existing.get("external_1_kwh") is None and external_1_kwh is not None)
                        or (existing.get("external_2_kwh") is None and external_2_kwh is not None)
                    )
                    if not has_gaps:
                        current += timedelta(days=1)
                        continue

                if sfml_forecast is not None or actual_kwh is not None or external_1_kwh is not None or external_2_kwh is not None:
                    sfml_acc = _compute_accuracy(actual_kwh, sfml_forecast)
                    ext1_acc = _compute_accuracy(actual_kwh, external_1_kwh)
                    ext2_acc = _compute_accuracy(actual_kwh, external_2_kwh)
                    best = _determine_best_source(sfml_acc, ext1_acc, ext2_acc)

                    await self._upsert_day(
                        conn,
                        day_str,
                        actual_kwh=actual_kwh,
                        sfml_forecast_kwh=sfml_forecast,
                        sfml_accuracy_percent=sfml_acc,
                        external_1_kwh=external_1_kwh,
                        external_1_accuracy_percent=ext1_acc,
                        external_2_kwh=external_2_kwh,
                        external_2_accuracy_percent=ext2_acc,
                        best_source=best,
                    )
                    days_added += 1

                current += timedelta(days=1)

        _LOGGER.info(
            "Historical forecast comparison data collected: %d days added to DB",
            days_added,
        )
        return True

    async def async_repair_missing_sfml_forecasts(self, days: int = 7) -> int:
        """Repair missing SFML forecasts from database. @zara"""
        _LOGGER.info("Repairing missing SFML forecasts for last %d days", days)

        sfml_data = await self._get_all_sfml_summaries()

        async with self._get_db_connection() as conn:
            if not conn:
                return 0

            repaired_count = 0
            end_date = date.today()
            start_date = end_date - timedelta(days=days - 1)

            current = start_date
            while current <= end_date:
                day_str = current.isoformat()
                existing = await self._get_existing_day(conn, day_str)

                if existing and existing.get("sfml_forecast_kwh") is None:
                    sfml_info = sfml_data.get(day_str, {})
                    sfml_forecast = sfml_info.get("predicted_kwh")

                    if sfml_forecast is not None:
                        actual_kwh = existing.get("actual_kwh")
                        sfml_acc = _compute_accuracy(actual_kwh, sfml_forecast)

                        # Recompute best_source
                        ext1_acc = existing.get("external_1_accuracy_percent")
                        ext2_acc = existing.get("external_2_accuracy_percent")
                        best = _determine_best_source(sfml_acc, ext1_acc, ext2_acc)

                        await self._upsert_day(
                            conn,
                            day_str,
                            sfml_forecast_kwh=sfml_forecast,
                            sfml_accuracy_percent=sfml_acc,
                            best_source=best,
                        )

                        _LOGGER.info("Repaired SFML forecast for %s: %.2f kWh", day_str, sfml_forecast)
                        repaired_count += 1

                current += timedelta(days=1)

        if repaired_count > 0:
            _LOGGER.info("Repaired %d missing SFML forecasts in DB", repaired_count)

        return repaired_count
