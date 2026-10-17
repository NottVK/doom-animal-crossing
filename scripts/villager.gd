class_name Villager
extends StaticBody3D
## Aldeano con el que se puede hablar. Su diálogo cambia según la fase de la historia.

@export var display_name := "Aldeano"
@export var species := "bunny"
@export var fur := Color.WHITE
@export var accent := Color(1, 0.6, 0.7)

## Story.Phase -> Array[String]
var lines: Dictionary = {}

var _model: Node3D
var _t := 0.0
var _talking := false


func _ready() -> void:
	collision_layer = 1
	_model = CharacterModel.build(species, fur, accent)
	add_child(_model)

	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.4
	cap.height = 1.5
	shape.shape = cap
	shape.position.y = 0.75
	add_child(shape)

	var area := Area3D.new()
	area.collision_layer = 4
	area.collision_mask = 0
	var area_shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.9
	area_shape.shape = sphere
	area_shape.position.y = 0.8
	area.add_child(area_shape)
	add_child(area)

	_t = randf() * TAU
	CharacterModel.animate(_model, 0.0, 0.0)


func face(point: Vector3) -> void:
	var d := point - global_position
	_model.rotation.y = atan2(-d.x, -d.z)


func _process(delta: float) -> void:
	_t += delta
	if not _talking:
		_model.position.y = (sin(_t * 2.0) * 0.5 + 0.5) * 0.03


func interact(player: Player) -> void:
	if _talking:
		return
	var hud := get_tree().get_first_node_in_group("hud") as HUD
	if hud == null:
		return
	face(player.global_position)
	_talking = true
	player.can_move = false
	var script: Array = lines.get(Story.phase, ["..."])
	hud.say(display_name, script, _end_talk.bind(player))


func _end_talk(player: Player) -> void:
	_talking = false
	player.can_move = true
