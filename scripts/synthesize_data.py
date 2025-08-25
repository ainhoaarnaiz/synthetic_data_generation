"""Blender script used to generate the synthetic dataset.
"""

import bpy
import bpy_extras.object_utils
import mathutils
import chess
import numpy as np 
from pathlib import Path
import typing
import json
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
CAMERA_STATIC = False
LIGHT_STATIC = True
MIN_BOARD_CORNER_PADDING = 25  # pixels
CAMERA_DISTANCE = 15
BOARD_SIZE = 16.0  # meters
BOARD_MARGIN = 0.75  # meters (on each side)
SQUARE_LENGTH = (BOARD_SIZE - 2 * BOARD_MARGIN) / 8
COLLECTION_NAME = "Chess position"


def point_to(obj, focus: mathutils.Vector, roll: float = 0):
    # Based on https://blender.stackexchange.com/a/127440
    loc = obj.location
    direction = focus - loc
    quat = direction.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    roll_matrix = mathutils.Matrix.Rotation(roll, 4, "Z")
    loc = loc.to_tuple()
    obj.matrix_world = quat @ roll_matrix
    obj.location = loc


def setup_camera(color: chess.Color) -> dict:
    camera = bpy.context.scene.camera
    # Constrain camera to always be above the board, looking directly at center
    board_center = mathutils.Vector((0., 0., 0.))
    # Randomize azimuth, radius and height
    azimuth = np.random.uniform(0, 360)
    # Camera radius: min 4, max 10 (in SQUARE_LENGTH units)
    radius = np.random.uniform(4 * SQUARE_LENGTH, 10 * SQUARE_LENGTH)
    x = radius * np.cos(np.deg2rad(azimuth))
    y = radius * np.sin(np.deg2rad(azimuth))
    # Camera height: min 8, max 14 (in SQUARE_LENGTH units)
    z = np.random.uniform(8 * SQUARE_LENGTH, 14 * SQUARE_LENGTH)
    loc = mathutils.Vector((x, y, z))
    camera.location = loc
    point_to(camera, board_center)
    bpy.context.view_layer.update()
    return {
        "azimuth": azimuth,
        "location": loc.to_tuple()
    }


def setup_spotlight(light) -> dict:
    # Constrain spotlights to be above the board, always pointing down
    board_center = mathutils.Vector((0., 0., 0.))
    # Randomize azimuth, radius and height
    angle_xy_plane = np.random.uniform(0, 360)
    radius = np.random.uniform(7 * SQUARE_LENGTH, 11 * SQUARE_LENGTH)
    x = radius * np.cos(np.deg2rad(angle_xy_plane))
    y = radius * np.sin(np.deg2rad(angle_xy_plane))
    z = np.random.uniform(8 * SQUARE_LENGTH, 14 * SQUARE_LENGTH)
    location = mathutils.Vector((x, y, z))
    light.location = location
    point_to(light, board_center)
    # Set spotlight power to 5000W
    light.data.energy = 5000
    return {
        "xy_angle": angle_xy_plane,
        "focus": board_center.to_tuple(),
        "location": location.to_tuple(),
        "power": light.data.energy
    }


def setup_lighting() -> dict:
    flash = bpy.data.objects["Camera flash light"]
    spot1 = bpy.data.objects["Spot 1"]
    spot2 = bpy.data.objects["Spot 2"]

    # Randomly choose mode, but always keep at least one light active
    if np.random.rand() < 0.5:
        # Flash mode
        visibilities = {flash: True, spot1: False, spot2: False}
        mode = "flash"
    else:
        # Spotlights mode
        visibilities = {flash: False, spot1: True, spot2: True}
        mode = "spotlights"

    # Place flash above board center, always pointing down
    board_center = mathutils.Vector((0., 0., 0.))
    flash.location = mathutils.Vector((0., 0., np.random.uniform(12, 16) * SQUARE_LENGTH))
    point_to(flash, board_center)
    # Set flash power to 5000W
    flash.data.energy = 5000

    for obj, visibility in visibilities.items():
        obj.hide_render = not visibility

    return {
        "mode": mode,
        "flash": {
            "active": not flash.hide_render,
            "power": flash.data.energy
        },
        **{
            key: {
                "active": not obj.hide_render,
                **setup_spotlight(obj)
            } for (key, obj) in {"spot1": spot1, "spot2": spot2}.items()
        }
    }


def add_piece(piece, square, collection):
    color = {
        chess.WHITE: "White",
        chess.BLACK: "Black"
    }[piece.color]
    piece_name = {
        chess.PAWN: "Pawn",
        chess.KNIGHT: "Knight",
        chess.BISHOP: "Bishop",
        chess.ROOK: "Rook",
        chess.QUEEN: "Queen",
        chess.KING: "King"
    }[piece.piece_type]
    name = color + " " + piece_name
    print(f"Placing piece: {name} on square: {chess.square_name(square)}")

    # Calculate file and rank (Blender X = file, Y = rank)
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    # Center board at origin
    # Place squares with margin offset, center board at origin
    x = -BOARD_SIZE / 2 + BOARD_MARGIN + (file + 0.5) * SQUARE_LENGTH
    y = -BOARD_SIZE / 2 + BOARD_MARGIN + (rank + 0.5) * SQUARE_LENGTH
    location = mathutils.Vector((x, y, 0))
    rotation = mathutils.Euler((0., 0., -1.5708))  # -90 degrees in radians
    print(f"Placing {name} at Blender coords: {location}")

    # Print available object names for debugging
    if name not in bpy.data.objects:
        print(f"WARNING: Object '{name}' not found in Blender objects!")
        print("Available objects:", list(bpy.data.objects.keys()))

    src_obj = bpy.data.objects.get(name)
    if src_obj is None:
        print(f"ERROR: Could not find source object for {name}. Skipping piece.")
        return None
    obj = src_obj.copy()
    obj.data = src_obj.data.copy()
    obj.animation_data_clear()
    obj.location = location
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    return obj


