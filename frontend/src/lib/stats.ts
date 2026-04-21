/**
 * Wilson score confidence interval for a binomial proportion.
 * More accurate than the normal approximation at small n and at p close to 0 or 1.
 */
export function wilsonCI(
  correct: number,
  total: number,
  z = 1.96,
): { low: number; high: number } {
  if (total <= 0) return { low: 0, high: 0 }
  const p = correct / total
  const z2 = z * z
  const denom = 1 + z2 / total
  const center = (p + z2 / (2 * total)) / denom
  const margin = (z * Math.sqrt((p * (1 - p)) / total + z2 / (4 * total * total))) / denom
  return {
    low: Math.max(0, center - margin),
    high: Math.min(1, center + margin),
  }
}

/** `n` threshold below which CI visualizations should get a low-confidence treatment. */
export const LOW_SAMPLE_THRESHOLD = 10
