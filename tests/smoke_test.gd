extends SceneTree
## Prueba de humo: godot --headless --path . -s tests/smoke_test.gd
## Carga la isla, atrapa una mariposa con la red y recorre la historia hasta la grieta.

var _fail := false
var Story: Node  # el autoload no se resuelve por nombre con -s


func _check(cond: bool, msg: String) -> void:
	if cond:
		print("  ok   ", msg)
	else:
		print("  FAIL ", msg)
		_fail = true


func _initialize() -> void:
	run.call_deferred()


func run() -> void:
	Story = root.get_node("Story")
	var main: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	await physics_frame
	await physics_frame

	var butterflies := get_nodes_in_group("butterfly")
	_check(butterflies.size() == 10, "hay 10 mariposas (%d)" % butterflies.size())

	var player: Player = null
	for n in main.get_children():
		if n is Player:
			player = n
	_check(player != null, "existe el jugador")

	# Coloca una mariposa frente a la red y balancéala.
	var b := butterflies[0] as Node3D
	b.global_position = player.global_position + Vector3(0, 1.0, -1.5)
	await physics_frame
	await physics_frame
	await physics_frame
	player.swing_net()
	_check(Story.butterflies == 1, "la red atrapa una mariposa (%d)" % Story.butterflies)

	for i in 4:
		Story.catch_butterfly()
	_check(Story.phase == 1, "5 mariposas -> fase OMEN")

	Engine.time_scale = 20.0
	await create_timer(9.5).timeout
	Engine.time_scale = 1.0
	_check(Story.phase == 2, "tras el temblor se abre la grieta (RIFT)")
	await physics_frame
	await physics_frame

	print("SMOKE ", "FAILED" if _fail else "OK")
	quit(1 if _fail else 0)
