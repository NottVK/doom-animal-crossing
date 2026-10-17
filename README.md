# Doom Crossing

Hub cozy estilo Animal Crossing que termina abriendo un portal a un combate estilo DOOM: The Dark Ages.
Proyecto en **Godot 4.4** (GDScript, renderer GL Compatibility).

## Estado: Parte 1 — la isla, antes de que llegue el Slayer

- Isla 3D explorable con plaza, casas, árboles, flores y ciclo día/noche.
- **Canelita** (placeholder hecho con primitivas) en tercera persona: caminar, correr, saltar y red de atrapar mariposas.
- Aldeanos con diálogo que cambia según la fase de la historia.
- 10 mariposas que revolotean; al atrapar 5 la tierra tiembla y se abre una **grieta** en la plaza (fin del capítulo 1).
- Interfaz estilo Animal Crossing (paneles crema, diálogo con máquina de escribir).

## Cómo jugar

1. Instala [Godot 4.4+](https://godotengine.org/download) (versión estándar, no .NET).
2. Abre `project.godot` y pulsa **F5**.

| Acción | Control |
|---|---|
| Mover / correr / saltar | WASD (o flechas) / Shift / Espacio |
| Mirar | Ratón (clic para capturarlo, Esc para soltarlo) |
| Red | F o clic izquierdo |
| Hablar | E |

## Pruebas

```sh
godot --headless --path . --import          # primera vez
godot --headless --path . -s tests/smoke_test.gd
```

## Estructura

```
scenes/main.tscn          escena raíz (solo carga island.gd)
scripts/island.gd         construye la isla, el clima y la grieta
scripts/player.gd         Canelita: movimiento, cámara, red, interacción
scripts/villager.gd       aldeanos y diálogo
scripts/butterfly.gd      mariposas
scripts/hud.gd            interfaz y cuadro de diálogo
scripts/story.gd          autoload: fases de la historia, campanas, mariposas
scripts/character_model.gd  modelos placeholder con primitivas
tests/smoke_test.gd       prueba de humo headless
docs/DESIGN.md            visión y hoja de ruta
```

## Nota sobre personajes

Los nombres de trabajo (Canelita, Slayer) vienen de la idea original. Si el proyecto se va a publicar,
conviene reemplazarlos por personajes, nombres y modelos propios.
