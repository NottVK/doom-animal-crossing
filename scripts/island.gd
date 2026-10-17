extends Node3D
## Construye la isla completa por código: terreno, casas, árboles, aldeanos, mariposas,
## ciclo día/noche y la grieta que cierra el capítulo 1.

const ISLAND_RADIUS := 38.0
const PLAZA_RADIUS := 7.0
const DAY_LENGTH := 300.0
const BUTTERFLY_COUNT := 10
const RIFT_DELAY := 9.0

var _rng := RandomNumberGenerator.new()
var _sun: DirectionalLight3D
var _env: Environment
var _sky_mat: ProceduralSkyMaterial
var _time := 0.38
var _omen := 0.0
var _player: Player
var _hud: HUD
var _rift: Node3D
var _occupied: Array[Vector3] = []


func _ready() -> void:
	Story.reset()
	_rng.seed = 20200320
	_build_environment()
	_build_terrain()
	_build_plaza()
	_build_houses()
	_build_trees()
	_build_flowers()
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


# ---------- ambiente ----------

func _build_environment() -> void:
	_sky_mat = ProceduralSkyMaterial.new()
	var sky := Sky.new()
	sky.sky_material = _sky_mat
	_env = Environment.new()
	_env.background_mode = Environment.BG_SKY
	_env.sky = sky
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	_env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = _env
	add_child(we)

	_sun = DirectionalLight3D.new()
	_sun.shadow_enabled = true
	_sun.directional_shadow_max_distance = 70.0
	add_child(_sun)
	_apply_time()


func _apply_time() -> void:
	var elev := sin((_time - 0.25) * TAU)
	_sun.rotation_degrees = Vector3(-(_time - 0.25) * 360.0, 30.0, 0.0)
	_sun.light_energy = clampf(elev * 1.6, 0.0, 0.8) * (1.0 - _omen * 0.5)
	_sun.light_color = Color(1, 0.95, 0.85).lerp(Color(1.0, 0.55, 0.3),
			clampf(1.0 - absf(elev) * 3.0, 0.0, 1.0))

	var day := clampf(elev * 2.0 + 0.5, 0.0, 1.0)
	var dusk := clampf(1.0 - absf(elev) * 4.0, 0.0, 1.0)
	var top := Color(0.03, 0.04, 0.12).lerp(Color(0.35, 0.65, 0.95), day)
	var hor := Color(0.08, 0.1, 0.22).lerp(Color(0.78, 0.92, 1.0), day).lerp(Color(1.0, 0.6, 0.4), dusk * 0.6)
	top = top.lerp(Color(0.25, 0.02, 0.04), _omen)
	hor = hor.lerp(Color(0.9, 0.2, 0.1), _omen)
	_sky_mat.sky_top_color = top
	_sky_mat.sky_horizon_color = hor
	_sky_mat.ground_horizon_color = hor
	_sky_mat.ground_bottom_color = top.darkened(0.4)
	_env.ambient_light_energy = lerpf(0.2, 0.7, day)


# ---------- terreno ----------

func _build_terrain() -> void:
	var island := StaticBody3D.new()
	island.collision_layer = 1
	add_child(island)

	var grass := CylinderMesh.new()
	grass.top_radius = ISLAND_RADIUS
	grass.bottom_radius = ISLAND_RADIUS - 1.5
	grass.height = 2.0
	CharacterModel.add_mesh(island, grass, Color(0.5, 0.82, 0.38), Vector3(0, -1.0, 0))

	var beach := CylinderMesh.new()
	beach.top_radius = ISLAND_RADIUS + 4.0
	beach.bottom_radius = ISLAND_RADIUS + 6.0
	beach.height = 1.9
	CharacterModel.add_mesh(island, beach, Color(0.96, 0.88, 0.66), Vector3(0, -1.0, 0))

	var col := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = ISLAND_RADIUS + 3.0
	shape.height = 2.0
	col.shape = shape
	col.position.y = -1.0
	island.add_child(col)

	var sea := PlaneMesh.new()
	sea.size = Vector2(600, 600)
	var sea_mi := CharacterModel.add_mesh(self, sea, Color(0.3, 0.7, 0.9, 0.85), Vector3(0, -0.5, 0))
	var sea_mat := sea_mi.material_override as StandardMaterial3D
	sea_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sea_mat.roughness = 0.1


