"""Genera los modelos del escenario de la isla con Blender (bpy): árboles, cedros, arbustos, rocas,
flores, pasto, casas, cerca, farola, letrero y pez.

Uso:
    python tools/blender/build_environment.py assets/env [carpeta_de_previews] [solo,estos,modelos]

Las piezas orgánicas (árboles, arbustos, rocas, pez) se funden en una sola malla con relieve y
sombreado por altura; las de madera o casas se dejan con bordes biselados.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from build_characters import Character  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/env"
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
rad = math.radians
B = "root"   # las piezas estáticas no tienen esqueleto; todas van al mismo grupo


def finish(c, cam=None):
    """Funde (si es orgánico), une y exporta el modelo estático."""
    if c.organic:
        c._fuse_organic()
    bpy.ops.object.select_all(action="DESELECT")
    for o in c.parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = c.parts[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = c.name
    obj.vertex_groups.clear()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, c.name.lower() + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_animations=False,
                              export_skins=False, export_yup=True, export_cameras=False, export_lights=False)
    print("exportado", path)
    if PREVIEW and cam:
        c.preview("p", cam_loc=cam[0], target=cam[1], lens=cam[2])


def prism(c, name, pts, depth, material, rot=(0, 0, 0), loc=(0, 0, 0)):
    """Prisma a partir de un polígono 2D (x, z) extruido en Y (para frontones de techo)."""
    verts = [(x, -depth / 2, z) for x, z in pts] + [(x, depth / 2, z) for x, z in pts]
    n = len(pts)
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return c._finish_part(o, material, B, False)


# ---------------------------------------------------------------- vegetación
def build_tree(name, seed, fruit=False):
    rnd = random.Random(seed)
    c = Character(name)
    c.organic = True
    c.voxel = 0.05
    c.decimate = 0.35
    c.displace = 0.14
    c.displace_scale = 0.35
    c.gradient = (0.0, 5.2, 0.55, 1.15)
    c.keep_separate = {"fruit"}
    bark = c.mat("bark", (0.52, 0.36, 0.24))
    leaves = c.mat("leaves", (0.38, 0.68, 0.30))
    leaves2 = c.mat("leaves2", (0.47, 0.75, 0.33))
    orange = c.mat("fruit", (1.0, 0.55, 0.15), rough=0.4)

    lean = rnd.uniform(-0.15, 0.15)
    c.limb("trunk", (0, 0, -0.1), (lean, 0, 1.4), 0.34, 0.25, bark, B)
    c.limb("trunk2", (lean, 0, 1.4), (-lean * 0.5, 0.05, 2.6), 0.25, 0.18, bark, B)
    for i in range(5):
        a = i * math.tau / 5 + rnd.uniform(-0.3, 0.3)
        c.limb("root", (0, 0, 0.3), (math.cos(a) * 0.6, math.sin(a) * 0.6, -0.05), 0.16, 0.06, bark, B)
    for sgn in (-1, 1):
        c.limb("branch", (0, 0, 2.0), (sgn * 0.8, rnd.uniform(-0.3, 0.3), 3.0), 0.12, 0.07, bark, B)
    center = Vector((0, 0, 3.7))
    blobs = []
    for i in range(10):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.8)))
        if d.length > 1:
            d.normalize()
        pos = center + Vector((d.x * 1.3, d.y * 1.3, d.z * 0.8))
        r = rnd.uniform(0.85, 1.25)
        blobs.append((pos, r))
        c.sphere("leaf", tuple(pos), (r, r, r * 0.85), leaves if i % 2 else leaves2, B)
    if fruit:
        for i in range(9):
            pos, r = blobs[i % len(blobs)]
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(0.2, 1), rnd.uniform(-0.6, 0.3))).normalized()
            c.sphere("fruit", tuple(pos + d * (r * 0.95)), (0.14, 0.14, 0.14), orange, B)
    finish(c, ((7, 12, 4), (0, 0, 2.6), 50))


def build_cedar(name, seed):
    rnd = random.Random(seed)
    c = Character(name)
    c.organic = True
    c.voxel = 0.05
    c.decimate = 0.35
    c.displace = 0.10
    c.displace_scale = 0.3
    c.gradient = (0.3, 6.0, 0.5, 1.1)
    bark = c.mat("bark", (0.46, 0.30, 0.20))
    needles = c.mat("needles", (0.20, 0.50, 0.32))
    c.limb("trunk", (0, 0, -0.1), (0, 0, 1.5), 0.28, 0.2, bark, B)
    z, r = 1.2, 1.7
    for i in range(4):
        c.cone("tier", (rnd.uniform(-0.05, 0.05), 0, z + 0.9), r, 1.9, needles, B)
        z += 1.05
        r *= 0.74
    finish(c, ((7, 12, 4), (0, 0, 2.8), 50))


def build_bush(name, seed, flower_rgb):
    rnd = random.Random(seed)
    c = Character(name)
    c.organic = True
    c.voxel = 0.03
    c.decimate = 0.4
    c.displace = 0.08
    c.displace_scale = 0.25
    c.gradient = (0.0, 1.1, 0.55, 1.15)
    c.keep_separate = {"bloom", "bloom_c"}
    leaves = c.mat("leaves", (0.33, 0.62, 0.30))
    bloom = c.mat("bloom", flower_rgb, rough=0.6)
    center = c.mat("bloom_c", (1.0, 0.9, 0.4))
    for i in range(6):
        p = (rnd.uniform(-0.45, 0.45), rnd.uniform(-0.3, 0.3), rnd.uniform(0.35, 0.6))
        r = rnd.uniform(0.32, 0.45)
        c.sphere("leaf", p, (r, r, r * 0.9), leaves, B)
    for i in range(10):
        a = rnd.uniform(0, math.tau)
        p = Vector((math.cos(a) * 0.48, math.sin(a) * 0.36 + 0.03, rnd.uniform(0.45, 0.75)))
        c.sphere("bloom", tuple(p), (0.08, 0.08, 0.06), bloom, B)
        c.sphere("bloom_c", tuple(p + Vector((0, 0, 0.04))), (0.03, 0.03, 0.03), center, B)
    finish(c, ((2.2, 4, 1.4), (0, 0, 0.5), 50))


def build_rock(name, seed):
    rnd = random.Random(seed)
    c = Character(name)
    c.organic = True
    c.voxel = 0.025
    c.decimate = 0.4
    c.displace = 0.18
    c.displace_scale = 0.35
    c.gradient = (-0.1, 0.8, 0.6, 1.1)
    stone = c.mat("stone", (0.50, 0.49, 0.47))
    moss = c.mat("moss", (0.40, 0.55, 0.30))
    c.sphere("rock", (0, 0, 0.25), (0.6, 0.5, 0.42), stone, B)
    c.sphere("rock2", (0.4, 0.2, 0.15), (0.35, 0.32, 0.28), stone, B)
    c.sphere("rock3", (-0.35, -0.15, 0.12), (0.3, 0.28, 0.22), stone, B)
    c.sphere("moss", (rnd.uniform(-0.1, 0.1), 0, 0.55), (0.42, 0.35, 0.12), moss, B)
    finish(c, ((2.2, 4, 1.4), (0, 0, 0.3), 50))


def build_grass(name, seed):
    rnd = random.Random(seed)
    c = Character(name)
    g1 = c.mat("grass", (0.38, 0.70, 0.30))
    g2 = c.mat("grass2", (0.50, 0.80, 0.36))
    for i in range(9):
        a = rnd.uniform(0, math.tau)
        tilt = rnd.uniform(5, 25)
        h = rnd.uniform(0.22, 0.38)
        c.cone("blade", (math.cos(a) * 0.05, math.sin(a) * 0.05, h / 2), 0.025, h, g1 if i % 2 else g2, B,
               rot=(rad(tilt) * math.cos(a), rad(tilt) * math.sin(a), 0))
    finish(c)


def build_flower(name, petal_rgb):
    c = Character(name)
    stem = c.mat("stem", (0.35, 0.65, 0.28))
    petal = c.mat("petal", petal_rgb, rough=0.6)
    center = c.mat("center", (1.0, 0.85, 0.3))
    c.cylinder("stem", (0, 0, 0.16), 0.012, 0.32, stem, B)
    for sgn in (-1, 1):
        c.sphere("leaf", (sgn * 0.05, 0, 0.1), (0.05, 0.018, 0.022), stem, B, rot=(0, rad(sgn * 30), 0))
    for i in range(5):
        a = i * math.tau / 5
        c.sphere("petal", (math.cos(a) * 0.045, math.sin(a) * 0.045, 0.33), (0.045, 0.03, 0.012), petal, B,
                 rot=(0, 0, a))
    c.sphere("center", (0, 0, 0.34), (0.025, 0.025, 0.018), center, B)
    finish(c)


# ---------------------------------------------------------------- construcciones
def build_house(name, wall_rgb, roof_rgb, trim_rgb, door_rgb):
    c = Character(name)
    wall = c.mat("wall", wall_rgb)
    plank = c.mat("plank", tuple(v * 0.9 for v in wall_rgb))
    roof = c.mat("roof", roof_rgb)
    roof_dk = c.mat("roof_dk", tuple(v * 0.82 for v in roof_rgb))
    trim = c.mat("trim", trim_rgb)
    door = c.mat("door", door_rgb)
    door_dk = c.mat("door_dk", tuple(v * 0.85 for v in door_rgb))
    glass = c.mat("glass", (0.70, 0.88, 1.0), rough=0.15)
    stone = c.mat("stone", (0.62, 0.60, 0.58))
    brick = c.mat("brick", (0.72, 0.42, 0.32))
    gold = c.mat("gold", (0.95, 0.78, 0.30), rough=0.3)
    soil = c.mat("soil", (0.45, 0.30, 0.20))
    red = c.mat("bloom", (1.0, 0.45, 0.5))
    yellow = c.mat("bloom2", (1.0, 0.85, 0.3))

    W, D, H = 4.0, 4.0, 2.6
    c.box("foundation", (0, 0, 0.12), (W + 0.3, D + 0.3, 0.3), stone, B, bevel=0.05)
    c.box("walls", (0, 0, 0.25 + H / 2), (W, D, H), wall, B, bevel=0.06)
    # tablones horizontales en las cuatro caras
    for k in range(9):
        z = 0.45 + k * 0.27
        for y in (D / 2 + 0.01, -D / 2 - 0.01):
            c.box("plank", (0, y, z), (W - 0.3, 0.03, 0.05), plank, B, bevel=0.01)
        for x in (W / 2 + 0.01, -W / 2 - 0.01):
            c.box("plank", (x, 0, z), (0.03, D - 0.3, 0.05), plank, B, bevel=0.01)
    for x in (-W / 2, W / 2):
        for y in (-D / 2, D / 2):
            c.box("corner", (x, y, 0.25 + H / 2), (0.18, 0.18, H + 0.05), trim, B, bevel=0.03)
    # techo a dos aguas con alero, tejas y cumbrera
    top = 0.25 + H
    slope = rad(32)
    half = W / 2 + 0.45
    run = half / math.cos(slope)
    for sgn in (-1, 1):
        cx = sgn * half / 2
        cz = top + math.tan(slope) * half / 2 + 0.05
        c.box("roof", (cx, 0, cz), (run, D + 0.8, 0.14), roof, B, bevel=0.04, rot=(0, sgn * slope, 0))
        for k in range(6):
            t = (k + 0.5) / 6
            tx = sgn * half * (1 - t)
            tz = top + math.tan(slope) * half * t + 0.14
            c.box("shingle", (tx, 0, tz), (0.08, D + 0.82, 0.05), roof_dk, B, bevel=0.015,
                  rot=(0, sgn * slope, 0))
    c.box("ridge", (0, 0, top + math.tan(slope) * half + 0.1), (0.25, D + 0.9, 0.16), roof_dk, B, bevel=0.05)
    for y in (D / 2, -D / 2):
        prism(c, "gable", [(-W / 2, 0), (W / 2, 0), (0, math.tan(slope) * W / 2)], 0.1, wall, loc=(0, y, top))
    c.box("chimney", (-1.0, -0.6, top + 1.2), (0.45, 0.45, 1.3), brick, B, bevel=0.03)
    c.box("chimney_cap", (-1.0, -0.6, top + 1.88), (0.58, 0.58, 0.1), stone, B, bevel=0.02)
    # puerta con marco, tejadillo, pomo y escalón
    fy = D / 2 + 0.04
    c.box("door_frame", (0, fy, 1.1), (1.2, 0.08, 1.85), trim, B, bevel=0.03)
    c.box("door", (0, fy + 0.04, 1.08), (0.95, 0.06, 1.7), door, B, bevel=0.03)
    for z in (0.65, 1.45):
        c.box("door_panel", (0, fy + 0.08, z), (0.7, 0.03, 0.55), door_dk, B, bevel=0.02)
    c.sphere("knob", (0.32, fy + 0.11, 1.05), (0.05, 0.05, 0.05), gold, B)
    c.box("awning", (0, fy + 0.3, 2.2), (1.6, 0.7, 0.1), roof, B, bevel=0.03, rot=(rad(-15), 0, 0))
    c.box("step", (0, fy + 0.35, 0.1), (1.4, 0.6, 0.2), stone, B, bevel=0.04)
    # ventanas con marco, cruz, contraventanas y jardinera
    for x in (-1.35, 1.35):
        z = 1.55
        c.box("win_frame", (x, fy, z), (0.95, 0.08, 0.95), trim, B, bevel=0.03)
        c.box("glass", (x, fy + 0.02, z), (0.75, 0.06, 0.75), glass, B, bevel=0.01)
        c.box("mullion", (x, fy + 0.06, z), (0.06, 0.04, 0.78), trim, B, bevel=0.01)
        c.box("mullion", (x, fy + 0.06, z), (0.78, 0.04, 0.06), trim, B, bevel=0.01)
        for sgn in (-1, 1):
            c.box("shutter", (x + sgn * 0.62, fy + 0.02, z), (0.28, 0.05, 0.95), door, B, bevel=0.02)
        c.box("planter", (x, fy + 0.18, z - 0.62), (0.9, 0.3, 0.22), door, B, bevel=0.03)
        c.box("soil", (x, fy + 0.18, z - 0.5), (0.8, 0.22, 0.04), soil, B)
        for i in range(5):
            c.sphere("bloom", (x - 0.32 + i * 0.16, fy + 0.2, z - 0.42), (0.07, 0.07, 0.07),
                     red if i % 2 else yellow, B)
    finish(c, ((7, 11, 4.5), (0, 0, 2.0), 45))


def build_fence(name):
    c = Character(name)
    wood = c.mat("wood", (0.80, 0.62, 0.42))
    wood_dk = c.mat("wood_dk", (0.66, 0.48, 0.32))
    for x in (-0.9, 0.9):
        c.box("post", (x, 0, 0.45), (0.14, 0.14, 0.9), wood_dk, B, bevel=0.03)
        c.cone("post_cap", (x, 0, 0.94), 0.1, 0.12, wood_dk, B)
    for z in (0.35, 0.7):
        c.box("rail", (0, 0, z), (1.95, 0.07, 0.12), wood, B, bevel=0.02)
    finish(c)


def build_lamp(name):
    c = Character(name)
    iron = c.mat("iron", (0.18, 0.28, 0.24), rough=0.4)
    light = c.mat("lamp", (1.0, 0.9, 0.6), rough=0.2, emit=(1.0, 0.85, 0.5), strength=2.0)
    c.cylinder("base", (0, 0, 0.1), 0.18, 0.2, iron, B)
    c.cylinder("post", (0, 0, 1.3), 0.05, 2.4, iron, B)
    c.torus("ring", (0, 0, 0.6), 0.07, 0.02, iron, B)
    c.sphere("lamp", (0, 0, 2.65), (0.2, 0.2, 0.24), light, B)
    c.cone("cap", (0, 0, 2.95), 0.26, 0.22, iron, B)
    c.sphere("tip", (0, 0, 3.08), (0.05, 0.05, 0.05), iron, B)
    finish(c)


def build_signboard(name):
    c = Character(name)
    wood = c.mat("wood", (0.80, 0.62, 0.42))
    wood_dk = c.mat("wood_dk", (0.60, 0.42, 0.28))
    for x in (-0.8, 0.8):
        c.box("post", (x, 0, 0.75), (0.12, 0.12, 1.5), wood_dk, B, bevel=0.03)
    c.box("board", (0, 0, 1.45), (1.9, 0.08, 0.75), wood, B, bevel=0.04)
    c.box("board_trim", (0, 0, 1.85), (2.0, 0.12, 0.08), wood_dk, B, bevel=0.02)
    finish(c)


def build_fish(name):
    c = Character(name)
    c.organic = True
    c.voxel = 0.008
    c.decimate = 0.4
    c.gradient = (0.12, -0.06, 0.55, 1.15)   # lomo oscuro, panza clara
    c.keep_separate = {"eye", "pupil"}
    body = c.mat("scales", (0.62, 0.70, 0.78))
    fin = c.mat("fin", (0.55, 0.62, 0.72))
    white = c.mat("eye", (1, 1, 1))
    dark = c.mat("pupil", (0.05, 0.05, 0.05))
    c.sphere("body", (0, 0, 0.05), (0.07, 0.18, 0.08), body, B)
    c.cone("tail", (0, -0.2, 0.05), 0.08, 0.12, fin, B, rot=(rad(-90), 0, 0), scale=(0.25, 1, 1))
    c.cone("dorsal", (0, -0.02, 0.13), 0.05, 0.08, fin, B, scale=(0.25, 1, 1))
    for sgn in (-1, 1):
        c.sphere("eye", (sgn * 0.05, 0.12, 0.07), (0.018, 0.018, 0.018), white, B)
        c.sphere("pupil", (sgn * 0.058, 0.125, 0.07), (0.01, 0.01, 0.01), dark, B)
    finish(c, ((0.6, 0.6, 0.35), (0, 0, 0.05), 50))


if __name__ == "__main__":
    ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None

    def want(name):
        return ONLY is None or name in ONLY

    if want("tree_round"):
        build_tree("tree_round", 1)
    if want("tree_round2"):
        build_tree("tree_round2", 7)
    if want("tree_fruit"):
        build_tree("tree_fruit", 3, fruit=True)
    if want("tree_cedar"):
        build_cedar("tree_cedar", 5)
    if want("bush_pink"):
        build_bush("bush_pink", 2, (1.0, 0.60, 0.72))
    if want("bush_white"):
        build_bush("bush_white", 4, (1.0, 0.98, 0.95))
    if want("rock"):
        build_rock("rock", 6)
    if want("rock2"):
        build_rock("rock2", 9)
    if want("grass"):
        build_grass("grass", 8)
    if want("flower_red"):
        build_flower("flower_red", (1.0, 0.40, 0.45))
    if want("flower_yellow"):
        build_flower("flower_yellow", (1.0, 0.85, 0.30))
    if want("flower_white"):
        build_flower("flower_white", (0.98, 0.97, 0.95))
    if want("house_a"):
        build_house("house_a", (1.0, 0.93, 0.80), (0.92, 0.48, 0.42), (1.0, 1.0, 0.97), (0.55, 0.38, 0.28))
    if want("house_b"):
        build_house("house_b", (1.0, 0.84, 0.88), (0.48, 0.66, 0.92), (1.0, 1.0, 0.97), (0.40, 0.55, 0.80))
    if want("house_c"):
        build_house("house_c", (0.86, 0.95, 0.84), (0.88, 0.66, 0.32), (1.0, 1.0, 0.97), (0.45, 0.62, 0.40))
    if want("fence"):
        build_fence("fence")
    if want("lamp"):
        build_lamp("lamp")
    if want("signboard"):
        build_signboard("signboard")
    if want("fish"):
        build_fish("fish")
