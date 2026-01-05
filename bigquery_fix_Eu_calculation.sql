-- ============================================================================
-- BigQuery SQL Script: Add Superelevation and Lateral Force Index (FIXED)
-- ============================================================================
-- FIX APPLIED: Uses ABS(XLEVEL) for Ea to prevent sign calculation errors.
--
-- Output Table: Henderson_242to252_Speed_clean_canon_with_phy
-- ============================================================================

CREATE OR REPLACE TABLE `uiuc-cee-aolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_phy` AS

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
    -- 3.1 SUPERELEVATION CALCULATIONS (FIXED)
    -- ========================================================================
    
    -- Actual superelevation (Ea): Use ABSOLUTE VALUE of XLEVEL
    -- XLEVEL can be negative (left curve), but calculation requires magnitude
    ABS(XLEVEL) AS Ea_actual_inches,
    
    -- Degree of curve (D): Use absolute value of CURVE_CANON_MEDIAN
    ABS(CURVE_CANON_MEDIAN) AS D_curve_degrees,
    
    -- Speed (V): Use Speed field (mph)
    ABS(Speed) AS V_speed_mph,
    
    -- Equilibrium superelevation (Ee) for measured speed V and curve D
    -- Formula: Ee = 0.0007 × D × V² (inches)
    ROUND(0.0007 * ABS(CURVE_CANON_MEDIAN) * POWER(ABS(Speed), 2), 4) AS Ee_equilibrium_inches,
    
    -- Curve radius (R) from degree of curve (D)
    -- Formula: R ≈ 5730 / D (feet)
    CASE 
      WHEN ABS(CURVE_CANON_MEDIAN) > 0.01 
      THEN ROUND(5730.0 / ABS(CURVE_CANON_MEDIAN), 2)
      ELSE 1000000.0  -- Essentially infinite radius for straight track
    END AS R_curve_radius_feet
    
  FROM `uiuc-cee-aolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`
),

superelevation_metrics AS (
  SELECT
    bc.*,
    pc.g_fps2,
    pc.radius_constant,
    
    -- ========================================================================
    -- UNBALANCED SUPERELEVATION (Eu) - NOW CORRECT
    -- ========================================================================
    
    -- Cant deficiency: Eu = Ee - Ea
    -- Now safe because both Ee and Ea are positive magnitudes
    ROUND(bc.Ee_equilibrium_inches - bc.Ea_actual_inches, 4) AS Eu_unbalanced_inches,
    
    -- Balance status classification
    CASE
      WHEN (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) > 0.5 
        THEN 'UNDERBALANCED'  -- Cant deficiency (speed too high)
      WHEN (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) < -0.5 
        THEN 'OVERBALANCED'   -- Cant excess (speed too low)
      ELSE 'BALANCED'         -- Within tolerance
    END AS balance_status,
    
    -- Magnitude of imbalance
    ROUND(ABS(bc.Ee_equilibrium_inches - bc.Ea_actual_inches), 4) AS imbalance_magnitude_inches,
    
    -- ========================================================================
    -- 3.2 LATERAL FORCE INDEX (MASS-FREE)
    -- ========================================================================
    
    -- Normalized lateral index: L* = Ea - V²/(g×R)
    ROUND(
      bc.Ea_actual_inches - (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) /  
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
      )
    , 6) AS L_star_normalized_lateral_index,
    
    -- ========================================================================
    -- LATERAL FORCE COMPONENTS
    -- ========================================================================
    
    -- V²/(g×R) term (inches) - centrifugal force component
    ROUND(
      POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
      (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
    , 6) AS centrifugal_term_inches,
    
    -- Rail Bias Logic (Using Absolute Ea)
    -- If Ea (banking) > Centrifugal Force → Train falls inward (Low Rail)
    -- If Ea (banking) < Centrifugal Force → Train pushes outward (High Rail)
    CASE
      WHEN bc.Ea_actual_inches > (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
      ) THEN 'LOW_RAIL_BIAS'  -- Excess banking (Overbalanced)
      WHEN bc.Ea_actual_inches < (
        POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
        (pc.g_fps2 * bc.R_curve_radius_feet * 12.0)
      ) THEN 'HIGH_RAIL_BIAS' -- Insufficient banking (Underbalanced)
      ELSE 'NEUTRAL'
    END AS rail_loading_bias,
    
    -- Quadratic metrics
    ROUND(POWER(bc.V_speed_mph, 2), 2) AS V_squared_mph2,
    ROUND(bc.D_curve_degrees * POWER(bc.V_speed_mph, 2), 2) AS D_V_squared_interaction,
    
    -- Lateral acceleration (g)
    ROUND(
      POWER(bc.V_speed_mph * 5280.0 / 3600.0, 2) / 
      (pc.g_fps2 * bc.R_curve_radius_feet)
    , 6) AS lateral_acceleration_g,
    
    -- ========================================================================
    -- SAFETY METRICS
    -- ========================================================================
    
    -- Cant deficiency ratio
    CASE 
      WHEN bc.Ee_equilibrium_inches > 0.1
      THEN ROUND(
        (bc.Ee_equilibrium_inches - bc.Ea_actual_inches) / 
        NULLIF(bc.Ee_equilibrium_inches, 0) * 100
      , 2)
      ELSE NULL
    END AS cant_deficiency_ratio_pct,
    
    -- Speed ratio
    CASE
      WHEN bc.D_curve_degrees > 0.01 AND bc.Ea_actual_inches > 0
      THEN ROUND(
        bc.V_speed_mph / 
        NULLIF(SQRT(bc.Ea_actual_inches / (0.0007 * bc.D_curve_degrees)), 0)
      , 4)
      ELSE NULL
    END AS speed_ratio_to_equilibrium,
    
    -- Equilibrium Speed
    CASE
      WHEN bc.D_curve_degrees > 0.01 AND bc.Ea_actual_inches > 0
      THEN ROUND(SQRT(bc.Ea_actual_inches / (0.0007 * bc.D_curve_degrees)), 2)
      ELSE NULL
    END AS V_equilibrium_mph

  FROM base_calculations bc
  CROSS JOIN physics_constants pc
)

