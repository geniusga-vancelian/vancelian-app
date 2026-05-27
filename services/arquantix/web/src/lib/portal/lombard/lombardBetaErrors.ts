export class LombardBetaError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'LombardBetaError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

export class LombardSafetyError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'LombardSafetyError'
    this.code = code
    this.httpStatus = httpStatus
  }
}
