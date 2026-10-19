class_name Player
extends CharacterBody3D
## Canelita en vista lateral 2.5D: se camina de lado por un carril y solo se puede ir
## al fondo/frente dentro de las zonas de profundidad (`lane_limits`).

signal target_changed(target: Node3D)

@export var walk_speed := 4.5
@export var run_speed := 7.5
@export var jump_velocity := 6.5
@export var x_limit := 38.0
@export var camera_x_limit := 30.0

var can_move := true
## Callable(x: float) -> Vector2(z_min, z_max) con el rango de profundidad permitido en esa x.
var lane_limits := Callable()

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _camera: Camera3D
var _model: Node3D
var _arm_r: Node3D          # solo con el modelo de respaldo (primitivas)
var _anim: AnimationPlayer  # solo con el modelo .glb
var _anim_playing := ""
var _net_area: Area3D
var _interact_area: Area3D
var _target: Node3D = null
var _anim_t := 0.0
var _swing_t := 0.0
var _swing_cool := 0.0
var _shake_t := 0.0
var _shake_amp := 0.0

const SWING_TIME := 0.35
const MODEL_PATH := "res://assets/models/canelita.glb"


func _ready() -> void:
	collision_layer = 1
	collision_mask = 1

	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.5
	shape.shape = cap
	shape.position.y = 0.75
	add_child(shape)

	_model = _load_model()
	_model.rotation.y = -PI / 2.0   # mira a la derecha
	add_child(_model)

	_net_area = Area3D.new()
	_net_area.collision_layer = 0
	_net_area.collision_mask = 2
	var net_shape := CollisionShape3D.new()
	var net_sphere := SphereShape3D.new()
	net_sphere.radius = 1.6
	net_shape.shape = net_sphere
	net_shape.position = Vector3(0, 1.0, -1.5)
	_net_area.add_child(net_shape)
	_model.add_child(_net_area)

	_interact_area = Area3D.new()
	_interact_area.collision_layer = 0
	_interact_area.collision_mask = 4
	var int_shape := CollisionShape3D.new()
	var int_sphere := SphereShape3D.new()
	int_sphere.radius = 2.0
	int_shape.shape = int_sphere
	int_shape.position.y = 0.9
	_interact_area.add_child(int_shape)
	add_child(_interact_area)

	_camera = Camera3D.new()
	_camera.top_level = true
	_camera.fov = 38.0
	add_child(_camera)
	_camera.rotation_degrees = Vector3(-11.0, 0.0, 0.0)
	_camera.global_position = _camera_target()
	_camera.make_current()
	_publish_camera()


## Modelo 3D de Blender (tools/blender); si falta, usa el de primitivas.
func _load_model() -> Node3D:
	if ResourceLoader.exists(MODEL_PATH):
		var scene := load(MODEL_PATH) as PackedScene
		if scene:
			var inst := scene.instantiate() as Node3D
			CharacterModel.apply_toon(inst)
			_anim = _find_anim_player(inst)
			if _anim:
				for anim_name in _anim.get_animation_list():
					if String(anim_name).begins_with("idle") or String(anim_name).begins_with("walk"):
						_anim.get_animation(anim_name).loop_mode = Animation.LOOP_LINEAR
				_play("idle")
			return inst
	var fallback := CharacterModel.build("dog", Color(0.98, 0.82, 0.3), Color(0.55, 0.78, 0.4))
	_arm_r = fallback.get_node("ArmR")
	_attach_net(_arm_r)
	return fallback


func _find_anim_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var found := _find_anim_player(child)
		if found:
			return found
	return null


func _play(prefix: String, blend := 0.12) -> void:
	if _anim == null or _anim_playing == prefix:
		return
	for anim_name in _anim.get_animation_list():
		if String(anim_name).begins_with(prefix):
			_anim_playing = prefix
			_anim.play(anim_name, blend)
			return


func _attach_net(arm: Node3D) -> void:
	CharacterModel.add_mesh(arm, CharacterModel.capsule(0.025, 1.4), Color(0.55, 0.38, 0.24),
			Vector3(0, -0.45, -0.7), Vector3.ONE, Vector3(90, 0, 0))
	var hoop := TorusMesh.new()
	hoop.inner_radius = 0.2
	hoop.outer_radius = 0.25
	CharacterModel.add_mesh(arm, hoop, Color(0.85, 0.3, 0.3), Vector3(0, -0.45, -1.55),
			Vector3.ONE, Vector3(90, 0, 0))
	var bag := CharacterModel.add_mesh(arm, CharacterModel.sphere(0.22), Color.WHITE,
			Vector3(0, -0.45, -1.55), Vector3(1, 1, 0.5))
	bag.material_override = CharacterModel.mat(Color(1, 1, 1, 0.45), true)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("net"):
		swing_net()
	elif event.is_action_pressed("interact") and _target and can_move:
		_target.call("interact", self)


