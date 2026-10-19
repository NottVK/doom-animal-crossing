class_name WorldAssets
extends RefCounted
## Carga los modelos del escenario (assets/env/*.glb) con el material toon del juego.

const DIR := "res://assets/env/"

static var _mesh_cache := {}


## Instancia un modelo .glb del escenario (por nombre, sin extensión).
static func instance(model: String) -> Node3D:
	var scene := load(DIR + model + ".glb") as PackedScene
	var node := scene.instantiate() as Node3D
	CharacterModel.apply_toon(node)
	return node


## Malla de un modelo con materiales toon, para repartir muchas copias con MultiMesh.
static func mesh(model: String) -> Mesh:
	if _mesh_cache.has(model):
		return _mesh_cache[model]
	var node := (load(DIR + model + ".glb") as PackedScene).instantiate()
	var mi := _find_mesh(node)
	var m := mi.mesh.duplicate() as ArrayMesh
	for i in m.get_surface_count():
		var src := m.surface_get_material(i) as BaseMaterial3D
		if src:
			m.surface_set_material(i, CharacterModel.toon_from(src, CharacterModel.has_vertex_colors(m, i)))
	node.free()
	_mesh_cache[model] = m
	return m


static func _find_mesh(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node
	for child in node.get_children():
		var found := _find_mesh(child)
		if found:
			return found
	return null
