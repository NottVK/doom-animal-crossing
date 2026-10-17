class_name CharacterModel
extends RefCounted
## Genera animalitos redondos con primitivas (placeholder hasta tener modelos de Blender).
## El frente del modelo apunta a -Z.

static func mat(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 1.0
	m.metallic_specular = 0.0
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
