# Diseño

## Visión

Dos juegos que se influyen: una **isla cozy** para explorar, jugar minijuegos y fabricar armas, y un
**portal** a un infierno en 3D con combate pesado y animaciones al estilo DOOM: The Dark Ages.
Coop **online de 2 jugadores**, asimétrico: una exploradora (Brisa) y un guerrero (Centinela).

Ciclo de juego: `hub ⇄ misión en el infierno ⇄ regreso al hub con botín`.

## Contraste visual

| | Isla | Infierno |
|---|---|---|
| Formas | redondas, planas, sin contornos | angulosas, pesadas |
| Color | pasteles | alto contraste, neón, sangre |
| Luz | suave | sombras duras, fuego |
| UI | paneles crema, diálogo con texto | HUD agresivo |

El cambio de mundo debe ser un único sistema (shaders + post-proceso + música) para ajustar el contraste en un punto.

## Mecánicas

- Herramientas que sirven en ambos mundos (red → arma cuerpo a cuerpo, resortera → disparo, caña → gancho).
- Compañero que acompaña en ambos mundos.
- Crafteo en la isla con materiales de minijuegos; botín del infierno vuelve a la isla.
- Música adaptativa por capas (ukulele y campanas → guitarras distorsionadas).

## Hoja de ruta

1. **Parte 1 (hecha):** isla, Brisa, aldeanos, mariposas, ciclo día/noche, grieta.
2. Conexión online de 2 jugadores moviéndose en la isla (ENet + relay/lobby con código de sala).
3. Inventario compartido, minijuegos (pesca, insectos), banco de crafteo.
4. Portal con transición y arena de combate; llegada del Slayer.
5. Combate: armas, IA, animaciones, glory kills.
6. Niveles, progresión y pulido (audio, VFX, UI).

## Decisiones técnicas

- **Godot 4.4**, GDScript. Datos (armas, recetas, NPCs) deberían migrar a `Resource`s al crecer.
- Modelos y animaciones: Blender + Mixamo para la base, animaciones propias para combate y portal.
- Multijugador: host-autoritativo, API de red de Godot; diseñar el estado compartido desde ya.
- Los modelos actuales son placeholders de primitivas: se reemplazan por glTF sin tocar la lógica.
