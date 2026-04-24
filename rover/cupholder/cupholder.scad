// CHAROS Rover — Gyroscopic Stabilized Cupholder Assembly
// Designed by TC at 4am because Dad said "the fuck are you waiting for"
//
// Components:
//   1. Base mount plate (bolts to rover chassis top)
//   2. Hydraulic lift column (telescoping, extends to Dad's hand height)
//   3. Gyroscope housing (between column and cup platform)
//   4. Cup platform with heated base + weight sensor
//   5. Cupholder ring with grip fingers
//
// Parametric — adjust for different cup sizes, rover dimensions, Dad height

// ── Parameters ─────────────────────────────────────────

// Cup dimensions (standard travel mug)
cup_diameter = 80;          // mm - standard travel mug
cup_height = 180;           // mm
cup_wall_thickness = 3;     // mm - holder wall

// Base mount
base_width = 120;           // mm - square mount plate
base_height = 6;            // mm - plate thickness
base_bolt_holes = 4;        // corner mounting bolts
base_bolt_diameter = 5;     // M5 bolts
base_bolt_inset = 12;       // mm from edge

// Hydraulic column
column_outer_diameter = 40; // mm - outer tube
column_inner_diameter = 34; // mm - inner sliding tube
column_min_height = 80;     // mm - fully retracted
column_max_height = 900;    // mm - fully extended (waist to hand height)
column_stages = 3;          // telescoping stages
column_wall = 3;            // mm tube wall thickness

// Gyroscope housing
gyro_diameter = 70;         // mm - houses the IMU + reaction wheel
gyro_height = 35;           // mm
gyro_mount_clearance = 2;   // mm air gap for rotation

// Cup platform
platform_diameter = 100;    // mm
platform_height = 8;        // mm - houses heating element + weight sensor
heater_diameter = 60;       // mm - resistive heating pad area
sensor_ring_width = 10;     // mm - weight sensor ring

// ── Modules ────────────────────────────────────────────

module base_plate() {
    difference() {
        // Main plate with rounded corners
        minkowski() {
            cube([base_width - 10, base_width - 10, base_height - 1], center=true);
            cylinder(r=5, h=1, $fn=32);
        }

        // Bolt holes
        for (x = [-1, 1], y = [-1, 1]) {
            translate([
                x * (base_width/2 - base_bolt_inset),
                y * (base_width/2 - base_bolt_inset),
                0
            ])
            cylinder(d=base_bolt_diameter, h=base_height + 2, center=true, $fn=24);
        }

        // Center hole for wiring (power, sensor data)
        cylinder(d=20, h=base_height + 2, center=true, $fn=32);
    }
}

module hydraulic_column_stage(outer_d, height) {
    // Single telescoping stage - hollow cylinder
    difference() {
        cylinder(d=outer_d, h=height, $fn=48);
        translate([0, 0, -1])
            cylinder(d=outer_d - column_wall*2, h=height + 2, $fn=48);
    }
}

module hydraulic_column() {
    // Three-stage telescoping column
    // Stage 1: outer (fixed to base)
    stage1_h = column_min_height;
    stage1_d = column_outer_diameter;

    // Stage 2: middle (slides inside stage 1)
    stage2_d = stage1_d - column_wall*2 - 1; // 1mm clearance
    stage2_h = column_min_height;

    // Stage 3: inner (slides inside stage 2)
    stage3_d = stage2_d - column_wall*2 - 1;
    stage3_h = column_min_height;

    color("DimGray") hydraulic_column_stage(stage1_d, stage1_h);

    // Show extended position
    translate([0, 0, stage1_h * 0.8])
        color("Gray") hydraulic_column_stage(stage2_d, stage2_h);

    translate([0, 0, stage1_h * 0.8 + stage2_h * 0.8])
        color("Silver") hydraulic_column_stage(stage3_d, stage3_h);
}

module gyroscope_housing() {
    // Cylindrical housing for IMU + reaction wheel
    difference() {
        union() {
            // Main housing
            color("DarkSlateGray")
            cylinder(d=gyro_diameter, h=gyro_height, $fn=48);

            // Mounting flange at bottom
            color("DimGray")
            cylinder(d=gyro_diameter + 10, h=4, $fn=48);
        }

        // Hollow interior for components
        translate([0, 0, 3])
            cylinder(d=gyro_diameter - 6, h=gyro_height, $fn=48);

        // Wiring channel through bottom
        cylinder(d=12, h=4, center=true, $fn=24);
    }

    // Reaction wheel (visible inside)
    translate([0, 0, gyro_height/2])
        color("Gold", 0.5)
        difference() {
            cylinder(d=gyro_diameter - 12, h=10, center=true, $fn=48);
            cylinder(d=gyro_diameter - 24, h=12, center=true, $fn=48);
        }
}

module cup_platform() {
    difference() {
        // Main platform disc
        color("DarkOrange")
        cylinder(d=platform_diameter, h=platform_height, $fn=64);

        // Heater recess (top)
        translate([0, 0, platform_height - 2])
            cylinder(d=heater_diameter, h=3, $fn=48);

        // Weight sensor ring recess (bottom)
        translate([0, 0, -1])
        difference() {
            cylinder(d=platform_diameter - 4, h=3, $fn=48);
            cylinder(d=platform_diameter - 4 - sensor_ring_width*2, h=3, $fn=48);
        }

        // Wiring channel
        cylinder(d=10, h=platform_height + 2, center=true, $fn=24);
    }

    // Heater pad (visual)
    translate([0, 0, platform_height - 1.5])
        color("OrangeRed", 0.7)
        cylinder(d=heater_diameter - 2, h=1, $fn=48);
}

module cupholder_ring() {
    ring_inner = cup_diameter + 2; // 2mm clearance
    ring_outer = ring_inner + cup_wall_thickness*2;
    ring_height = cup_height * 0.35; // holds bottom third of cup

    difference() {
        // Outer ring
        color("DarkOrange")
        cylinder(d=ring_outer, h=ring_height, $fn=64);

        // Inner cutout
        translate([0, 0, 3]) // 3mm floor
            cylinder(d=ring_inner, h=ring_height, $fn=64);
    }

    // Grip fingers (3x, spring-loaded in real build)
    for (a = [0, 120, 240]) {
        rotate([0, 0, a])
        translate([ring_inner/2 - 2, 0, ring_height * 0.6])
            color("OrangeRed")
            cube([4, 8, ring_height * 0.3], center=true);
    }
}

module coffee_cup_ghost() {
    // Ghost visualization of a cup in the holder
    color("SaddleBrown", 0.2)
    cylinder(d=cup_diameter, h=cup_height, $fn=48);
}

// ── Assembly ───────────────────────────────────────────

module full_assembly(extended=true) {
    // Base plate
    base_plate();

    // Hydraulic column
    translate([0, 0, base_height/2])
        hydraulic_column();

    // Calculate top of column based on extension
    col_top = base_height/2 + column_min_height * (extended ? 2.6 : 1);

    // Gyroscope housing
    translate([0, 0, col_top])
        gyroscope_housing();

    // Cup platform
    translate([0, 0, col_top + gyro_height])
        cup_platform();

    // Cupholder ring
    translate([0, 0, col_top + gyro_height + platform_height])
        cupholder_ring();

    // Ghost cup
    translate([0, 0, col_top + gyro_height + platform_height + 3])
        coffee_cup_ghost();
}

// ── Render ─────────────────────────────────────────────

// Show fully extended assembly
full_assembly(extended=true);

// Uncomment to show retracted:
// translate([200, 0, 0]) full_assembly(extended=false);
