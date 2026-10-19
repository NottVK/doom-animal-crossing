extends Node3D
## Construye la isla como un carril largo visto de lado (2.5D): caminas a izquierda/derecha y
## solo hay profundidad en las zonas de DEPTH_ZONES (plaza, puertas de las casas, playa).
## También crea el clima, el ciclo día/noche y la grieta que cierra el capítulo 1.

const BUTTERFLY_COUNT := 16
const DAY_LENGTH := 300.0
const RIFT_DELAY := 9.0
const PLAZA_RADIUS := 7.0
const HOUSE_XS := [-24.0, 18.0, 30.0]

## Rango de z permitido fuera de las zonas (un carril con un poco de holgura).
const LANE := Vector2(-0.7, 0.7)

## Zonas donde se puede ir al fondo/frente: centro x, semiancho, borde suave, z mínima y máxima.
const DEPTH_ZONES := [
	{ "x": 0.0, "half": 8.0, "edge": 3.0, "zmin": -5.5, "zmax": 4.0 },
	{ "x": -24.0, "half": 2.2, "edge": 1.5, "zmin": -4.3, "zmax": 0.7 },
	{ "x": 18.0, "half": 2.2, "edge": 1.5, "zmin": -4.3, "zmax": 0.7 },
	{ "x": 30.0, "half": 2.2, "edge": 1.5, "zmin": -4.3, "zmax": 0.7 },
	{ "x": -31.0, "half": 2.5, "edge": 1.5, "zmin": -0.7, "zmax": 2.7 },   # orilla del estanque
]

var _rng := RandomNumberGenerator.new()
var _sun: DirectionalLight3D
var _env: Environment
var _sky_mat: ProceduralSkyMaterial
var _time := 0.38
var _omen := 0.0
var _player: Player
var _hud: HUD
var _rift: Node3D
var _clouds: Array[Node3D] = []
var _occupied: Array[Vector3] = []


func _ready() -> void:
	Story.reset()
	_rng.seed = 20200320
	_build_environment()
	_build_terrain()
	_build_houses()
	_build_props()
	_build_vegetation()
	_build_pond()
	_build_scenery()
	_build_villagers()
	_build_player()
	_build_hud()
	for i in BUTTERFLY_COUNT:
		_spawn_butterfly()
	Story.phase_changed.connect(_on_phase_changed)


func _process(delta: float) -> void:
	_time = fposmod(_time + delta / DAY_LENGTH, 1.0)
	var target := 0.0 if Story.phase == Story.Phase.PEACEFUL else 1.0
	_omen = move_toward(_omen, target, delta / 6.0)
	_apply_time()
	for c in _clouds:
		c.position.x += delta * 0.8
		if c.position.x > 100.0:
			c.position.x = -100.0


## Rango de profundidad (z mínima, z máxima) permitido en la posición x.
func lane_range(x: float) -> Vector2:
	var lo := LANE.x
	var hi := LANE.y
	for zone: Dictionary in DEPTH_ZONES:
		var half: float = zone["half"]
		var w := 1.0 - smoothstep(half, half + float(zone["edge"]), absf(x - float(zone["x"])))
		lo = minf(lo, lerpf(LANE.x, float(zone["zmin"]), w))
		hi = maxf(hi, lerpf(LANE.y, float(zone["zmax"]), w))
	return Vector2(lo, hi)


# ---------- ambiente ----------

func _build_environment() -> void:
	_sky_mat = ProceduralSkyMaterial.new()
	var sky := Sky.new()
	sky.sky_material = _sky_mat
	_env = Environment.new()
	_env.background_mode = Environment.BG_SKY
	_env.sky = sky
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	var we := WorldEnvironment.new()
	we.environment = _env
	add_child(we)

	_sun = DirectionalLight3D.new()
	_sun.shadow_enabled = true
	_sun.directional_shadow_max_distance = 60.0
	add_child(_sun)
	_apply_time()


