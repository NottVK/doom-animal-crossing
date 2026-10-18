# Doom Crossing

Hub cozy estilo Animal Crossing que termina abriendo un portal a un combate estilo DOOM: The Dark Ages.
Proyecto en **Godot 4.4** (GDScript, renderer GL Compatibility).

## Estado: Parte 1 — la isla, antes de que llegue el Slayer

- Isla en **2.5D de lado** (estilo Undertale): caminas a izquierda/derecha por un carril y solo hay profundidad
  en zonas concretas (plaza, puertas de las casas, playa).
- Look Animal Crossing: horizonte curvado, colores pastel, luz suave, colinas y nubes (shader en `character_model.gd`).
- **Canelita** (perrita chibi caramelo con overol, diseño propio): modelo 3D con esqueleto y animaciones (idle, caminar, golpe de red), generado con Blender. Caminar, correr, saltar y atrapar mariposas.
- **Centinela** (guerrero blindado con escudo): modelo y animaciones listos para la Parte 2, aún sin usar en el juego.
- Aldeanos con diálogo que cambia según la fase de la historia.
- 10 mariposas que revolotean; al atrapar 5 la tierra tiembla y se abre una **grieta** en la plaza (fin del capítulo 1).
- Interfaz estilo Animal Crossing (paneles crema, diálogo con máquina de escribir).

## Cómo jugar

1. Instala [Godot 4.4+](https://godotengine.org/download) (versión estándar, no .NET).
2. Abre `project.godot` y pulsa **F5**.

| Acción | Control |
|---|---|
| Mover / correr / saltar | A D o ← → / Shift / Espacio |
| Profundidad (solo en las zonas del camino) | W S o ↑ ↓ |
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
scripts/island.gd         construye la isla, zonas de profundidad, clima y grieta
scripts/player.gd         Canelita: movimiento por carril, cámara lateral, red, interacción
scripts/villager.gd       aldeanos y diálogo
scripts/butterfly.gd      mariposas
scripts/hud.gd            interfaz y cuadro de diálogo
scripts/story.gd          autoload: fases de la historia, campanas, mariposas
scripts/character_model.gd  shader toon con mundo curvado y modelos placeholder de aldeanos
assets/models/            canelita.glb y centinela.glb (generados)
tools/blender/build_characters.py  genera los .glb (ver abajo)
tests/smoke_test.gd       prueba de humo headless
docs/DESIGN.md            visión y hoja de ruta
```

## Regenerar los modelos 3D

Los `.glb` salen de un script de Blender (modelado, esqueleto, animaciones y exportación):

```sh
pip install bpy            # Blender como módulo de Python (Python 3.11/3.13 según la versión)
python tools/blender/build_characters.py assets/models [carpeta_de_previews]
```

## Nota sobre personajes

Canelita y el Centinela son diseños propios inspirados en el estilo de los juegos que homenajea el proyecto,
no copias de personajes de terceros.
