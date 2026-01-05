-- ============================================================================
-- INVESTIGATION QUERY: High Cant Deficiency (Eu) Analysis
-- ============================================================================
-- Purpose: Inspect rows where Eu is approx 10.26" to understand why it's so high.
-- This usually happens if:
-- 1. Speed (V) is very high on a sharp curve (High Ee)
-- 2. Actual Superelevation (Ea) is missing or negative (Inverse logic?)
-- 3. Data anomaly (Spike in Speed or Curvature)
-- ============================================================================

SELECT
  RunID,
  MP,
  MPFoot,
  Date(ReportDate) as Date,
  
  -- The core value we are investigating
  Eu_unbalanced_inches,
  
  -- The components of Eu (Eu = Ee - Ea)
  Ee_equilibrium_inches,
  Ea_actual_inches AS Ea_XLEVEL,
  
  -- Input variables
  V_speed_mph,
  D_curve_degrees,
  CURVE_CANON_MEDIAN,
  
  -- Context
  L_star_normalized_lateral_index,
  balance_status,
  rail_loading_bias

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`

-- Filter for the extreme values mentioned in feedback
WHERE Eu_unbalanced_inches > 10.0

ORDER BY Eu_unbalanced_inches DESC;
