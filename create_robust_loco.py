import altrios as alt

def get_robust_loco():
    """
    Creates and returns a robust Locomotive object (approx 4400 HP / 3.3 MW).
    Uses the 'modify-default' strategy to avoid direct schema instantiation errors.
    """
    # 1. Get default locomotive as dictionary
    loco_dict = alt.Locomotive.default().to_pydict()

    # 2. Key Mapping based on inspection
    # Structure: loco_type -> ConventionalLoco -> fc/gen/edrv
    if 'loco_type' in loco_dict:
        # Check if ConventionalLoco is nested
        if 'ConventionalLoco' in loco_dict['loco_type']:
             conv_loco = loco_dict['loco_type']['ConventionalLoco']
        else:
            # Fallback for some versions? Unlikely based on inspect output
             raise ValueError("Unexpected default locomotive structure: missing ConventionalLoco")
    else:
        raise ValueError("Unexpected default locomotive structure: missing loco_type")

    # 3. Set High Power Values (3.3 MW)
    power_watts = 3300000.0
    conv_loco['fc']['pwr_out_max_watts'] = power_watts
    conv_loco['gen']['pwr_out_max_watts'] = power_watts
    conv_loco['edrv']['pwr_out_max_watts'] = power_watts
    
    # ELIMINATE POWER RAMP LAG (Fix for startup stall)
    if 'fc' in conv_loco:
        conv_loco['fc']['pwr_ramp_lag_seconds'] = 0.0
        conv_loco['fc']['pwr_out_max_init_watts'] = power_watts
    
    # Also set top-level pwr if it exists (some structs duplicate)
    if 'pwr_out_max_watts' in conv_loco:
         conv_loco['pwr_out_max_watts'] = power_watts

    # 4. Set Weights and Traction
    mass_kg = 195000.0
    force_max_n = 800000.0 # ~180,000 lbs starting TE

    conv_loco['mass_kilograms'] = mass_kg
    # Some versions have mass at top level too
    loco_dict['mass_kilograms'] = mass_kg 
    loco_dict['force_max_newtons'] = force_max_n

    # 5. Rebuild Locomotive Object
    # This invokes the Rust deserializer with the structurally correct data
    return alt.Locomotive.from_pydict(loco_dict)

if __name__ == "__main__":
    try:
        loco = get_robust_loco()
        print("Successfully created robust locomotive!")
        # Verify
        d = loco.to_pydict()
        val = d['loco_type']['ConventionalLoco']['fc']['pwr_out_max_watts']
        print(f"Verified Power: {val/1e6} MW")
    except Exception as e:
        print(f"Failed to create locomotive: {e}")
