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


def saveobj(model, filename):
    if not filename.endswith('.obj'):
        filename += '.obj'

    try:
        with open(filename, 'w') as f:
            f.write(f"o {os.path.basename(filename)}\n")

            # Initialize offset values
            vertex_offset = 0
            face_offset = 0

            for submesh_index, (mesh_vertex_count, mesh_face_count, _, _) in enumerate(model['mesh']):
                f.write(f"g Submesh_{submesh_index}\n")

                # Write vertices
                for v in model['position'][vertex_offset:vertex_offset + mesh_vertex_count]:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")

                # Write normals
                if 'normal' in model:
                    for n in model['normal'][vertex_offset:vertex_offset + mesh_vertex_count]:
                        f.write(f"vn {n[0]} {n[1]} {n[2]}\n")

                # Write UVs
                if 'uv' in model:
                    for uv in model['uv'][vertex_offset:vertex_offset + mesh_vertex_count]:
                        f.write(f"vt {uv[0]} {uv[1]}\n")

                # Write faces
                for v1, v2, v3 in model['face'][face_offset:face_offset + mesh_face_count]:
                    f.write(f"f {v1 + 1}/{v1 + 1} {v2 + 1}/{v2 + 1} {v3 + 1}/{v3 + 1}\n")

                # Update the offset for the next submesh
                vertex_offset += mesh_vertex_count
                face_offset += mesh_face_count

            print(f"OBJ saved with {len(model['face'])} faces and {len(model['bone_name']) if 'bone_name' in model else 0} bones.")

    except Exception as e:
        print(f"Failed to save OBJ: {e}")


def savegltf(model, filename):
    gltf = GLTF2()
    buffer_data = bytearray()

    # Vertices
    if 'position' in model:
        vertex_data = np.array(model['position'], dtype=np.float32).tobytes()
        buffer_data.extend(vertex_data)

    # Normals
    if 'normal' in model:
        normal_data = np.array(model['normal'], dtype=np.float32).tobytes()
        buffer_data.extend(normal_data)

    # UVs
    if 'uv' in model:
        uv_data = np.array(model['uv'], dtype=np.float32).tobytes()
        buffer_data.extend(uv_data)

    # Faces (Indices)
    if 'face' in model:
        face_data = np.array([f for sublist in model['face'] for f in sublist], dtype=np.uint16).tobytes()
        buffer_data.extend(face_data)

    # Create buffer and buffer views
    buffer = Buffer()
    buffer.byteLength = len(buffer_data)
    gltf.buffers.append(buffer)
    
    # Vertices buffer view
    if 'position' in model:
        buffer_view = BufferView(buffer=0, byteOffset=0, byteLength=len(vertex_data), target=34962)  # ARRAY_BUFFER
        gltf.bufferViews.append(buffer_view)

    # Normals buffer view
    if 'normal' in model:
        buffer_view = BufferView(buffer=0, byteOffset=len(vertex_data), byteLength=len(normal_data), target=34962)  # ARRAY_BUFFER
        gltf.bufferViews.append(buffer_view)

    # UVs buffer view
    if 'uv' in model:
        buffer_view = BufferView(buffer=0, byteOffset=len(vertex_data) + len(normal_data), byteLength=len(uv_data), target=34962)  # ARRAY_BUFFER
        gltf.bufferViews.append(buffer_view)

    # Indices buffer view
    if 'face' in model:
        buffer_view = BufferView(buffer=0, byteOffset=len(vertex_data) + len(normal_data) + len(uv_data), byteLength=len(face_data), target=34963)  # ELEMENT_ARRAY_BUFFER
        gltf.bufferViews.append(buffer_view)

    buffer.uri = filename + ".bin"
    with open(buffer.uri, 'wb') as bin_file:
        bin_file.write(buffer_data)

    # Define mesh attributes and primitives
    attributes = Attributes()
    if 'position' in model:
        attributes.POSITION = len(gltf.accessors)
        accessor = Accessor(bufferView=0, componentType=5126, count=len(model['position']), type="VEC3")  # FLOAT
        gltf.accessors.append(accessor)

    if 'normal' in model:
        attributes.NORMAL = len(gltf.accessors)
        accessor = Accessor(bufferView=1, componentType=5126, count=len(model['normal']), type="VEC3")  # FLOAT
        gltf.accessors.append(accessor)

    if 'uv' in model:
        attributes.TEXCOORD_0 = len(gltf.accessors)
        accessor = Accessor(bufferView=2, componentType=5126, count=len(model['uv']), type="VEC2")  # FLOAT
        gltf.accessors.append(accessor)

    if 'face' in model:
        primitive = Primitive(attributes=attributes, indices=len(gltf.accessors), mode=4)  # TRIANGLES
        accessor = Accessor(bufferView=3, componentType=5123, count=len(model['face']) * 3, type="SCALAR")  # UNSIGNED_SHORT
        gltf.accessors.append(accessor)
        mesh = Mesh(primitives=[primitive])
        gltf.meshes.append(mesh)

    # Define node and scene
    node = Node(mesh=len(gltf.meshes) - 1)
    gltf.nodes.append(node)
    scene = Scene(nodes=[0])
    gltf.scenes.append(scene)

    gltf.asset = Asset(version="2.0")
    gltf.scene = 0
    gltf.save(filename)
    print(f"GLTF saved to: {filename}")


def parse_mesh(path):
    model = {}
    with open(path, 'rb') as f:
        _magic_number = f.read(8)
        model['bone_exist'] = readuint32(f)
        model['mesh'] = []

        if model['bone_exist']:
            if model['bone_exist'] > 1:
                count = readuint8(f)
                f.read(2)
                f.read(count * 4)
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
                bone_name = bone_name.decode().replace('\0', '').replace(' ', '_')
                bone_names.append(bone_name)
            model['bone_name'] = bone_names

            bone_extra_info = readuint8(f)
            if bone_extra_info:
                for _ in range(bone_count):
                    f.read(28)

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

            _flag = readuint8(f)
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

    return model