func _apply_time() -> void:
	var elev := sin((_time - 0.25) * TAU)
	_sun.rotation_degrees = Vector3(-(_time - 0.25) * 360.0, 25.0, 0.0)
	_sun.light_energy = clampf(elev * 1.6, 0.0, 0.6) * (1.0 - _omen * 0.5)
	_sun.light_color = Color(1, 0.96, 0.88).lerp(Color(1.0, 0.6, 0.35),
			clampf(1.0 - absf(elev) * 3.0, 0.0, 1.0))

	var day := clampf(elev * 2.0 + 0.5, 0.0, 1.0)
	var dusk := clampf(1.0 - absf(elev) * 4.0, 0.0, 1.0)
	var top := Color(0.05, 0.06, 0.16).lerp(Color(0.45, 0.75, 0.98), day)
	var hor := Color(0.1, 0.12, 0.25).lerp(Color(0.86, 0.96, 1.0), day).lerp(Color(1.0, 0.7, 0.55), dusk * 0.6)
	top = top.lerp(Color(0.25, 0.02, 0.04), _omen)
	hor = hor.lerp(Color(0.9, 0.2, 0.1), _omen)
	_sky_mat.sky_top_color = top
	_sky_mat.sky_horizon_color = hor
	_sky_mat.ground_horizon_color = hor
	_sky_mat.ground_bottom_color = top.darkened(0.4)
	_env.ambient_light_energy = lerpf(0.2, 0.4, day)


# ---------- terreno ----------

func _plane(size: Vector2, pos: Vector3, color: Color, sub_w: int, sub_d: int, alpha := false) -> MeshInstance3D:
	var pm := PlaneMesh.new()
	pm.size = size
	pm.subdivide_width = sub_w
	pm.subdivide_depth = sub_d
	var mi := CharacterModel.add_mesh(self, pm, color, pos)
	if alpha:
		mi.material_override = CharacterModel.mat(color, true)
	return mi


const POND := Vector2(-31.0, 5.6)
const POND_R := 2.6
const PLAZA_C := Vector2(0.0, -0.5)

var _noise := FastNoiseLite.new()
var _noise2 := FastNoiseLite.new()


## Suelo plano en las zonas por donde se camina (carril, plaza, patios); relieve en el resto.
func _flat_mask(x: float, z: float) -> float:
	var m := smoothstep(2.4, 5.0, absf(z))
	m *= smoothstep(PLAZA_RADIUS + 1.0, PLAZA_RADIUS + 3.5, Vector2(x, z).distance_to(PLAZA_C))
	for hx: float in HOUSE_XS:
		m *= smoothstep(3.8, 6.0, Vector2(x, z).distance_to(Vector2(hx, -6.5)))
	return m


## Altura del suelo: colinas suaves al fondo, estanque hundido y orilla que baja al mar.
func ground_height(x: float, z: float) -> float:
	var n := _noise.get_noise_2d(x, z)
	var back := 1.0 - smoothstep(-16.0, -6.0, z)
	var h := back * (0.5 + n * 1.3) + n * 0.12
	h *= _flat_mask(x, z)
	h -= smoothstep(10.0, 14.0, z) * 0.9
	var dp := Vector2(x, z).distance_to(POND)
	if dp < POND_R + 0.8:
		h = lerpf(-0.6, h, smoothstep(POND_R - 0.9, POND_R + 0.8, dp))
	return h


