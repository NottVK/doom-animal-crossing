"""Genera los modelos 3D del proyecto con Blender (bpy): malla suave, esqueleto y animaciones.

Uso (con el módulo bpy instalado):
    python tools/blender/build_characters.py assets/models [carpeta_de_previews]

Salida: canelita.glb y centinela.glb. El frente de los modelos mira a +Y en Blender, que al
exportar a glTF (Y arriba) queda mirando a -Z, igual que en Godot.
Animaciones: idle-loop, walk-loop y swing (Canelita) / attack (Centinela).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/models"
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
FPS = 30


class Character:
    def __init__(self, name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = FPS
        self.name = name
        self.parts = []
        self.mats = {}
        self.arm = None

    # ---------- materiales y mallas ----------
    def mat(self, key, rgb, rough=0.85, emit=None, strength=4.0, alpha=1.0):
        if key not in self.mats:
            m = bpy.data.materials.new(key)
            m.use_nodes = True
            b = m.node_tree.nodes["Principled BSDF"]
            # Los colores se escriben en sRGB; Blender trabaja en lineal.
            lin = tuple(v ** 2.2 for v in rgb)
            b.inputs["Base Color"].default_value = (*lin, 1.0)
            b.inputs["Roughness"].default_value = rough
            b.inputs["Alpha"].default_value = alpha
            if emit:
                b.inputs["Emission Color"].default_value = (*emit, 1.0)
                b.inputs["Emission Strength"].default_value = strength
            self.mats[key] = m
        return self.mats[key]

    def _finish_part(self, o, material, bone, smooth):
        if smooth:
            bpy.ops.object.shade_smooth()
        o.data.materials.append(material)
        vg = o.vertex_groups.new(name=bone)
        vg.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
        self.parts.append(o)
        return o

    def sphere(self, name, loc, scale, material, bone, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=18, radius=1.0, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        o.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return self._finish_part(o, material, bone, True)

    def box(self, name, loc, size, material, bone, bevel=0.03, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        o.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 4
        bpy.ops.object.modifier_apply(modifier="bevel")
        return self._finish_part(o, material, bone, False)

    def cylinder(self, name, loc, radius, depth, material, bone, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        return self._finish_part(o, material, bone, True)

    def cone(self, name, loc, radius, depth, material, bone, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=radius, radius2=0.0, depth=depth, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        return self._finish_part(o, material, bone, True)

    def torus(self, name, loc, major, minor, material, bone, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=12, major_radius=major,
                                         minor_radius=minor, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        return self._finish_part(o, material, bone, True)

    # ---------- esqueleto ----------
    def make_armature(self, bones):
        """bones: lista de (nombre, cabeza, cola, padre). El padre debe ir antes que el hijo."""
        bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
        self.arm = bpy.context.active_object
        self.arm.name = self.name + "_Armature"
        data = self.arm.data
        for b in list(data.edit_bones):
            data.edit_bones.remove(b)
        for name, head, tail, parent in bones:
            eb = data.edit_bones.new(name)
            eb.head = head
            eb.tail = tail
            if parent:
                eb.parent = data.edit_bones[parent]
        bpy.ops.object.mode_set(mode="OBJECT")

    def finish_mesh(self):
        bpy.ops.object.select_all(action="DESELECT")
        for o in self.parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = self.parts[0]
        bpy.ops.object.join()
        mesh = bpy.context.active_object
        mesh.name = self.name
        mod = mesh.modifiers.new("Armature", "ARMATURE")
        mod.object = self.arm
        mesh.parent = self.arm
        self.mesh = mesh

    # ---------- animación ----------
    def rot(self, bone, axis, angle):
        """Cuaternión local que equivale a girar `angle` alrededor de un eje del mundo en reposo."""
        rest = self.arm.data.bones[bone].matrix_local.to_3x3()
        r_world = Matrix.Rotation(angle, 3, axis)
        return (rest.inverted() @ r_world @ rest).to_quaternion()

    def key(self, bone, frame, axis=None, angle=0.0, loc=None):
        pb = self.arm.pose.bones[bone]
        if axis:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = self.rot(bone, axis, angle)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
        if loc is not None:
            pb.location = loc
            pb.keyframe_insert("location", frame=frame)

    def begin(self, name):
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        self.arm.animation_data_create()
        self.action = bpy.data.actions.new(name)
        self.arm.animation_data.action = self.action
        self.anim_name = name

    def end(self, length):
        self.action.use_frame_range = True
        self.action.frame_start = 1
        self.action.frame_end = length
        self.action.use_cyclic = self.anim_name.endswith("loop")
        ad = self.arm.animation_data
        track = ad.nla_tracks.new()
        track.name = self.anim_name
        track.strips.new(self.anim_name, 1, self.action)
        ad.action = None

    def export(self):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, self.name.lower() + ".glb")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_animations=True,
                                  export_animation_mode="NLA_TRACKS", export_yup=True,
                                  export_cameras=False, export_lights=False)
        print("exportado", path)

    # ---------- vista previa ----------
    def preview(self, tag, frame=None):
        if not PREVIEW:
            return
        os.makedirs(PREVIEW, exist_ok=True)
        sc = bpy.context.scene
        if frame is not None:
            sc.frame_set(frame)
        for o in list(bpy.data.objects):
            if o.type in {"CAMERA", "LIGHT"}:
                bpy.data.objects.remove(o)
        w = bpy.data.worlds.new("w")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.72, 0.86, 1.0, 1)
        w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
        sc.world = w
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), 0, math.radians(150))
        sc.collection.objects.link(sun)
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        cam.data.lens = 60
        cam.location = (2.6, 5.4, 1.9)
        cam.rotation_euler = (Vector((0, 0, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(cam)
        sc.camera = cam
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 20
        sc.render.resolution_x = 560
        sc.render.resolution_y = 700
        sc.render.filepath = os.path.join(PREVIEW, f"{self.name}_{tag}.png")
        bpy.ops.render.render(write_still=True)


def mirror(v, s):
    return (v[0] * s, v[1], v[2])


# =====================================================================
# Canelita: perrita isleña (inspirada en el estilo, diseño propio)
# =====================================================================
def build_canelita():
    c = Character("Canelita")
    fur = c.mat("fur", (0.98, 0.80, 0.28))
    fur_dark = c.mat("fur_dark", (0.90, 0.68, 0.20))
    cream = c.mat("cream", (1.0, 0.93, 0.72))
    vest = c.mat("vest", (0.42, 0.72, 0.40))
    dark = c.mat("dark", (0.10, 0.07, 0.07), rough=0.4)
    white = c.mat("white", (1, 1, 1), rough=0.3)
    pink = c.mat("pink", (1.0, 0.55, 0.62))
    shoe = c.mat("shoe", (0.55, 0.36, 0.22))
    wood = c.mat("wood", (0.62, 0.44, 0.28))
    ring = c.mat("ring", (0.9, 0.28, 0.28))
    mesh_m = c.mat("net", (1, 1, 1), alpha=0.4)

    fur_light = c.mat("fur_light", (1.0, 0.90, 0.52))
    inner_ear = c.mat("inner_ear", (1.0, 0.70, 0.66))
    vest_dk = c.mat("vest_dk", (0.30, 0.58, 0.30))
    gold = c.mat("gold", (0.95, 0.78, 0.25), rough=0.35)
    sock = c.mat("sock", (1.0, 0.97, 0.9))
    shoe_lt = c.mat("shoe_lt", (0.72, 0.50, 0.32))
    rad = math.radians

    # cuerpo y chaleco con botones, bolsillos, cuello y dobladillo
    c.sphere("body", (0, 0, 0.82), (0.43, 0.36, 0.46), fur, "hips")
    c.sphere("vest", (0, 0.12, 0.84), (0.39, 0.29, 0.40), vest, "chest")
    c.sphere("vest_collar", (0, 0.10, 1.12), (0.31, 0.21, 0.07), vest_dk, "chest")
    c.sphere("vest_hem", (0, 0.10, 0.53), (0.36, 0.26, 0.05), vest_dk, "hips")
    for z in (0.98, 0.84, 0.70):
        c.sphere("button", (0, 0.40, z), (0.036, 0.022, 0.036), gold, "chest")
    for sd in (-1, 1):
        c.sphere("pocket", (sd * 0.17, 0.35, 0.64), (0.10, 0.03, 0.08), vest_dk, "chest")
    c.sphere("tail", (0, -0.45, 0.70), (0.10, 0.17, 0.10), fur, "tail")
    c.sphere("tail_tip", (0, -0.59, 0.73), (0.08, 0.09, 0.08), fur_light, "tail")

    # cabeza: mejillas esponjosas, cejas, boca, flequillo y moño con liga
    c.sphere("head", (0, 0, 1.42), (0.47, 0.42, 0.41), fur, "head")
    c.sphere("muzzle", (0, 0.33, 1.33), (0.21, 0.18, 0.15), cream, "head")
    c.sphere("nose", (0, 0.49, 1.38), (0.065, 0.05, 0.05), dark, "head")
    c.sphere("nose_shine", (0.015, 0.525, 1.395), (0.018, 0.012, 0.012), white, "head")
    c.sphere("mouth", (0, 0.50, 1.295), (0.075, 0.02, 0.012), dark, "head")
    c.sphere("tongue", (0, 0.485, 1.27), (0.04, 0.03, 0.022), pink, "head")
    for x in (-0.07, 0.0, 0.07):
        c.cone("bang", (x, 0.15, 1.79), 0.05, 0.17, fur, "head", rot=(rad(-55), 0, rad(-x * 220)))
    c.torus("hair_band", (0, -0.03, 1.80), 0.10, 0.026, vest, "head")
    c.sphere("topknot", (0, -0.03, 1.91), (0.12, 0.12, 0.12), fur, "head")
    c.cone("knot_tip", (0, -0.03, 2.0), 0.05, 0.13, fur, "head")
    for sd in (-1, 1):
        side = "L" if sd < 0 else "R"
        c.sphere("cheek", (sd * 0.38, 0.12, 1.33), (0.14, 0.12, 0.12), fur, "head")
        c.sphere("eye", (sd * 0.17, 0.37, 1.49), (0.068, 0.042, 0.095), dark, "head")
        c.sphere("shine", (sd * 0.155, 0.405, 1.525), (0.025, 0.02, 0.025), white, "head")
        c.sphere("shine2", (sd * 0.185, 0.405, 1.46), (0.012, 0.01, 0.012), white, "head")
        c.sphere("brow", (sd * 0.17, 0.35, 1.60), (0.075, 0.025, 0.02), fur_dark, "head", rot=(0, 0, rad(sd * 14)))
        c.sphere("blush", (sd * 0.30, 0.29, 1.39), (0.075, 0.02, 0.05), pink, "head")
        c.sphere("ear", (sd * 0.50, 0.0, 1.36), (0.10, 0.16, 0.25), fur_dark, "ear_" + side,
                 rot=(0, rad(-sd * 12), 0))
        c.sphere("ear_in", (sd * 0.49, 0.10, 1.37), (0.05, 0.07, 0.18), inner_ear, "ear_" + side,
                 rot=(0, rad(-sd * 12), 0))
        # brazos con manos, pulgar y nudillos
        c.sphere("arm", (sd * 0.46, 0, 0.88), (0.10, 0.10, 0.25), fur, "arm_" + side)
        c.sphere("hand", (sd * 0.46, 0.04, 0.60), (0.105, 0.105, 0.105), cream, "hand_" + side)
        c.sphere("thumb", (sd * 0.53, 0.08, 0.62), (0.04, 0.05, 0.055), cream, "hand_" + side)
        for i in (-1, 0, 1):
            c.sphere("knuckle", (sd * 0.46 + i * 0.045, 0.125, 0.575), (0.036, 0.036, 0.036), cream, "hand_" + side)
        # piernas con calcetín y zapato con suela y puntera
        c.sphere("leg", (sd * 0.18, 0, 0.27), (0.12, 0.12, 0.21), fur_dark, "leg_" + side)
        c.sphere("sock", (sd * 0.18, 0, 0.17), (0.128, 0.128, 0.07), sock, "leg_" + side)
        c.sphere("shoe", (sd * 0.18, 0.06, 0.085), (0.14, 0.21, 0.085), shoe, "leg_" + side)
        c.sphere("toe", (sd * 0.18, 0.21, 0.085), (0.105, 0.09, 0.065), shoe_lt, "leg_" + side)
        c.sphere("sole", (sd * 0.18, 0.07, 0.03), (0.145, 0.23, 0.035), dark, "leg_" + side)

    # red de atrapar mariposas (parte de la mano derecha)
    c.cylinder("pole", (0.46, 0.75, 0.62), 0.028, 1.5, wood, "hand_R", rot=(rad(90), 0, 0))
    c.cylinder("grip", (0.46, 0.10, 0.62), 0.036, 0.22, ring, "hand_R", rot=(rad(90), 0, 0))
    c.torus("hoop", (0.46, 1.62, 0.62), 0.24, 0.025, ring, "hand_R", rot=(0, rad(90), 0))
    c.sphere("net", (0.46, 1.62, 0.62), (0.015, 0.22, 0.22), mesh_m, "hand_R")

    bones = [
        ("root", (0, 0, 0), (0, 0, 0.15), None),
        ("hips", (0, 0, 0.5), (0, 0, 0.8), "root"),
        ("chest", (0, 0, 0.8), (0, 0, 1.15), "hips"),
        ("head", (0, 0, 1.15), (0, 0, 1.8), "chest"),
        ("ear_L", (-0.40, 0, 1.55), (-0.52, 0, 1.2), "head"),
        ("ear_R", (0.40, 0, 1.55), (0.52, 0, 1.2), "head"),
        ("tail", (0, -0.38, 0.66), (0, -0.62, 0.74), "hips"),
        ("arm_L", (-0.44, 0, 1.08), (-0.46, 0, 0.68), "chest"),
        ("arm_R", (0.44, 0, 1.08), (0.46, 0, 0.68), "chest"),
        ("hand_L", (-0.46, 0, 0.68), (-0.46, 0.05, 0.52), "arm_L"),
        ("hand_R", (0.46, 0, 0.68), (0.46, 0.05, 0.52), "arm_R"),
        ("leg_L", (-0.18, 0, 0.5), (-0.18, 0, 0.06), "hips"),
        ("leg_R", (0.18, 0, 0.5), (0.18, 0, 0.06), "hips"),
    ]
    c.make_armature(bones)
    c.finish_mesh()
    c.preview("rest")

    X, Z = "X", "Z"
    hold = 0.2   # el brazo derecho sostiene la red hacia adelante

    # idle: respira, mueve orejas y cola
    c.begin("idle-loop")
    for f in range(1, 62, 6):
        t = (f - 1) / 60.0 * math.tau
        c.key("chest", f, X, 0.03 * math.sin(t))
        c.key("head", f, X, 0.04 * math.sin(t + 0.6))
        c.key("ear_L", f, X, 0.10 * math.sin(t + 1.0))
        c.key("ear_R", f, X, 0.10 * math.sin(t + 1.0))
        c.key("tail", f, Z, 0.5 * math.sin(2 * t))
        c.key("arm_R", f, X, hold + 0.04 * math.sin(t))
        c.key("arm_L", f, X, 0.05 * math.sin(t))
    c.end(61)

    # walk: piernas y brazos alternados, rebote del cuerpo
    c.begin("walk-loop")
    for f in range(1, 26, 2):
        t = (f - 1) / 24.0 * math.tau
        s = math.sin(t)
        c.key("leg_L", f, X, 0.75 * s)
        c.key("leg_R", f, X, -0.75 * s)
        c.key("arm_L", f, X, -0.55 * s)
        c.key("arm_R", f, X, hold + 0.20 * s)
        c.key("hips", f, loc=(0, 0, abs(math.sin(t)) * 0.05))
        c.key("chest", f, Z, 0.05 * s)
        c.key("head", f, X, 0.05 * abs(s))
        c.key("ear_L", f, X, 0.25 * abs(s))
        c.key("ear_R", f, X, 0.25 * abs(s))
        c.key("tail", f, Z, 0.7 * s)
    c.preview("walk", 4)
    c.end(25)

    # swing: la red sube y golpea hacia adelante
    c.begin("swing")
    poses = [(1, hold), (5, 2.4), (7, 2.5), (11, 0.1), (15, 0.0), (19, hold)]
    for f, a in poses:
        c.key("arm_R", f, X, a)
        c.key("chest", f, X, -0.15 if f in (5, 7) else (0.12 if f in (11, 15) else 0.0))
    c.preview("swing", 11)
    c.end(19)

    c.export()


# =====================================================================
# Centinela: guerrero de armadura verde (inspirado en el estilo, diseño propio)
# =====================================================================
def build_centinela():
    c = Character("Centinela")
    armor = c.mat("armor", (0.27, 0.45, 0.25), rough=0.45)
    armor_dk = c.mat("armor_dk", (0.17, 0.30, 0.17), rough=0.5)
    steel = c.mat("steel", (0.14, 0.14, 0.16), rough=0.4)
    gold = c.mat("gold", (0.85, 0.66, 0.22), rough=0.35)
    visor = c.mat("visor", (0.05, 0.4, 0.15), rough=0.2, emit=(0.25, 1.0, 0.45), strength=5.0)
    cloth = c.mat("cloth", (0.45, 0.12, 0.10))

    leather = c.mat("leather", (0.25, 0.17, 0.12), rough=0.8)
    blade = c.mat("blade", (0.55, 0.57, 0.62), rough=0.25)
    flame = c.mat("flame", (0.9, 0.3, 0.05), rough=0.3, emit=(1.0, 0.45, 0.1), strength=6.0)
    rad = math.radians

    # torso en V: peto con costillas, esternón, emblema, cinturón, faldón de malla y escarcelas
    c.box("chest", (0, 0, 1.34), (0.74, 0.44, 0.40), armor, "chest", bevel=0.08)
    c.box("chest_low", (0, 0, 1.12), (0.52, 0.38, 0.22), armor_dk, "chest", bevel=0.06)
    c.box("plate", (0, 0.23, 1.38), (0.46, 0.07, 0.30), armor_dk, "chest", bevel=0.03)
    for z in (1.26, 1.34, 1.42):
        c.box("rib", (0, 0.265, z), (0.40, 0.03, 0.045), steel, "chest", bevel=0.01)
    c.box("sternum", (0, 0.27, 1.34), (0.05, 0.035, 0.30), gold, "chest", bevel=0.01)
    c.torus("emblem", (0, 0.285, 1.40), 0.085, 0.016, gold, "chest", rot=(rad(90), 0, 0))
    c.box("belly", (0, 0, 1.0), (0.44, 0.32, 0.20), steel, "hips", bevel=0.05)
    c.box("belt", (0, 0, 0.88), (0.56, 0.38, 0.09), leather, "hips", bevel=0.02)
    c.box("buckle", (0, 0.195, 0.88), (0.14, 0.03, 0.10), gold, "hips", bevel=0.01)
    c.box("pelvis", (0, 0, 0.76), (0.54, 0.36, 0.20), armor_dk, "hips", bevel=0.04)
    c.box("mail", (0, 0.0, 0.62), (0.54, 0.35, 0.14), steel, "hips", bevel=0.03)
    c.box("tabard", (0, 0.20, 0.52), (0.24, 0.04, 0.50), cloth, "hips", bevel=0.01)
    for sd in (-1, 1):
        for i, z in enumerate((0.70, 0.60, 0.50)):
            c.box("tasset", (sd * (0.24 + i * 0.03), 0.18, z), (0.17, 0.04, 0.10), armor_dk, "hips", bevel=0.015)
    # capa hecha jirones y manto
    c.box("mantle", (0, -0.20, 1.58), (0.82, 0.22, 0.10), cloth, "chest", bevel=0.03)
    for x, ln in ((-0.24, 1.05), (-0.08, 1.35), (0.08, 1.15), (0.24, 1.40)):
        c.box("cape", (x, -0.31, 1.52 - ln / 2), (0.15, 0.04, ln), cloth, "chest", bevel=0.01)
    c.box("collar", (0, -0.08, 1.60), (0.46, 0.34, 0.10), armor_dk, "chest", bevel=0.04)
    c.box("neck", (0, 0, 1.56), (0.22, 0.22, 0.10), steel, "chest", bevel=0.02)
    c.box("gorget", (0, 0.06, 1.60), (0.34, 0.24, 0.08), steel, "chest", bevel=0.03)

    # casco: placa facial, visor en T, babero, respiraderos, remaches y cresta
    c.box("helmet", (0, 0, 1.80), (0.40, 0.42, 0.38), armor, "head", bevel=0.11)
    c.box("faceplate", (0, 0.19, 1.73), (0.34, 0.16, 0.26), armor_dk, "head", bevel=0.05)
    c.box("visor_h", (0, 0.275, 1.78), (0.30, 0.04, 0.06), visor, "head", bevel=0.012)
    c.box("visor_v", (0, 0.275, 1.72), (0.05, 0.04, 0.16), visor, "head", bevel=0.012)
    c.box("brow", (0, 0.24, 1.86), (0.38, 0.08, 0.05), steel, "head", bevel=0.015)
    c.box("chin", (0, 0.22, 1.60), (0.24, 0.10, 0.08), steel, "head", bevel=0.02)
    c.box("crest", (0, -0.02, 2.04), (0.06, 0.38, 0.12), gold, "head", bevel=0.02)
    for x in (-0.14, -0.05, 0.05, 0.14):
        c.sphere("rivet", (x, 0.215, 1.93), (0.02, 0.02, 0.02), gold, "head")
    for sd in (-1, 1):
        c.box("vent", (sd * 0.205, 0.10, 1.76), (0.03, 0.14, 0.16), steel, "head", bevel=0.01)
        for i in range(3):
            c.box("vent_slot", (sd * 0.222, 0.10, 1.71 + i * 0.045), (0.012, 0.11, 0.015), armor_dk, "head")

    for sd in (-1, 1):
        side = "L" if sd < 0 else "R"
        # hombreras en capas con púas, codo con pincho, brazal con remaches, puño con dedos
        c.sphere("pauld1", (sd * 0.54, 0, 1.54), (0.30, 0.28, 0.22), armor, "arm_" + side)
        c.sphere("pauld2", (sd * 0.56, 0, 1.43), (0.32, 0.30, 0.13), armor_dk, "arm_" + side)
        c.box("pauld_trim", (sd * 0.56, 0, 1.36), (0.44, 0.40, 0.04), gold, "arm_" + side, bevel=0.012)
        c.cone("spike", (sd * 0.62, 0, 1.78), 0.07, 0.28, steel, "arm_" + side, rot=(0, rad(sd * 22), 0))
        c.cone("spike2", (sd * 0.72, 0, 1.66), 0.055, 0.2, steel, "arm_" + side, rot=(0, rad(sd * 55), 0))
        c.box("upper_arm", (sd * 0.60, 0, 1.18), (0.22, 0.24, 0.38), armor_dk, "arm_" + side, bevel=0.04)
        c.sphere("elbow", (sd * 0.60, -0.02, 1.0), (0.14, 0.14, 0.14), steel, "arm_" + side)
        c.cone("elbow_spike", (sd * 0.74, -0.02, 1.0), 0.05, 0.16, steel, "arm_" + side, rot=(0, rad(sd * 90), 0))
        c.box("forearm", (sd * 0.60, 0.02, 0.84), (0.28, 0.30, 0.40), armor, "forearm_" + side, bevel=0.06)
        c.box("vambrace", (sd * 0.60, 0.02, 0.97), (0.31, 0.33, 0.05), gold, "forearm_" + side, bevel=0.012)
        for z in (0.90, 0.82, 0.74):
            c.sphere("rivet", (sd * 0.745, 0.02, z), (0.02, 0.02, 0.02), gold, "forearm_" + side)
        c.box("fist", (sd * 0.60, 0.04, 0.58), (0.22, 0.24, 0.16), steel, "forearm_" + side, bevel=0.04)
        for i in range(4):
            c.box("finger", (sd * 0.60 + (i - 1.5) * 0.05, 0.15, 0.55), (0.044, 0.07, 0.11), steel,
                  "forearm_" + side, bevel=0.012)
        # piernas: cuisse, rodillera con ala, greba con cresta, bota con puntera y puño dorado
        c.box("thigh", (sd * 0.20, 0, 0.55), (0.28, 0.30, 0.40), armor, "leg_" + side, bevel=0.05)
        c.box("thigh_trim", (sd * 0.20, 0.0, 0.72), (0.30, 0.32, 0.04), gold, "leg_" + side, bevel=0.01)
        c.sphere("knee", (sd * 0.20, 0.14, 0.36), (0.13, 0.09, 0.13), gold, "leg_" + side)
        c.box("poleyn", (sd * 0.20, 0.17, 0.36), (0.24, 0.05, 0.16), armor_dk, "leg_" + side, bevel=0.02)
        c.box("shin", (sd * 0.20, 0.02, 0.18), (0.26, 0.28, 0.34), armor_dk, "shin_" + side, bevel=0.05)
        c.box("shin_ridge", (sd * 0.20, 0.17, 0.18), (0.05, 0.04, 0.30), gold, "shin_" + side, bevel=0.01)
        c.box("boot", (sd * 0.20, 0.08, 0.05), (0.30, 0.44, 0.12), steel, "shin_" + side, bevel=0.04)
        c.sphere("toe", (sd * 0.20, 0.26, 0.06), (0.14, 0.10, 0.075), armor_dk, "shin_" + side)
        c.box("boot_cuff", (sd * 0.20, 0.02, 0.13), (0.30, 0.30, 0.04), gold, "shin_" + side, bevel=0.01)

    # escudo con remache central, tachuelas y borde dentado
    sx, sy, sz = -0.80, 0.22, 0.90
    c.cylinder("shield", (sx, sy, sz), 0.40, 0.07, steel, "forearm_L", rot=(rad(90), 0, 0))
    c.torus("shield_rim", (sx, sy + 0.03, sz), 0.40, 0.04, gold, "forearm_L", rot=(rad(90), 0, 0))
    c.sphere("shield_boss", (sx, sy + 0.06, sz), (0.10, 0.07, 0.10), gold, "forearm_L")
    c.cone("shield_spike", (sx, sy + 0.12, sz), 0.05, 0.12, steel, "forearm_L", rot=(rad(-90), 0, 0))
    for i in range(12):
        ang = i * math.tau / 12
        c.sphere("stud", (sx + 0.30 * math.cos(ang), sy + 0.05, sz + 0.30 * math.sin(ang)),
                 (0.03, 0.03, 0.03), gold, "forearm_L")
    for i in range(16):
        ang = i * math.tau / 16 + 0.1
        c.cone("tooth", (sx + 0.44 * math.cos(ang), sy, sz + 0.44 * math.sin(ang)), 0.045, 0.12, steel,
               "forearm_L", rot=(0, rad(90) - ang, 0))

    # espada de filo ardiente en la mano derecha
    hx, hy, hz = 0.60, 0.04, 0.58
    c.cylinder("grip", (hx, hy, hz), 0.03, 0.26, leather, "forearm_R", rot=(rad(90), 0, 0))
    c.sphere("pommel", (hx, hy - 0.16, hz), (0.05, 0.05, 0.05), gold, "forearm_R")
    c.box("guard", (hx, hy + 0.16, hz), (0.05, 0.05, 0.32), gold, "forearm_R", bevel=0.01)
    c.box("blade", (hx, hy + 0.80, hz), (0.03, 1.30, 0.11), blade, "forearm_R", bevel=0.008)
    c.box("blade_glow", (hx, hy + 0.82, hz), (0.034, 1.26, 0.035), flame, "forearm_R", bevel=0.006)
    c.cone("blade_tip", (hx, hy + 1.47, hz), 0.055, 0.14, blade, "forearm_R", rot=(rad(-90), 0, 0))

    bones = [
        ("root", (0, 0, 0), (0, 0, 0.2), None),
        ("hips", (0, 0, 0.8), (0, 0, 1.1), "root"),
        ("chest", (0, 0, 1.1), (0, 0, 1.55), "hips"),
        ("head", (0, 0, 1.55), (0, 0, 2.1), "chest"),
        ("arm_L", (-0.52, 0, 1.46), (-0.58, 0, 1.0), "chest"),
        ("arm_R", (0.52, 0, 1.46), (0.58, 0, 1.0), "chest"),
        ("forearm_L", (-0.58, 0, 1.0), (-0.58, 0.04, 0.52), "arm_L"),
        ("forearm_R", (0.58, 0, 1.0), (0.58, 0.04, 0.52), "arm_R"),
        ("leg_L", (-0.2, 0, 0.8), (-0.2, 0, 0.36), "hips"),
        ("leg_R", (0.2, 0, 0.8), (0.2, 0, 0.36), "hips"),
        ("shin_L", (-0.2, 0, 0.36), (-0.2, 0.02, 0.04), "leg_L"),
        ("shin_R", (0.2, 0, 0.36), (0.2, 0.02, 0.04), "leg_R"),
    ]
    c.make_armature(bones)
    c.finish_mesh()
    c.preview("rest")

    X = "X"

    c.begin("idle-loop")
    for f in range(1, 62, 6):
        t = (f - 1) / 60.0 * math.tau
        c.key("chest", f, X, 0.03 * math.sin(t))
        c.key("head", f, X, -0.03 * math.sin(t))
        c.key("arm_L", f, X, 0.06 * math.sin(t))
        c.key("arm_R", f, X, -0.06 * math.sin(t))
        c.key("forearm_L", f, X, 0.25)
        c.key("forearm_R", f, X, 0.25)
    c.end(61)

    c.begin("walk-loop")
    for f in range(1, 22, 2):
        t = (f - 1) / 20.0 * math.tau
        s = math.sin(t)
        c.key("leg_L", f, X, 0.6 * s)
        c.key("leg_R", f, X, -0.6 * s)
        c.key("shin_L", f, X, -0.5 * max(0.0, -s))
        c.key("shin_R", f, X, -0.5 * max(0.0, s))
        c.key("arm_L", f, X, -0.5 * s)
        c.key("arm_R", f, X, 0.5 * s)
        c.key("forearm_L", f, X, 0.45)
        c.key("forearm_R", f, X, 0.45)
        c.key("hips", f, loc=(0, 0, abs(math.sin(t)) * 0.04))
        c.key("chest", f, X, 0.06)
    c.preview("walk", 4)
    c.end(21)

    c.begin("attack")
    for f, a, fa in [(1, 0.0, 0.25), (5, 2.4, 0.3), (7, 2.6, 0.3), (11, 0.2, 0.5), (15, 0.1, 0.4), (20, 0.0, 0.25)]:
        c.key("arm_R", f, X, a)
        c.key("forearm_R", f, X, fa)
        c.key("chest", f, X, -0.12 if f in (5, 7) else (0.15 if f in (11, 15) else 0.0))
    c.preview("attack", 11)
    c.end(20)

    c.export()


if __name__ == "__main__":
    build_canelita()
    build_centinela()