## Balancea la red y atrapa las mariposas que estén dentro del alcance.
func swing_net() -> void:
	if not can_move or _swing_cool > 0.0:
		return
	_swing_cool = 0.5
	_swing_t = SWING_TIME
	_anim_playing = ""
	for area in _net_area.get_overlapping_areas():
		if area.has_method("catch_me"):
			area.call("catch_me")


## Gira el modelo para mirar hacia un punto (por ejemplo, el estanque al pescar).
func face_point(point: Vector3) -> void:
	var d := point - global_position
	_model.rotation.y = atan2(-d.x, -d.z)


func shake(duration: float, amplitude: float) -> void:
	_shake_t = duration
	_shake_amp = amplitude


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta

	var dir := Vector3.ZERO
	if can_move:
		var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		dir = Vector3(input.x, 0.0, input.y)
		if Input.is_action_just_pressed("jump") and is_on_floor():
			velocity.y = jump_velocity

	var speed := run_speed if Input.is_action_pressed("sprint") else walk_speed
	velocity.x = move_toward(velocity.x, dir.x * speed, speed * 10.0 * delta)
	velocity.z = move_toward(velocity.z, dir.z * speed, speed * 10.0 * delta)
	move_and_slide()

	# Carril: la profundidad solo existe dentro de las zonas definidas por el mundo.
	var p := global_position
	p.x = clampf(p.x, -x_limit, x_limit)
	if lane_limits.is_valid():
		var r: Vector2 = lane_limits.call(p.x)
		if p.z < r.x or p.z > r.y:
			p.z = clampf(p.z, r.x, r.y)
			velocity.z = 0.0
	global_position = p

	var flat := Vector2(velocity.x, velocity.z)
	if flat.length() > 0.5:
		_model.rotation.y = lerp_angle(_model.rotation.y, atan2(-flat.x, -flat.y), delta * 12.0)

	if global_position.y < -4.0:
		global_position = Vector3(0, 1.0, 0.0)
		velocity = Vector3.ZERO

	var target := _closest_interactable()
	if target != _target:
		_target = target
		target_changed.emit(_target)


func _camera_target() -> Vector3:
	return Vector3(clampf(global_position.x, -camera_x_limit, camera_x_limit),
			global_position.y * 0.5 + 3.4, global_position.z * 0.5 + 11.5)


func _publish_camera() -> void:
	RenderingServer.global_shader_parameter_set("curve_cam_pos", _camera.global_position)


func _process(delta: float) -> void:
	_swing_cool = maxf(0.0, _swing_cool - delta)
	var move := clampf(Vector2(velocity.x, velocity.z).length() / walk_speed, 0.0, 1.2)
	_swing_t = maxf(0.0, _swing_t - delta)
	if _anim:
		if _swing_t > 0.0:
			_play("swing", 0.05)
		elif move > 0.1 and is_on_floor():
			_play("walk")
			_anim.speed_scale = clampf(move, 0.6, 1.5)
		else:
			_play("idle")
			_anim.speed_scale = 1.0
	else:
		_anim_t += delta * (0.6 + move * 0.5)
		CharacterModel.animate(_model, _anim_t, move if is_on_floor() else 0.0)
		_model.position.y = absf(sin(_anim_t * 10.0)) * 0.06 * move if is_on_floor() else 0.0
		# Brazo derecho: reposo con la red en alto, y golpe hacia abajo al balancear.
		if _swing_t > 0.0:
			var k := 1.0 - _swing_t / SWING_TIME
			_arm_r.rotation.x = lerpf(2.3, 0.2, ease(k, 0.4))
		else:
			_arm_r.rotation.x = lerpf(_arm_r.rotation.x, 0.6, delta * 10.0)

	_camera.global_position = _camera.global_position.lerp(_camera_target(), 1.0 - exp(-6.0 * delta))
	_publish_camera()
	if _shake_t > 0.0:
		_shake_t -= delta
		_camera.h_offset = randf_range(-1.0, 1.0) * _shake_amp
		_camera.v_offset = randf_range(-1.0, 1.0) * _shake_amp
	else:
		_camera.h_offset = 0.0
		_camera.v_offset = 0.0


func _closest_interactable() -> Node3D:
	if not can_move:
		return null
	var best: Node3D = null
	var best_d := INF
	for area in _interact_area.get_overlapping_areas():
		var owner_node := area.get_parent() as Node3D
		if owner_node == null or not owner_node.has_method("interact"):
			continue
		var d := global_position.distance_to(owner_node.global_position)
		if d < best_d:
			best_d = d
			best = owner_node
	return best