## Color del suelo: pasto con matices, caminos de tierra de borde irregular, plaza empedrada y arena.
func _ground_color(x: float, z: float, h: float) -> Color:
	var n2 := _noise2.get_noise_2d(x, z)
	var col := Color(0.42, 0.66, 0.33).lerp(Color(0.50, 0.72, 0.38), n2 * 0.5 + 0.5)
	col = col.lerp(Color(0.34, 0.56, 0.28), clampf(h * 0.3, 0.0, 0.35))
	col = col.lerp(Color(0.88, 0.80, 0.60), smoothstep(8.6, 9.6, z + n2 * 0.6))
	var dp := Vector2(x, z).distance_to(POND)
	col = col.lerp(Color(0.80, 0.72, 0.55), 1.0 - smoothstep(POND_R + 0.3, POND_R + 1.0, dp + n2 * 0.3))

	var dirt := Color(0.74, 0.60, 0.42).lerp(Color(0.68, 0.54, 0.37), n2 * 0.5 + 0.5)
	var path := 1.0 - smoothstep(1.0, 1.3, absf(z) + n2 * 0.25)
	for hx: float in HOUSE_XS:
		if z < 0.5 and z > -4.6:
			path = maxf(path, 1.0 - smoothstep(0.75, 1.05, absf(x - hx) + n2 * 0.2))
	if z > 0.0 and z < POND.y - POND_R + 0.4:
		path = maxf(path, 1.0 - smoothstep(0.75, 1.05, absf(x - POND.x) + n2 * 0.2))
	col = col.lerp(dirt, path)

	var dpl := Vector2(x, z).distance_to(PLAZA_C)
	var tile := posmod(int(floor(x / 1.1)) + int(floor(z / 1.1)), 2)
	var stone := Color(0.82, 0.74, 0.62) if tile == 0 else Color(0.76, 0.68, 0.57)
	stone = stone.lerp(Color(0.62, 0.57, 0.50), clampf(n2, 0.0, 1.0) * 0.5)
	col = col.lerp(stone, 1.0 - smoothstep(PLAZA_RADIUS - 0.2, PLAZA_RADIUS + 0.2, dpl + n2 * 0.3))
	return col


func _build_terrain() -> void:
	_noise.seed = 7
	_noise.frequency = 0.035
	_noise2.seed = 11
	_noise2.frequency = 0.18

	var ground := StaticBody3D.new()
	ground.collision_layer = 1
	add_child(ground)
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(100, 2, 44)
	col.shape = box
	col.position = Vector3(0, -1, -5)
	ground.add_child(col)

	# Malla del suelo generada: relieve, normales y color por vértice.
	var step := 0.6
	var x0 := -60.0
	var z0 := -34.0
	var nx := int(120.0 / step) + 1
	var nz := int(50.0 / step) + 1
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols := PackedColorArray()
	verts.resize(nx * nz)
	norms.resize(nx * nz)
	cols.resize(nx * nz)
	var e := 0.3
	for j in nz:
		for i in nx:
			var x := x0 + i * step
			var z := z0 + j * step
			var h := ground_height(x, z)
			var k := j * nx + i
			verts[k] = Vector3(x, h, z)
			norms[k] = Vector3(ground_height(x - e, z) - ground_height(x + e, z), 2.0 * e,
					ground_height(x, z - e) - ground_height(x, z + e)).normalized()
			cols[k] = _ground_color(x, z, h).srgb_to_linear()
	var idx := PackedInt32Array()
	for j in nz - 1:
		for i in nx - 1:
			var a := j * nx + i
			var c := a + nx
			idx.append_array([a, a + 1, c, a + 1, c + 1, c])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mi := MeshInstance3D.new()
	mi.mesh = am
	var m := CharacterModel.mat(Color.WHITE)
	m.set_shader_parameter("use_vertex_color", true)
	mi.material_override = m
	add_child(mi)

	_plane(Vector2(700, 700), Vector3(0, -0.6, 0), Color(0.4, 0.78, 0.92, 0.85), 70, 70, true)


func _place(model: String, pos: Vector3, rot_y := 0.0, scl := 1.0) -> Node3D:
	var n := WorldAssets.instance(model)
	n.position = pos
	n.rotation.y = rot_y
	n.scale = Vector3.ONE * scl
	add_child(n)
	return n