func _build_plaza() -> void:
	var plaza := CylinderMesh.new()
	plaza.top_radius = PLAZA_RADIUS
	plaza.bottom_radius = PLAZA_RADIUS
	plaza.height = 0.06
	CharacterModel.add_mesh(self, plaza, Color(0.93, 0.8, 0.58), Vector3(0, 0.03, 0))
	_occupied.append(Vector3.ZERO)

	var sign_post := StaticBody3D.new()
	sign_post.position = Vector3(0, 0, 3.0)
	add_child(sign_post)
	CharacterModel.add_mesh(sign_post, CharacterModel.capsule(0.08, 1.4), Color(0.55, 0.38, 0.24), Vector3(0, 0.7, 0))
	var board := BoxMesh.new()
	board.size = Vector3(1.8, 0.7, 0.1)
	CharacterModel.add_mesh(sign_post, board, Color(0.95, 0.85, 0.6), Vector3(0, 1.5, 0))
	var label := Label3D.new()
	label.text = "Isla Calma"
	label.font_size = 64
	label.pixel_size = 0.0075
	label.modulate = Color("5b4636")
	label.position = Vector3(0, 1.5, 0.07)
	sign_post.add_child(label)
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.8, 2, 0.3)
	col.shape = box
	col.position.y = 1.0
	sign_post.add_child(col)


func _build_houses() -> void:
	var specs := [
		{ "angle": 40.0, "wall": Color(0.99, 0.9, 0.7), "roof": Color(0.9, 0.45, 0.4) },
		{ "angle": 160.0, "wall": Color(0.98, 0.78, 0.85), "roof": Color(0.45, 0.65, 0.9) },
		{ "angle": 280.0, "wall": Color(0.8, 0.92, 0.8), "roof": Color(0.85, 0.65, 0.3) },
	]
	for s in specs:
		var a := deg_to_rad(s["angle"] as float)
		var pos := Vector3(cos(a), 0.0, sin(a)) * 18.0
		_occupied.append(pos)
		_build_house(pos, s["wall"] as Color, s["roof"] as Color)
		_build_path(pos)


func _build_house(pos: Vector3, wall: Color, roof: Color) -> void:
	var h := StaticBody3D.new()
	h.position = pos
	add_child(h)
	h.look_at(Vector3(0, pos.y, 0))   # la puerta (-Z) mira a la plaza

	var body := BoxMesh.new()
	body.size = Vector3(4, 2.6, 4)
	CharacterModel.add_mesh(h, body, wall, Vector3(0, 1.3, 0))
	var roof_mesh := PrismMesh.new()
	roof_mesh.size = Vector3(5.2, 1.8, 5.2)
	CharacterModel.add_mesh(h, roof_mesh, roof, Vector3(0, 3.5, 0), Vector3.ONE, Vector3(0, 90, 0))
	var door := BoxMesh.new()
	door.size = Vector3(1, 1.7, 0.1)
	CharacterModel.add_mesh(h, door, Color(0.55, 0.38, 0.24), Vector3(0, 0.85, -2.03))
	var window := BoxMesh.new()
	window.size = Vector3(0.8, 0.8, 0.1)
	for side in [-1, 1]:
		CharacterModel.add_mesh(h, window, Color(0.7, 0.9, 1.0), Vector3(side * 1.3, 1.5, -2.03))

	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(4, 2.6, 4)
	col.shape = shape
	col.position.y = 1.3
	h.add_child(col)


func _build_path(to: Vector3) -> void:
	var length := to.length() - 3.0
	var path := BoxMesh.new()
	path.size = Vector3(2.0, 0.05, length)
	var mi := CharacterModel.add_mesh(self, path, Color(0.93, 0.8, 0.58), to * 0.5 + Vector3(0, 0.025, 0))
	mi.rotation.y = atan2(to.x, to.z)


func _is_blocked(p: Vector3, dist: float) -> bool:
	for o in _occupied:
		if p.distance_to(o) < dist:
			return true
	return false


func _build_trees() -> void:
	var count := 0
	var tries := 0
	while count < 38 and tries < 600:
		tries += 1
		var a := _rng.randf() * TAU
		var r := _rng.randf_range(PLAZA_RADIUS + 3.0, ISLAND_RADIUS - 3.0)
		var p := Vector3(cos(a) * r, 0.0, sin(a) * r)
		if _is_blocked(p, 5.5):
			continue
		_occupied.append(p)
		count += 1
		_add_tree(p)


func _add_tree(p: Vector3) -> void:
	var tree := StaticBody3D.new()
	tree.position = p
	add_child(tree)
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.25
	trunk.bottom_radius = 0.32
	trunk.height = 2.2
	CharacterModel.add_mesh(tree, trunk, Color(0.55, 0.38, 0.24), Vector3(0, 1.1, 0))
	var leaf := Color.from_hsv(_rng.randf_range(0.25, 0.37), 0.6, _rng.randf_range(0.65, 0.85))
	CharacterModel.add_mesh(tree, CharacterModel.sphere(1.7), leaf, Vector3(0, 3.3, 0), Vector3(1, 0.9, 1))
	CharacterModel.add_mesh(tree, CharacterModel.sphere(1.0), leaf.lightened(0.15), Vector3(0.7, 4.3, 0.3))
	if _rng.randf() < 0.35:
		for i in 5:
			var fp := Vector3(_rng.randf_range(-1.3, 1.3), _rng.randf_range(2.6, 3.8), _rng.randf_range(-1.3, 1.3))
			CharacterModel.add_mesh(tree, CharacterModel.sphere(0.13), Color(1.0, 0.55, 0.15), fp)
	var col := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = 0.4
	shape.height = 3.0
	col.shape = shape
	col.position.y = 1.5
	tree.add_child(col)


