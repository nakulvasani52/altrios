-- ============================================================================
-- Combined Physics Analysis Queries
-- Resistance Forces + Superelevation/Lateral Forces
-- ============================================================================
-- These queries reveal relationships between longitudinal forces (resistance)
-- and lateral forces (superelevation/curvature) for comprehensive track analysis
-- ============================================================================

-- ============================================================================
-- QUERY 1: Critical Sections - High Resistance AND High Lateral Forces
-- ============================================================================
-- Identifies the most challenging track sections where trains face both:
-- - High longitudinal resistance (steep grades, tight curves)
-- - High lateral forces (cant deficiency, high speeds on curves)
-- ============================================================================

SELECT
  MP,
  ROUND(AVG(Grade), 4) AS avg_grade_pct,
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph,
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(AVG(res_curve_lbs), 0) AS avg_curve_resistance_lbs,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 3) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 4) AS avg_lateral_accel_g,
  COUNT(*) AS num_observations,
  -- Classify section severity
  CASE
    WHEN AVG(res_total_lbs) > 150000 AND AVG(ABS(L_star_normalized_lateral_index)) > 0.5 
      THEN 'CRITICAL - High Resistance + High Lateral'
    WHEN AVG(res_total_lbs) > 150000 
      THEN 'HIGH RESISTANCE'
    WHEN AVG(ABS(L_star_normalized_lateral_index)) > 0.5 
      THEN 'HIGH LATERAL FORCE'
    ELSE 'MODERATE'
  END AS section_severity
FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY MP
HAVING COUNT(*) > 100  -- Filter out sparse data
ORDER BY 
  CASE 
    WHEN AVG(res_total_lbs) > 150000 AND AVG(ABS(L_star_normalized_lateral_index)) > 0.5 THEN 1
    WHEN AVG(res_total_lbs) > 150000 THEN 2
    WHEN AVG(ABS(L_star_normalized_lateral_index)) > 0.5 THEN 3
    ELSE 4
  END,
  avg_total_resistance_lbs DESC;


-- ============================================================================
-- QUERY 2: Power-Lateral Force Correlation
-- ============================================================================
-- Analyzes how power requirements correlate with lateral forces
-- Shows if high-power sections also have high lateral loading
-- ============================================================================

