class_name CharacterModel
extends RefCounted
## Genera animalitos redondos con primitivas (placeholder hasta tener modelos de Blender)
## y el material "toon" del juego: luz suave en bandas, borde de luz y mundo curvado.
## El frente del modelo apunta a -Z.

## Shader del look Animal Crossing. El mundo se curva hacia abajo con la distancia a la
## cámara (la posición viene del global `curve_cam_pos`, así también cuadran las sombras).
const SHADER_SRC := """
shader_type spatial;
render_mode %MODES%;

global uniform vec3 curve_cam_pos;

uniform vec4 albedo : source_color = vec4(1.0);
uniform bool use_vertex_color = false;
uniform vec3 emission_color : source_color = vec3(0.0);
uniform float emission_energy = 0.0;
uniform float curve_depth = 0.0025;
uniform float curve_side = 0.0007;
uniform float focus_dist = 12.0;

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float dz = max(0.0, (curve_cam_pos.z - world.z) - focus_dist);
	float dx = world.x - curve_cam_pos.x;
	world.y -= dz * dz * curve_depth + dx * dx * curve_side;
	VERTEX = (inverse(MODEL_MATRIX) * vec4(world, 1.0)).xyz;
}

void fragment() {
	vec4 c = albedo;
	if (use_vertex_color) {
		c *= COLOR;
	}
	ALBEDO = c.rgb;
	%ALPHA%
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	EMISSION = emission_color * emission_energy + c.rgb * rim * 0.12;
}
"""

static var _shaders := {}


static func mat(color: Color, alpha := false, double_sided := false) -> ShaderMaterial:
	var key := "%s_%s" % [alpha, double_sided]
	if not _shaders.has(key):
		var s := Shader.new()
		s.code = SHADER_SRC \
				.replace("%MODES%", "cull_disabled" if double_sided else "cull_back") \
				.replace("%ALPHA%", "ALPHA = c.a;" if alpha else "")
		_shaders[key] = s
	var m := ShaderMaterial.new()
	m.shader = _shaders[key]
	m.set_shader_parameter("albedo", color)
	return m


## Material que brilla (grieta, brasas).
static func glow_mat(base: Color, glow: Color, energy: float) -> ShaderMaterial:
	var m := mat(base)
	m.set_shader_parameter("emission_color", glow)
	m.set_shader_parameter("emission_energy", energy)
	return m


static func sphere(r: float) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	return s


static func capsule(r: float, h: float) -> CapsuleMesh:
	var c := CapsuleMesh.new()
	c.radius = r
	c.height = h
	return c


static func add_mesh(parent: Node3D, mesh: Mesh, color: Color, pos := Vector3.ZERO,
		scl := Vector3.ONE, rot_deg := Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat(color)
	mi.position = pos
	mi.scale = scl
	mi.rotation_degrees = rot_deg
	parent.add_child(mi)
	return mi


static func build(species: String, fur: Color, accent: Color) -> Node3D:
	var root := Node3D.new()
	var dark := Color(0.17, 0.12, 0.1)

	for side in [-1, 1]:
		var leg := Node3D.new()
		leg.name = "LegL" if side < 0 else "LegR"
		leg.position = Vector3(side * 0.18, 0.4, 0.0)
		root.add_child(leg)
		add_mesh(leg, capsule(0.11, 0.42), accent, Vector3(0, -0.2, 0))

		var arm := Node3D.new()
		arm.name = "ArmL" if side < 0 else "ArmR"
		arm.position = Vector3(side * 0.44, 1.0, 0.0)
		root.add_child(arm)
		add_mesh(arm, capsule(0.09, 0.46), fur, Vector3(0, -0.2, 0))

	add_mesh(root, sphere(0.42), fur, Vector3(0, 0.78, 0), Vector3(1.0, 1.05, 0.9))
	add_mesh(root, sphere(0.36), accent, Vector3(0, 0.74, -0.12), Vector3(1.0, 1.0, 0.7))

	var head := Node3D.new()
	head.name = "Head"
	head.position = Vector3(0, 1.38, 0)
	root.add_child(head)
	add_mesh(head, sphere(0.4), fur, Vector3.ZERO, Vector3(1.1, 0.95, 1.0))

	for side in [-1, 1]:
		add_mesh(head, sphere(0.065), dark, Vector3(side * 0.16, 0.04, -0.37))
		add_mesh(head, sphere(0.022), Color.WHITE, Vector3(side * 0.15, 0.07, -0.43))
		add_mesh(head, sphere(0.06), Color(1, 0.6, 0.65), Vector3(side * 0.27, -0.08, -0.31),
				Vector3(1, 0.6, 0.4))

	var nose_z := -0.42
	match species:
		"dog":
			nose_z = -0.46
			for side in [-1, 1]:
				add_mesh(head, sphere(0.16), accent, Vector3(side * 0.42, 0.02, 0),
						Vector3(0.6, 1.4, 0.9), Vector3(0, 0, side * 15))
			add_mesh(head, sphere(0.16), fur.lightened(0.35), Vector3(0, -0.12, -0.3),
					Vector3(1.2, 0.8, 0.9))
			add_mesh(root, sphere(0.12), fur, Vector3(0, 0.55, 0.38))
			add_mesh(head, sphere(0.1), accent, Vector3(0, 0.42, -0.05))
		"bunny":
			for side in [-1, 1]:
				add_mesh(head, capsule(0.09, 0.62), fur, Vector3(side * 0.18, 0.62, 0),
						Vector3.ONE, Vector3(0, 0, -side * 8))
				add_mesh(head, capsule(0.05, 0.5), Color(1, 0.7, 0.8), Vector3(side * 0.18, 0.62, -0.06),
						Vector3.ONE, Vector3(0, 0, -side * 8))
			add_mesh(root, sphere(0.14), Color.WHITE, Vector3(0, 0.55, 0.38))
		"frog":
			for side in [-1, 1]:
				add_mesh(head, sphere(0.14), fur, Vector3(side * 0.22, 0.34, -0.1))
				add_mesh(head, sphere(0.06), dark, Vector3(side * 0.22, 0.36, -0.22))
		"bear":
			for side in [-1, 1]:
				add_mesh(head, sphere(0.14), fur, Vector3(side * 0.3, 0.32, 0))
				add_mesh(head, sphere(0.07), accent, Vector3(side * 0.3, 0.32, -0.06))
	add_mesh(head, sphere(0.05), dark, Vector3(0, -0.06, nose_z), Vector3(1.2, 0.8, 0.8))
	return root


## Balanceo simple de brazos y piernas. move = 0 (quieto) .. 1 (corriendo).
static func animate(model: Node3D, t: float, move: float) -> void:
	var swing := sin(t * 10.0) * 0.7 * move
	(model.get_node("LegL") as Node3D).rotation.x = swing
	(model.get_node("LegR") as Node3D).rotation.x = -swing
	(model.get_node("ArmL") as Node3D).rotation.x = -swing * 0.8
	(model.get_node("ArmR") as Node3D).rotation.x = swing * 0.8
