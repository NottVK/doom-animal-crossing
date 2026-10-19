class_name FishingSpot
extends Node3D
## Minijuego de pesca en el estanque: lanzas el corcho, un pez se acerca, mordisquea un par de
## veces y luego pica. Hay que pulsar E (o F) justo cuando pica: antes lo espantas, tarde se escapa.
## Espacio recoge el sedal.

enum State { IDLE, WAITING, NIBBLE, BITE }

const FISH := [
	{ "name": "Carpín", "bells": 160, "min": 8, "max": 20, "weight": 40, "size": 0.7 },
	{ "name": "Carpa", "bells": 300, "min": 25, "max": 60, "weight": 30, "size": 1.1 },
	{ "name": "Lubina", "bells": 400, "min": 30, "max": 70, "weight": 20, "size": 1.2 },
	{ "name": "Pez dorado", "bells": 1300, "min": 6, "max": 14, "weight": 8, "size": 0.6 },
	{ "name": "Koi", "bells": 4000, "min": 40, "max": 80, "weight": 2, "size": 1.4 },
]
const BITE_WINDOW := 0.7

var pond_center := Vector3.ZERO
var pond_radius := 2.5

var _state := State.IDLE
var _player: Player
var _hud: HUD
var _bobber: Node3D
var _bobber_rest := Vector3.ZERO
var _shadow: Node3D
var _line: MeshInstance3D
var _fish: Dictionary = {}
var _timer := 0.0
var _nibbles := 0
var _dip := 0.0
var _t := 0.0
var _ignore_frame := -1
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	var area := Area3D.new()
	area.collision_layer = 4
	area.collision_mask = 0
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.9
	shape.shape = sphere
	shape.position.y = 0.8
	area.add_child(shape)
	add_child(area)


func is_busy() -> bool:
	return _state != State.IDLE


func interact(player: Player) -> void:
	if _state != State.IDLE:
		return
	_player = player
	_hud = get_tree().get_first_node_in_group("hud") as HUD
	_ignore_frame = Engine.get_process_frames() + 1
	player.can_move = false
	player.face_point(pond_center)
	_fish = _pick_fish()
	_cast()


func _pick_fish() -> Dictionary:
	var total := 0
	for f in FISH:
		total += f["weight"]
	var r := _rng.randi_range(1, total)
	for f in FISH:
		r -= f["weight"]
		if r <= 0:
			return f
	return FISH[0]


func _cast() -> void:
	var toward := (global_position - pond_center)
	toward.y = 0.0
	_bobber_rest = pond_center + toward.normalized() * pond_radius * 0.35
	_bobber = Node3D.new()
	get_parent().add_child(_bobber)
	_bobber.global_position = _bobber_rest
	CharacterModel.add_mesh(_bobber, CharacterModel.sphere(0.09), Color(0.95, 0.2, 0.2), Vector3(0, 0.05, 0))
	CharacterModel.add_mesh(_bobber, CharacterModel.sphere(0.09), Color.WHITE, Vector3(0, -0.02, 0), Vector3(1, 0.7, 1))

	_line = MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.006
	cyl.bottom_radius = 0.006
	cyl.height = 1.0
	_line.mesh = cyl
	_line.material_override = CharacterModel.mat(Color(0.95, 0.95, 0.95))
	get_parent().add_child(_line)

	# Sombra del pez: aparece lejos del corcho y se acerca nadando.
	_shadow = Node3D.new()
	get_parent().add_child(_shadow)
	var size: float = _fish["size"]
	var mi := CharacterModel.add_mesh(_shadow, CharacterModel.sphere(0.25), Color(0.05, 0.08, 0.12, 0.55),
			Vector3.ZERO, Vector3(0.45, 0.12, 1.0) * size)
	mi.material_override = CharacterModel.mat(Color(0.05, 0.08, 0.12, 0.55), true)
	var a := _rng.randf() * TAU
	_shadow.global_position = pond_center + Vector3(cos(a), 0, sin(a)) * pond_radius * 0.75 + Vector3(0, -0.06, 0)

	_state = State.WAITING
	_timer = _rng.randf_range(1.0, 2.5)
	_hud.toast("Lanzas el sedal... (Espacio para recoger)", 2.5)


