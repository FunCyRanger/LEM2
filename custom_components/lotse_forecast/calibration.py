from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class CalibrationModel:
    """EMA-based calibration model for solar forecast correction.

    Maintains a global scale factor (EMA of actual/raw ratio) and
    per-cloud-cover-bucket factors that track residual deviations
    from the global scale. Cloud factors model the *difference* from
    the global average — they do not compound with global_scale.

    The model state can be serialized via to_dict/from_dict for
    persistence across restarts (e.g. via RestoreEntity attributes).
    """

    def __init__(self, alpha: float = 0.2, cloud_buckets: int = 5) -> None:
        self.alpha = alpha
        self.cloud_buckets = cloud_buckets
        self.global_scale = 1.0
        self.cloud_factors: list[float] = [1.0] * cloud_buckets
        self.sample_count = 0
        self.mape: float | None = None
        self.today_predicted: dict[str, float] = {}
        self._raw_predicted: dict[str, float] = {}
        self._ape_sum = 0.0
        self.last_se_snapshot: float | None = None

    def _cloud_bucket(self, cloud_cover: float) -> int:
        """Map cloud cover percentage (0-100) to bucket index.
        
        Args:
            cloud_cover: Cloud cover in percentage (0-100).
            
        Returns:
            Bucket index (0 to cloud_buckets-1).
        """
        clamped = max(0, min(100, cloud_cover))
        bucket = int(clamped * self.cloud_buckets / 100)
        return min(bucket, self.cloud_buckets - 1)

    def update(
        self,
        actual_wh: float,
        raw_wh: float,
        cloud_cover: float | None = None,
    ) -> None:
        """Learn from one hour of actual vs raw forecast.

        Skips night-time or zero-raw samples. Updates the global scale
        EMA, then updates the cloud-cover bucket factor as a residual
        from the global scale (so they don't compound).
        
        Args:
            actual_wh: Actual measured energy (Wh).
            raw_wh: Raw forecast energy (Wh).
            cloud_cover: Optional cloud cover (0-100%).
        """
        if raw_wh <= 0:
            return
        ratio = actual_wh / raw_wh
        ratio = max(0.1, min(3.0, ratio))

        self.global_scale += self.alpha * (ratio - self.global_scale)

        if cloud_cover is not None:
            bucket = self._cloud_bucket(cloud_cover)
            residual = ratio / self.global_scale if self.global_scale > 0 else 1.0
            residual = max(0.1, min(3.0, residual))
            self.cloud_factors[bucket] += self.alpha * (
                residual - self.cloud_factors[bucket]
            )

        self.sample_count += 1
        pct_error = abs(actual_wh - raw_wh) / raw_wh * 100
        self._ape_sum += pct_error
        self.mape = self._ape_sum / self.sample_count

    def apply(self, raw_wh: float, cloud_cover: float | None = None) -> float:
        """Calibrate a raw forecast value.

        Applies global_scale * cloud_factor (if cloud data available).
        Cloud factors model residual from global scale, so the product
        represents the total correction.
        
        Args:
            raw_wh: Raw forecast energy (Wh).
            cloud_cover: Optional cloud cover (0-100%).
            
        Returns:
            Calibrated energy >= 0.
        """
        adjusted = raw_wh * self.global_scale
        if cloud_cover is not None:
            bucket = self._cloud_bucket(cloud_cover)
            adjusted *= self.cloud_factors[bucket]
        return max(0, adjusted)

    def store_forecast(self, calibrated: dict[str, float],
                       raw: dict[str, float] | None = None,
                       now: datetime | None = None) -> None:
        """Cache today's forecast (calibrated + raw) for past-hour merge + training.
        
        Args:
            calibrated: ISO timestamp → calibrated energy (Wh).
            raw: Optional ISO timestamp → raw energy (Wh).
            now: Reference time (default: UTC now).
        """
        if now is None:
            now = datetime.now(timezone.utc)
        today = now.date()
        self.today_predicted = {
            ts: wh for ts, wh in calibrated.items()
            if datetime.fromisoformat(ts).date() == today
        }
        if raw:
            self._raw_predicted = {
                ts: wh for ts, wh in raw.items()
                if datetime.fromisoformat(ts).date() == today
            }

    def reset(self) -> None:
        """Reset model to initial state (identity scaling, no training)."""
        self.global_scale = 1.0
        self.cloud_factors = [1.0] * self.cloud_buckets
        self.sample_count = 0
        self.mape = None
        self._ape_sum = 0.0
        self.today_predicted = {}
        self._raw_predicted = {}
        _LOGGER.info("Calibration model reset to defaults")

    def to_dict(self) -> dict:
        """Serialize model state for persistence.
        
        Returns:
            Dict with global_scale, cloud_factors, sample_count, mape, alpha.
        """
        return {
            "global_scale": self.global_scale,
            "cloud_factors": list(self.cloud_factors),
            "sample_count": self.sample_count,
            "mape": self.mape,
            "alpha": self.alpha,
            "today_predicted": self.today_predicted,
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> CalibrationModel:
        """Reconstruct model from serialized state.
        
        Args:
            data: Dict from to_dict().
            **kwargs: Override alpha or cloud_buckets.
            
        Returns:
            Restored CalibrationModel.
            
        Raises:
            ValueError: If cloud_factors length doesn't match cloud_buckets.
        """
        alpha = data.get("alpha", kwargs.get("alpha", 0.2))
        cloud_buckets = kwargs.get("cloud_buckets", 5)
        
        model = cls(alpha=alpha, cloud_buckets=cloud_buckets)
        
        # Validate and restore cloud_factors
        cf = data.get("cloud_factors", [1.0] * cloud_buckets)
        if len(cf) != cloud_buckets:
            _LOGGER.warning(
                "Cloud factors length %d doesn't match buckets %d; using defaults",
                len(cf), cloud_buckets
            )
            cf = [1.0] * cloud_buckets
        model.cloud_factors = list(cf)
        
        model.global_scale = float(data.get("global_scale", 1.0))
        model.sample_count = int(data.get("sample_count", 0))
        model.mape = data.get("mape")
        model.today_predicted = dict(data.get("today_predicted", {}))
        
        return model


def merge_past_hours(cache: dict[str, float], raw: dict[str, float],
                    now: datetime | None = None) -> dict[str, float]:
    """Merge cached past-hour values with raw forecast.
    
    For hours that have passed today, use cached (actual) values.
    For current and future hours, use raw forecast.
    Ignore cache from previous days.
    
    Args:
        cache: Past hours' actual/calibrated forecast (ISO → Wh).
        raw: Raw forecast (ISO → Wh).
        now: Reference time (default: UTC now).
        
    Returns:
        Merged forecast (ISO → Wh).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    if not raw:
        return {}
    
    today = now.date()
    merged = {}
    
    for ts, wh in raw.items():
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            # Can't parse timestamp; use raw
            merged[ts] = wh
            continue
        
        # If hour is in the past (before now) and same day, prefer cache
        if dt.date() == today and dt < now:
            if ts in cache:
                merged[ts] = cache[ts]
            else:
                merged[ts] = wh
        else:
            # Current or future hour: use raw
            merged[ts] = wh
    
    return merged


def compute_mape(actuals: list[float], forecasts: list[float]) -> float | None:
    """Compute Mean Absolute Percentage Error.
    
    Args:
        actuals: Actual measured values.
        forecasts: Forecast values.
        
    Returns:
        MAPE as percentage, or None if empty.
        
    Raises:
        ValueError: If lists have different lengths.
    """
    if not actuals:
        return None
    
    if len(actuals) != len(forecasts):
        raise ValueError(
            f"Mismatched lengths: {len(actuals)} actuals vs {len(forecasts)} forecasts"
        )
    
    errors = []
    for actual, forecast in zip(actuals, forecasts):
        if actual == 0:
            # Avoid division by zero; use small epsilon
            denom = max(0.001, abs(forecast))
        else:
            denom = abs(actual)
        
        error = abs(actual - forecast) / denom * 100
        errors.append(error)
    
    return sum(errors) / len(errors) if errors else None
