def largest_remainder_pct(counts: list[int]) -> list[int]:
    """Convert raw counts into integer percentages that sum to exactly 100.

    Plain round() on each share can land on 99 or 101 (e.g. three equal
    thirds round to 33/33/33 = 99). The largest-remainder method assigns
    the leftover point(s) to the entries with the biggest rounding error,
    so the UI never has to "fix" the math itself.
    """
    total = sum(counts)

    if total <= 0:
        return [0 for _ in counts]

    raw_shares = [count * 100 / total for count in counts]
    floored = [int(share) for share in raw_shares]
    remainder = 100 - sum(floored)

    remainders = sorted(
        range(len(counts)),
        key=lambda i: raw_shares[i] - floored[i],
        reverse=True,
    )

    result = list(floored)
    for i in remainders[:remainder]:
        result[i] += 1

    return result