SELECT
  RunID, Car, ReportDate, Division, Subdivision, LineCode, MP, MPFoot, MP_ASC_DEC,
  SyncCount, SyncSample, Speed, PostedClass, PostedSpeed, TrackNumber,
  LPROF31, LPROF62, LPROF124, RPROF31, RPROF62, RPROF124,
  LALIGN31, LALIGN62, LALIGN124, RALIGN31, RALIGN62, RALIGN124,
  GAUGE, XLEVEL, CTS, TWIST11, TWIST22, TWIST31, WARP62,
  LPROF_SC, RPROF_SC, LALIGN_SC, RALIGN_SC, LATITUDE, LONGITUDE,
  MP_atac, MP_100th, MP_10th, MP_10feet, MP_30feet, RunID_MP100th,
  LATITUDE_STR, LONGITUDE_STR, Grade, CURVE_CANON_MEDIAN,
  CURVE_CANON_2DP, CURVE_CANON_1DP,
  
  -- Resistance Columns
  weight_tons, res_rolling_lbs, res_davis_b_lbs, res_aero_lbs,
  res_grade_lbs, res_curve_lbs, res_total_lbs, power_required_kw,
  power_required_hp, res_rolling_pct, res_davis_b_pct, res_aero_pct,
  res_grade_pct, res_curve_pct,
  
  -- Corrected Physics Columns
  Ea_actual_inches,
  Ee_equilibrium_inches,
  Eu_unbalanced_inches,
  balance_status,
  imbalance_magnitude_inches,
  cant_deficiency_ratio_pct,
  V_equilibrium_mph,
  speed_ratio_to_equilibrium,
  L_star_normalized_lateral_index,
  centrifugal_term_inches,
  rail_loading_bias,
  lateral_acceleration_g,
  D_curve_degrees,
  R_curve_radius_feet,
  V_speed_mph,
  V_squared_mph2,
  D_V_squared_interaction

FROM superelevation_metrics
ORDER BY MP, MPFoot;
