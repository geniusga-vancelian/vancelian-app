/**
 * Validate Lombard production env completeness (no network).
 *
 * Usage:
 *   pnpm lombard:smoke:prod-env
 *   LOMBARD_V1_ENABLED=true pnpm lombard:smoke:prod-env --strict
 */
import { validateLombardProductionEnv } from '../src/lib/portal/lombard/lombardProdEnvValidation'

const strict = process.argv.includes('--strict')
const json = process.argv.includes('--json')

function main() {
  const lombardEnabled = process.env.LOMBARD_V1_ENABLED?.trim().toLowerCase() !== 'false'
  const result = validateLombardProductionEnv({
    lombardEnabled,
    throwOnFailure: strict && lombardEnabled,
  })

  if (json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
  } else {
    for (const row of result.checks) {
      console.log(`${row.ok ? 'OK' : 'FAIL'}  ${row.name} — ${row.detail}`)
    }
    console.log(
      result.ok
        ? '[lombard:smoke:prod-env] all required checks passed'
        : `[lombard:smoke:prod-env] missing: ${result.missing.join(', ')}`,
    )
  }

  process.exit(result.ok ? 0 : 1)
}

main()
