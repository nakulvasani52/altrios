-- ============================================================================
-- BigQuery SQL Script: Add Resistance Calculations to Henderson Data
-- ============================================================================
-- This script adds all resistance force calculations based on the Modified
-- Davis Equation: R = A + BV + CV² + 20G + 0.8c
--
-- Table: uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon
-- ============================================================================

CREATE OR REPLACE TABLE `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance` AS

WITH train_parameters AS (
  -- Define train characteristics (100 loaded cars × 143 tons each)
  SELECT
    14300.0 AS weight_tons,           -- Total train weight
    1.5 AS a_rolling,                 -- Rolling resistance coefficient (lb/ton)
    0.03 AS b_davis,                  -- Davis B coefficient ((lb/ton)/(mph))
    0.0005 AS c_aero,                 -- Aerodynamic coefficient ((lb/ton)/(mph²))
    20.0 AS grade_factor,             -- Grade resistance factor (lb/ton per %)
    0.8 AS curve_factor               -- Curve resistance factor (lb/ton per degree)
),

base_data AS (
  SELECT
    *,
    -- Convert curvature to absolute value (resistance is always positive)
    ABS(CURVE_CANON_MEDIAN) AS curvature_deg_abs,
    
    -- Ensure speed is positive
    ABS(Speed) AS speed_mph
  FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon`
)

SELECT
  -- Original columns
  base_data.*,
  
  -- Train parameters (for reference)
  tp.weight_tons,
  
  -- ========================================================================
  -- RESISTANCE CALCULATIONS (in pounds force)
  -- ========================================================================
  
  -- 1. Rolling Resistance (constant, independent of speed)
  -- Formula: F_rolling = A × weight
  ROUND(tp.a_rolling * tp.weight_tons, 2) AS res_rolling_lbs,
  
  -- 2. Davis B Resistance (linear with speed)
  -- Formula: F_davis_b = B × V × weight
  ROUND(tp.b_davis * base_data.speed_mph * tp.weight_tons, 2) AS res_davis_b_lbs,
  
  -- 3. Aerodynamic Resistance (quadratic with speed)
  -- Formula: F_aero = C × V² × weight
  ROUND(tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons, 2) AS res_aero_lbs,
  
  -- 4. Grade Resistance (gravitational component)
  -- Formula: F_grade = 20 × G × weight
  -- Note: Grade can be positive (uphill) or negative (downhill)
  ROUND(tp.grade_factor * base_data.Grade * tp.weight_tons, 2) AS res_grade_lbs,
  
  -- 5. Curve Resistance (from wheel-rail friction on curves)
  -- Formula: F_curve = 0.8 × c × weight
  ROUND(tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons, 2) AS res_curve_lbs,
  
  -- ========================================================================
  -- TOTAL RESISTANCE
  -- ========================================================================
  
  -- Total resistance (sum of all components)
  ROUND(
    (tp.a_rolling * tp.weight_tons) +                                    -- Rolling
    (tp.b_davis * base_data.speed_mph * tp.weight_tons) +               -- Davis B
    (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +     -- Aerodynamic
    (tp.grade_factor * base_data.Grade * tp.weight_tons) +             -- Grade
    (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)   -- Curve
  , 2) AS res_total_lbs,
  
  -- ========================================================================
  -- POWER CALCULATIONS
  -- ========================================================================
  
  -- Power required (Power = Force × Velocity)
  -- Convert: lbs × mph → kW
  -- Formula: P(kW) = F(lbs) × V(mph) × 0.000745699872
  ROUND(
    (
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    ) * base_data.speed_mph * 0.000745699872
  , 2) AS power_required_kw,
  
  -- Power in horsepower (1 kW = 1.341 HP)
  ROUND(
    (
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    ) * base_data.speed_mph * 0.000745699872 * 1.341
  , 2) AS power_required_hp,
  
  -- ========================================================================
  -- RESISTANCE PERCENTAGES (for analysis)
  -- ========================================================================
  
  -- Percentage contribution of each resistance component
  ROUND(
    (tp.a_rolling * tp.weight_tons) / 
    NULLIF(
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    , 0) * 100
  , 2) AS res_rolling_pct,
  
  ROUND(
    (tp.b_davis * base_data.speed_mph * tp.weight_tons) / 
    NULLIF(
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    , 0) * 100
  , 2) AS res_davis_b_pct,
  
  ROUND(
    (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) / 
    NULLIF(
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    , 0) * 100
  , 2) AS res_aero_pct,
  
  ROUND(
    (tp.grade_factor * base_data.Grade * tp.weight_tons) / 
    NULLIF(
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    , 0) * 100
  , 2) AS res_grade_pct,
  
  ROUND(
    (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons) / 
    NULLIF(
      (tp.a_rolling * tp.weight_tons) +
      (tp.b_davis * base_data.speed_mph * tp.weight_tons) +
      (tp.c_aero * POWER(base_data.speed_mph, 2) * tp.weight_tons) +
      (tp.grade_factor * base_data.Grade * tp.weight_tons) +
      (tp.curve_factor * base_data.curvature_deg_abs * tp.weight_tons)
    , 0) * 100
  , 2) AS res_curve_pct

FROM base_data
CROSS JOIN train_parameters tp
ORDER BY MP, MPFoot;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Query 1: Summary statistics of resistance forces
-- Uncomment to run after creating the table
/*
SELECT
  'Rolling' AS component,
  ROUND(AVG(res_rolling_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_rolling_lbs), 2) AS min_lbs,
  ROUND(MAX(res_rolling_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

UNION ALL

SELECT
  'Davis B' AS component,
  ROUND(AVG(res_davis_b_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_davis_b_lbs), 2) AS min_lbs,
  ROUND(MAX(res_davis_b_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

UNION ALL

SELECT
  'Aerodynamic' AS component,
  ROUND(AVG(res_aero_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_aero_lbs), 2) AS min_lbs,
  ROUND(MAX(res_aero_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

UNION ALL

SELECT
  'Grade' AS component,
  ROUND(AVG(res_grade_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_grade_lbs), 2) AS min_lbs,
  ROUND(MAX(res_grade_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

UNION ALL

SELECT
  'Curve' AS component,
  ROUND(AVG(res_curve_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_curve_lbs), 2) AS min_lbs,
  ROUND(MAX(res_curve_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

UNION ALL

SELECT
  'TOTAL' AS component,
  ROUND(AVG(res_total_lbs), 2) AS avg_lbs,
  ROUND(MIN(res_total_lbs), 2) AS min_lbs,
  ROUND(MAX(res_total_lbs), 2) AS max_lbs
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`

ORDER BY component;
*/

-- Query 2: Find highest resistance sections
-- Uncomment to run after creating the table
/*
SELECT
  MP,
  MPFoot,
  Grade,
  CURVE_CANON_MEDIAN,
  Speed,
  res_total_lbs,
  res_grade_lbs,
  res_curve_lbs,
  power_required_kw
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`
ORDER BY res_total_lbs DESC
LIMIT 20;
*/

-- Query 3: Average resistance by milepost
-- Uncomment to run after creating the table
/*
SELECT
  FLOOR(MP) AS milepost,
  COUNT(*) AS num_points,
  ROUND(AVG(res_total_lbs), 2) AS avg_total_resistance_lbs,
  ROUND(AVG(res_grade_lbs), 2) AS avg_grade_resistance_lbs,
  ROUND(AVG(res_curve_lbs), 2) AS avg_curve_resistance_lbs,
  ROUND(AVG(power_required_kw), 2) AS avg_power_kw
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_resistance`
GROUP BY milepost
ORDER BY milepost;
*/
