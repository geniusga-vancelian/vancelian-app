"""Price Alert Trigger Engine — institutional-grade.

Enhancements over hardened version:
  - Deterministic cross ordering (ASC for up, DESC for down)
  - Notification dedup (Redis key with 2s TTL)
  - Priority execution (orders before alerts)
  - Latency control (MAX_PROCESSING_MS budget per tick, defer remainder)
  - Recurring alerts (trigger_mode='recurring' stays active)
  - Extended metrics (dedup_skips, deferred_alerts, processing_time_per_tick)

Order execution hardening:
  - Pre-execution price check (skip if price moved beyond safety bounds)
  - Retry window (max 3 attempts within 1s window)
  - Partial fill detection and metadata tracking
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from services.price_alerts.cache import (
    add_alert_to_cache,
    check_notif_dedup,
    get_and_set_price,
    get_crossed_alert_ids_sorted,
    remove_alert_from_cache,
)
from services.price_alerts.metrics import LatencyTimer, get_metrics

logger = logging.getLogger(__name__)

MAX_PROCESSING_MS = 50.0


class PriceAlertEngine:
    """Stateless engine — all state lives in Redis + PostgreSQL."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self._deferred: list[tuple[str, str, float, str, str]] = []

    def on_price_batch(self, ticks: dict[str, dict], db_factory) -> int:
        """Process a batch of price ticks. Returns total triggered alerts."""
        metrics = get_metrics()
        total_triggered = 0

        for symbol, prices in ticks.items():
            with LatencyTimer() as tick_timer:
                asset = self._symbol_to_asset(symbol)
                if asset is None:
                    continue

                bid = self._extract_price(prices, "bid")
                ask = self._extract_price(prices, "ask")
                last = self._extract_price(prices, "last")

                if bid is None or ask is None:
                    if last is not None:
                        bid = bid or last
                        ask = ask or last
                    else:
                        continue

                mid = (bid + ask) / 2.0

                prev_bid = get_and_set_price(self.redis, asset, "bid", bid)
                prev_ask = get_and_set_price(self.redis, asset, "ask", ask)
                prev_mid = get_and_set_price(self.redis, asset, "mid", mid)

                tick_time = datetime.now(timezone.utc)

                triggered = 0
                triggered += self._check_source(asset, "mid", prev_mid, mid, tick_time, db_factory)
                triggered += self._check_source(asset, "bid", prev_bid, bid, tick_time, db_factory)
                triggered += self._check_source(asset, "ask", prev_ask, ask, tick_time, db_factory)
                total_triggered += triggered

            metrics.record_tick(tick_timer.elapsed_ms)

        if self._deferred:
            self._process_deferred(db_factory)

        return total_triggered

    def _check_source(
        self,
        asset: str,
        source: str,
        prev_price: Optional[float],
        current_price: float,
        tick_time: datetime,
        db_factory,
    ) -> int:
        if prev_price is None:
            return 0
        if abs(current_price - prev_price) < 1e-10:
            return 0

        if current_price > prev_price:
            pairs = get_crossed_alert_ids_sorted(self.redis, asset, "up", prev_price, current_price)
            direction = "up"
        else:
            pairs = get_crossed_alert_ids_sorted(self.redis, asset, "down", current_price, prev_price)
            direction = "down"

        if not pairs:
            return 0

        ids = [aid for aid, _ in pairs]
        logger.debug(
            "Crossing detected: asset=%s source=%s direction=%s prev=%.2f curr=%.2f candidates=%d ids=%s",
            asset, source, direction, prev_price, current_price, len(ids), ids[:5],
        )
        return self._process_triggered(ids, asset, current_price, source, direction, tick_time, db_factory)

    def _process_triggered(
        self,
        alert_ids: list[str],
        asset: str,
        current_price: float,
        source: str,
        direction: str,
        tick_time: datetime,
        db_factory,
    ) -> int:
        from services.price_alerts.models import PriceAlert

        metrics = get_metrics()
        db: Optional[Session] = None
        triggered = 0
        start = time.monotonic()

        # Deduplicate IDs (same alert can appear in multiple buckets)
        seen_ids: set[str] = set()
        unique_ids: list[str] = []
        for aid in alert_ids:
            if aid not in seen_ids:
                seen_ids.add(aid)
                unique_ids.append(aid)
        alert_ids = unique_ids

        with LatencyTimer() as timer:
            try:
                db = db_factory()
                now = datetime.now(timezone.utc)

                alerts = (
                    db.query(PriceAlert)
                    .filter(
                        PriceAlert.id.in_(alert_ids),
                        PriceAlert.status == "active",
                    )
                    .with_for_update(skip_locked=True)
                    .all()
                )

                alert_map = {str(a.id): a for a in alerts}

                order_alerts = []
                simple_alerts = []
                for aid in alert_ids:
                    a = alert_map.get(aid)
                    if a is None:
                        remove_alert_from_cache(self.redis, aid, asset, direction)
                        logger.debug("Removed stale cache entry: id=%s asset=%s dir=%s", aid, asset, direction)
                        continue
                    if a.price_source != source:
                        logger.debug(
                            "Skipping alert %s: price_source=%s != current_source=%s (will match on correct source)",
                            aid, a.price_source, source,
                        )
                        continue
                    if a.action_type == "order" and a.order_payload:
                        order_alerts.append(a)
                    else:
                        simple_alerts.append(a)

                if order_alerts or simple_alerts:
                    logger.info(
                        "Processing %d order(s) + %d alert(s) for %s [%s/%s] at %.2f",
                        len(order_alerts), len(simple_alerts), asset, source, direction, current_price,
                    )

                for alert in order_alerts + simple_alerts:
                    elapsed_ms = (time.monotonic() - start) * 1000.0
                    if elapsed_ms > MAX_PROCESSING_MS:
                        remaining = [str(a.id) for a in simple_alerts if str(a.id) not in {str(x.id) for x in order_alerts + simple_alerts[:simple_alerts.index(alert)]}]
                        if remaining:
                            for rid in remaining:
                                self._deferred.append((rid, asset, current_price, source, direction))
                            metrics.record_deferred(len(remaining))
                            logger.warning(
                                "Latency budget exceeded (%.1fms > %.1fms), deferred %d alert(s) for %s",
                                elapsed_ms, MAX_PROCESSING_MS, len(remaining), asset,
                            )
                        break

                    result = self._trigger_single(alert, asset, current_price, source, direction, now, db)
                    if result:
                        triggered += 1

                if triggered > 0:
                    db.commit()
                    logger.info(
                        "Triggered %d alert(s) for %s [%s] at %.2f (%.1fms)",
                        triggered, asset, source, current_price, timer.elapsed_ms,
                    )
            except Exception:
                if db is not None:
                    db.rollback()
                logger.exception("Error processing triggered alerts for %s", asset)

                self._rescue_failed_orders(
                    order_alerts, asset, direction, db_factory,
                )
            finally:
                if db is not None:
                    db.close()

        if triggered > 0:
            metrics.record_trigger(asset, triggered, timer.elapsed_ms)

        return triggered

    def _trigger_single(
        self,
        alert,
        asset: str,
        current_price: float,
        source: str,
        direction: str,
        now: datetime,
        db: Session,
    ) -> bool:
        """Process a single alert. Returns True if triggered."""
        metrics = get_metrics()

        if alert.cooldown_seconds and alert.cooldown_seconds > 0 and alert.last_triggered_at is not None:
            elapsed = (now - alert.last_triggered_at).total_seconds()
            if elapsed < alert.cooldown_seconds:
                metrics.record_cooldown_skip()
                return False

        is_recurring = getattr(alert, "trigger_mode", "once") == "recurring"

        if is_recurring:
            alert.last_triggered_at = now
            alert.triggered_price = current_price
            alert.trigger_count = (alert.trigger_count or 0) + 1
            alert.metadata_ = {
                "source": source,
                "direction": direction,
                "cross_price": current_price,
                "cross_timestamp": now.isoformat(),
            }
            metrics.record_recurring_trigger()
        else:
            alert.status = "triggered"
            alert.triggered_at = now
            alert.last_triggered_at = now
            alert.triggered_price = current_price
            alert.trigger_count = (alert.trigger_count or 0) + 1
            alert.metadata_ = {
                "source": source,
                "direction": direction,
                "cross_price": current_price,
                "cross_timestamp": now.isoformat(),
            }
            remove_alert_from_cache(self.redis, str(alert.id), asset, alert.direction)

        if alert.action_type == "order" and alert.order_payload:
            alert.execution_status = "pending"
            logger.info(
                "Order trigger: id=%s asset=%s side=%s type=%s trigger=%.2f cross=%.2f source=%s",
                alert.id, asset, alert.order_payload.get("side"), alert.order_payload.get("order_type"),
                float(alert.target_price), current_price, source,
            )
            self._execute_order_hook(alert, db)
        else:
            is_dedup = check_notif_dedup(self.redis, str(alert.client_id), asset, direction)
            if is_dedup:
                metrics.record_dedup_skip()
            else:
                self._enqueue_notification(alert, asset, current_price)

        return True

    def _rescue_failed_orders(
        self,
        order_alerts: list,
        asset: str,
        direction: str,
        db_factory,
    ) -> None:
        """After a rollback in _process_triggered, persist terminal status on a fresh session."""
        if not order_alerts:
            return
        rescue_db = None
        try:
            from services.price_alerts.models import PriceAlert

            rescue_db = db_factory()
            for alert in order_alerts:
                try:
                    row = (
                        rescue_db.query(PriceAlert)
                        .filter(PriceAlert.id == alert.id)
                        .with_for_update(skip_locked=True)
                        .first()
                    )
                    if row is None:
                        continue
                    row.status = "triggered"
                    row.triggered_at = alert.triggered_at or datetime.now(timezone.utc)
                    row.triggered_price = alert.triggered_price
                    exec_status = getattr(alert, "execution_status", None)
                    row.execution_status = exec_status if exec_status != "pending" else "failed"
                    row.metadata_ = {
                        **(alert.metadata_ or {}),
                        "rescue": True,
                        "failure_reason": (alert.metadata_ or {}).get("failure_reason", "commit_rollback"),
                    }
                    remove_alert_from_cache(self.redis, str(row.id), asset, direction)
                except Exception:
                    logger.exception("Rescue failed for order %s", alert.id)
            rescue_db.commit()
            logger.warning("Rescued %d order(s) after commit rollback for %s", len(order_alerts), asset)
        except Exception:
            if rescue_db is not None:
                rescue_db.rollback()
            logger.exception("Rescue session failed for %s", asset)
        finally:
            if rescue_db is not None:
                rescue_db.close()

    def _process_deferred(self, db_factory) -> None:
        """Process alerts deferred from previous ticks due to latency budget."""
        if not self._deferred:
            return
        batch = list(self._deferred)
        self._deferred.clear()

        by_key: dict[tuple[str, str, str], list[str]] = {}
        price_map: dict[tuple[str, str, str], float] = {}
        for aid, asset, price, source, direction in batch:
            key = (asset, source, direction)
            by_key.setdefault(key, []).append(aid)
            price_map[key] = price

        for key, ids in by_key.items():
            asset, source, direction = key
            price = price_map[key]
            self._process_triggered(ids, asset, price, source, direction, datetime.now(timezone.utc), db_factory)

    @staticmethod
    def _enqueue_notification(alert, asset: str, current_price: float) -> None:
        from services.notifications.dispatcher import get_dispatcher
        dispatcher = get_dispatcher()
        if dispatcher is None:
            return

        direction_label = "au-dessus de" if alert.direction == "up" else "en-dessous de"
        target_fmt = f"{float(alert.target_price):,.2f}"
        current_fmt = f"{current_price:,.2f}"
        dispatcher.enqueue(
            client_id=alert.client_id,
            type_="price_alert",
            title=f"{asset} a franchi {target_fmt} USD",
            body=f"{asset} est passé {direction_label} {target_fmt} USD (prix actuel : {current_fmt} USD)",
            payload={
                "alert_id": str(alert.id),
                "asset": asset,
                "target_price": float(alert.target_price),
                "triggered_price": current_price,
                "direction": alert.direction,
                "cross_price": current_price,
                "cross_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def _enqueue_order_notification(alert, side: str, result: dict) -> None:
        from services.notifications.dispatcher import get_dispatcher
        dispatcher = get_dispatcher()
        if dispatcher is None:
            return

        asset = alert.asset
        order_type = (alert.order_payload or {}).get("order_type", "limit").upper()
        side_label = "Achat" if side == "buy" else "Vente"
        exec_price = result.get("price")
        amount_fiat = result.get("amount_fiat") or result.get("net_eur")
        amount_crypto = result.get("amount_crypto")
        order_id = result.get("order_id")

        price_fmt = f"{float(exec_price):,.2f}" if exec_price else "—"
        status_label = "exécuté" if alert.execution_status == "executed" else "partiellement exécuté"

        title = f"{side_label} {order_type} {asset} {status_label}"
        body_parts = [f"Prix : {price_fmt} USD"]
        if side == "buy" and amount_fiat:
            body_parts.append(f"Montant : {float(amount_fiat):,.2f} EUR")
        if amount_crypto:
            body_parts.append(f"Quantité : {float(amount_crypto):.8f} {asset}")
        body = " · ".join(body_parts)

        dispatcher.enqueue(
            client_id=alert.client_id,
            type_="order_executed",
            title=title,
            body=body,
            payload={
                "alert_id": str(alert.id),
                "order_id": str(order_id) if order_id else None,
                "asset": asset,
                "side": side,
                "order_type": order_type.lower(),
                "execution_status": alert.execution_status,
                "execution_price": float(exec_price) if exec_price else None,
                "amount_fiat": float(amount_fiat) if amount_fiat else None,
                "amount_crypto": float(amount_crypto) if amount_crypto else None,
                "trigger_price": float(alert.target_price),
            },
        )

    # -- Order execution constants --
    _ORDER_MAX_ATTEMPTS = 3
    _ORDER_RETRY_WINDOW_S = 1.0
    _ORDER_DEFAULT_SAFETY_BPS = 200  # 2% default safety margin when no slippage_bps

    def _execute_order_hook(self, alert, db: Session) -> None:
        metrics = get_metrics()
        if alert.execution_status != "pending":
            return
        try:
            from decimal import Decimal
            from uuid import uuid4
            from services.exchange.service import ExchangeService
            from services.exchange.schemas import ExchangeBuyRequest, ExchangeSellRequest
            from services.portfolio_engine.hardening.security.context import ActorContext

            payload = alert.order_payload or {}
            side = payload.get("side")
            amount = payload.get("amount")

            if not side or not amount:
                alert.execution_status = "failed"
                alert.metadata_ = {**(alert.metadata_ or {}), "failure_reason": "missing_side_or_amount"}
                metrics.record_order_failed()
                return

            if side not in ("buy", "sell"):
                alert.execution_status = "failed"
                alert.metadata_ = {**(alert.metadata_ or {}), "failure_reason": f"invalid_side:{side}"}
                metrics.record_order_failed()
                return

            slippage_bps = payload.get("slippage_bps")
            safety_bps = float(slippage_bps) if slippage_bps else float(self._ORDER_DEFAULT_SAFETY_BPS)
            if not self._pre_execution_price_check(alert, side, safety_bps):
                return

            svc = ExchangeService()
            actor = ActorContext(actor_type="trigger_engine", actor_id=str(alert.id))
            remaining_amount = Decimal(str(amount))

            result = None
            attempt = 0
            last_error: Optional[str] = None
            start = time.monotonic()

            while attempt < self._ORDER_MAX_ATTEMPTS:
                attempt += 1
                if attempt > 1:
                    metrics.record_retry_attempt()
                    elapsed = time.monotonic() - start
                    if elapsed > self._ORDER_RETRY_WINDOW_S:
                        logger.warning(
                            "Retry window exhausted for alert %s (%.1fs > %.1fs) after %d attempt(s)",
                            alert.id, elapsed, self._ORDER_RETRY_WINDOW_S, attempt - 1,
                        )
                        break
                    time.sleep(0.1)

                ext_ref = f"trigger-{alert.id}-{uuid4().hex[:8]}"

                try:
                    if side == "buy":
                        req = ExchangeBuyRequest(
                            client_id=alert.client_id,
                            asset=alert.asset,
                            fiat_amount=remaining_amount,
                            currency="EUR",
                            external_reference=ext_ref,
                        )
                        result = svc.buy(db, req, actor)
                    else:
                        req = ExchangeSellRequest(
                            client_id=alert.client_id,
                            asset=alert.asset,
                            amount_crypto=remaining_amount,
                            currency="EUR",
                            external_reference=ext_ref,
                        )
                        result = svc.sell(db, req, actor)
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    logger.exception("Exchange call failed for alert %s (attempt %d/%d)", alert.id, attempt, self._ORDER_MAX_ATTEMPTS)
                    result = None
                    continue

                if result and result.get("status") == "completed":
                    break

                last_error = (result.get("reason") or result.get("error") or "unknown") if result else "no_response"
                logger.warning(
                    "Order attempt %d/%d failed for alert %s: %s",
                    attempt, self._ORDER_MAX_ATTEMPTS, alert.id, last_error,
                )

            if result is None or result.get("status") != "completed":
                alert.execution_status = "failed"
                reason = "all_attempts_failed"
                if result:
                    reason = result.get("reason") or result.get("error") or "exchange_error"
                alert.metadata_ = {
                    **(alert.metadata_ or {}),
                    "failure_reason": reason,
                    "failure_detail": last_error,
                    "exchange_status": result.get("status") if result else None,
                    "attempts": attempt,
                }
                metrics.record_order_failed()
                logger.warning("Order execution failed for alert %s after %d attempt(s): %s", alert.id, attempt, reason)
                return

            exec_price = result.get("price")
            if slippage_bps and exec_price and alert.target_price:
                trigger_px = float(alert.target_price)
                exec_px = float(exec_price)
                actual_bps = abs(exec_px - trigger_px) / trigger_px * 10000
                if actual_bps > float(slippage_bps):
                    alert.execution_status = "failed"
                    alert.metadata_ = {
                        **(alert.metadata_ or {}),
                        "failure_reason": "slippage_exceeded",
                        "slippage_bps_actual": round(actual_bps, 1),
                        "slippage_bps_max": slippage_bps,
                        "execution_price": float(exec_price),
                        "attempts": attempt,
                    }
                    metrics.record_order_failed()
                    logger.warning(
                        "Slippage exceeded for alert %s: actual=%.1fbps max=%dbps",
                        alert.id, actual_bps, slippage_bps,
                    )
                    return

            filled_crypto = result.get("amount_crypto")
            filled_fiat = result.get("amount_fiat") or result.get("net_eur")
            requested = float(amount)

            if side == "buy":
                filled_amount = float(filled_fiat or 0)
            else:
                filled_amount = float(filled_crypto or 0)

            remaining_amount = max(0.0, requested - filled_amount)

            if requested > 0 and filled_amount <= 0:
                alert.execution_status = "failed"
                alert.metadata_ = {
                    **(alert.metadata_ or {}),
                    "failure_reason": "zero_fill",
                    "filled_amount": 0,
                    "remaining_amount": requested,
                    "attempts": attempt,
                }
                metrics.record_order_failed()
                logger.warning("Order zero-fill for alert %s", alert.id)
                return

            is_partial = (filled_amount / requested) < 0.995 if requested > 0 else False

            if is_partial:
                alert.execution_status = "partial"
                metrics.record_partial_fill()
                metrics.record_partial_remaining(remaining_amount)
                logger.info(
                    "Order partial fill for alert %s: filled=%.4f / requested=%.4f remaining=%.4f",
                    alert.id, filled_amount, requested, remaining_amount,
                )
            else:
                alert.execution_status = "executed"
                metrics.record_order_executed()

            alert.metadata_ = {
                **(alert.metadata_ or {}),
                "execution_price": float(exec_price) if exec_price else None,
                "order_id": str(result.get("order_id")) if result.get("order_id") else None,
                "amount_crypto": float(filled_crypto or 0),
                "amount_fiat": float(filled_fiat or 0),
                "filled_amount": filled_amount,
                "remaining_amount": remaining_amount,
                "attempts": attempt,
                "partial_fill": is_partial,
                "can_retry_remaining": is_partial,
            }
            logger.info(
                "Order %s for alert %s: side=%s asset=%s price=%s attempts=%d",
                alert.execution_status, alert.id, side, alert.asset, exec_price, attempt,
            )

            self._enqueue_order_notification(alert, side, result)

        except Exception:
            alert.execution_status = "failed"
            alert.metadata_ = {**(alert.metadata_ or {}), "failure_reason": "exception"}
            metrics.record_order_failed()
            logger.exception("Order execution failed for alert %s", alert.id)

        finally:
            if alert.execution_status == "pending":
                alert.execution_status = "failed"
                alert.metadata_ = {
                    **(alert.metadata_ or {}),
                    "failure_reason": "unexpected_non_terminal_exit",
                }
                metrics.record_order_failed()
                logger.error("SAFETY GUARD: order %s exited hook still pending — forced to failed", alert.id)

    def _pre_execution_price_check(self, alert, side: str, safety_bps: float) -> bool:
        """Check live price from Redis before executing. Returns False if skipped."""
        metrics = get_metrics()
        try:
            price_source = "ask" if side == "buy" else "bid"
            key = f"prices:{alert.asset.upper()}:last_{price_source}"
            raw = self.redis.get(key) if self.redis else None
            if raw is None:
                return True

            live_price = float(raw)
            trigger_px = float(alert.target_price)
            if trigger_px <= 0:
                return True

            deviation_bps = abs(live_price - trigger_px) / trigger_px * 10000

            if side == "buy" and live_price > trigger_px:
                if deviation_bps > safety_bps:
                    alert.execution_status = "failed"
                    alert.metadata_ = {
                        **(alert.metadata_ or {}),
                        "failure_reason": "price_moved_beyond_safety",
                        "live_price": live_price,
                        "trigger_price": trigger_px,
                        "deviation_bps": round(deviation_bps, 1),
                        "safety_bps": safety_bps,
                    }
                    metrics.record_skipped_price()
                    metrics.record_order_failed()
                    logger.warning(
                        "Pre-exec skip BUY alert %s: live_ask=%.2f > trigger=%.2f (%.0fbps > %.0fbps)",
                        alert.id, live_price, trigger_px, deviation_bps, safety_bps,
                    )
                    return False

            elif side == "sell" and live_price < trigger_px:
                if deviation_bps > safety_bps:
                    alert.execution_status = "failed"
                    alert.metadata_ = {
                        **(alert.metadata_ or {}),
                        "failure_reason": "price_moved_beyond_safety",
                        "live_price": live_price,
                        "trigger_price": trigger_px,
                        "deviation_bps": round(deviation_bps, 1),
                        "safety_bps": safety_bps,
                    }
                    metrics.record_skipped_price()
                    metrics.record_order_failed()
                    logger.warning(
                        "Pre-exec skip SELL alert %s: live_bid=%.2f < trigger=%.2f (%.0fbps > %.0fbps)",
                        alert.id, live_price, trigger_px, deviation_bps, safety_bps,
                    )
                    return False

        except Exception:
            logger.exception("Pre-execution price check failed for alert %s (proceeding)", alert.id)
        return True

    @staticmethod
    def _extract_price(prices: dict, kind: str) -> Optional[float]:
        raw = prices.get(f"{kind}_price") or prices.get(kind)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _symbol_to_asset(provider_symbol: str) -> Optional[str]:
        s = provider_symbol.upper()
        for suffix in ("USDT", "BUSD", "USD", "EUR"):
            if s.endswith(suffix):
                asset = s[: -len(suffix)]
                if asset:
                    return asset
        return None


_engine_instance: Optional[PriceAlertEngine] = None


def get_alert_engine() -> Optional[PriceAlertEngine]:
    return _engine_instance


def init_alert_engine(redis_client) -> Optional[PriceAlertEngine]:
    global _engine_instance
    if redis_client is None:
        logger.warning("Redis unavailable — PriceAlertEngine disabled")
        return None
    _engine_instance = PriceAlertEngine(redis_client)
    logger.info("PriceAlertEngine initialized")
    return _engine_instance
