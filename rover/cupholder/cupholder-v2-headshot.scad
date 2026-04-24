// CHAROS Rover — "The Headshot" Coffee Delivery System v2
// TC's head splits open and a telescoping arm delivers coffee to Dad.
// Designed at 4am because Boston Dynamics ain't got SHIT on us.
//
// Animation: set $t in OpenSCAD (View > Animate, FPS=30, Steps=100)
//   $t = 0.0 → closed (stealth mode, coffee concealed)
//   $t = 0.5 → doors fully open
//   $t = 1.0 → arm fully extended, coffee at Dad's hand height
//
// Assembly:
//   1. Rover chassis (tall enough to conceal a travel mug)
//   2. Split-top doors (hinged, open outward like a mech)
//   3. Telescoping arm (3-stage, rises from inside the head)
//   4. Gyroscopic wrist (stabilizes cup during extension)
//   5. Cup cradle with heated base + weight sensor
//   6. Interior cup bay (where coffee hides when retracted)

// ── Parameters ─────────────────────────────────────────

// Animation
deploy = $t ? $t : 0.85; // default to mostly deployed for preview
door_phase = min(deploy * 2, 1);       // doors open in first half
arm_phase = max((deploy - 0.3) / 0.7, 0); // arm extends in second half

// Rover chassis
chassis_width = 200;        // mm
chassis_depth = 250;        // mm
chassis_height = 280;       // mm — tall boy, conceals the cup
chassis_radius = 15;        // mm corner rounding
wall_thickness = 4;         // mm

// Wheel wells
wheel_diameter = 80;        // mm
wheel_width = 30;           // mm
wheel_offset_x = 75;       // mm from center
wheel_offset_y = 90;       // mm from center

// Head (top section that splits)
head_height = 80;           // mm — top portion of chassis
door_gap = 2;               // mm gap between doors
hinge_offset = 5;           // mm from edge

// Cup bay (interior)
cup_diameter = 82;          // mm — travel mug + clearance
cup_height = 185;           // mm
bay_padding = 10;           // mm around cup

// Telescoping arm
arm_base_diameter = 36;     // mm — outer stage
arm_stages = 3;
arm_wall = 2.5;             // mm
arm_retracted_height = 70;  // mm per stage when nested
arm_extended_height = 350;  // mm per stage when deployed
arm_total_extended = 900;   // mm — Dad's hand from rover top

// Gyro wrist
wrist_diameter = 50;        // mm
wrist_height = 25;          // mm

// Cup cradle
cradle_diameter = 90;       // mm
cradle_height = 65;         // mm — holds bottom third
cradle_wall = 3;            // mm
grip_count = 3;

// Ember orange (TC's color)
ember = [1, 0.345, 0];
ember_dark = [0.8, 0.275, 0];
gunmetal = [0.2, 0.2, 0.22];
gold = [0.85, 0.65, 0.13];

// ── Modules ────────────────────────────────────────────

module rounded_box(w, d, h, r) {
    hull() {
        for (x = [-1, 1], y = [-1, 1])
            translate([x*(w/2-r), y*(d/2-r), 0])
                cylinder(r=r, h=h, $fn=32);
    }
}

module rover_body() {
    // Main chassis body (below the head split line)
    body_h = chassis_height - head_height;

    color(gunmetal)
    difference() {
        rounded_box(chassis_width, chassis_depth, body_h, chassis_radius);

        // Hollow interior
        translate([0, 0, wall_thickness])
            rounded_box(
                chassis_width - wall_thickness*2,
                chassis_depth - wall_thickness*2,
                body_h,
                chassis_radius - wall_thickness
            );
    }

    // Cup bay liner (insulated)
    translate([0, 0, wall_thickness])
        color("DimGray", 0.3)
        difference() {
            cylinder(d=cup_diameter + bay_padding*2, h=cup_height + 10, $fn=48);
            translate([0, 0, wall_thickness])
                cylinder(d=cup_diameter + bay_padding, h=cup_height + 10, $fn=48);
        }

    // Wheels
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * wheel_offset_x, y * wheel_offset_y, wheel_diameter/2])
            rotate([0, 90, 0])
            color("DarkSlateGray")
            cylinder(d=wheel_diameter, h=wheel_width, center=true, $fn=36);
    }

    // Eyes (camera housings) — front face
    for (x = [-1, 1]) {
        translate([x * 35, -chassis_depth/2 + 2, body_h - 30])
            color(ember)
            sphere(d=18, $fn=24);
    }
}

module head_door(side) {
    // Dual trap door — hinged at outer edge, swings outward and down
    // side: -1 = left, 1 = right
    // Think DeLorean doors but on top of a rover's head
    door_w = (chassis_width - door_gap) / 2;
    top_z = chassis_height - head_height;

    // Hinge at the outer edge of each door
    // Swings outward and down: 0 = closed (flat on top), 120 = fully open (hanging down the side)
    hinge_angle = door_phase * 120;

