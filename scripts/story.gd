extends Node
## Estado global de la historia (autoload "Story").
## PEACEFUL -> atrapas mariposas; OMEN -> la tierra tiembla; RIFT -> se abre la grieta.

signal stats_changed
signal phase_changed(phase: int)

enum Phase { PEACEFUL, OMEN, RIFT }

const BUTTERFLY_GOAL := 5
const BELLS_PER_BUTTERFLY := 120

var phase: int = Phase.PEACEFUL
var butterflies := 0
var bells := 0


func catch_butterfly() -> void:
	butterflies += 1
	bells += BELLS_PER_BUTTERFLY
	stats_changed.emit()
	if phase == Phase.PEACEFUL and butterflies >= BUTTERFLY_GOAL:
		set_phase(Phase.OMEN)


func set_phase(new_phase: int) -> void:
	if new_phase == phase:
		return
	phase = new_phase
	phase_changed.emit(phase)
	stats_changed.emit()


func reset() -> void:
	phase = Phase.PEACEFUL
	butterflies = 0
	bells = 0
	stats_changed.emit()


func objective() -> String:
	match phase:
		Phase.PEACEFUL:
			return "Atrapa mariposas con tu red (%d/%d)" % [mini(butterflies, BUTTERFLY_GOAL), BUTTERFLY_GOAL]
		Phase.OMEN:
			return "La tierra tiembla... ve a la plaza."
		_:
			return "???"
