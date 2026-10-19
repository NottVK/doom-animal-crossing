class_name HUD
extends CanvasLayer
## Interfaz estilo Animal Crossing: paneles crema con borde café, diálogo con máquina de escribir.

const INK := Color("5b4636")
const PANEL := Color("fffbe8")
const CHARS_PER_SEC := 45.0

var active := false

var _stats: Label
var _hint: Label
var _prompt: Label
var _toast: Label
var _dialog: PanelContainer
var _speaker: Label
var _text: Label
var _fade: ColorRect
var _endcard: Label
var _lines: Array = []
var _idx := -1
var _chars := 0.0
var _on_done: Callable


func _ready() -> void:
	add_to_group("hud")
	layer = 10
	_build_ui()
	Story.stats_changed.connect(_refresh)
	_refresh()
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 0.0, 1.5)
	toast("Bienvenida a Isla Calma", 4.0)


func _style(bg: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_border_width_all(4)
	s.border_color = INK
	s.set_corner_radius_all(18)
	s.content_margin_left = 16
	s.content_margin_right = 16
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	return s


func _label(size: int, color := INK) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _build_ui() -> void:
	var stats_panel := PanelContainer.new()
	stats_panel.add_theme_stylebox_override("panel", _style(PANEL))
	stats_panel.position = Vector2(14, 14)
	stats_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stats = _label(20)
	stats_panel.add_child(_stats)
	add_child(stats_panel)

	_hint = _label(16, Color.WHITE)
	_hint.text = "← → mover · ↑ ↓ profundidad (en las zonas del camino) · Shift correr · Espacio saltar · F / clic red · E hablar"
	add_child(_hint)

	_toast = _label(20, Color.WHITE)
	_toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_toast.offset_top = 90
	_toast.offset_left = -400
	_toast.offset_right = 400
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.add_theme_color_override("font_outline_color", INK)
	_toast.add_theme_constant_override("outline_size", 8)
	_toast.modulate.a = 0.0
	add_child(_toast)

	_prompt = _label(24, Color.WHITE)
	_prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.offset_top = -230
	_prompt.offset_left = -300
	_prompt.offset_right = 300
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt.add_theme_color_override("font_outline_color", INK)
	_prompt.add_theme_constant_override("outline_size", 8)
	add_child(_prompt)

	_dialog = PanelContainer.new()
	_dialog.add_theme_stylebox_override("panel", _style(PANEL))
	_dialog.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_dialog.offset_left = 60
	_dialog.offset_right = -60
	_dialog.offset_top = -190
	_dialog.offset_bottom = -30
	_dialog.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_dialog.visible = false
	var box := VBoxContainer.new()
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_speaker = _label(26, Color("3f9f4a"))
	_text = _label(24)
	_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(_speaker)
	box.add_child(_text)
	_dialog.add_child(box)
	add_child(_dialog)

	_endcard = _label(44, Color.WHITE)
	_endcard.set_anchors_preset(Control.PRESET_FULL_RECT)
	_endcard.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_endcard.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_endcard.add_theme_color_override("font_outline_color", Color(0.3, 0, 0))
	_endcard.add_theme_constant_override("outline_size", 14)
	_endcard.modulate.a = 0.0
	add_child(_endcard)

	_fade = ColorRect.new()
	_fade.color = Color.BLACK
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_fade)


func _refresh() -> void:
	_stats.text = "Campanas: %d    Mariposas: %d    Peces: %d\n%s" % [Story.bells, Story.butterflies, Story.fish, Story.objective()]


func set_prompt(text: String) -> void:
	_prompt.text = text


func toast(msg: String, seconds := 3.0) -> void:
	_toast.text = msg
	var tw := create_tween()
	tw.tween_property(_toast, "modulate:a", 1.0, 0.3)
	tw.tween_interval(seconds)
	tw.tween_property(_toast, "modulate:a", 0.0, 0.6)


func show_endcard(msg: String) -> void:
	_endcard.text = msg
	create_tween().tween_property(_endcard, "modulate:a", 1.0, 2.0)


func say(speaker: String, lines: Array, on_done: Callable) -> void:
	_lines = lines
	_idx = -1
	_on_done = on_done
	_speaker.text = speaker
	_dialog.visible = true
	active = true
	_next_line()


func _next_line() -> void:
	_idx += 1
	if _idx >= _lines.size():
		_dialog.visible = false
		active = false
		_on_done.call()
		return
	_text.text = str(_lines[_idx])
	_text.visible_characters = 0
	_chars = 0.0


func _line_done() -> bool:
	return _text.visible_characters == -1 or int(_chars) >= _text.text.length()


func _process(delta: float) -> void:
	_hint.position = Vector2(14, get_viewport().get_visible_rect().size.y - 30)
	if active and not _line_done():
		_chars += delta * CHARS_PER_SEC
		_text.visible_characters = int(_chars)


func _unhandled_input(event: InputEvent) -> void:
	if not active:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("jump") or event.is_action_pressed("net"):
		get_viewport().set_input_as_handled()
		if _line_done():
			_next_line()
		else:
			_chars = float(_text.text.length())
			_text.visible_characters = -1
