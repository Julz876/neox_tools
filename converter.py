import os
import struct
import numpy as np
from pygltflib import GLTF2, Scene, Node, Mesh, Buffer, BufferView, Accessor, Primitive, Attributes, Asset

def readuint8(f):
    return int(struct.unpack('B', f.read(1))[0])

def readuint16(f):
    return int(struct.unpack('H', f.read(2))[0])

def readuint32(f):
    return struct.unpack('I', f.read(4))[0]

def readfloat(f):
    return struct.unpack('f', f.read(4))[0]

def saveobj(model, filename, flip_uv=False):
    if not filename.endswith('.obj'):
        filename += '.obj'

    try:
        with open(filename, 'w', encoding='utf-8') as f:  # Ensure encoding is set for text writing
            f.write(f"o {os.path.basename(filename)}\n")
            print("Started writing OBJ file...")

            # Write vertices
            print(f"Total vertices: {len(model['position'])}")
            for v in model['position']:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")

            # Write normals if available
            if 'normal' in model:
                print(f"Total normals: {len(model['normal'])}")
                for n in model['normal']:
                    f.write(f"vn {n[0]} {n[1]} {n[2]}\n")

            vertex_offset = 0
            face_offset = 0

            # Handle submeshes and write UVs and faces separately
            for i, (mesh_vertex_count, mesh_face_count, _, _) in enumerate(model['mesh']):
                print(f"Processing Submesh {i}: Vertices {mesh_vertex_count}, Faces {mesh_face_count}")
                f.write(f"g Submesh_{i}\n")

                # Write UVs for this submesh
                for uv in model['uv'][vertex_offset:vertex_offset + mesh_vertex_count]:
                    if flip_uv:
                        uv = (uv[0], 1 - uv[1])  # Flip UV on the Y axis
                    f.write(f"vt {uv[0]} {uv[1]}\n")

                # Write faces, adjusting for vertex offset
                for v1, v2, v3 in model['face'][face_offset:face_offset + mesh_face_count]:
                    f.write(f"f {v1 + 1}/{v1 + 1} {v2 + 1}/{v2 + 1} {v3 + 1}/{v3 + 1}\n")

                # Update the offsets for the next submesh
                vertex_offset += mesh_vertex_count
                face_offset += mesh_face_count

            print(f"Total faces: {len(model['face'])}")

            # Write bone information as comments
            if 'bone_name' in model and 'bone_parent' in model:
                f.write("\n# Bone Information\n")
                for i, bone_name in enumerate(model['bone_name']):
                    parent = model['bone_parent'][i]
                    f.write(f"# Bone: {bone_name}, Parent: {parent}\n")

        print(f"OBJ saved with {len(model['face'])} faces and {len(model['bone_name'])} bones.")

    except Exception as e:
        print(f"Failed to save OBJ: {e}")

from pygltflib import Skin

def savegltf(model, filename, flip_uv=False):
    gltf = GLTF2()

    # Buffer data
    buffer_data = bytearray()

    # Vertices, normals, UVs
    vertex_data = np.array(model['position'], dtype=np.float32).tobytes()
    normal_data = np.array(model['normal'], dtype=np.float32).tobytes()
    uv_data = np.array([(uv[0], 1-uv[1]) if flip_uv else uv for uv in model['uv']], dtype=np.float32).tobytes()

    buffer_data.extend(vertex_data)
    buffer_data.extend(normal_data)
    buffer_data.extend(uv_data)

    # Faces
    face_data = np.array([face for sublist in model['face'] for face in sublist], dtype=np.uint16).tobytes()
    buffer_data.extend(face_data)

    # Joints and Weights (Bone data)
    if 'vertex_joint' in model and 'vertex_joint_weight' in model:
        joint_data = np.array(model['vertex_joint'], dtype=np.uint16).tobytes()
        weight_data = np.array(model['vertex_joint_weight'], dtype=np.float32).tobytes()
        buffer_data.extend(joint_data)
        buffer_data.extend(weight_data)
    else:
        joint_data = None
        weight_data = None

    buffer = Buffer()
    buffer.byteLength = len(buffer_data)
    gltf.buffers.append(buffer)

    # Write the buffer data to a binary file
    bin_filename = filename.replace('.gltf', '.bin')
    with open(bin_filename, 'wb') as bin_out:
        bin_out.write(buffer_data)
    buffer.uri = os.path.basename(bin_filename)

    # Create buffer views
    offset = 0
    buffer_view_position = BufferView(buffer=0, byteOffset=offset, byteLength=len(vertex_data), target=34962)
    offset += len(vertex_data)
    buffer_view_normal = BufferView(buffer=0, byteOffset=offset, byteLength=len(normal_data), target=34962)
    offset += len(normal_data)
    buffer_view_uv = BufferView(buffer=0, byteOffset=offset, byteLength=len(uv_data), target=34962)
    offset += len(uv_data)
    buffer_view_index = BufferView(buffer=0, byteOffset=offset, byteLength=len(face_data), target=34963)
    offset += len(face_data)

    gltf.bufferViews.extend([buffer_view_position, buffer_view_normal, buffer_view_uv, buffer_view_index])

    if joint_data and weight_data:
        buffer_view_joint = BufferView(buffer=0, byteOffset=offset, byteLength=len(joint_data), target=34962)
        offset += len(joint_data)
        buffer_view_weight = BufferView(buffer=0, byteOffset=offset, byteLength=len(weight_data), target=34962)
        offset += len(weight_data)
        gltf.bufferViews.extend([buffer_view_joint, buffer_view_weight])

    # Create accessors
    accessor_position = Accessor(bufferView=0, componentType=5126, count=len(model['position']), type="VEC3")
    accessor_normal = Accessor(bufferView=1, componentType=5126, count=len(model['normal']), type="VEC3")
    accessor_uv = Accessor(bufferView=2, componentType=5126, count=len(model['uv']), type="VEC2")
    accessor_index = Accessor(bufferView=3, componentType=5123, count=len(model['face']) * 3, type="SCALAR")
    
    gltf.accessors.extend([accessor_position, accessor_normal, accessor_uv, accessor_index])

    if joint_data and weight_data:
        accessor_joint = Accessor(bufferView=4, componentType=5121, count=len(model['vertex_joint']), type="VEC4")
        accessor_weight = Accessor(bufferView=5, componentType=5126, count=len(model['vertex_joint_weight']), type="VEC4")
        gltf.accessors.extend([accessor_joint, accessor_weight])

    # Define mesh attributes and primitives
    attributes = Attributes(POSITION=0, NORMAL=1, TEXCOORD_0=2)

    if joint_data and weight_data:
        attributes.JOINTS_0 = 4
        attributes.WEIGHTS_0 = 5

    primitive = Primitive(attributes=attributes, indices=3, mode=4)
    mesh = Mesh(primitives=[primitive])
    gltf.meshes.append(mesh)

    node = Node(mesh=0)
    gltf.nodes.append(node)

    scene = Scene(nodes=[0])
    gltf.scenes.append(scene)

    gltf.asset = Asset(version="2.0")
    gltf.scene = 0

    # Add skins if bones exist
    if joint_data and weight_data:
        joints = list(range(len(model['bone_name'])))
        gltf.skins.append(Skin(joints=joints))

    gltf.save(filename)
    print(f"GLTF saved to: {filename}")