def render_board(board, turn, output_file):
    scene = bpy.context.scene

    # Setup rendering
    scene.render.engine = "CYCLES"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_file)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800

    # Randomize camera and lighting
    if CAMERA_STATIC == False:
        camera_params = setup_camera(turn)
    if LIGHT_STATIC == False:
        lighting_params = setup_lighting()
    corner_coords = get_corner_coordinates(scene)
    print("corner_coords:", corner_coords)

    if COLLECTION_NAME not in bpy.data.collections:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        scene.collection.children.link(collection)
    collection = bpy.data.collections[COLLECTION_NAME]

    # Remove all objects from the collection
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    piece_data = []
    for square, piece in board.piece_map().items():
        obj = add_piece(piece, square, collection)
        piece_data.append({
            "piece": piece.symbol(),
            "square": chess.square_name(square),
            "box": get_bounding_box(scene, obj)
        })

    # Write data output
    data = {
        "fen": board.board_fen(),
        "white_turn": turn,
        "corners": corner_coords,
        "pieces": piece_data
    }
    output_path = Path(output_file)
    with (output_path.parent / (output_path.stem + ".json")).open("w") as f:
        json.dump(data, f)

    # Perform the rendering
    print("Starting render for", output_file)
    bpy.ops.render.render(write_still=1)
    print("Finished render for", output_file)


def get_corner_coordinates(scene) -> typing.List[typing.List[int]]:
    corner_points = np.array([[-1., -1],
                              [-1, 1],
                              [1, 1],
                              [1, -1]]) * 4 * SQUARE_LENGTH
    corner_points = np.concatenate((corner_points, np.zeros((4, 1))), axis=-1)
    sr = bpy.context.scene.render

    def _get_coords():
        for corner in corner_points:
            x, y, z = bpy_extras.object_utils.world_to_camera_view(
                scene, scene.camera, mathutils.Vector(corner)).to_tuple()
            y = 1. - y
            x *= sr.resolution_x * sr.resolution_percentage * .01
            y *= sr.resolution_y * sr.resolution_percentage * .01
            x, y = round(x), round(y)

            if not (MIN_BOARD_CORNER_PADDING <= x <= sr.resolution_x - MIN_BOARD_CORNER_PADDING) or \
                    not (MIN_BOARD_CORNER_PADDING <= y <= sr.resolution_y - MIN_BOARD_CORNER_PADDING):
                raise ValueError

            yield x, y
    try:
        return list(_get_coords())
    except ValueError:
        return None


def get_bounding_box(scene, obj) -> typing.Tuple[int, int, int, int]:
    """Obtain the bounding box of an object.

    Args:
        scene: the scene
        obj: the object

    Returns:
        typing.Tuple[int, int, int, int]: the box coordinates in the form (x, y, width, height)
    """
    # adapted from https://blender.stackexchange.com/a/158236
    cam_ob = scene.camera
    mat = cam_ob.matrix_world.normalized().inverted()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = obj.evaluated_get(depsgraph)
    me = mesh_eval.to_mesh()
    me.transform(obj.matrix_world)
    me.transform(mat)

    camera = cam_ob.data

    def _get_coords():
        frame = [-v for v in camera.view_frame(scene=scene)[:3]]
        for v in me.vertices:
            co_local = v.co
            z = -co_local.z

            if z <= 0.0:
                print("===========", z, obj, file=sys.stderr)
                continue
            else:
                frame = [(v / (v.z / z)) for v in frame]

            min_x, max_x = frame[1].x, frame[2].x
            min_y, max_y = frame[0].y, frame[1].y

            x = (co_local.x - min_x) / (max_x - min_x)
            y = (co_local.y - min_y) / (max_y - min_y)

            yield x, y

    xs, ys = np.array(list(_get_coords())).T

    min_x = np.clip(min(xs), 0.0, 1.0)
    max_x = np.clip(max(xs), 0.0, 1.0)
    min_y = np.clip(min(ys), 0.0, 1.0)
    max_y = np.clip(max(ys), 0.0, 1.0)

    mesh_eval.to_mesh_clear()

    r = scene.render
    fac = r.resolution_percentage * 0.01
    dim_x = r.resolution_x * fac
    dim_y = r.resolution_y * fac

    width = round((max_x - min_x) * dim_x)
    height = round((max_y - min_y) * dim_y)
    if width == 0 or height == 0:
        print(f"WARNING: Bounding box for {obj.name} is zero-sized. Skipping.")
        return None

    return (
        int(round(min_x * dim_x)),
        int(round(dim_y - max_y * dim_y)),
        int(round((max_x - min_x) * dim_x)),
        int(round((max_y - min_y) * dim_y))
    )


if __name__ == "__main__":
    fen_path = os.path.join(script_dir, "..", "data", "fens.txt")
    with open(fen_path, "r") as f:
        for i, fen in enumerate(map(str.strip, f)):
            print(f"FEN #{i}", file=sys.stderr)
            print("Raw line from file:", fen)
            turn, *fen_str = fen
            fen_str = "".join(fen_str)
            print("FEN string used:", fen_str)
            filename = os.path.join(script_dir, "..", "render", f"{i:04d}.png")
            board = chess.Board(fen_str)
            print("hola")
            render_board(board, turn == "W", filename)