func _build_flowers() -> void:
	var palette: Array[Color] = [
		Color(1, 0.5, 0.6), Color(1, 0.9, 0.3), Color(0.9, 0.9, 1),
		Color(1, 0.65, 0.3), Color(0.8, 0.5, 1),
	]
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = CharacterModel.sphere(0.12)
	var spots: Array[Vector3] = []
	var tries := 0
	while spots.size() < 350 and tries < 2000:
		tries += 1
		var a := _rng.randf() * TAU
		var r := _rng.randf_range(PLAZA_RADIUS + 1.0, ISLAND_RADIUS - 1.0)
		var p := Vector3(cos(a) * r, 0.1, sin(a) * r)
		var near_house := false
		for o in _occupied:
			if o.length() > 15.0 and p.distance_to(o) < 3.5:
				near_house = true
				break
		if not near_house:
			spots.append(p)
	mm.instance_count = spots.size()
	for i in spots.size():
		mm.set_instance_transform(i, Transform3D(Basis(), spots[i]))
		mm.set_instance_color(i, palette[_rng.randi() % palette.size()])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var m := CharacterModel.mat(Color.WHITE)
	m.vertex_color_use_as_albedo = true
	mmi.material_override = m
	add_child(mmi)


# ---------- personajes ----------

func _build_villagers() -> void:
	var cast := [
		{
			"name": "Lila", "species": "bunny",
			"fur": Color(1, 0.93, 0.95), "accent": Color(1, 0.6, 0.75), "angle": 200.0,
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
			"name": "Pepe", "species": "frog",
			"fur": Color(0.55, 0.85, 0.45), "accent": Color(0.95, 0.85, 0.3), "angle": 250.0,
			"lines": {
				Story.Phase.PEACEFUL: [
					"Croac. La pesca está lenta hoy, pero el sol está perfecto.",
					"Pronto habrá concursos en la isla. ¡Yo ya tengo mi caña lista!",
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
			"name": "Tato", "species": "bear",
			"fur": Color(0.7, 0.5, 0.35), "accent": Color(0.95, 0.6, 0.4), "angle": 300.0,
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
		var a := deg_to_rad(c["angle"] as float)
		v.position = Vector3(cos(a), 0.0, sin(a)) * 4.8
		add_child(v)
		v.face(Vector3.ZERO)


func _build_player() -> void:
	_player = Player.new()
	_player.position = Vector3(0, 0.5, 3.0 + 2.5)
	add_child(_player)


func _build_hud() -> void:
	_hud = HUD.new()
	add_child(_hud)
	_player.target_changed.connect(_on_target_changed)


func _on_target_changed(target: Node3D) -> void:
	if target is Villager:
		_hud.set_prompt("[E] Hablar con %s" % (target as Villager).display_name)
	else:
		_hud.set_prompt("")


func _spawn_butterfly() -> void:
	var b := Butterfly.new()
	var a := _rng.randf() * TAU
	var r := _rng.randf_range(4.0, ISLAND_RADIUS - 6.0)
	b.position = Vector3(cos(a) * r, _rng.randf_range(1.0, 2.2), sin(a) * r)
	b.limit = ISLAND_RADIUS - 4.0
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
	_rift.position = Vector3(0, 0.07, 0)
	_rift.scale = Vector3.ONE * 0.05
	add_child(_rift)

	var glow := StandardMaterial3D.new()
	glow.albedo_color = Color(0.1, 0.0, 0.0)
	glow.emission_enabled = true
	glow.emission = Color(1.0, 0.25, 0.05)
	glow.emission_energy_multiplier = 2.5

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
	var ember_mat := StandardMaterial3D.new()
	ember_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ember_mat.albedo_color = Color(1.0, 0.6, 0.15)
	ember_mesh.material = ember_mat
	embers.mesh = ember_mesh
	_rift.add_child(embers)

	var tw := create_tween()
	tw.tween_property(_rift, "scale", Vector3.ONE, 3.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_player.shake(3.0, 0.06)
	_hud.toast("Se abrió una grieta en la plaza...", 4.0)
	get_tree().create_timer(6.0).timeout.connect(
			_hud.show_endcard.bind("CAPÍTULO 1 · FIN\n\nAlgo viene del otro lado..."))
