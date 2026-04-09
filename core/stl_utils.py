import os
import struct

def validate_stl(filepath):
    try:
        sz = os.path.getsize(filepath)
        if sz < 84:
            return False, "El archivo es demasiado pequeño."
        with open(filepath, 'rb') as f:
            header = f.read(80)
            if b'solid ' in header[:10]:
                return True, "ASCII STL Detectado"
            tris = int.from_bytes(f.read(4), byteorder='little')
            expected = 84 + (tris * 50)
            if sz == expected:
                return True, "Binario STL Válido"
            return False, f"STL Incompleto/Roto: Pesa {sz}B, Motor exige {expected}B."
    except Exception as e:
        return False, f"Error lectura: {e}"

def analyze_stl(filepath):
    try:
        with open(filepath, 'rb') as f:
            if b'solid ' in f.read(80)[:10]:
                return None
            f.seek(80)
            tri_count = int.from_bytes(f.read(4), byteorder='little')
            min_x = min_y = min_z = float('inf')
            max_x = max_y = max_z = float('-inf')
            volume = 0.0
            for _ in range(tri_count):
                data = f.read(50)
                if len(data) < 50:
                    break
                v1 = struct.unpack('<3f', data[12:24])
                v2 = struct.unpack('<3f', data[24:36])
                v3 = struct.unpack('<3f', data[36:48])
                for v in (v1, v2, v3):
                    if v[0] < min_x: min_x = v[0]
                    if v[0] > max_x: max_x = v[0]
                    if v[1] < min_y: min_y = v[1]
                    if v[1] > max_y: max_y = v[1]
                    if v[2] < min_z: min_z = v[2]
                    if v[2] > max_z: max_z = v[2]
                v321 = v3[0]*v2[1]*v1[2]; v231 = v2[0]*v3[1]*v1[2]; v312 = v3[0]*v1[1]*v2[2]
                v132 = v1[0]*v3[1]*v2[2]; v213 = v2[0]*v1[1]*v3[2]; v123 = v1[0]*v2[1]*v3[2]
                volume += (1.0/6.0)*(-v321 + v231 + v312 - v132 - v213 + v123)
            vol_cm3 = abs(volume) / 1000.0
            weight_pla = vol_cm3 * 1.24
            return {
                "dx": round(max_x - min_x, 2),
                "dy": round(max_y - min_y, 2),
                "dz": round(max_z - min_z, 2),
                "vol_cm3": round(vol_cm3, 2),
                "weight_g": round(weight_pla, 2)
            }
    except:
        return None

def convert_stl_to_obj(stl_path, obj_path):
    try:
        with open(stl_path, 'rb') as f:
            f.read(80)
            tris = int.from_bytes(f.read(4), 'little')
            with open(obj_path, 'w') as out:
                out.write("# NEXUS CAD Export\no Nexus_Mesh\n")
                v_idx = 1
                for _ in range(tris):
                    data = f.read(50)
                    if len(data) < 50:
                        break
                    v1 = struct.unpack('<3f', data[12:24])
                    v2 = struct.unpack('<3f', data[24:36])
                    v3 = struct.unpack('<3f', data[36:48])
                    out.write(f"v {v1[0]} {v1[1]} {v1[2]}\nv {v2[0]} {v2[1]} {v2[2]}\nv {v3[0]} {v3[1]} {v3[2]}\nf {v_idx} {v_idx+1} {v_idx+2}\n")
                    v_idx += 3
        return True, "Convertido exitosamente."
    except Exception as e:
        return False, str(e)

def get_stl_hash():
    from core.constants import EXPORT_DIR
    path = os.path.join(EXPORT_DIR, "imported.stl")
    if os.path.exists(path):
        try:
            sz = os.path.getsize(path)
            if sz > 84:
                return f"{os.path.getmtime(path)}_{sz}"
        except:
            pass
    return ""