func _build_houses() -> void:
	var models := ["house_a", "house_b", "house_c"]
	for i in HOUSE_XS.size():
		var pos := Vector3(HOUSE_XS[i], 0.0, -6.5)
		_occupied.append(pos)
		_place(models[i], pos, PI)   # la puerta mira a la cámara
		var body := StaticBody3D.new()
		body.position = pos
		add_child(body)
		var col := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = Vector3(4.4, 3.0, 4.4)
		col.shape = shape
		col.position.y = 1.5
		body.add_child(col)


## Letrero de la plaza, farolas en el camino y tramos de cerca.
func _build_props() -> void:
	_occupied.append(Vector3(PLAZA_C.x, 0, PLAZA_C.y))
	_place("signboard", Vector3(4.5, 0, -3.5), PI)
	var label := Label3D.new()
	label.text = "Isla Calma"
	label.font_size = 64
	label.pixel_size = 0.0075
	label.modulate = Color("5b4636")
	label.position = Vector3(4.5, 1.45, -3.43)
	add_child(label)
	for x in [-16.0, -7.5, 9.0, 25.0]:
		_place("lamp", Vector3(x, 0, -1.8))
	for row in [[-19.5, -12.0], [11.0, 14.0], [22.5, 26.0]]:
		var x: float = row[0]
		while x <= row[1]:
			_place("fence", Vector3(x, 0, -2.4))
			x += 1.9


func _in_walkway(x: float, z: float) -> bool:
	if absf(z) < 1.8:
		return true
	if Vector2(x, z).distance_to(PLAZA_C) < PLAZA_RADIUS + 0.8:
		return true
	for hx: float in HOUSE_XS:
		if absf(x - hx) < 1.6 and z > -5.0 and z < 1.0:
			return true
	if Vector2(x, z).distance_to(POND) < POND_R + 1.2:
		return true
	if absf(x - POND.x) < 1.6 and z > 0.0 and z < POND.y:
		return true
	return false


func _is_blocked(p: Vector3, dist: float) -> bool:
	for o in _occupied:
		if p.distance_to(o) < dist:
			return true
	return false


## Árboles, arbustos, rocas, flores y pasto (modelos de Blender).
func _build_vegetation() -> void:
	var trees := ["tree_round", "tree_round2", "tree_fruit", "tree_cedar"]
	var count := 0
	var tries := 0
	while count < 44 and tries < 900:
		tries += 1
		var p := Vector3(_rng.randf_range(-48.0, 48.0), 0.0, _rng.randf_range(-24.0, -9.5))
		if _is_blocked(p, 4.6):
			continue
		_occupied.append(p)
		count += 1
		p.y = ground_height(p.x, p.z) - 0.1
		var model: String = trees[_rng.randi() % trees.size()]
		_place(model, p, _rng.randf() * TAU, _rng.randf_range(0.85, 1.15))

	# arbustos a los lados del camino, fuera de las zonas de paso
	var bushes := 0
	tries = 0
	while bushes < 24 and tries < 600:
		tries += 1
		var x := _rng.randf_range(-44.0, 44.0)
		var z := _rng.randf_range(-4.2, -2.6) if _rng.randf() < 0.5 else _rng.randf_range(2.6, 4.4)
		var p := Vector3(x, 0, z)
		if _in_walkway(x, z) or lane_range(x).y > 1.0 or lane_range(x).x < -1.0 or _is_blocked(p, 2.2):
			continue
		_occupied.append(p)
		bushes += 1
		_place("bush_pink" if _rng.randf() < 0.5 else "bush_white", p, _rng.randf() * TAU, _rng.randf_range(0.8, 1.2))

	for i in 12:
		var p := Vector3(_rng.randf_range(-46.0, 46.0), 0, _rng.randf_range(-12.0, -5.0))
		if _in_walkway(p.x, p.z) or _is_blocked(p, 2.5):
			continue
		p.y = ground_height(p.x, p.z) - 0.05
		_place("rock" if i % 2 else "rock2", p, _rng.randf() * TAU, _rng.randf_range(0.7, 1.3))

	_scatter("grass", 2200, 0.8, 1.4, -14.0, 9.0)
	_scatter("flower_red", 160, 0.9, 1.4, -10.0, 8.0)
	_scatter("flower_yellow", 160, 0.9, 1.4, -10.0, 8.0)
	_scatter("flower_white", 140, 0.9, 1.4, -10.0, 8.0)


