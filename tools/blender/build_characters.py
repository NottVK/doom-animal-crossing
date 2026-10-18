"""Genera los modelos 3D del proyecto con Blender (bpy): malla suave, esqueleto y animaciones.

Uso (con el módulo bpy instalado):
    python tools/blender/build_characters.py assets/models [carpeta_de_previews]

Salida: canelita.glb y centinela.glb (build_brisa queda como diseño alterno, no se exporta). El frente de los modelos mira a +Y en Blender, que al
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
        self.head_scale = 1.0   # agranda cabeza y orejas alrededor de (0, 0, head_pivot_z)
        self.head_pivot_z = 1.58
        # Modo orgánico: funde las piezas en una sola malla esculpida (remesh por vóxeles + suavizado),
        # pinta los colores como color de vértice y reparte los pesos del esqueleto suavemente.
        self.organic = False
        self.keep_separate = set()   # piezas de detalle que no se funden (ojos, nariz, red...)
        self.voxel = 0.014
        self.decimate = 0.3

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

    def cylinder(self, name, loc, radius, depth, material, bone, rot=(0, 0, 0), scale=(1, 1, 1)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        if tuple(scale) != (1, 1, 1):
            o.scale = scale
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return self._finish_part(o, material, bone, True)

    def cone(self, name, loc, radius, depth, material, bone, rot=(0, 0, 0), r2=0.0, scale=(1, 1, 1)):
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=radius, radius2=r2, depth=depth, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        if tuple(scale) != (1, 1, 1):
            o.scale = scale
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return self._finish_part(o, material, bone, True)

    def limb(self, name, a, b, ra, rb, material, bone, cap=True):
        """Segmento cónico entre dos puntos (radio ra en a, rb en b) con una esfera en el extremo b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        rot = d.to_track_quat("Z", "Y").to_euler()
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=d.length,
                                        location=(a + b) / 2, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        self._finish_part(o, material, bone, True)
        if cap:
            self.sphere(name + "_cap", tuple(b), (rb, rb, rb), material, bone)
        return o

    def strap(self, name, a, b, width, thick, material, bone):
        a, b = Vector(a), Vector(b)
        d = b - a
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(a + b) / 2, rotation=d.to_track_quat("Z", "Y").to_euler())
        o = bpy.context.active_object
        o.name = name
        o.scale = (width, thick, d.length)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return self._finish_part(o, material, bone, False)

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
        if self.head_scale != 1.0:
            pivot = Vector((0, 0, self.head_pivot_z))
            m = Matrix.Translation(pivot) @ Matrix.Scale(self.head_scale, 4) @ Matrix.Translation(-pivot)
            for o in self.parts:
                if o.vertex_groups[0].name in ("head", "ear_L", "ear_R"):
                    bpy.ops.object.select_all(action="DESELECT")
                    o.select_set(True)
                    bpy.context.view_layer.objects.active = o
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                    o.data.transform(m)
        if self.organic:
            self._fuse_organic()
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

    def _apply_mods(self, obj):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for m in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)

    def _fuse_organic(self):
        fuse = [o for o in self.parts if o.name.split(".")[0] not in self.keep_separate]
        keep = [o for o in self.parts if o not in fuse]
        # 1) cada pieza guarda su color como atributo, y se juntan en una malla "fuente"
        for o in fuse:
            col = o.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            attr = o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
            for d in attr.data:
                d.color = tuple(col)
        bpy.ops.object.select_all(action="DESELECT")
        for o in fuse:
            o.select_set(True)
        bpy.context.view_layer.objects.active = fuse[0]
        bpy.ops.object.join()
        src = bpy.context.active_object
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # 2) copia remallada: una sola superficie continua, suavizada y aligerada
        body = src.copy()
        body.data = src.data.copy()
        body.name = self.name + "_body"
        bpy.context.collection.objects.link(body)
        body.vertex_groups.clear()
        rm = body.modifiers.new("remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = self.voxel
        sm = body.modifiers.new("smooth", "LAPLACIANSMOOTH")
        sm.iterations = 4
        sm.lambda_factor = 0.8
        dec = body.modifiers.new("decimate", "DECIMATE")
        dec.ratio = self.decimate
        self._apply_mods(body)
        for a in list(body.data.color_attributes):
            body.data.color_attributes.remove(a)
        body.data.materials.clear()

        # 3) colores y pesos del esqueleto se transfieren desde la fuente (interpolados)
        dt = body.modifiers.new("transfer", "DATA_TRANSFER")
        dt.object = src
        dt.use_vert_data = True
        dt.data_types_verts = {"VGROUP_WEIGHTS", "COLOR_VERTEX"}
        dt.vert_mapping = "POLYINTERP_NEAREST"
        dt.layers_vgroup_select_src = "ALL"
        dt.layers_vgroup_select_dst = "NAME"
        dt.layers_vcol_vert_select_src = "ALL"
        dt.layers_vcol_vert_select_dst = "NAME"
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.datalayout_transfer(modifier="transfer")
        self._apply_mods(body)
        bpy.ops.object.shade_smooth()
        body.data.color_attributes.active_color_name = "Col"

        m = bpy.data.materials.new("body")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.85
        body.data.materials.append(m)

        bpy.data.objects.remove(src)
        self.parts = [body] + keep

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
        cam.location = (2.8, 5.6, 1.9)
        cam.rotation_euler = (Vector((0, 0, 0.95)) - cam.location).to_track_quat("-Z", "Y").to_euler()
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
# Brisa: zorra exploradora (diseño original, proporciones más realistas)
# =====================================================================
def build_brisa():
    c = Character("Brisa")
    c.head_scale = 1.3
    rad = math.radians
    fur = c.mat("fur", (0.88, 0.42, 0.13))
    fur_dk = c.mat("fur_dk", (0.50, 0.22, 0.07))
    cream = c.mat("cream", (0.98, 0.93, 0.82))
    sock = c.mat("sock", (0.16, 0.10, 0.08))
    jacket = c.mat("jacket", (0.14, 0.46, 0.40))
    jacket_dk = c.mat("jacket_dk", (0.09, 0.30, 0.27))
    shirt = c.mat("shirt", (0.92, 0.87, 0.74))
    mustard = c.mat("mustard", (0.92, 0.70, 0.20))
    leather = c.mat("leather", (0.38, 0.23, 0.13), rough=0.7)
    trouser = c.mat("trouser", (0.33, 0.27, 0.22))
    brass = c.mat("brass", (0.85, 0.65, 0.25), rough=0.3)
    eye_w = c.mat("eye_w", (1, 1, 1), rough=0.2)
    iris = c.mat("iris", (0.95, 0.62, 0.12), rough=0.25)
    dark = c.mat("dark", (0.05, 0.04, 0.04), rough=0.3)
    lens = c.mat("lens", (0.6, 0.85, 0.95), rough=0.1, alpha=0.5)
    wood = c.mat("wood", (0.62, 0.44, 0.28))
    ring = c.mat("ring", (0.80, 0.40, 0.15), rough=0.4)
    mesh_m = c.mat("net", (1, 1, 1), alpha=0.4)

    # torso: pelvis, abdomen, pecho con abrigo, hombros, faldón, cremallera
    c.sphere("pelvis", (0, 0, 0.97), (0.185, 0.125, 0.125), trouser, "hips")
    c.sphere("abdomen", (0, 0, 1.10), (0.15, 0.105, 0.12), shirt, "hips")
    c.sphere("chest", (0, 0, 1.29), (0.185, 0.125, 0.17), jacket, "chest")
    c.sphere("shoulders", (0, 0, 1.44), (0.25, 0.10, 0.07), jacket, "chest")
    c.cone("skirt", (0, 0, 1.02), 0.21, 0.30, jacket, "hips", r2=0.17, scale=(1, 0.75, 1))
    c.box("zipper", (0, 0.127, 1.20), (0.012, 0.012, 0.44), brass, "chest", bevel=0.003)
    c.cylinder("belt", (0, 0, 1.03), 0.205, 0.05, leather, "hips", scale=(1, 0.75, 1))
    c.box("buckle", (0, 0.157, 1.03), (0.05, 0.012, 0.045), brass, "hips", bevel=0.004)
    for sd in (-1, 1):
        c.box("pouch", (sd * 0.19, 0.05, 0.95), (0.07, 0.07, 0.10), leather, "hips", bevel=0.015)
    # cuello, cuello del abrigo, capucha, bufanda con extremo suelto
    c.limb("neck", (0, 0, 1.50), (0, 0, 1.62), 0.05, 0.045, fur, "neck", cap=False)
    c.torus("collar", (0, 0, 1.51), 0.078, 0.032, jacket_dk, "neck")
    c.sphere("hood", (0, -0.10, 1.49), (0.12, 0.07, 0.07), jacket_dk, "chest")
    c.torus("scarf", (0, 0.005, 1.55), 0.088, 0.028, mustard, "neck")
    c.box("scarf_tail", (-0.07, 0.105, 1.40), (0.075, 0.022, 0.30), mustard, "scarf_end", bevel=0.006)
    c.box("scarf_tail2", (-0.07, 0.105, 1.24), (0.075, 0.022, 0.03), brass, "scarf_end", bevel=0.004)
    # morral y correa cruzada
    c.strap("strap", (0.17, 0.0, 1.43), (-0.23, 0.0, 0.97), 0.035, 0.014, leather, "chest")
    c.box("satchel", (-0.25, 0.0, 0.90), (0.075, 0.16, 0.14), leather, "hips", bevel=0.015)
    c.box("flap", (-0.25, 0.0, 0.965), (0.08, 0.17, 0.045), jacket_dk, "hips", bevel=0.008)
    c.box("satchel_clasp", (-0.292, 0.0, 0.93), (0.01, 0.04, 0.03), brass, "hips", bevel=0.004)

    # cabeza de zorra: cráneo, hocico alargado, mejillas con pelaje, ojos con iris, orejas
    c.sphere("head", (0, 0, 1.69), (0.115, 0.12, 0.11), fur, "head")
    c.sphere("muzzle", (0, 0.135, 1.655), (0.052, 0.095, 0.045), fur, "head")
    c.sphere("jaw", (0, 0.12, 1.625), (0.045, 0.085, 0.028), cream, "head")
    c.sphere("nose", (0, 0.228, 1.665), (0.019, 0.017, 0.015), dark, "head")
    c.sphere("mouth", (0, 0.195, 1.64), (0.032, 0.04, 0.004), dark, "head")
    for sd in (-1, 1):
        side = "L" if sd < 0 else "R"
        th = math.atan2(sd * 0.8, -0.5)
        c.cone("cheek_fur", (sd * 0.105, 0.03, 1.65), 0.05, 0.14, cream, "head", rot=(0, th, 0))
        c.sphere("cheek", (sd * 0.07, 0.10, 1.64), (0.04, 0.05, 0.04), cream, "head")
        c.sphere("eye", (sd * 0.052, 0.108, 1.70), (0.024, 0.014, 0.017), eye_w, "head")
        c.sphere("iris", (sd * 0.052, 0.118, 1.70), (0.016, 0.008, 0.016), iris, "head")
        c.sphere("pupil", (sd * 0.052, 0.122, 1.70), (0.008, 0.005, 0.012), dark, "head")
        c.sphere("shine", (sd * 0.047, 0.126, 1.707), (0.004, 0.003, 0.004), eye_w, "head")
        c.sphere("lid", (sd * 0.052, 0.109, 1.714), (0.026, 0.015, 0.007), fur_dk, "head")
        c.sphere("brow", (sd * 0.056, 0.105, 1.737), (0.030, 0.010, 0.008), fur_dk, "head", rot=(0, 0, rad(-sd * 15)))
        tilt = rad(sd * 14)
        c.cone("ear", (sd * 0.075, -0.01, 1.82), 0.062, 0.20, fur, "ear_" + side, rot=(0, tilt, 0))
        c.cone("ear_in", (sd * 0.075, 0.012, 1.815), 0.036, 0.15, cream, "ear_" + side, rot=(0, tilt, 0))
        c.cone("ear_tip", (sd * (0.075 + 0.095 * math.sin(tilt)), -0.01, 1.82 + 0.095 * math.cos(tilt)),
               0.022, 0.07, sock, "ear_" + side, rot=(0, tilt, 0))
        # gafas sobre la frente
        c.cylinder("goggle", (sd * 0.045, 0.116, 1.765), 0.032, 0.022, brass, "head", rot=(rad(90), 0, 0))
        c.cylinder("lens", (sd * 0.045, 0.1275, 1.765), 0.025, 0.012, lens, "head", rot=(rad(90), 0, 0))
    c.torus("headband", (0, -0.005, 1.755), 0.12, 0.009, leather, "head")
    c.box("goggle_bridge", (0, 0.118, 1.765), (0.03, 0.012, 0.012), leather, "head", bevel=0.003)

    # cola frondosa con punta clara (dos huesos)
    c.limb("tail_a", (0, -0.10, 0.97), (0, -0.28, 1.00), 0.045, 0.075, fur, "tail1")
    c.limb("tail_b", (0, -0.28, 1.00), (0, -0.52, 1.05), 0.085, 0.07, fur, "tail2")
    c.sphere("tail_fluff", (0, -0.42, 1.03), (0.095, 0.17, 0.095), fur, "tail2")
    c.sphere("tail_tip", (0, -0.62, 1.07), (0.065, 0.11, 0.065), cream, "tail2")

    for sd in (-1, 1):
        S = "L" if sd < 0 else "R"
        x = sd * 0.10
        # piernas: pantalón, rodilla, bota alta con cordones, suela y puntera
        c.limb("thigh", (x, 0, 0.93), (x, 0.0, 0.50), 0.095, 0.075, trouser, "thigh_" + S)
        c.sphere("knee", (x, 0.01, 0.49), (0.075, 0.075, 0.075), trouser, "thigh_" + S)
        c.limb("boot_shaft", (x, 0, 0.46), (x, 0, 0.10), 0.074, 0.058, leather, "shin_" + S)
        c.torus("boot_cuff", (x, 0, 0.455), 0.077, 0.016, jacket_dk, "shin_" + S)
        for i in range(3):
            c.box("lace", (x, 0.068, 0.37 - i * 0.07), (0.07, 0.012, 0.014), cream, "shin_" + S, bevel=0.002)
        c.sphere("foot", (x, 0.07, 0.065), (0.065, 0.14, 0.055), leather, "foot_" + S)
        c.sphere("toe", (x, 0.16, 0.05), (0.055, 0.07, 0.045), leather, "foot_" + S)
        c.sphere("sole", (x, 0.08, 0.02), (0.07, 0.16, 0.02), dark, "foot_" + S)
        # brazos: manga, codo, antebrazo con pelaje, puño del abrigo, mano enguantada con dedos
        sh, el, wr = (sd * 0.21, 0, 1.42), (sd * 0.25, 0, 1.15), (sd * 0.26, 0.03, 0.90)
        c.sphere("shoulder_cap", sh, (0.075, 0.075, 0.075), jacket, "upper_arm_" + S)
        c.limb("sleeve", sh, el, 0.066, 0.056, jacket, "upper_arm_" + S)
        c.limb("forearm", el, wr, 0.05, 0.04, fur, "forearm_" + S)
        c.limb("cuff", (sd * 0.252, 0.005, 1.10), (sd * 0.256, 0.01, 1.02), 0.058, 0.056, jacket_dk, "forearm_" + S, cap=False)
        c.sphere("palm", (sd * 0.26, 0.06, 0.84), (0.042, 0.03, 0.055), sock, "hand_" + S)
        for i in range(4):
            fx = sd * 0.26 + (i - 1.5) * 0.016
            c.limb("finger", (fx, 0.07, 0.80), (fx, 0.095, 0.745), 0.012, 0.010, sock, "hand_" + S)
        tx = sd * 0.26 - sd * 0.04
        c.limb("thumb", (tx, 0.05, 0.85), (tx - sd * 0.01, 0.09, 0.80), 0.014, 0.011, sock, "hand_" + S)

    # red de atrapar mariposas (parte de la mano derecha)
    hx, hz = 0.26, 0.84
    c.cylinder("pole", (hx, 0.75, hz), 0.014, 1.5, wood, "hand_R", rot=(rad(90), 0, 0))
    c.cylinder("grip", (hx, 0.10, hz), 0.022, 0.20, leather, "hand_R", rot=(rad(90), 0, 0))
    c.torus("hoop", (hx, 1.62, hz), 0.22, 0.014, ring, "hand_R", rot=(0, rad(90), 0))
    c.sphere("net", (hx, 1.62, hz), (0.008, 0.20, 0.20), mesh_m, "hand_R")

    bones = [
        ("root", (0, 0, 0), (0, 0, 0.1), None),
        ("hips", (0, 0, 0.95), (0, 0, 1.1), "root"),
        ("chest", (0, 0, 1.1), (0, 0, 1.42), "hips"),
        ("neck", (0, 0, 1.42), (0, 0, 1.58), "chest"),
        ("head", (0, 0, 1.58), (0, 0, 1.85), "neck"),
        ("ear_L", (-0.07, 0, 1.80), (-0.11, 0, 1.98), "head"),
        ("ear_R", (0.07, 0, 1.80), (0.11, 0, 1.98), "head"),
        ("tail1", (0, -0.10, 0.95), (0, -0.28, 1.0), "hips"),
        ("tail2", (0, -0.28, 1.0), (0, -0.62, 1.07), "tail1"),
        ("scarf_end", (-0.07, 0.10, 1.50), (-0.07, 0.11, 1.12), "chest"),
        ("upper_arm_L", (-0.21, 0, 1.43), (-0.25, 0, 1.15), "chest"),
        ("upper_arm_R", (0.21, 0, 1.43), (0.25, 0, 1.15), "chest"),
        ("forearm_L", (-0.25, 0, 1.15), (-0.26, 0.03, 0.90), "upper_arm_L"),
        ("forearm_R", (0.25, 0, 1.15), (0.26, 0.03, 0.90), "upper_arm_R"),
        ("hand_L", (-0.26, 0.03, 0.90), (-0.26, 0.09, 0.76), "forearm_L"),
        ("hand_R", (0.26, 0.03, 0.90), (0.26, 0.09, 0.76), "forearm_R"),
        ("thigh_L", (-0.1, 0, 0.95), (-0.1, 0, 0.50), "hips"),
        ("thigh_R", (0.1, 0, 0.95), (0.1, 0, 0.50), "hips"),
        ("shin_L", (-0.1, 0, 0.50), (-0.1, 0, 0.10), "thigh_L"),
        ("shin_R", (0.1, 0, 0.50), (0.1, 0, 0.10), "thigh_R"),
        ("foot_L", (-0.1, 0, 0.10), (-0.1, 0.16, 0.03), "shin_L"),
        ("foot_R", (0.1, 0, 0.10), (0.1, 0.16, 0.03), "shin_R"),
    ]
    c.make_armature(bones)
    c.finish_mesh()
    c.preview("rest")

    X, Z = "X", "Z"
    hold = (0.05, 0.25)   # brazo derecho: sostiene la red hacia adelante

    # idle: respira, parpadeo de orejas, cola y bufanda al viento
    c.begin("idle-loop")
    for f in range(1, 62, 6):
        t = (f - 1) / 60.0 * math.tau
        c.key("chest", f, X, 0.025 * math.sin(t))
        c.key("head", f, X, 0.03 * math.sin(t + 0.6))
        c.key("ear_L", f, X, 0.10 * max(0.0, math.sin(2 * t)))
        c.key("ear_R", f, X, 0.08 * max(0.0, math.sin(2 * t + 1.5)))
        c.key("tail1", f, Z, 0.15 * math.sin(t))
        c.key("tail2", f, Z, 0.25 * math.sin(t + 0.8))
        c.key("scarf_end", f, X, 0.10 * math.sin(t + 1.0))
        c.key("upper_arm_L", f, X, 0.04 * math.sin(t))
        c.key("upper_arm_R", f, X, hold[0] + 0.03 * math.sin(t))
        c.key("forearm_R", f, X, hold[1])
        c.key("forearm_L", f, X, 0.15)
    c.end(61)

    # walk: zancada con flexión de rodilla, balanceo de cadera y cola
    c.begin("walk-loop")
    for f in range(1, 26, 2):
        t = (f - 1) / 24.0 * math.tau
        s_, k_ = math.sin(t), math.cos(t)
        c.key("thigh_L", f, X, 0.55 * s_)
        c.key("thigh_R", f, X, -0.55 * s_)
        c.key("shin_L", f, X, -0.9 * max(0.0, k_))
        c.key("shin_R", f, X, -0.9 * max(0.0, -k_))
        c.key("foot_L", f, X, 0.15 * s_)
        c.key("foot_R", f, X, -0.15 * s_)
        c.key("upper_arm_L", f, X, -0.45 * s_)
        c.key("forearm_L", f, X, 0.35 - 0.15 * s_)
        c.key("upper_arm_R", f, X, hold[0] + 0.12 * s_)
        c.key("forearm_R", f, X, hold[1])
        c.key("hips", f, Z, 0.07 * s_, loc=(0, 0, abs(math.sin(t)) * 0.035))
        c.key("chest", f, Z, -0.08 * s_)
        c.key("head", f, Z, 0.04 * s_)
        c.key("ear_L", f, X, 0.12 * abs(s_))
        c.key("ear_R", f, X, 0.12 * abs(s_))
        c.key("tail1", f, Z, 0.25 * s_)
        c.key("tail2", f, Z, 0.45 * math.sin(t - 0.7))
        c.key("scarf_end", f, X, 0.20 * math.sin(2 * t))
    c.preview("walk", 4)
    c.end(25)

    # swing: la red sube por encima y golpea al frente con giro de torso
    c.begin("swing")
    ua = [(1, hold[0]), (5, 2.4), (7, 2.5), (11, 0.0), (15, -0.1), (19, hold[0])]
    fo = {1: hold[1], 5: 0.3, 7: 0.3, 11: 0.1, 15: 0.2, 19: hold[1]}
    twist = {1: 0.0, 5: 0.25, 7: 0.3, 11: -0.3, 15: -0.2, 19: 0.0}
    for f, a_ in ua:
        c.key("upper_arm_R", f, X, a_)
        c.key("forearm_R", f, X, fo[f])
        c.key("chest", f, Z, twist[f])
        c.key("upper_arm_L", f, X, -0.5 if f in (11, 15) else 0.0)
        c.key("scarf_end", f, X, 0.4 if f in (11, 15) else 0.0)
    c.preview("swing", 11)
    c.end(19)

    c.export()


# =====================================================================
# Canelita: perrita chibi (pelaje caramelo y blanco, overol azul; diseño propio)
# =====================================================================
def build_canelita():
    c = Character("Canelita")
    c.organic = True
    c.voxel = 0.011
    c.decimate = 0.5
    c.keep_separate = {"eye", "shine", "shine2", "nose", "nose_shine", "mouth", "tongue", "brow", "blush",
                       "button", "bib_pocket", "stripe", "sole", "leaf", "leaf2",
                       "pole", "grip", "hoop", "net"}
    rad = math.radians
    fur = c.mat("fur", (0.82, 0.54, 0.26))
    fur_dk = c.mat("fur_dk", (0.62, 0.37, 0.16))
    cream = c.mat("cream", (1.0, 0.95, 0.85))
    inner_ear = c.mat("inner_ear", (1.0, 0.72, 0.70))
    dark = c.mat("dark", (0.10, 0.07, 0.07), rough=0.4)
    white = c.mat("white", (1, 1, 1), rough=0.3)
    pink = c.mat("pink", (1.0, 0.55, 0.62))
    denim = c.mat("denim", (0.35, 0.58, 0.85))
    denim_dk = c.mat("denim_dk", (0.25, 0.45, 0.72))
    coral = c.mat("coral", (1.0, 0.52, 0.42))
    brass = c.mat("brass", (0.95, 0.78, 0.25), rough=0.35)
    leaf = c.mat("leaf", (0.45, 0.78, 0.40))
    sneaker = c.mat("sneaker", (0.98, 0.98, 0.96))
    wood = c.mat("wood", (0.62, 0.44, 0.28))
    ring = c.mat("ring", (0.9, 0.28, 0.28))
    mesh_m = c.mat("net", (1, 1, 1), alpha=0.4)

    # cuerpo con overol: peto con bolsillo, tirantes con botones, short
    c.sphere("body", (0, 0, 0.82), (0.43, 0.36, 0.46), fur, "hips")
    c.sphere("belly", (0, 0.10, 0.90), (0.31, 0.26, 0.31), cream, "chest")
    c.sphere("overall", (0, 0.04, 0.72), (0.45, 0.38, 0.34), denim, "hips")
    c.sphere("bib", (0, 0.15, 0.93), (0.30, 0.20, 0.24), denim_dk, "chest")
    c.sphere("bib_pocket", (0, 0.335, 0.88), (0.12, 0.03, 0.09), denim, "chest")
    for sd in (-1, 1):
        c.sphere("strap", (sd * 0.20, 0.09, 1.10), (0.05, 0.04, 0.15), denim_dk, "chest")
        c.sphere("button", (sd * 0.20, 0.17, 1.0), (0.035, 0.022, 0.035), brass, "chest")
    c.sphere("tail", (0, -0.44, 0.70), (0.12, 0.15, 0.12), fur, "tail")
    c.sphere("tail_tip", (0, -0.53, 0.72), (0.085, 0.09, 0.085), cream, "tail")
    c.torus("scarf", (0, 0.03, 1.06), 0.31, 0.06, coral, "chest")
    c.sphere("scarf_tail", (0.20, 0.28, 0.98), (0.10, 0.04, 0.20), coral, "chest", rot=(0, 0, rad(-12)))

    # cabeza redonda: mejillas blancas, hocico ancho, franja, ojos grandes, orejas paradas
    c.sphere("head", (0, 0, 1.42), (0.47, 0.42, 0.41), fur, "head")
    c.sphere("blaze", (0, 0.34, 1.52), (0.07, 0.06, 0.20), cream, "head")
    c.sphere("muzzle", (0, 0.33, 1.33), (0.23, 0.19, 0.16), cream, "head")
    c.sphere("nose", (0, 0.505, 1.375), (0.07, 0.05, 0.05), dark, "head")
    c.sphere("nose_shine", (0.018, 0.54, 1.39), (0.018, 0.012, 0.012), white, "head")
    c.sphere("mouth", (0, 0.515, 1.295), (0.08, 0.02, 0.012), dark, "head")
    c.sphere("tongue", (0, 0.50, 1.27), (0.042, 0.03, 0.022), pink, "head")
    for sd in (-1, 1):
        side = "L" if sd < 0 else "R"
        c.sphere("cheek", (sd * 0.37, 0.14, 1.32), (0.15, 0.13, 0.13), cream, "head")
        c.sphere("eye", (sd * 0.17, 0.37, 1.49), (0.068, 0.042, 0.095), dark, "head")
        c.sphere("shine", (sd * 0.155, 0.405, 1.525), (0.025, 0.02, 0.025), white, "head")
        c.sphere("shine2", (sd * 0.185, 0.405, 1.46), (0.012, 0.01, 0.012), white, "head")
        c.sphere("brow", (sd * 0.17, 0.35, 1.60), (0.075, 0.025, 0.02), fur_dk, "head", rot=(0, 0, rad(sd * 14)))
        c.sphere("blush", (sd * 0.30, 0.29, 1.39), (0.075, 0.02, 0.05), pink, "head")
        tilt = rad(sd * 14)
        c.cone("ear", (sd * 0.27, -0.02, 1.80), 0.14, 0.36, fur, "ear_" + side, rot=(0, tilt, 0))
        c.cone("ear_in", (sd * 0.27, 0.03, 1.78), 0.085, 0.28, inner_ear, "ear_" + side, rot=(0, tilt, 0))
        # brazos con manga corta, manos con pulgar y nudillos
        c.sphere("arm", (sd * 0.46, 0, 0.86), (0.10, 0.10, 0.24), fur, "arm_" + side)
        c.sphere("sleeve", (sd * 0.46, 0, 1.00), (0.125, 0.125, 0.13), coral, "arm_" + side)
        c.sphere("hand", (sd * 0.46, 0.04, 0.60), (0.105, 0.105, 0.105), cream, "hand_" + side)
        c.sphere("thumb", (sd * 0.53, 0.08, 0.62), (0.04, 0.05, 0.055), cream, "hand_" + side)
        for i in (-1, 0, 1):
            c.sphere("knuckle", (sd * 0.46 + i * 0.045, 0.125, 0.575), (0.036, 0.036, 0.036), cream, "hand_" + side)
        # piernas: short de overol, calcetín y zapatillas blancas con suela coral
        c.sphere("short", (sd * 0.18, 0, 0.40), (0.15, 0.15, 0.13), denim, "leg_" + side)
        c.sphere("leg", (sd * 0.18, 0, 0.27), (0.115, 0.115, 0.17), fur, "leg_" + side)
        c.sphere("sock", (sd * 0.18, 0, 0.17), (0.125, 0.125, 0.07), cream, "leg_" + side)
        c.sphere("shoe", (sd * 0.18, 0.06, 0.085), (0.14, 0.21, 0.085), sneaker, "leg_" + side)
        c.sphere("toe", (sd * 0.18, 0.21, 0.085), (0.105, 0.09, 0.065), sneaker, "leg_" + side)
        c.sphere("stripe", (sd * 0.18, 0.09, 0.11), (0.145, 0.05, 0.02), coral, "leg_" + side)
        c.sphere("sole", (sd * 0.18, 0.07, 0.03), (0.145, 0.23, 0.035), coral, "leg_" + side)
    # pasador de hoja en la cabeza
    c.sphere("leaf", (0.30, 0.27, 1.70), (0.075, 0.025, 0.12), leaf, "head", rot=(0, 0, rad(-35)))
    c.sphere("leaf2", (0.20, 0.31, 1.66), (0.06, 0.022, 0.10), leaf, "head", rot=(0, 0, rad(25)))

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
        ("ear_L", (-0.27, 0, 1.62), (-0.31, 0, 1.97), "head"),
        ("ear_R", (0.27, 0, 1.62), (0.31, 0, 1.97), "head"),
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
        c.key("ear_L", f, X, 0.10 * max(0.0, math.sin(2 * t)))
        c.key("ear_R", f, X, 0.08 * max(0.0, math.sin(2 * t + 1.5)))
        c.key("tail", f, Z, 0.5 * math.sin(2 * t))
        c.key("arm_R", f, X, hold + 0.04 * math.sin(t))
        c.key("arm_L", f, X, 0.05 * math.sin(t))
    c.end(61)

    # walk: piernas y brazos alternados, rebote del cuerpo
    c.begin("walk-loop")
    for f in range(1, 26, 2):
        t = (f - 1) / 24.0 * math.tau
        s_ = math.sin(t)
        c.key("leg_L", f, X, 0.75 * s_)
        c.key("leg_R", f, X, -0.75 * s_)
        c.key("arm_L", f, X, -0.55 * s_)
        c.key("arm_R", f, X, hold + 0.20 * s_)
        c.key("hips", f, loc=(0, 0, abs(math.sin(t)) * 0.05))
        c.key("chest", f, Z, 0.05 * s_)
        c.key("head", f, X, 0.05 * abs(s_))
        c.key("ear_L", f, X, 0.2 * abs(s_))
        c.key("ear_R", f, X, 0.2 * abs(s_))
        c.key("tail", f, Z, 0.7 * s_)
    c.preview("walk", 4)
    c.end(25)

    # swing: la red sube y golpea hacia adelante
    c.begin("swing")
    for f, a_ in [(1, hold), (5, 2.4), (7, 2.5), (11, 0.1), (15, 0.0), (19, hold)]:
        c.key("arm_R", f, X, a_)
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
