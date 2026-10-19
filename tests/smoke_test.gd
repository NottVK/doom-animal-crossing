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
	_check(butterflies.size() == 16, "hay 16 mariposas (%d)" % butterflies.size())

	var player: Player = null
	for n in main.get_children():
		if n is Player:
			player = n
	_check(player != null, "existe el jugador")

	# Carril: fuera de las zonas no hay profundidad; en la plaza sí.
	player.global_position = Vector3(-14, 0.5, -4.0)
	await physics_frame
	await physics_frame
	_check(player.global_position.z >= -0.71, "fuera de zona la z se limita al carril (%.2f)" % player.global_position.z)
	player.global_position = Vector3(0, 0.5, -4.0)
	await physics_frame
	await physics_frame
	_check(player.global_position.z < -3.5, "en la plaza se puede ir al fondo (%.2f)" % player.global_position.z)
	player.global_position = Vector3(-14, 0.5, 0.0)
	await physics_frame

	# Coloca una mariposa frente a la red y balancéala.
	var b := butterflies[0] as Node3D
	b.global_position = player.global_position + Vector3(1.5, 1.0, 0)
	await physics_frame
	await physics_frame
	await physics_frame
	player.swing_net()
	_check(Story.butterflies >= 1, "la red atrapa al menos una mariposa (%d)" % Story.butterflies)

	for i in 4:
		Story.catch_butterfly()
	_check(Story.phase == 1, "5 mariposas -> fase OMEN")

	Engine.time_scale = 20.0
	await create_timer(9.5).timeout
	Engine.time_scale = 1.0
	_check(Story.phase == 2, "tras el temblor se abre la grieta (RIFT)")
	await physics_frame
	await physics_frame

	# Pesca: lanzar, esperar a que pique y tirar a tiempo.
	var spot: FishingSpot = null
	for n in main.get_children():
		if n is FishingSpot:
			spot = n
	_check(spot != null, "existe el estanque de pesca")
	player.can_move = true
	spot.interact(player)
	_check(spot.is_busy() and not player.can_move, "al pescar el jugador se queda quieto")
	spot.reel()
	_check(not spot.is_busy() and Story.fish == 0, "tirar antes de tiempo espanta al pez")
	spot.interact(player)
	spot._state = FishingSpot.State.BITE
	var bells_before: int = Story.bells
	spot.reel()
	_check(Story.fish == 1 and Story.bells > bells_before, "tirar cuando pica atrapa el pez")

	print("SMOKE ", "FAILED" if _fail else "OK")
	quit(1 if _fail else 0)
