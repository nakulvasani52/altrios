-- ============================================================================
-- Combined Physics Analysis Queries - WITH TRAIN DIRECTION
-- Resistance Forces + Superelevation/Lateral Forces + Direction
-- ============================================================================
-- IMPORTANT: MP_ASC_DEC indicates train travel direction:
-- - 'A' = Northbound (MP 242 → 252, increasing milepost)
-- - 'D' = Southbound (MP 252 → 242, decreasing milepost)
--
-- Key insight: Same track, opposite experience!
-- - Positive grade = uphill for 'A', downhill for 'D'
-- - Negative grade = downhill for 'A', uphill for 'D'
-- ============================================================================

-- ============================================================================
-- QUERY 1: Directional Asymmetry Analysis
-- ============================================================================
-- Compares same milepost for northbound (A) vs southbound (D) trains
-- Shows how direction completely changes the physics experience
-- ============================================================================

WITH direction_stats AS (
  SELECT
    MP,
    MP_ASC_DEC,
    AVG(res_total_lbs) AS avg_resistance,
    AVG(res_grade_lbs) AS avg_grade_resistance,
    AVG(power_required_kw) AS avg_power,
    AVG(L_star_normalized_lateral_index) AS avg_lateral_index,
    AVG(Grade) AS avg_grade,
    AVG(D_curve_degrees) AS avg_curve,
    AVG(V_speed_mph) AS avg_speed,
    COUNT(*) AS num_obs
  FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
  GROUP BY MP, MP_ASC_DEC
  HAVING COUNT(*) > 100
)

SELECT
  a.MP,
  
  -- Northbound (A: MP 242→252) metrics
  ROUND(a.avg_resistance, 0) AS northbound_resistance_lbs,
  ROUND(a.avg_grade_resistance, 0) AS northbound_grade_res_lbs,
  ROUND(a.avg_power, 0) AS northbound_power_kw,
  ROUND(a.avg_lateral_index, 3) AS northbound_lateral_index,
  
  -- Southbound (D: MP 252→242) metrics
  ROUND(d.avg_resistance, 0) AS southbound_resistance_lbs,
  ROUND(d.avg_grade_resistance, 0) AS southbound_grade_res_lbs,
  ROUND(d.avg_power, 0) AS southbound_power_kw,
  ROUND(d.avg_lateral_index, 3) AS southbound_lateral_index,
  
  -- Asymmetry metrics (how different are the directions?)
  ROUND(a.avg_resistance - d.avg_resistance, 0) AS resistance_difference_lbs,
  ROUND(a.avg_grade_resistance - d.avg_grade_resistance, 0) AS grade_res_difference_lbs,
  ROUND(a.avg_power - d.avg_power, 0) AS power_difference_kw,
  
  -- Percent difference
  ROUND(ABS(a.avg_resistance - d.avg_resistance) / NULLIF((a.avg_resistance + d.avg_resistance) / 2, 0) * 100, 1) AS resistance_pct_diff,
  
  -- Track geometry (same for both directions)
  ROUND(a.avg_grade, 4) AS grade_pct,
  ROUND(a.avg_curve, 2) AS curve_deg,
  
  -- Effective grade experience
  CASE
    WHEN a.avg_grade > 0.1 THEN 'Northbound: UPHILL, Southbound: DOWNHILL'
    WHEN a.avg_grade < -0.1 THEN 'Northbound: DOWNHILL, Southbound: UPHILL'
    ELSE 'Both directions: FLAT'
  END AS grade_experience,
  
  -- Which direction is more challenging?
  CASE
    WHEN a.avg_resistance > d.avg_resistance + 10000 THEN 'Northbound harder'
    WHEN d.avg_resistance > a.avg_resistance + 10000 THEN 'Southbound harder'
    ELSE 'Similar difficulty'
  END AS direction_comparison

FROM direction_stats a
INNER JOIN direction_stats d ON a.MP = d.MP AND a.MP_ASC_DEC = 'A' AND d.MP_ASC_DEC = 'D'
WHERE a.num_obs > 100 AND d.num_obs > 100
ORDER BY ABS(a.avg_resistance - d.avg_resistance) DESC
LIMIT 50;


-- ============================================================================
-- QUERY 2: Effective Grade Analysis by Direction
-- ============================================================================
-- Shows actual uphill/downhill experience based on direction + grade
-- ============================================================================