func _process(delta: float) -> void:
	if _state == State.IDLE:
		return
	_t += delta
	_timer -= delta
	match _state:
		State.WAITING:
			var target := _bobber_rest + Vector3(0, -0.06, 0)
			var to := target - _shadow.global_position
			to.y = 0.0
			if _timer <= 0.0 and to.length() > 0.35:
				_shadow.global_position += to.normalized() * 0.45 * delta
				_shadow.look_at(_shadow.global_position + to, Vector3.UP)
			elif to.length() <= 0.35:
				_state = State.NIBBLE
				_nibbles = _rng.randi_range(1, 3)
				_timer = _rng.randf_range(0.6, 1.1)
			_shadow.position.x += sin(_t * 6.0) * 0.002
		State.NIBBLE:
			if _timer <= 0.0:
				_dip = 0.05
				_nibbles -= 1
				if _nibbles < 0:
					_state = State.BITE
					_timer = BITE_WINDOW
					_dip = 0.18
					_hud.toast("¡Pica! ¡Ahora!", 0.6)
				else:
					_timer = _rng.randf_range(0.7, 1.3)
		State.BITE:
			_dip = 0.18
			if _timer <= 0.0:
				_finish(false, "Se escapó... hay que ser más rápida.")
				return
	_dip = move_toward(_dip, 0.0, delta * 0.4) if _state != State.BITE else _dip
	if _bobber:
		_bobber.global_position = _bobber_rest + Vector3(0, sin(_t * 2.5) * 0.015 - _dip, 0)
	_update_line()


func _update_line() -> void:
	if _line == null or _player == null:
		return
	var tip := _player.global_position + Vector3(0, 1.6, 0) + (_bobber_rest - _player.global_position).normalized() * 0.8
	tip.y = _player.global_position.y + 1.6
	var end := _bobber.global_position + Vector3(0, 0.12, 0)
	var mid := (tip + end) * 0.5
	var dir := end - tip
	_line.global_position = mid
	_line.look_at(mid + dir, Vector3.UP if absf(dir.normalized().y) < 0.99 else Vector3.FORWARD)
	_line.rotate_object_local(Vector3.RIGHT, PI / 2)
	_line.scale = Vector3(1, dir.length(), 1)


func _unhandled_input(event: InputEvent) -> void:
	if _state == State.IDLE or Engine.get_process_frames() <= _ignore_frame:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("net"):
		get_viewport().set_input_as_handled()
		reel()
	elif event.is_action_pressed("jump"):
		get_viewport().set_input_as_handled()
		_finish(false, "Recoges el sedal.")


## Tirar del sedal: solo funciona en el momento en que el pez pica.
func reel() -> void:
	match _state:
		State.BITE:
			_catch()
		State.WAITING, State.NIBBLE:
			_finish(false, "Tiraste muy pronto... el pez se asustó.")


func _catch() -> void:
	var size := _rng.randi_range(int(_fish["min"]), int(_fish["max"]))
	var reward: int = _fish["bells"]
	var fish_name: String = _fish["name"]
	Story.catch_fish(reward)
	_cleanup()
	# El pez sale del agua y se muestra sobre la cabeza.
	var trophy := WorldAssets.instance("fish")
	trophy.scale = Vector3.ONE * (1.5 + float(_fish["size"]) * 1.5)
	get_parent().add_child(trophy)
	trophy.global_position = _player.global_position + Vector3(0, 2.3, 0)
	trophy.rotation.y = PI / 2
	var tw := create_tween().set_loops(4)
	tw.tween_property(trophy, "rotation:z", 0.4, 0.15)
	tw.tween_property(trophy, "rotation:z", -0.4, 0.15)
	_hud.say("¡Pescaste!", [
		"¡Pesqué un %s de %d cm!" % [fish_name.to_lower(), size],
		"Vale %d campanas. ¡Qué buena pieza!" % reward,
	], _end_after_catch.bind(trophy))


func _end_after_catch(trophy: Node3D) -> void:
	trophy.queue_free()
	_release_player()


func _finish(_success: bool, msg: String) -> void:
	_cleanup()
	if _hud:
		_hud.toast(msg, 2.5)
	_release_player()


func _cleanup() -> void:
	_state = State.IDLE
	for n in [_bobber, _shadow, _line]:
		if is_instance_valid(n):
			n.queue_free()
	_bobber = null
	_shadow = null
	_line = null


func _release_player() -> void:
	if _player:
		_player.can_move = true
