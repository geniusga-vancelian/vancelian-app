export class LombardAsyncTimeoutError extends Error {
  readonly code = 'lombard.prepare_timeout'
  readonly step: string

  constructor(step: string, timeoutMs: number) {
    super(
      `La préparation de l'emprunt a expiré (${step}, ${Math.round(timeoutMs / 1000)} s). Réessayez dans quelques instants.`,
    )
    this.name = 'LombardAsyncTimeoutError'
    this.step = step
  }
}

export async function withLombardAsyncTimeout<T>(
  step: string,
  fn: () => Promise<T>,
  timeoutMs: number,
): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      fn(),
      new Promise<T>((_, reject) => {
        timeoutId = setTimeout(() => reject(new LombardAsyncTimeoutError(step, timeoutMs)), timeoutMs)
      }),
    ])
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}
