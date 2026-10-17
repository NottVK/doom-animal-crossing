class_name Player
extends CharacterBody3D
## Canelita: personaje en tercera persona con red de atrapar mariposas.

signal target_changed(target: Node3D)

@export var walk_speed := 5.0
@export var run_speed := 8.5
@export var jump_velocity := 6.5
@export var mouse_sensitivity := 0.003

var can_move := true

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _pivot: Node3D
var _spring: SpringArm3D
var _camera: Camera3D
var _model: Node3D
var _arm_r: Node3D
var _net_area: Area3D
var _interact_area: Area3D
var _target: Node3D = null
var _anim_t := 0.0
var _swing_t := 0.0
var _swing_cool := 0.0
var _shake_t := 0.0
var _shake_amp := 0.0

const SWING_TIME := 0.35


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

	_model = CharacterModel.build("dog", Color(0.98, 0.82, 0.3), Color(0.55, 0.78, 0.4))
	add_child(_model)
	_arm_r = _model.get_node("ArmR")
	_attach_net(_arm_r)

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

	_pivot = Node3D.new()
	_pivot.position.y = 1.4
	add_child(_pivot)
	_spring = SpringArm3D.new()
	_spring.spring_length = 5.5
	_spring.rotation.x = -0.35
	_spring.collision_mask = 1
	_spring.margin = 0.2
	_spring.add_excluded_object(get_rid())
	_pivot.add_child(_spring)
	_camera = Camera3D.new()
	_camera.fov = 70.0
	_spring.add_child(_camera)
	_camera.make_current()


func _attach_net(arm: Node3D) -> void:
	CharacterModel.add_mesh(arm, CharacterModel.capsule(0.025, 1.4), Color(0.55, 0.38, 0.24),
			Vector3(0, -0.45, -0.7), Vector3.ONE, Vector3(90, 0, 0))
	var hoop := TorusMesh.new()
	hoop.inner_radius = 0.2
	hoop.outer_radius = 0.25
	CharacterModel.add_mesh(arm, hoop, Color(0.85, 0.3, 0.3), Vector3(0, -0.45, -1.55),
			Vector3.ONE, Vector3(90, 0, 0))
	var bag := CharacterModel.add_mesh(arm, CharacterModel.sphere(0.22), Color(1, 1, 1),
			Vector3(0, -0.45, -1.55), Vector3(1, 1, 0.5))
	var bag_mat := bag.material_override as StandardMaterial3D
	bag_mat.albedo_color.a = 0.45
	bag_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_pivot.rotate_y(-event.relative.x * mouse_sensitivity)
		_spring.rotation.x = clampf(_spring.rotation.x - event.relative.y * mouse_sensitivity, -1.2, 0.2)
		return
	if event.is_action_pressed("net"):
		if event is InputEventMouseButton and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			get_viewport().set_input_as_handled()
			return
		swing_net()
	elif event.is_action_pressed("interact") and _target and can_move:
		_target.call("interact", self)


## Balancea la red y atrapa las mariposas que estén dentro del alcance.
func swing_net() -> void:
	if not can_move or _swing_cool > 0.0:
		return
	_swing_cool = 0.5
	_swing_t = SWING_TIME
	for area in _net_area.get_overlapping_areas():
		if area.has_method("catch_me"):
			area.call("catch_me")


func shake(duration: float, amplitude: float) -> void:
	_shake_t = duration
	_shake_amp = amplitude


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta

	var dir := Vector3.ZERO
	if can_move:
		var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		dir = _pivot.global_basis * Vector3(input.x, 0.0, input.y)
		dir.y = 0.0
		if Input.is_action_just_pressed("jump") and is_on_floor():
			velocity.y = jump_velocity

	var speed := run_speed if Input.is_action_pressed("sprint") else walk_speed
	velocity.x = move_toward(velocity.x, dir.x * speed, speed * 10.0 * delta)
	velocity.z = move_toward(velocity.z, dir.z * speed, speed * 10.0 * delta)
	move_and_slide()

	if dir.length() > 0.1:
		_model.rotation.y = lerp_angle(_model.rotation.y, atan2(-dir.x, -dir.z), delta * 12.0)

	if global_position.y < -4.0:
		global_position = Vector3(0, 1.0, 3.0)
		velocity = Vector3.ZERO

	var target := _closest_interactable()
	if target != _target:
		_target = target
		target_changed.emit(_target)


func _process(delta: float) -> void:
	_swing_cool = maxf(0.0, _swing_cool - delta)
	var move := clampf(Vector2(velocity.x, velocity.z).length() / walk_speed, 0.0, 1.2)
	_anim_t += delta * (0.6 + move * 0.5)
	CharacterModel.animate(_model, _anim_t, move if is_on_floor() else 0.0)
	_model.position.y = absf(sin(_anim_t * 10.0)) * 0.06 * move if is_on_floor() else 0.0

	# Brazo derecho: reposo con la red en alto, y golpe hacia abajo al balancear.
	var rest := 0.6
	if _swing_t > 0.0:
		_swing_t = maxf(0.0, _swing_t - delta)
		var k := 1.0 - _swing_t / SWING_TIME
		_arm_r.rotation.x = lerpf(2.3, 0.2, ease(k, 0.4))
	else:
		_arm_r.rotation.x = lerpf(_arm_r.rotation.x, rest, delta * 10.0)

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