## Reparte muchas copias de un modelo pequeño con un solo MultiMesh.
func _scatter(model: String, amount: int, smin: float, smax: float, zmin: float, zmax: float) -> void:
	var xforms: Array[Transform3D] = []
	var tries := 0
	while xforms.size() < amount and tries < amount * 6:
		tries += 1
		var x := _rng.randf_range(-50.0, 50.0)
		var z := _rng.randf_range(zmin, zmax)
		if _in_walkway(x, z):
			continue
		var y := ground_height(x, z)
		if y < -0.25:
			continue
		var s := _rng.randf_range(smin, smax)
		var basis := Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * s)
		xforms.append(Transform3D(basis, Vector3(x, y, z)))
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = WorldAssets.mesh(model)
	mm.instance_count = xforms.size()
	for i in xforms.size():
		mm.set_instance_transform(i, xforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	add_child(mmi)


## Estanque con nenúfares, rocas, juncos y el punto de pesca.
func _build_pond() -> void:
	var water := CylinderMesh.new()
	water.top_radius = POND_R + 0.1
	water.bottom_radius = POND_R + 0.1
	water.height = 0.04
	water.radial_segments = 48
	var wm := MeshInstance3D.new()
	wm.mesh = water
	wm.material_override = CharacterModel.mat(Color(0.22, 0.52, 0.72, 0.85), true)
	wm.position = Vector3(POND.x, -0.2, POND.y)
	add_child(wm)
	for i in 3:
		var a := 1.0 + i * 1.7
		var p := Vector3(POND.x + cos(a) * 1.4, -0.17, POND.y + sin(a) * 1.3)
		var pad := CylinderMesh.new()
		pad.top_radius = 0.28
		pad.bottom_radius = 0.28
		pad.height = 0.02
		CharacterModel.add_mesh(self, pad, Color(0.35, 0.62, 0.30), p)
		if i == 1:
			CharacterModel.add_mesh(self, CharacterModel.sphere(0.09), Color(1.0, 0.65, 0.78), p + Vector3(0.05, 0.05, 0))
	for i in 7:
		var a := PI + 0.3 + i * (PI - 0.6) / 6.0   # mitad trasera de la orilla
		var p := Vector3(POND.x + cos(a) * (POND_R + 0.4), 0, POND.y - sin(a) * (POND_R + 0.4))
		p.y = ground_height(p.x, p.z) - 0.05
		if i % 2 == 0:
			_place("rock" if i % 4 == 0 else "rock2", p, _rng.randf() * TAU, _rng.randf_range(0.5, 0.8))
		else:
			_place("grass", p, _rng.randf() * TAU, 2.2)

	var spot := FishingSpot.new()
	spot.position = Vector3(POND.x, 0, POND.y - POND_R - 0.3)
	spot.pond_center = Vector3(POND.x, -0.18, POND.y)
	spot.pond_radius = POND_R
	add_child(spot)


## Colinas lejanas y nubes: dan profundidad al fondo y hacen que el horizonte se curve.
func _build_scenery() -> void:
	var hill_colors: Array[Color] = [Color(0.66, 0.88, 0.58), Color(0.58, 0.82, 0.6), Color(0.74, 0.9, 0.72)]
	for i in 10:
		var scl := Vector3(_rng.randf_range(16.0, 24.0), _rng.randf_range(7.0, 11.0), 10.0)
		var pos := Vector3(-90.0 + i * 20.0 + _rng.randf_range(-4.0, 4.0), -1.0, _rng.randf_range(-48.0, -36.0))
		CharacterModel.add_mesh(self, CharacterModel.sphere(1.0), hill_colors[i % 3], pos, scl)

	for i in 9:
		var c := Node3D.new()
		c.position = Vector3(_rng.randf_range(-90.0, 90.0), _rng.randf_range(16.0, 26.0), _rng.randf_range(-75.0, -50.0))
		for j in 4:
			var r := _rng.randf_range(3.0, 5.0)
			CharacterModel.add_mesh(c, CharacterModel.sphere(r), Color(1, 1, 1),
					Vector3(j * 4.0 - 6.0, _rng.randf_range(-0.5, 1.0), 0), Vector3(1, 0.6, 0.8))
		add_child(c)
		_clouds.append(c)


# ---------- personajes ----------

func _build_villagers() -> void:
	var cast := [
		{
			"name": "Lila", "species": "bunny", "pos": Vector3(-9, 0, 0),
			"fur": Color(1, 0.93, 0.95), "accent": Color(1, 0.6, 0.75),
			"lines": {
				Story.Phase.PEACEFUL: [
					"¡Hola, Canelita! Qué día más lindo para pasear por la isla.",
					"Dicen que hay mariposas muy bonitas cerca de las flores. ¿Me atrapas unas cuantas con tu red?",
				],
				Story.Phase.OMEN: [
					"¿Sentiste eso? El suelo tembló...",
					"Mis orejas no mienten: algo viene. Ve a la plaza, rápido.",
				],
				Story.Phase.RIFT: [
					"¡Hay fuego en la plaza! Eso no venía en el catálogo de decoración...",
				],
			},
		},
		{
			"name": "Pepe", "species": "frog", "pos": Vector3(-3, 0, -2.5),
			"fur": Color(0.55, 0.85, 0.45), "accent": Color(0.95, 0.85, 0.3),
			"lines": {
				Story.Phase.PEACEFUL: [
					"Croac. La pesca está lenta hoy, pero el sol está perfecto.",
					"¿Ya probaste el estanque del oeste? Acércate a la orilla y pulsa E para pescar.",
					"Cuando el corcho se hunda de golpe, ¡tira! Si tiras antes, el pez se asusta.",
				],
				Story.Phase.OMEN: [
					"Las ranas sentimos las vibraciones... y esto no es un temblor normal.",
				],
				Story.Phase.RIFT: [
					"Croac... croac... ¡Eso viene del otro lado!",
				],
			},
		},
		{
			"name": "Tato", "species": "bear", "pos": Vector3(14, 0, 0),
			"fur": Color(0.7, 0.5, 0.35), "accent": Color(0.95, 0.6, 0.4),
			"lines": {
				Story.Phase.PEACEFUL: [
					"Mmm... huele a pan recién horneado. Hora perfecta para una siesta.",
					"Las mariposas dan buenas campanas. ¡Yo tengo una colección enorme!",
				],
				Story.Phase.OMEN: [
					"¿Oyes ese rugido bajo la tierra? Qué siesta tan rara...",
				],
				Story.Phase.RIFT: [
					"Creo que me voy a quedar muy quieto por aquí. Muy, muy quieto.",
				],
			},
		},
	]
	for c in cast:
		var v := Villager.new()
		v.display_name = c["name"]
		v.species = c["species"]
		v.fur = c["fur"]
		v.accent = c["accent"]
		v.lines = c["lines"]
		v.position = c["pos"]
		add_child(v)
		v.face(v.position + Vector3(0, 0, 20))   # mira a la cámara


func _build_player() -> void:
	_player = Player.new()
	_player.position = Vector3(-14, 0.5, 0)
	_player.lane_limits = lane_range
	add_child(_player)


func _build_hud() -> void:
	_hud = HUD.new()
	add_child(_hud)
	_player.target_changed.connect(_on_target_changed)


func _on_target_changed(target: Node3D) -> void:
	if target is Villager:
		_hud.set_prompt("[E] Hablar con %s" % (target as Villager).display_name)
	elif target is FishingSpot:
		_hud.set_prompt("[E] Pescar")
	else:
		_hud.set_prompt("")


func _spawn_butterfly() -> void:
	var b := Butterfly.new()
	b.position = Vector3(_rng.randf_range(-34.0, 34.0), _rng.randf_range(1.0, 2.2), _rng.randf_range(-3.0, 3.0))
	b.caught.connect(_on_butterfly_caught)
	add_child(b)


func _on_butterfly_caught() -> void:
	await get_tree().create_timer(4.0).timeout
	if Story.phase == Story.Phase.PEACEFUL:
		_spawn_butterfly()


# ---------- historia ----------

func _on_phase_changed(phase: int) -> void:
	if phase == Story.Phase.OMEN:
		_hud.toast("La tierra empieza a temblar...", 4.0)
		_player.shake(RIFT_DELAY, 0.02)
		for b in get_tree().get_nodes_in_group("butterfly"):
			b.queue_free()
		get_tree().create_timer(RIFT_DELAY).timeout.connect(Story.set_phase.bind(Story.Phase.RIFT))
	elif phase == Story.Phase.RIFT:
		_open_rift()


func _open_rift() -> void:
	_rift = Node3D.new()
	_rift.position = Vector3(0, 0.08, -0.5)
	_rift.scale = Vector3.ONE * 0.05
	add_child(_rift)

	var glow := CharacterModel.glow_mat(Color(0.1, 0.0, 0.0), Color(1.0, 0.2, 0.05), 1.3)

	var disc := CylinderMesh.new()
	disc.top_radius = 3.0
	disc.bottom_radius = 3.0
	disc.height = 0.02
	var disc_mi := MeshInstance3D.new()
	disc_mi.mesh = disc
	disc_mi.material_override = glow
	_rift.add_child(disc_mi)

	for i in 9:
		var ang := TAU * i / 9.0 + _rng.randf_range(-0.2, 0.2)
		var len := _rng.randf_range(4.5, 8.0)
		var crack := BoxMesh.new()
		crack.size = Vector3(0.25, 0.03, len)
		var mi := MeshInstance3D.new()
		mi.mesh = crack
		mi.material_override = glow
		mi.position = Vector3(sin(ang), 0.0, cos(ang)) * (len * 0.5)
		mi.rotation.y = ang
		_rift.add_child(mi)

	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.25, 0.1)
	light.light_energy = 6.0
	light.omni_range = 16.0
	light.position.y = 1.5
	_rift.add_child(light)

	var embers := CPUParticles3D.new()
	embers.amount = 100
	embers.lifetime = 3.0
	embers.direction = Vector3.UP
	embers.spread = 20.0
	embers.initial_velocity_min = 1.5
	embers.initial_velocity_max = 4.0
	embers.gravity = Vector3(0, 0.5, 0)
	embers.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	embers.emission_sphere_radius = 2.5
	embers.scale_amount_min = 0.5
	embers.scale_amount_max = 1.5
	var ember_mesh := CharacterModel.sphere(0.05)
	ember_mesh.material = CharacterModel.glow_mat(Color.BLACK, Color(1.0, 0.6, 0.15), 3.0)
	embers.mesh = ember_mesh
	_rift.add_child(embers)

	var tw := create_tween()
	tw.tween_property(_rift, "scale", Vector3.ONE, 3.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_player.shake(3.0, 0.06)
	_hud.toast("Se abrió una grieta en la plaza...", 4.0)
	get_tree().create_timer(6.0).timeout.connect(
			_hud.show_endcard.bind("CAPÍTULO 1 · FIN\n\nAlgo viene del otro lado..."))