SELECT
  -- Power bins (kW)
  CASE
    WHEN power_required_kw < 0 THEN 'Regenerative (<0)'
    WHEN power_required_kw < 2000 THEN 'Low (0-2000)'
    WHEN power_required_kw < 4000 THEN 'Medium (2000-4000)'
    WHEN power_required_kw < 6000 THEN 'High (4000-6000)'
    ELSE 'Very High (>6000)'
  END AS power_category,
  
  COUNT(*) AS num_observations,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  ROUND(AVG(res_total_lbs), 0) AS avg_resistance_lbs,
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- Percentage in each balance status
  ROUND(AVG(CASE WHEN balance_status = 'UNDERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_underbalanced,
  ROUND(AVG(CASE WHEN balance_status = 'OVERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_overbalanced,
  
  -- Average curve and grade
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(Grade), 3) AS avg_grade_pct

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY power_category
ORDER BY 
  CASE power_category
    WHEN 'Regenerative (<0)' THEN 1
    WHEN 'Low (0-2000)' THEN 2
    WHEN 'Medium (2000-4000)' THEN 3
    WHEN 'High (4000-6000)' THEN 4
    WHEN 'Very High (>6000)' THEN 5
  END;


-- ============================================================================
-- QUERY 3: Curve-Grade Interaction Analysis
-- ============================================================================
-- Analyzes combined effect of curves and grades on both resistance and lateral forces
-- Shows how these two geometric features interact
-- ============================================================================

SELECT
  -- Grade categories
  CASE
    WHEN Grade < -0.3 THEN 'Steep Downhill (<-0.3%)'
    WHEN Grade < 0 THEN 'Moderate Downhill (0 to -0.3%)'
    WHEN Grade < 0.3 THEN 'Flat (0 to 0.3%)'
    WHEN Grade < 0.5 THEN 'Moderate Uphill (0.3-0.5%)'
    ELSE 'Steep Uphill (>0.5%)'
  END AS grade_category,
  
  -- Curve categories
  CASE
    WHEN D_curve_degrees < 0.5 THEN 'Straight (<0.5°)'
    WHEN D_curve_degrees < 1.5 THEN 'Gentle Curve (0.5-1.5°)'
    WHEN D_curve_degrees < 2.5 THEN 'Moderate Curve (1.5-2.5°)'
    ELSE 'Sharp Curve (>2.5°)'
  END AS curve_category,
  
  COUNT(*) AS num_observations,
  
  -- Resistance metrics
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(AVG(res_curve_lbs), 0) AS avg_curve_resistance_lbs,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  
  -- Lateral force metrics
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- Combined severity score (normalized)
  ROUND(
    (AVG(res_total_lbs) / 100000.0) + 
    (AVG(ABS(L_star_normalized_lateral_index)) * 10)
  , 2) AS combined_severity_score

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY grade_category, curve_category
HAVING COUNT(*) > 1000  -- Filter sparse combinations
ORDER BY combined_severity_score DESC;


-- ============================================================================
-- QUERY 4: Speed-Dependent Analysis
-- ============================================================================
-- Shows how both resistance and lateral forces vary with speed
-- Reveals quadratic relationships (V² terms)
-- ============================================================================

SELECT
  -- Speed bins
  CASE
    WHEN V_speed_mph < 25 THEN '0-25 mph'
    WHEN V_speed_mph < 30 THEN '25-30 mph'
    WHEN V_speed_mph < 35 THEN '30-35 mph'
    WHEN V_speed_mph < 40 THEN '35-40 mph'
    ELSE '40+ mph'
  END AS speed_bin,
  
  COUNT(*) AS num_observations,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph,
  
  -- Resistance components (speed-dependent)
  ROUND(AVG(res_davis_b_lbs), 0) AS avg_davis_b_lbs,  -- Linear with V
  ROUND(AVG(res_aero_lbs), 0) AS avg_aero_lbs,        -- Quadratic with V
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  
  -- Lateral force (quadratic with V)
  ROUND(AVG(centrifugal_term_inches), 4) AS avg_centrifugal_term_in,
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  
  -- Superelevation metrics
  ROUND(AVG(Ee_equilibrium_inches), 3) AS avg_equilibrium_cant_in,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- V² and D×V² terms
  ROUND(AVG(V_squared_mph2), 0) AS avg_V_squared,
  ROUND(AVG(D_V_squared_interaction), 0) AS avg_D_V_squared

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY speed_bin
ORDER BY avg_speed_mph;


-- ============================================================================
-- QUERY 5: Rail Loading vs Resistance Analysis
-- ============================================================================
-- Correlates rail loading bias with resistance forces
-- Shows if high-rail or low-rail bias affects resistance
-- ============================================================================

SELECT
  rail_loading_bias,
  balance_status,
  
  COUNT(*) AS num_observations,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage,
  
  -- Resistance metrics
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(AVG(res_curve_lbs), 0) AS avg_curve_resistance_lbs,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  
  -- Lateral force metrics
  ROUND(AVG(L_star_normalized_lateral_index), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- Track geometry
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(Ea_actual_inches), 3) AS avg_actual_cant_in,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
WHERE rail_loading_bias != 'NEUTRAL'  -- Exclude the single neutral point
GROUP BY rail_loading_bias, balance_status
ORDER BY rail_loading_bias, balance_status;


-- ============================================================================
-- QUERY 6: Top 20 Most Challenging Locations (Combined Physics)
-- ============================================================================
-- Identifies specific locations with highest combined stress
-- Considers both longitudinal (resistance) and lateral (superelevation) forces
-- ============================================================================

SELECT
  MP,
  MPFoot,
  Grade AS grade_pct,
  D_curve_degrees AS curve_deg,
  V_speed_mph AS speed_mph,
  
  -- Resistance forces
  res_total_lbs,
  res_grade_lbs,
  res_curve_lbs,
  power_required_kw,
  
  -- Lateral forces
  Eu_unbalanced_inches AS cant_deficiency_in,
  L_star_normalized_lateral_index AS lateral_index,
  lateral_acceleration_g AS lateral_accel_g,
  balance_status,
  rail_loading_bias,
  
  -- Combined stress indicator
  ROUND(
    (res_total_lbs / 100000.0) +                          -- Normalize resistance
    (ABS(L_star_normalized_lateral_index) * 10) +         -- Scale lateral index
    (lateral_acceleration_g * 100)                        -- Scale lateral accel
  , 2) AS combined_stress_score

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
WHERE 
  res_total_lbs > 100000  -- Significant resistance
  OR ABS(L_star_normalized_lateral_index) > 0.5  -- Significant lateral force
ORDER BY combined_stress_score DESC
LIMIT 20;


-- ============================================================================
-- QUERY 7: Resistance-Lateral Force Correlation Matrix
-- ============================================================================
-- Statistical correlation between key resistance and lateral force metrics
-- Shows which forces tend to occur together
-- ============================================================================

SELECT
  ROUND(CORR(res_total_lbs, ABS(L_star_normalized_lateral_index)), 4) AS corr_resistance_lateral_index,
  ROUND(CORR(res_total_lbs, lateral_acceleration_g), 4) AS corr_resistance_lateral_accel,
  ROUND(CORR(res_grade_lbs, Eu_unbalanced_inches), 4) AS corr_grade_res_cant_deficiency,
  ROUND(CORR(res_curve_lbs, D_curve_degrees), 4) AS corr_curve_res_curve_deg,
  ROUND(CORR(power_required_kw, lateral_acceleration_g), 4) AS corr_power_lateral_accel,
  ROUND(CORR(V_speed_mph, Eu_unbalanced_inches), 4) AS corr_speed_cant_deficiency,
  ROUND(CORR(D_curve_degrees, ABS(L_star_normalized_lateral_index)), 4) AS corr_curve_lateral_index,
  
  -- Sample size
  COUNT(*) AS total_observations

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`;


-- ============================================================================
-- QUERY 8: Energy Efficiency vs Track Geometry
-- ============================================================================
-- Analyzes how track geometry (grade + curve + superelevation) affects energy
-- Shows opportunities for energy savings through geometry improvements
-- ============================================================================

SELECT
  FLOOR(MP) AS milepost,
  
  -- Energy metrics
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  ROUND(SUM(CASE WHEN power_required_kw < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_regenerative,
  
  -- Resistance breakdown
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(AVG(res_curve_lbs), 0) AS avg_curve_resistance_lbs,
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  
  -- Lateral forces (affect wheel-rail friction → resistance)
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  
  -- Track geometry
  ROUND(AVG(Grade), 3) AS avg_grade_pct,
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- Energy efficiency indicator (lower is better)
  ROUND(AVG(res_total_lbs) / NULLIF(AVG(V_speed_mph), 0), 0) AS resistance_per_mph,
  
  COUNT(*) AS num_observations

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY milepost
ORDER BY milepost;
