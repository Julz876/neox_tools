import ctypes, zlib, zstandard, lz4.block, zipfile, os, platform
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def decompression_algorithm(zflag=0):
    if zflag == 0:
        return "NONE"
    elif zflag == 1:
        return "ZLIB"
    elif zflag == 2:
        return "LZ4"
    elif zflag == 3:
        return "ZSTANDARD"
    raise Exception("ERROR IN DECOMPRESSION ALGORITHM")

def init_rotor():
    key = b'sixteen byte key'  # Replace this with the appropriate key
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor

def _reverse_string(s):
    l = list(s)
    l = list(map(lambda x: x ^ 154, l[0:128])) + l[128:]
    l.reverse()
    return bytes(l)

def nxs_unpack(data):
    print(f"Operating System: {platform.system()}")
    print(f"Architecture: {platform.architecture()}")

    wrapped_key = ctypes.create_string_buffer(4)
    data_in = ctypes.create_string_buffer(data[20:])

    if os.name == "posix":
        try:
            liblinux = ctypes.CDLL("./dll/libpubdecrypt.so")
        except OSError as e:
            raise Exception(f"Error loading DLL on POSIX system: {e}")
        returning = liblinux.public_decrypt(data_in, wrapped_key)
    elif os.name == "nt":
        try:
            libwindows = ctypes.CDLL('./dll/libpubdecrypt.dll')
        except OSError as e:
            raise Exception(f"Error loading DLL on Windows: {e}")
        returning = libwindows.public_decrypt(data_in, wrapped_key)
    else:
        raise Exception("Unsupported operating system.")

    ephemeral_key = int.from_bytes(wrapped_key.raw, "little")

    decrypted = []

    for i, x in enumerate(data[20 + 128:]):
        val = x ^ ((ephemeral_key >> (i % 4 * 8)) & 0xff)
        if i % 4 == 3:
            ror = (ephemeral_key >> 19) | ((ephemeral_key << (32 - 19)) & 0xFFFFFFFF)
            ephemeral_key = (ror + ((ror << 2) & 0xFFFFFFFF) + 0xE6546B64) & 0xFFFFFFFF
        decrypted.append(val)

    decrypted = bytes(decrypted)
    return decrypted

def zflag_decompress(flag, data, origlength=0):
    if flag == 1:
        return zlib.decompress(data, bufsize=origlength)
    elif flag == 2:
        return lz4.block.decompress(data, uncompressed_size=origlength)
    elif flag == 3:
        return zstandard.ZstdDecompressor().decompress(data)
    return data

def special_decompress(flag, data):
    if flag == "rot":
        rotor = init_rotor()
        return _reverse_string(zlib.decompress(rotor.update(data)))
    elif flag == "nxs3":
        buf = nxs_unpack(data)
        return lz4.block.decompress(buf, int.from_bytes(data[16:20], "little"))
    return data
