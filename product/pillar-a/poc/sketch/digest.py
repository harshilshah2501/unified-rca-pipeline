from __future__ import annotations

from typing import Protocol

from tdigest import TDigest


class Digest(Protocol):
    def update(self, x: float) -> None: ...
    def quantile(self, q: float) -> float: ...
    def merge(self, other: Digest) -> None: ...
    def to_centroids(self) -> list[dict]: ...
    def sample_count(self) -> int: ...


class TDigestAdapter:
    def __init__(self, compression: float = 100.0) -> None:
        self.compression = compression
        self._td = TDigest()
        self._n = 0

    def update(self, x: float) -> None:
        self._td.update(x)
        self._n += 1

    def quantile(self, q: float) -> float:
        if self._n == 0:
            return 0.0
        return float(self._td.percentile(q * 100.0))

    def merge(self, other: Digest) -> None:
        if not isinstance(other, TDigestAdapter):
            raise TypeError("can only merge TDigestAdapter")
        self._td = self._td + other._td
        self._n += other._n

    def to_centroids(self) -> list[dict]:
        cents = []
        for c in getattr(self._td, "C", []):
            # tdigest Centroid has mean and count
            m = getattr(c, "mean", None)
            w = getattr(c, "count", None)
            if m is None:
                continue
            cents.append({"m": float(m), "w": float(w or 1)})
        if not cents and self._n:
            # fallback single centroid
            cents = [{"m": self.quantile(0.5), "w": float(self._n)}]
        return cents

    def sample_count(self) -> int:
        return self._n

    def to_json_body(self) -> dict:
        return {
            "compression": self.compression,
            "encoding": "centroids_json",
            "centroids": self.to_centroids(),
        }

    @classmethod
    def from_json_body(cls, body: dict) -> "TDigestAdapter":
        compression = float(body.get("compression", 100.0))
        adapter = cls(compression=compression)
        for c in body.get("centroids") or []:
            m = float(c["m"])
            w = int(float(c.get("w", 1)))
            for _ in range(max(w, 1)):
                adapter.update(m)
        return adapter