def parse_mesh(path):
    model = {}
    try:
        with open(path, 'rb') as f:
            _magic_number = f.read(8)
            model['bone_exist'] = readuint32(f)
            model['mesh'] = []

            if model['bone_exist']:
                bone_count = readuint16(f)
                parent_nodes = []
                for _ in range(bone_count):
                    parent_node = readuint8(f)
                    if parent_node == 255:
                        parent_node = -1
                    parent_nodes.append(parent_node)
                model['bone_parent'] = parent_nodes

                bone_names = []
                for _ in range(bone_count):
                    bone_name = f.read(32)
                    bone_name = bone_name.decode('latin-1').replace('\0', '').replace(' ', '_')
                    bone_names.append(bone_name)
                model['bone_name'] = bone_names

                model['bone_original_matrix'] = []
                for i in range(bone_count):
                    matrix = [readfloat(f) for _ in range(16)]
                    matrix = np.array(matrix).reshape(4, 4)
                    model['bone_original_matrix'].append(matrix)

                if len(list(filter(lambda x: x == -1, parent_nodes))) > 1:
                    num = len(model['bone_parent'])
                    model['bone_parent'] = list(map(lambda x: num if x == -1 else x, model['bone_parent']))
                    model['bone_parent'].append(-1)
                    model['bone_name'].append('dummy_root')
                    model['bone_original_matrix'].append(np.identity(4))

                _flag = readuint8(f)  # 00
                assert _flag == 0

            _offset = readuint32(f)
            while True:
                flag = readuint16(f)
                if flag == 1:
                    break
                f.seek(-2, 1)
                mesh_vertex_count = readuint32(f)
                mesh_face_count = readuint32(f)
                uv_layers = readuint8(f)
                color_len = readuint8(f)

                model['mesh'].append((mesh_vertex_count, mesh_face_count, uv_layers, color_len))

            vertex_count = readuint32(f)
            face_count = readuint32(f)

            model['position'] = []
            for _ in range(vertex_count):
                x = readfloat(f)
                y = readfloat(f)
                z = readfloat(f)
                model['position'].append((x, y, z))

            model['normal'] = []
            for _ in range(vertex_count):
                x = readfloat(f)
                y = readfloat(f)
                z = readfloat(f)
                model['normal'].append((x, y, z))

            _flag = readuint16(f)
            if _flag:
                f.seek(vertex_count * 12, 1)

            model['face'] = []
            for _ in range(face_count):
                v1 = readuint16(f)
                v2 = readuint16(f)
                v3 = readuint16(f)
                model['face'].append((v1, v2, v3))

            model['uv'] = []
            for mesh_vertex_count, _, uv_layers, _ in model['mesh']:
                if uv_layers > 0:
                    for _ in range(mesh_vertex_count):
                        u = readfloat(f)
                        v = readfloat(f)
                        model['uv'].append((u, v))
                    f.read(mesh_vertex_count * 8 * (uv_layers - 1))
                else:
                    for _ in range(mesh_vertex_count):
                        u = 0.0
                        v = 0.0
                        model['uv'].append((u, v))

            for mesh_vertex_count, _, _, color_len in model['mesh']:
                f.read(mesh_vertex_count * 4 * color_len)

            if model['bone_exist']:
                model['vertex_joint'] = []
                for _ in range(vertex_count):
                    vertex_joints = [readuint8(f) for _ in range(4)]
                    model['vertex_joint'].append(vertex_joints)

                model['vertex_joint_weight'] = []
                for _ in range(vertex_count):
                    vertex_joint_weights = [readfloat(f) for _ in range(4)]
                    model['vertex_joint_weight'].append(vertex_joint_weights)

    except Exception as e:
        print(f"Error parsing bones: {e}")
        return None

    return model

