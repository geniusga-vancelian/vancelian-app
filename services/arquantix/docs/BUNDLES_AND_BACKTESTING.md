# Bundles and Backtesting

## Bundle Weight Storage

### Database Schema

Bundle weights are stored in the `bundle_components` table with the following structure:

- **Table**: `bundle_components`
- **Column**: `weight` (type: `Numeric(10, 4)`)
- **Storage Format**: **Percentage (0-100)**
- **Example**: A weight of `80.0` means 80% (0.8 as a fraction)

### Weight Conversion

When resolving bundle weights for backtesting:

1. **Storage**: Weights are stored as percentages (0-100) in the database
2. **Resolution**: The `resolve_bundle_effective_weights()` function converts percentages to fractions (0-1)
3. **Validation**: After conversion, weights must:
   - All be > 0
   - Sum to 1.0 (within tolerance 1e-6)

### Example

```python
# In database: BundleComponent.weight = 80.0 (80%)
# After conversion: 0.8 (fraction)
# Validation: sum([0.8, 0.2]) == 1.0 ✅
```

## Bundle Resolver

### Function: `resolve_bundle_effective_weights()`

**Location**: `api/services/bundles/resolver.py`

**Purpose**: Resolve effective weights for a bundle at a given date.

**Input**:
- `db`: SQLAlchemy session
- `bundle_id`: Bundle ID (int)
- `target_date`: Date (date)

**Output**:
- `Dict[int, float]`: Map of instrument_id -> weight (fraction 0-1)

**Conversion**:
- Reads `BundleComponent.weight` from database (percentage 0-100)
- Converts to fraction: `weight_fraction = weight / 100.0`
- Validates: all weights > 0, sum == 1.0 (tolerance 1e-6)

**Errors**:
- Raises `BundleValidationError` if:
  - Bundle not found
  - Component has no weight
  - Component has non-positive weight
  - Weights sum != 1.0

## CPPI Integration

### Error Handling

When CPPI strategy uses a bundle:

1. **Resolver Call**: `resolve_bundle_effective_weights()` is called
2. **Validation Error**: If bundle weights are invalid, `BundleValidationError` is raised
3. **Executor Catch**: CPPI executor catches `BundleValidationError` and converts to `ValueError` with clear message
4. **API Response**: FastAPI route catches `ValueError` and returns:
   - **422 Unprocessable Entity** if error message contains "Invalid bundle allocation"
   - **400 Bad Request** for other validation errors

### Error Message Format

```
Invalid bundle allocation: {error_details}. Weights must sum to 100% (or 1.0) and be > 0.
```

## Validation Rules

### Strict Validation

1. **No Normalization**: Weights are NOT normalized. Invalid weights cause errors.
2. **Tolerance**: Sum validation uses tolerance 1e-6 (0.000001)
3. **Positive Weights**: All weights must be > 0 (strict)

### Example Validation Failures

```python
# ❌ Invalid: weights sum to 99% (0.99 as fraction)
weights = {1: 0.60, 2: 0.39}  # Sum = 0.99
# Error: "Bundle {id} weights sum to 0.990000 (fraction) / 99.00% (percentage), expected 1.0 / 100.0"

# ❌ Invalid: negative weight
weights = {1: 0.50, 2: -0.10}  # Negative weight
# Error: "Bundle {id} component for instrument 2 has non-positive weight: -10.0%"

# ✅ Valid: weights sum to 100% (1.0 as fraction)
weights = {1: 0.60, 2: 0.40}  # Sum = 1.0
```

## Bundle Types

### Fixed Instruments

- Type: `"fixed_instruments"`
- Resolution: Direct conversion from `BundleComponent.weight` (percentage) to fraction
- Validation: Same as above

### Composite Fixed

- Type: `"composite_fixed"`
- Resolution: Recursively resolves child bundles, aggregates weights
- Validation: Same as above (strict, no normalization)

### Dynamic

- Type: `"dynamic"`
- Status: Not yet implemented
- Error: Raises `BundleValidationError` if attempted