SELECT
  -- Grade categories (track geometry)
  CASE
    WHEN Grade < -0.3 THEN 'Track Grade: <-0.3%'
    WHEN Grade < 0 THEN 'Track Grade: 0 to -0.3%'
    WHEN Grade < 0.3 THEN 'Track Grade: 0 to 0.3%'
    WHEN Grade < 0.5 THEN 'Track Grade: 0.3-0.5%'
    ELSE 'Track Grade: >0.5%'
  END AS track_grade_category,
  
  MP_ASC_DEC AS direction,
  CASE 
    WHEN MP_ASC_DEC = 'A' THEN 'Northbound (242→252)'
    WHEN MP_ASC_DEC = 'D' THEN 'Southbound (252→242)'
  END AS direction_label,
  
  -- Effective grade experience (what the train actually feels)
  CASE
    -- Northbound (A): Positive grade = uphill, Negative grade = downhill
    WHEN MP_ASC_DEC = 'A' AND Grade > 0.1 THEN 'UPHILL'
    WHEN MP_ASC_DEC = 'A' AND Grade < -0.1 THEN 'DOWNHILL'
    -- Southbound (D): Positive grade = downhill, Negative grade = uphill
    WHEN MP_ASC_DEC = 'D' AND Grade > 0.1 THEN 'DOWNHILL'
    WHEN MP_ASC_DEC = 'D' AND Grade < -0.1 THEN 'UPHILL'
    ELSE 'FLAT'
  END AS effective_grade_experience,
  
  COUNT(*) AS num_observations,
  
  -- Resistance metrics
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  
  -- Energy recovery
  ROUND(SUM(CASE WHEN power_required_kw < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_regenerative,
  
  -- Lateral forces
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  
  -- Actual grade value
  ROUND(AVG(Grade), 4) AS avg_grade_pct,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY track_grade_category, MP_ASC_DEC, effective_grade_experience
HAVING COUNT(*) > 1000
ORDER BY 
  CASE effective_grade_experience
    WHEN 'UPHILL' THEN 1
    WHEN 'FLAT' THEN 2
    WHEN 'DOWNHILL' THEN 3
  END,
  avg_total_resistance_lbs DESC;


-- ============================================================================
-- QUERY 3: Top 10 Challenging Sections by Direction
-- ============================================================================
-- Separate rankings for northbound vs southbound
-- ============================================================================

(
  -- Top 10 for Northbound (A: 242→252)
  SELECT
    'NORTHBOUND (242→252)' AS train_direction,
    MP,
    MPFoot,
    Grade AS grade_pct,
    CASE
      WHEN Grade > 0.1 THEN 'Uphill for northbound'
      WHEN Grade < -0.1 THEN 'Downhill for northbound'
      ELSE 'Flat'
    END AS grade_experience,
    D_curve_degrees AS curve_deg,
    V_speed_mph AS speed_mph,
    res_total_lbs,
    res_grade_lbs,
    power_required_kw,
    L_star_normalized_lateral_index AS lateral_index,
    balance_status,
    
    ROUND(
      (res_total_lbs / 100000.0) + 
      (ABS(L_star_normalized_lateral_index) * 10) +
      (lateral_acceleration_g * 100)
    , 2) AS combined_stress_score
    
  FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
  WHERE MP_ASC_DEC = 'A' AND res_total_lbs > 50000
  ORDER BY combined_stress_score DESC
  LIMIT 10
)

UNION ALL

(
  -- Top 10 for Southbound (D: 252→242)
  SELECT
    'SOUTHBOUND (252→242)' AS train_direction,
    MP,
    MPFoot,
    Grade AS grade_pct,
    CASE
      WHEN Grade > 0.1 THEN 'Downhill for southbound'
      WHEN Grade < -0.1 THEN 'Uphill for southbound'
      ELSE 'Flat'
    END AS grade_experience,
    D_curve_degrees AS curve_deg,
    V_speed_mph AS speed_mph,
    res_total_lbs,
    res_grade_lbs,
    power_required_kw,
    L_star_normalized_lateral_index AS lateral_index,
    balance_status,
    
    ROUND(
      (res_total_lbs / 100000.0) + 
      (ABS(L_star_normalized_lateral_index) * 10) +
      (lateral_acceleration_g * 100)
    , 2) AS combined_stress_score
    
  FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
  WHERE MP_ASC_DEC = 'D' AND res_total_lbs > 50000
  ORDER BY combined_stress_score DESC
  LIMIT 10
)

ORDER BY train_direction, combined_stress_score DESC;


-- ============================================================================
-- QUERY 4: Energy Balance by Direction
-- ============================================================================
-- Shows traction vs regenerative power for each direction
-- ============================================================================

SELECT
  FLOOR(MP) AS milepost,
  MP_ASC_DEC AS direction,
  CASE 
    WHEN MP_ASC_DEC = 'A' THEN 'Northbound (242→252)'
    WHEN MP_ASC_DEC = 'D' THEN 'Southbound (252→242)'
  END AS direction_label,
  
  COUNT(*) AS num_observations,
  
  -- Power metrics
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  ROUND(MAX(power_required_kw), 0) AS max_power_kw,
  ROUND(MIN(power_required_kw), 0) AS min_power_kw,
  
  -- Energy balance
  ROUND(AVG(CASE WHEN power_required_kw > 0 THEN power_required_kw ELSE 0 END), 0) AS avg_traction_power_kw,
  ROUND(AVG(CASE WHEN power_required_kw < 0 THEN ABS(power_required_kw) ELSE 0 END), 0) AS avg_regen_power_kw,
  
  -- Percentage in each mode
  ROUND(SUM(CASE WHEN power_required_kw > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_traction,
  ROUND(SUM(CASE WHEN power_required_kw < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_regenerative,
  
  -- Resistance breakdown
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  
  -- Track geometry
  ROUND(AVG(Grade), 4) AS avg_grade_pct,
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY milepost, MP_ASC_DEC
HAVING COUNT(*) > 100
ORDER BY milepost, MP_ASC_DEC;


-- ============================================================================
-- QUERY 5: Overall Direction Comparison
-- ============================================================================
-- Summary statistics: Northbound vs Southbound
-- ============================================================================

SELECT
  MP_ASC_DEC AS direction,
  CASE 
    WHEN MP_ASC_DEC = 'A' THEN 'Northbound (MP 242→252)'
    WHEN MP_ASC_DEC = 'D' THEN 'Southbound (MP 252→242)'
  END AS direction_label,
  
  COUNT(*) AS total_observations,
  
  -- Resistance statistics
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  ROUND(STDDEV(res_total_lbs), 0) AS stddev_resistance_lbs,
  ROUND(MIN(res_total_lbs), 0) AS min_resistance_lbs,
  ROUND(MAX(res_total_lbs), 0) AS max_resistance_lbs,
  
  -- Grade resistance (direction-dependent!)
  ROUND(AVG(res_grade_lbs), 0) AS avg_grade_resistance_lbs,
  ROUND(MIN(res_grade_lbs), 0) AS min_grade_resistance_lbs,
  ROUND(MAX(res_grade_lbs), 0) AS max_grade_resistance_lbs,
  
  -- Power statistics
  ROUND(AVG(power_required_kw), 0) AS avg_power_kw,
  ROUND(MIN(power_required_kw), 0) AS min_power_kw,
  ROUND(MAX(power_required_kw), 0) AS max_power_kw,
  
  -- Energy balance
  ROUND(SUM(CASE WHEN power_required_kw > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_traction_mode,
  ROUND(SUM(CASE WHEN power_required_kw < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_regen_mode,
  
  -- Lateral force statistics
  ROUND(AVG(ABS(L_star_normalized_lateral_index)), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  
  -- Balance status
  ROUND(AVG(CASE WHEN balance_status = 'UNDERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_underbalanced,
  ROUND(AVG(CASE WHEN balance_status = 'OVERBALANCED' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_overbalanced,
  
  -- Track geometry (same for both, but shown for reference)
  ROUND(AVG(Grade), 4) AS avg_grade_pct,
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY MP_ASC_DEC
ORDER BY MP_ASC_DEC;


-- ============================================================================
-- QUERY 6: Curve-Direction Interaction
-- ============================================================================
-- Analyzes if curve effects vary by travel direction
-- ============================================================================

SELECT
  CASE
    WHEN D_curve_degrees < 0.5 THEN 'Straight'
    WHEN D_curve_degrees < 1.5 THEN 'Gentle Curve'
    WHEN D_curve_degrees < 2.5 THEN 'Moderate Curve'
    ELSE 'Sharp Curve'
  END AS curve_category,
  
  MP_ASC_DEC AS direction,
  CASE 
    WHEN MP_ASC_DEC = 'A' THEN 'Northbound'
    WHEN MP_ASC_DEC = 'D' THEN 'Southbound'
  END AS direction_label,
  
  COUNT(*) AS num_observations,
  
  -- Curve resistance (should be similar for both directions)
  ROUND(AVG(res_curve_lbs), 0) AS avg_curve_resistance_lbs,
  ROUND(AVG(res_total_lbs), 0) AS avg_total_resistance_lbs,
  
  -- Lateral forces (may vary slightly by direction)
  ROUND(AVG(L_star_normalized_lateral_index), 4) AS avg_lateral_index,
  ROUND(AVG(lateral_acceleration_g), 5) AS avg_lateral_accel_g,
  ROUND(AVG(Eu_unbalanced_inches), 3) AS avg_cant_deficiency_in,
  
  -- Rail loading
  ROUND(AVG(CASE WHEN rail_loading_bias = 'HIGH_RAIL_BIAS' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_high_rail,
  ROUND(AVG(CASE WHEN rail_loading_bias = 'LOW_RAIL_BIAS' THEN 1.0 ELSE 0.0 END) * 100, 1) AS pct_low_rail,
  
  -- Track geometry
  ROUND(AVG(D_curve_degrees), 2) AS avg_curve_deg,
  ROUND(AVG(V_speed_mph), 1) AS avg_speed_mph

FROM `uiuc-cee-eolima.nvasani2_geometry_data.Henderson_242to252_Speed_clean_canon_with_physics`
GROUP BY curve_category, MP_ASC_DEC
HAVING COUNT(*) > 1000
ORDER BY curve_category, MP_ASC_DEC;
