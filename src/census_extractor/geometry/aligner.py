"""
Continuation Page Row Alignment using Normalized Vertical Coordinates.
Formulates cross-page alignment as a monotonic minimum-distance matching problem:
j = argmin |y_i^(t) - y_j^(t+1)|
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from .row_segmenter import RowCrop


@dataclass
class MatchedRowPair:
    pair_index: int
    anchor_row: RowCrop
    continuation_row: Optional[RowCrop]
    vertical_distance: float
    confidence: float
    is_aligned: bool


class ContinuationAligner:
    def __init__(self, max_distance_tolerance: float = 0.08):
        self.max_distance = max_distance_tolerance

    def align_rows(
        self, anchor_rows: List[RowCrop], continuation_rows: List[RowCrop]
    ) -> List[MatchedRowPair]:
        """Aligns anchor page rows with continuation page rows using normalized y positions."""
        N = len(anchor_rows)
        M = len(continuation_rows)

        if N == 0:
            return []
        if M == 0:
            return [
                MatchedRowPair(
                    pair_index=i,
                    anchor_row=r,
                    continuation_row=None,
                    vertical_distance=1.0,
                    confidence=0.0,
                    is_aligned=False,
                )
                for i, r in enumerate(anchor_rows)
            ]

        # If equal count, compute direct pairwise distance
        if N == M:
            pairs = []
            for i in range(N):
                dist = abs(anchor_rows[i].y_normalized - continuation_rows[i].y_normalized)
                conf = (
                    max(0.0, 1.0 - (dist / self.max_distance)) if dist <= self.max_distance else 0.5
                )
                pairs.append(
                    MatchedRowPair(
                        pair_index=i,
                        anchor_row=anchor_rows[i],
                        continuation_row=continuation_rows[i],
                        vertical_distance=dist,
                        confidence=conf,
                        is_aligned=(dist <= self.max_distance),
                    )
                )
            return pairs

        # If counts differ (N != M), solve Dynamic Programming Monotonic Sequence Matching
        # DP[i, j] = min cost to match first i anchor rows with a subset of first j continuation rows
        matched_indices = self._solve_monotonic_dp(
            [r.y_normalized for r in anchor_rows], [r.y_normalized for r in continuation_rows]
        )

        pairs = []
        for i, r in enumerate(anchor_rows):
            j = matched_indices.get(i)
            if j is not None and j < M:
                c_row = continuation_rows[j]
                dist = abs(r.y_normalized - c_row.y_normalized)
                conf = max(0.0, 1.0 - (dist / self.max_distance))
                is_aligned = dist <= self.max_distance
            else:
                c_row = None
                dist = 1.0
                conf = 0.0
                is_aligned = False

            pairs.append(
                MatchedRowPair(
                    pair_index=i,
                    anchor_row=r,
                    continuation_row=c_row,
                    vertical_distance=dist,
                    confidence=conf,
                    is_aligned=is_aligned,
                )
            )

        return pairs

    def _solve_monotonic_dp(self, y_anchor: List[float], y_cont: List[float]) -> Dict[int, int]:
        """Finds monotonic mapping i -> j minimizing sum of absolute differences."""
        N, M = len(y_anchor), len(y_cont)
        if N > M:
            # More anchor rows than continuation rows: match continuation rows to nearest anchor
            # and map reverse
            rev_map = self._solve_monotonic_dp(y_cont, y_anchor)
            return {v: k for k, v in rev_map.items()}

        # Cost matrix DP of shape (N+1, M+1)
        dp = np.full((N + 1, M + 1), float("inf"))
        parent = np.full((N + 1, M + 1), -1, dtype=int)
        dp[0, :] = 0.0

        for i in range(1, N + 1):
            for j in range(i, M + 1):
                cost = abs(y_anchor[i - 1] - y_cont[j - 1])
                # Option 1: match i to j
                if dp[i - 1, j - 1] + cost < dp[i, j]:
                    dp[i, j] = dp[i - 1, j - 1] + cost
                    parent[i, j] = j - 1

                # Option 2: skip continuation row j (take best previous match)
                if dp[i, j - 1] < dp[i, j]:
                    dp[i, j] = dp[i, j - 1]
                    parent[i, j] = parent[i, j - 1]

        # Backtrack
        matched: Dict[int, int] = {}
        curr_j = M
        for i in range(N, 0, -1):
            matched_j = parent[i, curr_j]
            if matched_j != -1:
                matched[i - 1] = matched_j
                curr_j = matched_j
            else:
                # Nearest fallback
                matched[i - 1] = min(i - 1, M - 1)

        return matched