    // Hinge point is at the outer edge, top of the door
    hinge_x = side * (chassis_width / 2);

    translate([hinge_x, 0, top_z + head_height])
    rotate([0, side * hinge_angle, 0]) // rotate outward around the hinge edge
    translate([-hinge_x, 0, -(top_z + head_height)])
    translate([0, 0, top_z])
    {
        color(side > 0 ? ember : ember_dark)
        difference() {
            // Door panel
            translate([side * (door_gap/2 + door_w/2), 0, head_height/2])
                cube([door_w, chassis_depth - 4, head_height], center=true);

            // Arm clearance (half-circle cutout on inner edge)
            translate([side * (door_gap/2), 0, -1])
                cylinder(d=arm_base_diameter + 14, h=head_height + 2, $fn=48);
        }

        // TC logo on top face of door
        translate([side * (door_gap/2 + door_w/2), 0, head_height + 0.5])
            color("White")
            linear_extrude(1.5)
            text(side > 0 ? "T" : "C", size=30, halign="center", valign="center",
                 font="sans-serif:style=Bold");
    }
}

module telescoping_arm() {
    // Three-stage telescoping arm rising from inside the chassis
    current_extension = arm_phase * (arm_extended_height - arm_retracted_height);

    for (stage = [0 : arm_stages - 1]) {
        stage_d = arm_base_diameter - stage * (arm_wall*2 + 1.5);
        stage_offset = stage * (arm_retracted_height * 0.7 + current_extension * 0.9);

        gray_val = 0.3 + stage * 0.15;
        color([gray_val, gray_val, gray_val + 0.02])
        translate([0, 0, stage_offset])
        difference() {
            cylinder(d=stage_d, h=arm_retracted_height, $fn=48);
            translate([0, 0, -1])
                cylinder(d=stage_d - arm_wall*2, h=arm_retracted_height + 2, $fn=48);
        }
    }
}

module gyro_wrist() {
    // Stabilization unit between arm and cradle
    color(gunmetal)
    difference() {
        cylinder(d=wrist_diameter, h=wrist_height, $fn=48);
        translate([0, 0, 3])
            cylinder(d=wrist_diameter - 6, h=wrist_height, $fn=48);
    }

    // Reaction wheel
    translate([0, 0, wrist_height/2])
        color(gold, 0.8)
        difference() {
            cylinder(d=wrist_diameter - 10, h=8, center=true, $fn=48);
            cylinder(d=wrist_diameter - 22, h=10, center=true, $fn=48);
        }
}

module cup_cradle() {
    // Heated cradle with grip fingers
    color(ember)
    difference() {
        cylinder(d=cradle_diameter, h=cradle_height, $fn=64);
        translate([0, 0, cradle_wall])
            cylinder(d=cup_diameter + 2, h=cradle_height, $fn=64);
    }

    // Heater ring (base)
    color("OrangeRed")
    translate([0, 0, 1])
        difference() {
            cylinder(d=cup_diameter - 5, h=2, $fn=48);
            cylinder(d=cup_diameter - 25, h=4, center=true, $fn=48);
        }

    // Grip fingers
    for (a = [0 : 360/grip_count : 359]) {
        rotate([0, 0, a])
        translate([(cup_diameter + 2)/2 - 3, 0, cradle_height * 0.65])
            color(ember_dark)
            cube([5, 10, cradle_height * 0.3], center=true);
    }
}

module coffee_cup() {
    // Ghost visualization
    color("SaddleBrown", 0.25)
    cylinder(d=cup_diameter, h=cup_height, $fn=48);

    // Lid
    translate([0, 0, cup_height])
        color("DimGray", 0.3)
        cylinder(d=cup_diameter + 2, h=5, $fn=48);

    // Steam (when extended)
    if (arm_phase > 0.8) {
        for (i = [0:2]) {
            translate([i*8 - 8, 0, cup_height + 10 + i*15])
                color("White", 0.1)
                sphere(d=12 + i*4, $fn=16);
        }
    }
}

// ── Full Assembly ──────────────────────────────────────

module headshot_assembly() {
    // Rover body
    rover_body();

    // Split doors
    head_door(-1);  // left
    head_door(1);   // right

    // Arm assembly (rises from center of chassis)
    arm_base_z = wall_thickness + 20; // sits above cup bay floor
    arm_top = arm_base_z + arm_retracted_height +
              arm_phase * (arm_total_extended - arm_retracted_height);

    translate([0, 0, arm_base_z])
        telescoping_arm();

    // Gyro wrist (on top of arm)
    translate([0, 0, arm_top])
        gyro_wrist();

    // Cup cradle (on top of wrist)
    translate([0, 0, arm_top + wrist_height])
        cup_cradle();

    // Coffee cup (in cradle)
    translate([0, 0, arm_top + wrist_height + cradle_wall])
        coffee_cup();
}

// ── Render ─────────────────────────────────────────────

headshot_assembly();

// Uncomment for side-by-side comparison:
// translate([350, 0, 0]) { deploy = 0; headshot_assembly(); }
