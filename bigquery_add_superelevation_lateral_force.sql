-- ============================================================================
-- BigQuery SQL Script: Add Superelevation and Lateral Force Index
-- ============================================================================
-- This script adds FRA/UIUC framework physics features:
-- 1. Superelevation (actual, equilibrium, unbalanced)
-- 2. Normalized Lateral Force Index (mass-free)
-- 3. Balance/deficiency/excess metrics
--
-- Source Table: Henderson_242to252_Speed_clean_canon_with_resistance
-- Output Table: Henderson_242to252_Speed_clean_canon_with_physics
-- ============================================================================

CREATE OR REPLACE TABLE `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics` AS

WITH physics_constants AS (
  -- Physical constants for calculations
  SELECT
    32.174 AS g_fps2,              -- Gravitational acceleration (ft/s²)
    5730.0 AS radius_constant      -- Radius conversion: R ≈ 5730/D for standard gauge
),

base_calculations AS (
  SELECT
    *,
    
    -- ========================================================================
    -- 3.1 SUPERELEVATION CALCULATIONS
    -- ========================================================================
    
    -- Actual superelevation (Ea): Use XLEVEL (crosslevel in inches)
    XLEVEL AS Ea_actual_inches,
    
    -- Degree of curve (D): Use absolute value of CURVE_CANON_MEDIAN
    ABS(CURVE_CANON_MEDIAN) AS D_curve_degrees,
    
    -- Speed (V): Use Speed field (mph)
    ABS(Speed) AS V_speed_mph,
    
    -- Equilibrium superelevation (Ee) for measured speed V and curve D
    -- Formula: Ee = 0.0007 × D × V² (inches)
    ROUND(0.0007 * ABS(CURVE_CANON_MEDIAN) * POWER(ABS(Speed), 2), 4) AS Ee_equilibrium_inches,
    
    -- Curve radius (R) from degree of curve (D)
    -- Formula: R ≈ 5730 / D (feet)
    -- Handle straight sections (D = 0) with very large radius
    CASE 
      WHEN ABS(CURVE_CANON_MEDIAN) > 0.01 
      THEN ROUND(5730.0 / ABS(CURVE_CANON_MEDIAN), 2)
      ELSE 1000000.0  -- Essentially infinite radius for straight track
    END AS R_curve_radius_feet
    
  FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`
),

superelevation_metrics AS (
  SELECT
    bc.*,
    pc.g_fps2,
    pc.radius_constant,
    
    -- ========================================================================
    -- UNBALANCED SUPERELEVATION (Eu)
    -- ========================================================================
    
    -- Cant deficiency: Eu = Ee - Ea
    -- Positive Eu = cant deficiency (underbalanced, speed > equilibrium)
    -- Negative Eu = cant excess (overbalanced, speed < equilibrium)
    ROUND(bc.Ee_equilibrium_inches - bc.Ea_actual_inches, 4) AS Eu_unbalanced_inches,
    
    -- Balance status classification
    CASE
      WHEN (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) > 0.5 
        THEN 'UNDERBALANCED'  -- Cant deficiency (speed too high)
      WHEN (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) < -0.5 
        THEN 'OVERBALANCED'   -- Cant excess (speed too low)
      ELSE 'BALANCED'         -- Within tolerance
    END AS balance_status,
    
    -- Magnitude of imbalance (absolute value)
    ROUND(ABS(bc.Ee_equilibrium_inches - bc.Ea_actual_inches), 4) AS imbalance_magnitude_inches,
    
    -- ========================================================================
    -- 3.2 LATERAL FORCE INDEX (MASS-FREE)
    -- ========================================================================
    
    -- Normalized lateral index: L* = Ea - V²/(g×R)
    -- This is the mass-free version of lateral force
    -- Units: inches (after scaling)
    ROUND(
      bc.Ea_actual_inches - (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) /  -- Convert mph to fps, then square
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)    -- g×R in inches
      )
    , 6) AS L_star_normalized_lateral_index,
    
    -- Alternative formulation using Eu directly
    -- L* can also be expressed as: L* = -Eu (approximately, with unit conversions)
    -- This shows the relationship between lateral force and cant deficiency
    
    -- ========================================================================
    -- LATERAL FORCE COMPONENTS
    -- ========================================================================
    
    -- V²/(g×R) term (inches) - centrifugal force component
    ROUND(
      POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
      (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
    , 6) AS centrifugal_term_inches,
    
    -- High-rail vs low-rail bias indicator
    -- Positive L* → outward force → high-rail loading
    -- Negative L* → inward force → low-rail loading
    CASE
      WHEN bc.Ea_actual_inches - (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
      ) > 0 THEN 'HIGH_RAIL_BIAS'
      WHEN bc.Ea_actual_inches - (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
      ) < 0 THEN 'LOW_RAIL_BIAS'
      ELSE 'NEUTRAL'
    END AS rail_loading_bias,
    
    -- ========================================================================
    -- QUADRATIC SENSITIVITY METRICS
    -- ========================================================================
    
    -- V² term (for sensitivity analysis)
    ROUND(POWER(bc.V_speed_mph, 2), 2) AS V_squared_mph2,
    
    -- D × V² interaction term (curve-speed interaction)
    ROUND(bc.D_curve_degrees * POWER(bc.V_speed_mph, 2), 2) AS D_V_squared_interaction,
    
    -- Lateral acceleration (g-force, unitless)
    -- a_lateral = V² / (g × R)
    ROUND(
      POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
      (pc.g_fps2 * bc.R_curve_radius_feet)
    , 6) AS lateral_acceleration_g,
    
    -- ========================================================================
    -- SAFETY AND COMFORT METRICS
    -- ========================================================================
    
    -- Cant deficiency ratio (Eu / Ee)
    -- Indicates how far from equilibrium the train is operating
    CASE 
      WHEN bc.Ee_equilibrium_inches > 0.1
      THEN ROUND(
        (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) / 
        NULLIF(bc.Ee_equilibrium_inches, 0) * 100
      , 2)
      ELSE NULL
    END AS cant_deficiency_ratio_pct,
    
    -- Speed ratio (V / V_equilibrium)
    -- V_equilibrium is the speed where Ee = Ea
    -- V_eq = SQRT(Ea / (0.0007 × D))
    CASE
      WHEN bc.D_curve_degrees > 0.01 AND bc.Ea_actual_inches > 0
      THEN ROUND(
        bc.V_speed_mph / 
        NULLIF(SQRT(bc.Ea_actual_inches / (0.0007 * bc.D_curve_degrees)), 0)
      , 4)
      ELSE NULL
    END AS speed_ratio_to_equilibrium,
    
    -- Equilibrium speed for actual superelevation
    -- V_eq = SQRT(Ea / (0.0007 × D))
    CASE
      WHEN bc.D_curve_degrees > 0.01 AND bc.Ea_actual_inches > 0
      THEN ROUND(SQRT(bc.Ea_actual_inches / (0.0007 * bc.D_curve_degrees)), 2)
      ELSE NULL
    END AS V_equilibrium_mph

  FROM base_calculations bc
  CROSS JOIN physics_constants pc
)

SELECT
  -- ========================================================================
  -- ALL ORIGINAL COLUMNS (including resistance calculations)
  -- ========================================================================
  RunID,
  Car,
  ReportDate,
  Division,
  Subdivision,
  LineCode,
  MP,
  MPFoot,
  MP_ASC_DEC,
  SyncCount,
  SyncSample,
  Speed,
  PostedClass,
  PostedSpeed,
  TrackNumber,
  LPROF31, LPROF62, LPROF124,
  RPROF31, RPROF62, RPROF124,
  LALIGN31, LALIGN62, LALIGN124,
  RALIGN31, RALIGN62, RALIGN124,
  GAUGE,
  XLEVEL,
  CTS,
  TWIST11, TWIST22, TWIST31,
  WARP62,
  LPROF_SC, RPROF_SC,
  LALIGN_SC, RALIGN_SC,
  LATITUDE, LONGITUDE,
  MP_atac, MP_100th, MP_10th, MP_10feet, MP_30feet,
  RunID_MP100th,
  LATITUDE_STR, LONGITUDE_STR,
  Grade,
  CURVE_CANON_MEDIAN, CURVE_CANON_2DP, CURVE_CANON_1DP,
  
  -- Resistance calculations (from previous table)
  weight_tons,
  res_rolling_lbs,
  res_davis_b_lbs,
  res_aero_lbs,
  res_grade_lbs,
  res_curve_lbs,
  res_total_lbs,
  power_required_kw,
  power_required_hp,
  res_rolling_pct,
  res_davis_b_pct,
  res_aero_pct,
  res_grade_pct,
  res_curve_pct,
  
  -- ========================================================================
  -- NEW SUPERELEVATION COLUMNS
  -- ========================================================================
  Ea_actual_inches,
  Ee_equilibrium_inches,
  Eu_unbalanced_inches,
  balance_status,
  imbalance_magnitude_inches,
  cant_deficiency_ratio_pct,
  V_equilibrium_mph,
  speed_ratio_to_equilibrium,
  
  -- ========================================================================
  -- NEW LATERAL FORCE COLUMNS
  -- ========================================================================
  L_star_normalized_lateral_index,
  centrifugal_term_inches,
  rail_loading_bias,
  lateral_acceleration_g,
  
  -- ========================================================================
  -- CURVE GEOMETRY
  -- ========================================================================
  D_curve_degrees,
  R_curve_radius_feet,
  V_speed_mph,
  V_squared_mph2,
  D_V_squared_interaction

FROM superelevation_metrics
ORDER BY MP, MPFoot;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Query 1: Summary of superelevation metrics
-- Uncomment to run after creating the table
/*
SELECT
  'Actual Superelevation (Ea)' AS metric,
  ROUND(AVG(Ea_actual_inches), 4) AS avg_value,
  ROUND(MIN(Ea_actual_inches), 4) AS min_value,
  ROUND(MAX(Ea_actual_inches), 4) AS max_value,
  'inches' AS unit
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`

UNION ALL

SELECT
  'Equilibrium Superelevation (Ee)' AS metric,
  ROUND(AVG(Ee_equilibrium_inches), 4) AS avg_value,
  ROUND(MIN(Ee_equilibrium_inches), 4) AS min_value,
  ROUND(MAX(Ee_equilibrium_inches), 4) AS max_value,
  'inches' AS unit
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`

UNION ALL

SELECT
  'Unbalanced Superelevation (Eu)' AS metric,
  ROUND(AVG(Eu_unbalanced_inches), 4) AS avg_value,
  ROUND(MIN(Eu_unbalanced_inches), 4) AS min_value,
  ROUND(MAX(Eu_unbalanced_inches), 4) AS max_value,
  'inches' AS unit
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`

UNION ALL

SELECT
  'Normalized Lateral Index (L*)' AS metric,
  ROUND(AVG(L_star_normalized_lateral_index), 6) AS avg_value,
  ROUND(MIN(L_star_normalized_lateral_index), 6) AS min_value,
  ROUND(MAX(L_star_normalized_lateral_index), 6) AS max_value,
  'unitless' AS unit
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`

UNION ALL

SELECT
  'Lateral Acceleration' AS metric,
  ROUND(AVG(lateral_acceleration_g), 6) AS avg_value,
  ROUND(MIN(lateral_acceleration_g), 6) AS min_value,
  ROUND(MAX(lateral_acceleration_g), 6) AS max_value,
  'g-force' AS unit
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`;
*/

-- Query 2: Balance status distribution
-- Uncomment to run after creating the table
/*
SELECT
  balance_status,
  COUNT(*) AS num_observations,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY balance_status
ORDER BY num_observations DESC;
*/

-- Query 3: Rail loading bias distribution
-- Uncomment to run after creating the table
/*
SELECT
  rail_loading_bias,
  COUNT(*) AS num_observations,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage,
  ROUND(AVG(L_star_normalized_lateral_index), 6) AS avg_lateral_index
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY rail_loading_bias
ORDER BY num_observations DESC;
*/

-- Query 4: Highest lateral force locations
-- Uncomment to run after creating the table
/*
SELECT
  MP,
  MPFoot,
  D_curve_degrees,
  V_speed_mph,
  Ea_actual_inches,
  Eu_unbalanced_inches,
  L_star_normalized_lateral_index,
  lateral_acceleration_g,
  rail_loading_bias,
  balance_status
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
WHERE ABS(L_star_normalized_lateral_index) > 0.1  -- High lateral forces
ORDER BY ABS(L_star_normalized_lateral_index) DESC
LIMIT 20;
*/

-- Query 5: Cant deficiency analysis by milepost
-- Uncomment to run after creating the table
/*
SELECT
  FLOOR(MP) AS milepost,
  COUNT(*) AS num_observations,
  ROUND(AVG(Eu_unbalanced_inches), 4) AS avg_cant_deficiency_inches,
  ROUND(AVG(L_star_normalized_lateral_index), 6) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 6) AS avg_lateral_accel_g,
  ROUND(AVG(CASE WHEN balance_status = 'UNDERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 2) AS pct_underbalanced,
  ROUND(AVG(CASE WHEN balance_status = 'OVERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 2) AS pct_overbalanced
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY milepost
ORDER BY milepost;
*/
