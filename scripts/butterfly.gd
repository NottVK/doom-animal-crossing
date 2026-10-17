class_name Butterfly
extends Area3D
## Mariposa que revolotea por la isla. Se atrapa con la red del jugador.

signal caught

var limit := 34.0

var _target := Vector3.ZERO
var _has_target := false
var _speed := 1.6
var _t := 0.0
var _wing_l: Node3D
var _wing_r: Node3D


func _ready() -> void:
	collision_layer = 2
	collision_mask = 0
	add_to_group("butterfly")
	_t = randf() * TAU
	_speed = randf_range(1.3, 2.0)

	var shape := CollisionShape3D.new()
	var s := SphereShape3D.new()
	s.radius = 0.45
	shape.shape = s
	add_child(shape)

	var color := Color.from_hsv(randf(), 0.55, 1.0)
	CharacterModel.add_mesh(self, CharacterModel.capsule(0.03, 0.2), Color(0.2, 0.15, 0.15),
			Vector3.ZERO, Vector3.ONE, Vector3(90, 0, 0))
	_wing_l = _make_wing(-1, color)
	_wing_r = _make_wing(1, color)


func _make_wing(side: int, color: Color) -> Node3D:
	var pivot := Node3D.new()
	add_child(pivot)
	var quad := QuadMesh.new()
	quad.size = Vector2(0.32, 0.26)
	var mi := CharacterModel.add_mesh(pivot, quad, color, Vector3(side * 0.16, 0, 0),
			Vector3.ONE, Vector3(-90, 0, 0))
	var m := mi.material_override as StandardMaterial3D
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return pivot


func _process(delta: float) -> void:
	_t += delta
	if not _has_target or global_position.distance_to(_target) < 0.5:
		_pick_target()
	var dir := (_target - global_position).normalized()
	global_position += dir * _speed * delta
	global_position.y += sin(_t * 6.0) * 0.4 * delta
	var flap := 0.2 + (sin(_t * 22.0) * 0.5 + 0.5) * 0.9
	_wing_l.rotation.z = -flap
	_wing_r.rotation.z = flap


func _pick_target() -> void:
	var a := randf() * TAU
	var r := randf_range(3.0, limit)
	_target = Vector3(cos(a) * r, randf_range(0.9, 2.6), sin(a) * r)
	_has_target = true


func catch_me() -> void:
	if is_queued_for_deletion():
		return
	Story.catch_butterfly()
	caught.emit()
	queue_free()
