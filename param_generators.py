# param_generators.py
# Módulo de Geometría Procedural NEXUS CAD v21.1

def get_stl_base(sc, tx, ty, tz):
    return f"  var sc = {sc/100.0}; var tx = {tx}; var ty = {ty}; var tz = {tz};\n  var dron = null;\n  if (typeof IMPORTED_STL !== 'undefined') {{ var parts = Array.isArray(IMPORTED_STL) ? IMPORTED_STL : [IMPORTED_STL]; for(var i=0; i<parts.length; i++) {{ var p = parts[i]; if(p && p.polygons && typeof p.scale !== 'function') {{ try {{ p = CSG.fromPolygons(p.polygons); }} catch(e) {{}} }} if(p && typeof p.union === 'function') {{ if(!dron) dron = p; else dron = dron.union(p); }} }} }}\n  if(!dron || typeof dron.union !== 'function') {{ return CSG.cube({{radius:[0.01, 0.01, 0.01]}}); }}\n  dron = UTILS.scale(dron, [sc, sc, sc]); dron = UTILS.trans(dron, [tx, ty, tz]);\n"

def get_code(h, p):
    code = "function main() {\n"
    
    # -----------------------------------------
    # 1. BOCETOS Y TEXTOS
    # -----------------------------------------
    if h == "sketcher":
        code += f"  var h_ext = {p['sketch_h']};\n  var raw_pts = `{p['sketch_pts'].replace(chr(10), '\\n')}`;\n  var lines = raw_pts.split('\\n'); var pts = [];\n  for(var i=0; i<lines.length; i++) {{ var str = lines[i].replace(/[\\[\\]]/g, '').trim(); var coords = str.split(/[,;|\\t ]+/); var coords_filtered = coords.filter(x => x !== ''); if(coords_filtered.length >= 2) pts.push([parseFloat(coords_filtered[0]), parseFloat(coords_filtered[1])]); }}\n  if(pts.length < 3) return CSG.cube({{radius:[0.01,0.01,0.01]}});\n  try {{ return UTILS.mat(CAG.fromPoints(pts).extrude({{offset: [0, 0, h_ext]}})); }} catch(e) {{ return CSG.cube({{radius:[5,5,5]}}); }}\n}}"
    
    elif h == "texto":
        txt_input = p['txt_input'].upper()[:15]; estilo = p['txt_estilo']; base = p['txt_base']; grabado = p['txt_grabado']
        if not txt_input: txt_input = " "
        code += f"  var texto = \"{txt_input}\"; var h = GH;\n"
        code += f"  var font = {{ 'A':[14,17,31,17,17], 'B':[30,17,30,17,30], 'C':[14,17,16,17,14], 'D':[30,17,17,17,30], 'E':[31,16,30,16,31], 'F':[31,16,30,16,16], 'G':[14,17,23,17,14], 'H':[17,17,31,17,17], 'I':[14,4,4,4,14], 'J':[7,2,2,18,12], 'K':[17,18,28,18,17], 'L':[16,16,16,16,31], 'M':[17,27,21,17,17], 'N':[17,25,21,19,17], 'O':[14,17,17,17,14], 'P':[30,17,30,16,16], 'Q':[14,17,21,18,13], 'R':[30,17,30,18,17], 'S':[14,16,14,1,14], 'T':[31,4,4,4,4], 'U':[17,17,17,17,14], 'V':[17,17,17,10,4], 'W':[17,17,21,27,17], 'X':[17,10,4,10,17], 'Y':[17,10,4,4,4], 'Z':[31,2,4,8,31], ' ':[0,0,0,0,0], '0':[14,17,17,17,14], '1':[4,12,4,4,14], '2':[14,1,14,16,31], '3':[14,1,14,1,14], '4':[18,18,31,2,2], '5':[31,16,14,1,14], '6':[14,16,30,17,14], '7':[31,1,2,4,8], '8':[14,17,14,17,14], '9':[14,17,15,1,14] }};\n"
        z_start = "h/2" if not grabado else "h - 1"; h_letra = "h/2" if not grabado else "h+2"
        if "Voxel" in estilo:
            es_grueso = "1.1" if "Grueso" in estilo else "2.1"
            code += f"  var pText = null; var vSize = 2; var charWidth = 6 * vSize;\n  for(var i=0; i<texto.length; i++) {{ var cMat = font[texto[i]] || font[' ']; var offX = i * charWidth; for(var r=0; r<5; r++) {{ for(var c=0; c<5; c++) {{ if ((cMat[r] >> (4 - c)) & 1) {{ var vox = CSG.cube({{center:[offX+(c*vSize), (4-r)*vSize, {z_start}], radius:[vSize/{es_grueso}, vSize/{es_grueso}, {h_letra}/2]}}); if(!pText) pText = vox; else pText = pText.union(vox); }} }} }} }}\n  var totalL = Math.max(texto.length * charWidth, 10);\n"
        elif estilo == "Braille":
            rad_braille = "1.5" if not grabado else "1.8"
            code += f"  var braille = {{ 'A':[1], 'B':[1,2], 'C':[1,4], 'D':[1,4,5], 'E':[1,5], 'F':[1,2,4], 'G':[1,2,4,5], 'H':[1,2,5], 'I':[2,4], 'J':[2,4,5], 'K':[1,3], 'L':[1,2,3], 'M':[1,3,4], 'N':[1,3,4,5], 'O':[1,3,5], 'P':[1,2,3,4], 'Q':[1,2,3,4,5], 'R':[1,2,3,5], 'S':[2,3,4], 'T':[2,3,4,5], 'U':[1,3,6], 'V':[1,2,3,6], 'W':[2,4,5,6], 'X':[1,3,4,6], 'Y':[1,3,4,5,6], 'Z':[1,3,5,6], ' ':[0] }};\n  var pText = null; var stepX = 4; var stepY = 4; var charWidth = 10;\n  for(var i=0; i<texto.length; i++) {{ var dots = braille[texto[i]] || [1]; var offX = i * charWidth; for(var d=0; d<dots.length; d++) {{ var p = dots[d]; if (p === 0) continue; var cx = (p>3) ? stepX : 0; var cy = ((p-1)%3 === 0) ? stepY*2 : (((p-1)%3 === 1) ? stepY : 0); var domo = CSG.sphere({{center:[offX+cx, cy, {z_start}], radius:{rad_braille}, resolution:16}}); if(!pText) pText = domo; else pText = pText.union(domo); }} }}\n  var totalL = Math.max(texto.length * charWidth, 10);\n"
        code += "  if (!pText) pText = CSG.cube({center:[0,0,0], radius:[0.01, 0.01, 0.01]});\n  var baseObj = null;\n"
        if base == "Llavero (Anilla)": code += "  var bc = CSG.cube({center:[(totalL/2)-3, 3, h/4], radius:[(totalL/2)+2, 8, h/4]}); var anclaje = CSG.cylinder({start:[totalL, 3, 0], end:[totalL, 3, h/2], radius:6, slices:32}).subtract(CSG.cylinder({start:[totalL, 3, -1], end:[totalL, 3, h/2+1], radius:3, slices:16})); baseObj = bc.union(anclaje);\n"
        elif base == "Placa Atornillable": code += "  var bc = CSG.cube({center:[totalL/2-3, 3, h/4], radius:[totalL/2+10, 10, h/4]}); var h1 = CSG.cylinder({start:[-8, 3, -1], end:[-8, 3, h], radius:2.5, slices:16}); var h2 = CSG.cylinder({start:[totalL+2, 3, -1], end:[totalL+2, 3, h], radius:2.5, slices:16}); baseObj = bc.subtract(h1).subtract(h2);\n"
        elif base == "Soporte de Mesa": code += "  var bc = CSG.cube({center:[totalL/2-3, 3, h/4], radius:[totalL/2+2, 5, h/4]}); var pata = CSG.cube({center:[totalL/2-3, -5, h/8], radius:[totalL/2+2, 10, h/8]}); baseObj = bc.union(pata);\n"
        elif base == "Colgante Militar": code += "  var b_cen = CSG.cube({center:[totalL/2-3, 4, h/4], radius:[totalL/2-1, 10, h/4]}); var b_izq = CSG.cylinder({start:[-4, 4, 0], end:[-4, 4, h/2], radius:10, slices:32}); var b_der = CSG.cylinder({start:[totalL-2, 4, 0], end:[totalL-2, 4, h/2], radius:10, slices:32}); var agujero = CSG.cylinder({start:[-8, 4, -1], end:[-8, 4, h], radius:2.5, slices:16}); baseObj = b_cen.union(b_izq).union(b_der).subtract(agujero);\n"
        elif base == "Placa Ovalada": code += "  var c1 = CSG.cylinder({start:[-2, 4, 0], end:[-2, 4, h/2], radius:12, slices:64}); var c2 = CSG.cylinder({start:[totalL-4, 4, 0], end:[totalL-4, 4, h/2], radius:12, slices:64}); var p_med = CSG.cube({center:[totalL/2-3, 4, h/4], radius:[totalL/2-1, 12, h/4]}); baseObj = p_med.union(c1).union(c2);\n"
        code += "  if(baseObj) {\n"
        if grabado: code += "      return UTILS.mat(baseObj.subtract(pText));\n  } else {\n      return UTILS.mat(pText);\n  }\n}"
        else: code += "      return UTILS.mat(baseObj.union(pText));\n  } else {\n      return UTILS.mat(pText);\n  }\n}"

    # -----------------------------------------
    # 2. STL ULTIMATE FORGE
    # -----------------------------------------
    elif h.startswith("stl"):
        code += get_stl_base(p['sc'], p['tx'], p['ty'], p['tz'])
        if h == "stl": code += "  return UTILS.mat(dron);\n}"
        elif h == "stl_flatten": code += f"  return UTILS.mat(dron.subtract(CSG.cube({{center:[0,0,-500+{p['stlf_z']}], radius:[1000,1000,500]}})));\n}}"
        elif h == "stl_split":
            ax = p['stls_axis']; pos = p['stls_pos']
            cx = pos-500 if ax=='X' else 0; cy = pos-500 if ax=='Y' else 0; cz = pos-500 if ax=='Z' else 0
            code += f"  return UTILS.mat(dron.subtract(CSG.cube({{center:[{cx},{cy},{cz}], radius:[1000,1000,1000]}})));\n}}"
        elif h == "stl_crop": S = p['stlc_s'] / 2.0; code += f"  return UTILS.mat(dron.intersect(CSG.cube({{center:[0,0,0], radius:[{S},{S},{S}]}})));\n}}"
        elif h == "stl_drill":
            ax = p['stld_axis']; R = p['stld_r']; p1 = p['stld_px']; p2 = p['stld_py']
            st = f"[-500,{p1},{p2}]" if ax=='X' else (f"[{p1},-500,{p2}]" if ax=='Y' else f"[{p1},{p2},-500]")
            en = f"[500,{p1},{p2}]" if ax=='X' else (f"[{p1},500,{p2}]" if ax=='Y' else f"[{p1},{p2},500]")
            code += f"  return UTILS.mat(dron.subtract(CSG.cylinder({{start:{st}, end:{en}, radius:{R}}})));\n}}"
        elif h == "stl_mount":
            w = p['stlm_w']; d = p['stlm_d']
            code += f"  var m1 = CSG.cube({{center:[{d/2},0,0], radius:[{w/2},15,3]}}).subtract(CSG.cylinder({{start:[{d/2},0,-5], end:[{d/2},0,5], radius:2.2, slices:16}}));\n"
            code += f"  var m2 = CSG.cube({{center:[{-d/2},0,0], radius:[{w/2},15,3]}}).subtract(CSG.cylinder({{start:[{-d/2},0,-5], end:[{-d/2},0,5], radius:2.2, slices:16}}));\n"
            code += f"  return UTILS.mat(dron.union(m1).union(m2));\n}}"
        elif h == "stl_ears":
            r = p['stle_r']; d = p['stle_d']
            code += f"  var c1=CSG.cylinder({{start:[{d/2},{d/2},0], end:[{d/2},{d/2},0.4], radius:{r}}}); var c2=CSG.cylinder({{start:[{-d/2},{d/2},0], end:[{-d/2},{d/2},0.4], radius:{r}}});\n"
            code += f"  var c3=CSG.cylinder({{start:[{d/2},{-d/2},0], end:[{d/2},{-d/2},0.4], radius:{r}}}); var c4=CSG.cylinder({{start:[{-d/2},{-d/2},0], end:[{-d/2},{-d/2},0.4], radius:{r}}});\n"
            code += f"  return UTILS.mat(dron.union(c1).union(c2).union(c3).union(c4));\n}}"
        elif h == "stl_patch": code += f"  return UTILS.mat(dron.union(CSG.cube({{center:[0,0,0], radius:[{p['stlp_sx']/2},{p['stlp_sy']/2},{p['stlp_sz']/2}]}})));\n}}"
        elif h == "stl_honeycomb":
            hex_r = p['stlh_r']
            code += f"  var dx = {hex_r}*1.732+2; var dy = {hex_r}*1.5+2; var holes = null;\n"
            code += f"  for(var x = -100; x < 100; x += dx) {{ for(var y = -100; y < 100; y += dy) {{\n      var offset = (Math.abs(Math.round(y/dy)) % 2 === 1) ? dx/2 : 0;\n"
            code += f"      var hex = CSG.cylinder({{start:[x+offset, y, -500], end:[x+offset, y, 500], radius:{hex_r}, slices:6}});\n      if(!holes) holes = hex; else holes = holes.union(hex);\n  }} }}\n  if(holes) return UTILS.mat(dron.subtract(holes));\n  return UTILS.mat(dron);\n}}"
        elif h == "stl_propguard":
            r = p['stlpg_r']; t = p['stlpg_t']; px = p['stlpg_x']; py = p['stlpg_y']
            code += f"  var out = CSG.cylinder({{start:[{px},{py},0], end:[{px},{py},10], radius:{r+t}, slices:32}});\n  var inn = CSG.cylinder({{start:[{px},{py},-1], end:[{px},{py},11], radius:{r}, slices:32}});\n"
            code += f"  return UTILS.mat(dron.union(out.subtract(inn)));\n}}"

    # -----------------------------------------
    # 3. GENERADORES PARAMÉTRICOS 3D (LÓGICA LIMPIA)
    # -----------------------------------------
    elif h == "laser":
        code += f"  var w = {p['las_x']}; var l = {p['las_y']}; var z_cut = {p['las_z']};\n"
        code += f"  var base_obj = CSG.cube({{center:[0,0,10], radius:[w/2, l/2, 10]}}).subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,21], radius:5, slices:16}}));\n"
        code += f"  var cut_plane = CSG.cube({{center:[0,0,z_cut], radius:[w, l, 0.5]}});\n  return UTILS.mat(base_obj.intersect(cut_plane));\n}}"
    elif h == "array_lin":
        code += f"  var filas = {int(p['alin_f'])}; var columnas = {int(p['alin_c'])}; var dx = {p['alin_dx']}; var dy = {p['alin_dy']}; var h = {p['alin_h']};\n"
        code += f"  var array_obj = null; var start_x = -((columnas - 1) * dx) / 2; var start_y = -((filas - 1) * dy) / 2;\n"
        code += f"  for(var i=0; i<filas; i++) {{ for(var j=0; j<columnas; j++) {{\n"
        code += f"      var px = start_x + (j * dx); var py = start_y + (i * dy);\n"
        code += f"      var pieza = CSG.cylinder({{start:[px,py,0], end:[px,py,h], radius:5, slices:16}});\n"
        code += f"      if(!array_obj) array_obj = pieza; else array_obj = array_obj.union(pieza);\n"
        code += f"  }} }}\n  return UTILS.mat(array_obj || CSG.cube({{radius:[1,1,1]}}));\n}}"
    elif h == "array_pol":
        code += f"  var n = {int(p['apol_n'])}; var radio_corona = {p['apol_r']}; var r_pieza = {p['apol_rp']}; var h = {p['apol_h']};\n"
        code += f"  var array_obj = null;\n"
        code += f"  for(var i=0; i<n; i++) {{\n      var a = (i * Math.PI * 2) / n; var px = Math.cos(a) * radio_corona; var py = Math.sin(a) * radio_corona;\n"
        code += f"      var pieza = CSG.cylinder({{start:[px,py,0], end:[px,py,h], radius:r_pieza, slices:16}});\n"
        code += f"      if(!array_obj) array_obj = pieza; else array_obj = array_obj.union(pieza);\n  }}\n"
        code += f"  var base = CSG.cylinder({{start:[0,0,0], end:[0,0,h/2], radius:radio_corona + r_pieza + 2, slices:32}});\n"
        code += f"  if(array_obj) base = base.subtract(array_obj);\n  return UTILS.mat(base);\n}}"
    elif h == "loft":
        code += f"  var side_base = {p['loft_w']}; var r_top = {p['loft_r']}; var h = {p['loft_h']}; var wall = {p['loft_g']};\n"
        code += f"  var res = 40; var dz = h / res; var loft_obj = null; var hueco = null;\n"
        code += f"  for(var i=0; i<res; i++) {{\n      var z = i * dz; var t = i / res; var slice_res = 32;\n"
        code += f"      for(var j=0; j<slice_res; j++) {{\n          var a1 = (j * Math.PI * 2) / slice_res;\n"
        code += f"          var cx1 = Math.cos(a1) * r_top; var cy1 = Math.sin(a1) * r_top; var sec = Math.floor(j / (slice_res/4));\n"
        code += f"          var sqx1 = 0; var sqy1 = 0; var m = side_base/2;\n"
        code += f"          if(sec==0) {{ sqx1=m; sqy1=m * Math.tan(a1); }} else if(sec==1) {{ sqx1=m/Math.tan(a1); sqy1=m; }} else if(sec==2) {{ sqx1=-m; sqy1=-m*Math.tan(a1); }} else {{ sqx1=-m/Math.tan(a1); sqy1=-m; }}\n"
        code += f"          if(Math.abs(sqx1)>m) sqx1 = Math.sign(sqx1)*m; if(Math.abs(sqy1)>m) sqy1 = Math.sign(sqy1)*m;\n"
        code += f"          var x_curr = sqx1*(1-t) + cx1*t; var y_curr = sqy1*(1-t) + cy1*t;\n"
        code += f"          var x_int = (Math.abs(sqx1)>0 ? sqx1-Math.sign(sqx1)*wall : 0)*(1-t) + Math.cos(a1)*(r_top-wall)*t;\n"
        code += f"          var y_int = (Math.abs(sqy1)>0 ? sqy1-Math.sign(sqy1)*wall : 0)*(1-t) + Math.sin(a1)*(r_top-wall)*t;\n"
        code += f"          var p_ext = CSG.cylinder({{start:[x_curr, y_curr, z], end:[x_curr, y_curr, z+dz+0.1], radius:wall/2, slices:8}});\n"
        code += f"          var p_int = CSG.cylinder({{start:[x_int, y_int, z], end:[x_int, y_int, z+dz+0.1], radius:wall/4, slices:4}});\n"
        code += f"          if(!loft_obj) loft_obj = p_ext; else loft_obj = loft_obj.union(p_ext);\n"
        code += f"          if(!hueco) hueco = p_int; else hueco = hueco.union(p_int);\n      }}\n  }}\n"
        code += f"  if(hueco) loft_obj = loft_obj.subtract(hueco);\n  return UTILS.mat(loft_obj || CSG.cube({{radius:[1,1,1]}}));\n}}"
    elif h == "voronoi":
        code += f"  var r_out = {p['vor_ro']}; var r_in = {p['vor_ri']}; var h = {p['vor_h']}; var d = {int(p['vor_d'])};\n"
        code += f"  var pipe = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_out, slices:32}}).subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:r_in, slices:32}}));\n"
        code += f"  var holes = null; var z_step = (r_out - r_in) * 2.5; var r_esfera = (r_out - r_in) * 1.8; var t = 0;\n"
        code += f"  for(var z = z_step; z < h - z_step; z += z_step) {{\n      var offset_a = (t % 2 === 1) ? Math.PI/d : 0;\n"
        code += f"      for(var i=0; i<d; i++) {{\n          var a = (i * Math.PI * 2 / d) + offset_a;\n"
        code += f"          var cx = Math.cos(a) * (r_out - (r_out-r_in)/2); var cy = Math.sin(a) * (r_out - (r_out-r_in)/2);\n"
        code += f"          var hole = CSG.sphere({{center:[cx, cy, z], radius:r_esfera, resolution:8}});\n"
        code += f"          if(!holes) holes = hole; else holes = holes.union(hole);\n      }}\n      t++;\n  }}\n"
        code += f"  if(holes) return UTILS.mat(pipe.subtract(holes));\n  return UTILS.mat(pipe);\n}}"
    elif h == "evolvente":
        code += f"  var dientes = {int(p['evo_d'])}; var m = {p['evo_m']}; var h = {p['evo_h']};\n"
        code += f"  var r_pitch = (dientes * m) / 2; var r_ext = r_pitch + m; var r_root = r_pitch - 1.25 * m;\n"
        code += f"  var gear = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_root, slices:64}});\n"
        code += f"  var t_w = (Math.PI * r_pitch / dientes) * 0.8;\n"
        code += f"  for(var i=0; i<dientes; i++) {{\n      var a = (i * Math.PI * 2) / dientes;\n"
        code += f"      var cx1 = Math.cos(a)*(r_root + m*0.3); var cy1 = Math.sin(a)*(r_root + m*0.3);\n"
        code += f"      var cx2 = Math.cos(a)*r_pitch;          var cy2 = Math.sin(a)*r_pitch;\n"
        code += f"      var cx3 = Math.cos(a)*(r_ext - m*0.2);  var cy3 = Math.sin(a)*(r_ext - m*0.2);\n"
        code += f"      var t1 = CSG.cylinder({{start:[cx1,cy1,0], end:[cx1,cy1,h], radius:t_w*0.6, slices:16}});\n"
        code += f"      var t2 = CSG.cylinder({{start:[cx2,cy2,0], end:[cx2,cy2,h], radius:t_w*0.4, slices:16}});\n"
        code += f"      var t3 = CSG.cylinder({{start:[cx3,cy3,0], end:[cx3,cy3,h], radius:t_w*0.15, slices:16}});\n"
        code += f"      gear = gear.union(t1).union(t2).union(t3);\n  }}\n"
        code += f"  var hole = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius: r_root * 0.3, slices:32}});\n"
        code += f"  return UTILS.mat(UTILS.rotZ(gear.subtract(hole), KINE_T));\n}}"
    elif h == "cremallera":
        code += f"  var dientes = {int(p['crem_d'])}; var m = {p['crem_m']}; var h = {p['crem_h']}; var w = {p['crem_w']};\n"
        code += f"  var pitch = Math.PI * m; var len = dientes * pitch;\n"
        code += f"  var rack = CSG.cube({{center:[len/2, w/2, h/2], radius:[len/2, w/2, h/2]}}); var t_w = pitch / 2;\n"
        code += f"  for(var i=0; i<dientes; i++) {{\n      var px = i * pitch + pitch/2;\n"
        code += f"      var t1 = CSG.cube({{center:[px, w + m*0.2, h/2], radius:[t_w*0.4, m*0.3, h/2]}});\n"
        code += f"      var t2 = CSG.cube({{center:[px, w + m*0.7, h/2], radius:[t_w*0.2, m*0.4, h/2]}});\n"
        code += f"      rack = rack.union(t1).union(t2);\n  }}\n  return UTILS.mat(UTILS.trans(rack, [KINE_T/10, 0, 0]));\n}}"
    elif h == "conico":
        code += f"  var dientes = {int(p['con_d'])}; var rb = {p['con_rb']}; var rt = {p['con_rt']}; var h = {p['con_h']};\n"
        code += f"  var res = 20; var dz = h / res; var gear = null; var m = rb / (dientes/2);\n"
        code += f"  for(var z=0; z<res; z++) {{\n      var z_pos = z * dz; var r_curr = rb - (rb - rt)*(z/res); var r_root = Math.max(0.1, r_curr - m);\n"
        code += f"      var core = CSG.cylinder({{start:[0,0,z_pos], end:[0,0,z_pos+dz], radius:r_root, slices:32}});\n"
        code += f"      if(!gear) gear = core; else gear = gear.union(core);\n"
        code += f"      var t_w = (Math.PI * r_curr / dientes) * 0.8;\n"
        code += f"      for(var i=0; i<dientes; i++) {{\n          var a = (i * Math.PI * 2) / dientes;\n"
        code += f"          var cx1 = Math.cos(a)*(r_root + m*0.3); var cy1 = Math.sin(a)*(r_root + m*0.3);\n"
        code += f"          var cx2 = Math.cos(a)*r_curr;           var cy2 = Math.sin(a)*r_curr;\n"
        code += f"          var t1 = CSG.cylinder({{start:[cx1,cy1,z_pos], end:[cx1,cy1,z_pos+dz], radius:t_w*0.6, slices:8}});\n"
        code += f"          var t2 = CSG.cylinder({{start:[cx2,cy2,z_pos], end:[cx2,cy2,z_pos+dz], radius:t_w*0.3, slices:8}});\n"
        code += f"          gear = gear.union(t1).union(t2);\n      }}\n  }}\n"
        code += f"  var hole = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius: rt * 0.3, slices:16}});\n"
        code += f"  if(gear) return UTILS.mat(UTILS.rotZ(gear.subtract(hole), KINE_T));\n  return UTILS.mat(CSG.cube({{radius:[1,1,1]}}));\n}}"
    elif h == "multicaja":
        code += f"  var w = {p['mc_x']}; var l = {p['mc_y']}; var h = {p['mc_z']}; var tol = {p['mc_tol']}; var sep = {p['mc_sep']};\n"
        code += f"  var t = 2; var ext = CSG.cube({{center:[0,0,h/2], radius:[w/2, l/2, h/2]}});\n"
        code += f"  var int_box = CSG.cube({{center:[0,0,h/2+t], radius:[w/2-t, l/2-t, h/2]}}); var caja = ext.subtract(int_box);\n"
        code += f"  var offsetZ = h + sep + (KINE_T/5); var tapa_b = CSG.cube({{center:[0,0, offsetZ + t/2], radius:[w/2, l/2, t/2]}});\n"
        code += f"  var tapa_i = CSG.cube({{center:[0,0, offsetZ - t/2], radius:[w/2-t-tol, l/2-t-tol, t/2]}}); var tapa = tapa_b.union(tapa_i);\n"
        code += f"  return UTILS.mat(caja.union(tapa));\n}}"
    elif h == "perfil":
        code += f"  var puntas = {int(p['perf_p'])}; var rext = {p['perf_re']}; var rint = {p['perf_ri']}; var h = {p['perf_h']};\n"
        code += f"  var pieza = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:rint, slices:32}});\n"
        code += f"  var d_theta = (Math.PI * 2) / puntas; var r_punta = (rext - rint) / 1.5;\n"
        code += f"  for(var i=0; i<puntas; i++) {{\n     var a = i * d_theta; var px = Math.cos(a) * (rint + r_punta*0.8); var py = Math.sin(a) * (rint + r_punta*0.8);\n"
        code += f"     var punta = CSG.cylinder({{start:[px, py, 0], end:[px, py, h], radius:r_punta, slices:16}});\n"
        code += f"     pieza = pieza.union(punta);\n  }}\n  return UTILS.mat(UTILS.rotZ(pieza, KINE_T));\n}}"
    elif h == "revolucion":
        code += f"  var h = {p['rev_h']}; var r1 = {p['rev_r1']}; var r2 = {p['rev_r2']}; var grosor = {p['rev_g']};\n"
        code += f"  var res = 60; var dz = h / res; var solido = null; var hueco = null;\n"
        code += f"  for(var i=0; i<res; i++) {{\n      var z = i * dz; var f = Math.sin((z/h) * Math.PI); var rad = r1 + (r2 - r1)*(z/h) + (f * 15);\n"
        code += f"      var capa = CSG.cylinder({{start:[0,0,z], end:[0,0,z+dz], radius:rad, slices:32}});\n"
        code += f"      if(!solido) solido = capa; else solido = solido.union(capa);\n"
        code += f"      if (grosor > 0 && z > grosor) {{\n         var r_int = Math.max(0.1, rad - grosor);\n"
        code += f"         var capa_h = CSG.cylinder({{start:[0,0,z], end:[0,0,z+dz+0.1], radius:r_int, slices:32}});\n"
        code += f"         if(!hueco) hueco = hueco.union(capa_h);\n      }}\n  }}\n"
        code += f"  if(grosor > 0 && hueco) solido = solido.subtract(hueco);\n  return UTILS.mat(solido);\n}}"
    elif h == "cubo":
        g = p['c_grosor']
        code += f"  var pieza = CSG.cube({{center:[0,0,GH/2], radius:[GW/2, GL/2, GH/2]}});\n"
        if g > 0: code += f"  var int_box = CSG.cube({{center:[0,0,GH/2 + {g}], radius:[GW/2 - {g}, GL/2 - {g}, GH/2]}});\n  pieza = pieza.subtract(int_box);\n"
        code += f"  return UTILS.mat(pieza);\n}}"
    elif h == "cilindro":
        rint = p['p_rint']; c = int(p['p_lados'])
        code += f"  var pieza = CSG.cylinder({{start:[0,0,0], end:[0,0,GH], radius:GW/2, slices:{c}}});\n"
        if rint > 0: code += f"  var int_cyl = CSG.cylinder({{start:[0,0,-1], end:[0,0,GH+2], radius:{rint}, slices:{c}}});\n  pieza = pieza.subtract(int_cyl);\n"
        code += f"  return UTILS.mat(pieza);\n}}"
    elif h == "escuadra":
        code += f"  var l = {p['l_largo']}; var w = {p['l_ancho']}; var t = {p['l_grosor']}; var r = {p['l_hueco']}; var chaf = {p['l_chaf']};\n"
        code += f"  var base = CSG.cube({{center:[l/2, w/2, t/2], radius:[l/2, w/2, t/2]}}); var wall = CSG.cube({{center:[t/2, w/2, l/2], radius:[t/2, w/2, l/2]}}); var pieza = base.union(wall);\n"
        if p['l_chaf'] > 0: code += f"  var fillet = CSG.cylinder({{start:[t, 0, t], end:[t, w, t], radius:chaf, slices:16}}); pieza = pieza.union(fillet);\n"
        if p['l_hueco'] > 0: code += f"  var h1 = CSG.cylinder({{start:[l*0.7, w/2, -1], end:[l*0.7, w/2, t+1], radius:r, slices:32}});\n  var h2 = CSG.cylinder({{start:[-1, w/2, l*0.7], end:[t+1, w/2, l*0.7], radius:r, slices:32}});\n  pieza = pieza.subtract(h1).subtract(h2);\n"
        code += f"  return UTILS.mat(pieza);\n}}"
    elif h == "engranaje":
        code += f"  var dientes = {int(p['e_dientes'])}; var r = {p['e_radio']}; var h = {p['e_grosor']};\n"
        code += f"  var d_x = r*0.15; var d_y = r*0.2;\n  var pieza = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r, slices:64}});\n"
        code += f"  for(var i=0; i<dientes; i++) {{\n    var a = (i * Math.PI * 2) / dientes;\n"
        code += f"    var diente = CSG.cube({{center:[Math.cos(a)*r, Math.sin(a)*r, h/2], radius:[d_x, d_y, h/2]}}); pieza = pieza.union(diente);\n  }}\n"
        if p['e_eje'] > 0: code += f"  var hueco = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:{p['e_eje']} + G_TOL, slices:32}}); pieza = pieza.subtract(hueco);\n"
        code += f"  return UTILS.mat(UTILS.rotZ(pieza, KINE_T));\n}}"
    elif h == "pcb":
        code += f"  var px = {p['pcb_x']}; var py = {p['pcb_y']}; var h = {p['pcb_h']}; var t = {p['pcb_t']};\n"
        code += f"  var ext = CSG.cube({{center:[0,0,h/2], radius:[px/2 + t, py/2 + t, h/2]}});\n"
        code += f"  var int_box = CSG.cube({{center:[0,0,h/2 + t], radius:[px/2, py/2, h/2]}}); var pieza = ext.subtract(int_box);\n"
        code += f"  var dx = px/2 - 3.5; var dy = py/2 - 3.5; var m = [[1,1], [1,-1], [-1,1], [-1,-1]];\n"
        code += f"  for(var i=0; i<4; i++) {{\n    var cyl = CSG.cylinder({{start:[m[i][0]*dx, m[i][1]*dy, 0], end:[m[i][0]*dx, m[i][1]*dy, h-2], radius: 3.5, slices:16}});\n"
        code += f"    var hole = CSG.cylinder({{start:[m[i][0]*dx, m[i][1]*dy, 2], end:[m[i][0]*dx, m[i][1]*dy, h], radius: 1.5 + (G_TOL/2), slices:16}});\n"
        code += f"    pieza = pieza.union(cyl).subtract(hole);\n  }}\n  return UTILS.mat(pieza);\n}}"
    elif h == "vslot":
        code += f"  var l = {p['v_l']};\n  var pieza = CSG.cube({{center:[0,0,l/2], radius:[10,10,l/2]}});\n"
        code += f"  var ch = CSG.cylinder({{start:[0,0,-1], end:[0,0,l+1], radius:2.1 + (G_TOL/2), slices:32}}); pieza = pieza.subtract(ch);\n"
        code += f"  pieza = pieza.subtract(CSG.cube({{center:[0,10,l/2], radius:[3,2,l/2+1]}})).subtract(CSG.cube({{center:[0,8.5,l/2], radius:[5,1.5,l/2+1]}}));\n"
        code += f"  pieza = pieza.subtract(CSG.cube({{center:[0,-10,l/2], radius:[3,2,l/2+1]}})).subtract(CSG.cube({{center:[0,-8.5,l/2], radius:[5,1.5,l/2+1]}}));\n"
        code += f"  pieza = pieza.subtract(CSG.cube({{center:[10,0,l/2], radius:[2,3,l/2+1]}})).subtract(CSG.cube({{center:[8.5,0,l/2], radius:[1.5,5,l/2+1]}}));\n"
        code += f"  pieza = pieza.subtract(CSG.cube({{center:[-10,0,l/2], radius:[2,3,l/2+1]}})).subtract(CSG.cube({{center:[-8.5,0,l/2], radius:[1.5,5,l/2+1]}}));\n"
        code += f"  return UTILS.mat(pieza);\n}}"
    elif h == "bisagra":
        code += f"  var l = {p['bi_l']}; var d = {p['bi_d']};\n"
        code += f"  var fix = CSG.cylinder({{start:[0,0,0], end:[0,0,l/3], radius:d/2, slices:32}});\n"
        code += f"  var fix2 = CSG.cylinder({{start:[0,0,2*l/3], end:[0,0,l], radius:d/2, slices:32}});\n"
        code += f"  var move = CSG.cylinder({{start:[0,0,l/3+G_TOL], end:[0,0,2*l/3-G_TOL], radius:d/2, slices:32}});\n"
        code += f"  var pin = CSG.cylinder({{start:[0,0,l/3-d/4], end:[0,0,2*l/3+d/4], radius:(d/4)-G_TOL, slices:32}});\n"
        code += f"  var cut_pin = CSG.cylinder({{start:[0,0,l/3-d/2], end:[0,0,2*l/3+d/2], radius:d/4, slices:32}});\n"
        code += f"  var fijo = fix.union(fix2).subtract(cut_pin).union(pin);\n  var movil = move.subtract(cut_pin);\n"
        code += f"  movil = UTILS.trans(movil, [0,0,-l/2]); movil = UTILS.rotX(movil, KINE_T); movil = UTILS.trans(movil, [0,0,l/2]);\n"
        code += f"  return UTILS.mat(fijo.union(movil));\n}}"
    elif h == "abrazadera":
        code += f"  var diam = {p['clamp_d']}; var grosor = {p['clamp_g']}; var ancho = {p['clamp_w']};\n"
        code += f"  var ext = CSG.cylinder({{start:[0,0,0], end:[0,0,ancho], radius:(diam/2)+grosor, slices:64}});\n"
        code += f"  var int_cyl = CSG.cylinder({{start:[0,0,-1], end:[0,0,ancho+1], radius:diam/2 + G_TOL, slices:64}});\n"
        code += f"  var corteInf = CSG.cube({{center:[0, -50, ancho/2], radius:[50, 50, ancho]}});\n"
        code += f"  var arco = ext.subtract(int_cyl).subtract(corteInf);\n"
        code += f"  var distPestana = (diam/2) + grosor + 5;\n"
        code += f"  var pestana = CSG.cube({{center:[ distPestana, grosor/2, ancho/2 ], radius:[7.5, grosor/2, ancho/2]}});\n"
        code += f"  var pestana2 = CSG.cube({{center:[ -distPestana, grosor/2, ancho/2 ], radius:[7.5, grosor/2, ancho/2]}});\n"
        code += f"  var m3 = CSG.cylinder({{start:[ distPestana, 10, ancho/2 ], end:[ distPestana, -10, ancho/2 ], radius:1.7 + (G_TOL/2), slices:16}});\n"
        code += f"  var m3_2 = CSG.cylinder({{start:[ -distPestana, 10, ancho/2 ], end:[ -distPestana, -10, ancho/2 ], radius:1.7 + (G_TOL/2), slices:16}});\n"
        code += f"  return UTILS.mat(arco.union(pestana).union(pestana2).subtract(m3).subtract(m3_2));\n}}"
    elif h == "fijacion":
        m, l_tornillo = p['fij_m'], p['fij_l']
        r_hex = (m * 1.8) / 2; h_cabeza = m * 0.8; r_eje = m / 2
        if l_tornillo == 0: 
            code += f"  var m = {m}; var h = {h_cabeza};\n  var cuerpo = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:{r_hex}, slices:6}});\n  var agujero = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:({r_eje} + G_TOL), slices:32}});\n  return UTILS.mat(cuerpo.subtract(agujero));\n}}"
        else: 
            code += f"  var m = {m}; var l_tornillo = {l_tornillo}; var h_cabeza = {h_cabeza}; var r_hex = {r_hex};\n  var cabeza = CSG.cylinder({{start:[0,0,0], end:[0,0,h_cabeza], radius:r_hex, slices:6}});\n  var eje = CSG.cylinder({{start:[0,0,h_cabeza - 0.1], end:[0,0,h_cabeza + l_tornillo], radius:({r_eje} - G_TOL) - (m*0.08), slices:32}});\n  var pieza = cabeza.union(eje); var paso = m * 0.15;\n  for(var z = h_cabeza + 1; z < h_cabeza + l_tornillo - 1; z += paso*1.5) {{\n      var anillo = CSG.cylinder({{start:[0,0,z], end:[0,0,z+paso], radius:({r_eje} - G_TOL), slices:16}});\n      pieza = pieza.union(anillo);\n  }}\n  return UTILS.mat(UTILS.rotZ(pieza, KINE_T));\n}}"
    elif h == "rodamiento":
        code += f"  var d_int = {p['rod_dint']}; var d_ext = {p['rod_dext']}; var h = {p['rod_h']};\n"
        code += f"  var pista_ext = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:d_ext/2, slices:64}}).subtract( CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:(d_ext/2)-2 + G_TOL, slices:64}}) );\n"
        code += f"  var pista_int_base = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:(d_int/2)+2 - G_TOL, slices:64}}).subtract( CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:d_int/2, slices:64}}) );\n"
        code += f"  var pista_int = UTILS.rotZ(pista_int_base, KINE_T);\n"
        code += f"  var pieza = pista_ext.union(pista_int);\n"
        code += f"  var r_espacio = (((d_ext/2)-2) - ((d_int/2)+2)) / 2; var radio_centro = ((d_int/2)+2 + (d_ext/2)-2)/2;\n"
        code += f"  var n_bolas = Math.floor((Math.PI * 2 * radio_centro) / (r_espacio * 2.2));\n"
        code += f"  for(var i=0; i<n_bolas; i++) {{\n      var a = (i * Math.PI * 2) / n_bolas; var bx = Math.cos(a + KINE_T/100) * radio_centro; var by = Math.sin(a + KINE_T/100) * radio_centro;\n"
        code += f"      var bola = CSG.sphere({{center:[bx, by, h/2], radius:(r_espacio*0.95) - (G_TOL/2), resolution:16}});\n"
        code += f"      pieza = pieza.union(bola);\n  }}\n  return UTILS.mat(pieza);\n}}"
    elif h == "planetario":
        code += f"  var r_sol = {p['plan_rs']}; var r_planeta = {p['plan_rp']}; var h = {p['plan_h']};\n"
        code += f"  var r_anillo = r_sol + (r_planeta*2); var dist_centros = r_sol + r_planeta;\n"
        code += f"  var T = KINE_T; var carrier_T = T * (r_sol / (r_sol + r_anillo)); var planet_T = T * (r_sol / r_planeta);\n"
        code += f"  var sol_base = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_sol - 1, slices:32}});\n"
        code += f"  var dientes_sol = Math.floor(r_sol * 1.5);\n"
        code += f"  for(var i=0; i<dientes_sol; i++) {{\n      var a = (i * Math.PI * 2) / dientes_sol;\n"
        code += f"      var diente = CSG.cylinder({{start:[Math.cos(a)*r_sol, Math.sin(a)*r_sol, 0], end:[Math.cos(a)*r_sol, Math.sin(a)*r_sol, h], radius:1.2, slices:12}});\n"
        code += f"      sol_base = sol_base.union(diente);\n  }}\n"
        code += f"  var sol = UTILS.rotZ(sol_base.subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:3, slices:16}})), T);\n"
        code += f"  var planetas = null; var dientes_planeta = Math.floor(r_planeta * 1.5);\n"
        code += f"  for(var p=0; p<3; p++) {{\n      var ap = (p * Math.PI * 2) / 3;\n"
        code += f"      var planeta = CSG.cylinder({{start:[0, 0, 0], end:[0, 0, h], radius:r_planeta - 1 - G_TOL, slices:32}});\n"
        code += f"      for(var i=0; i<dientes_planeta; i++) {{\n          var a = (i * Math.PI * 2) / dientes_planeta;\n"
        code += f"          var px = Math.cos(a)*(r_planeta - G_TOL); var py = Math.sin(a)*(r_planeta - G_TOL);\n"
        code += f"          var diente_p = CSG.cylinder({{start:[px, py, 0], end:[px, py, h], radius:1.2 - (G_TOL/2), slices:12}});\n"
        code += f"          planeta = planeta.union(diente_p);\n      }}\n"
        code += f"      planeta = planeta.subtract(CSG.cylinder({{start:[0, 0, -1], end:[0, 0, h+1], radius:2, slices:12}}));\n"
        code += f"      planeta = UTILS.rotZ(planeta, -planet_T);\n"
        code += f"      var angulo_pos = ap + (carrier_T * Math.PI / 180);\n"
        code += f"      var cx = Math.cos(angulo_pos) * dist_centros; var cy = Math.sin(angulo_pos) * dist_centros;\n"
        code += f"      planeta = UTILS.trans(planeta, [cx, cy, 0]);\n"
        code += f"      if(!planetas) planetas = planeta; else planetas = planetas.union(planeta);\n  }}\n"
        code += f"  var corona = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_anillo + 5, slices:64}}).subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:r_anillo + G_TOL, slices:64}}));\n"
        code += f"  var dientes_corona = Math.floor(r_anillo * 1.5); var anillo_dientes = null;\n"
        code += f"  for(var i=0; i<dientes_corona; i++) {{\n      var a = (i * Math.PI * 2) / dientes_corona;\n"
        code += f"      var diente_c = CSG.cylinder({{start:[Math.cos(a)*(r_anillo + G_TOL), Math.sin(a)*(r_anillo + G_TOL), 0], end:[Math.cos(a)*(r_anillo + G_TOL), Math.sin(a)*(r_anillo + G_TOL), h], radius:1.2, slices:12}});\n"
        code += f"      if(!anillo_dientes) anillo_dientes = diente_c; else anillo_dientes = anillo_dientes.union(diente_c);\n  }}\n"
        code += f"  if(anillo_dientes) corona = corona.union(anillo_dientes);\n"
        code += f"  var obj = sol.union(corona);\n  if(planetas) obj = obj.union(planetas);\n  return UTILS.mat(obj);\n}}"
    elif h == "polea":
        code += f"  var dientes = {int(p['pol_t'])}; var ancho = {p['pol_w']}; var r_eje = {p['pol_d']/2};\n"
        code += f"  var pitch = 2; var r_primitivo = (dientes * pitch) / (2 * Math.PI); var r_ext = r_primitivo - 0.25;\n"
        code += f"  var cuerpo = CSG.cylinder({{start:[0,0,1.5], end:[0,0,1.5+ancho], radius:r_ext, slices:64}});\n"
        code += f"  var matriz_dientes = null;\n"
        code += f"  for(var i=0; i<dientes; i++) {{\n      var a = (i * Math.PI * 2) / dientes;\n"
        code += f"      var d = CSG.cylinder({{start:[Math.cos(a)*r_ext, Math.sin(a)*r_ext, 1], end:[Math.cos(a)*r_ext, Math.sin(a)*r_ext, 2+ancho], radius:0.55, slices:8}});\n"
        code += f"      if(!matriz_dientes) matriz_dientes = d; else matriz_dientes = matriz_dientes.union(d);\n  }}\n"
        code += f"  if(matriz_dientes) cuerpo = cuerpo.subtract(matriz_dientes);\n"
        code += f"  var base = CSG.cylinder({{start:[0,0,0], end:[0,0,1.5], radius:r_ext + 1, slices:64}});\n"
        code += f"  var tapa = CSG.cylinder({{start:[0,0,1.5+ancho], end:[0,0,3+ancho], radius:r_ext + 1, slices:64}});\n"
        code += f"  var polea = base.union(cuerpo).union(tapa);\n"
        code += f"  polea = polea.subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,5+ancho], radius:r_eje + (G_TOL/2), slices:32}}));\n  return UTILS.mat(UTILS.rotZ(polea, KINE_T));\n}}"
    elif h == "helice":
        code += f"  var rad = {p['hel_r']}; var n = {int(p['hel_n'])}; var pitch = {p['hel_p']};\n"
        code += f"  var hub = CSG.cylinder({{start:[0,0,0], end:[0,0,10], radius:8, slices:32}});\n"
        code += f"  var agujero = CSG.cylinder({{start:[0,0,-1], end:[0,0,11], radius:2.5 + G_TOL, slices:16}});\n"
        code += f"  var aspas = null;\n"
        code += f"  for(var i=0; i<n; i++) {{\n    var a = (i * Math.PI * 2) / n; var dx = Math.cos(a); var dy = Math.sin(a);\n"
        code += f"    var aspa = CSG.cylinder({{start:[6*dx, 6*dy, 5 - (pitch/10)], end:[rad*dx, rad*dy, 5 + (pitch/10)], radius: 3, slices: 4}});\n"
        code += f"    if(!aspas) aspas = aspa; else aspas = aspas.union(aspa);\n  }}\n"
        code += f"  if(aspas) hub = hub.union(aspas);\n  return UTILS.mat(UTILS.rotZ(hub.subtract(agujero), KINE_T));\n}}"
    elif h == "rotula":
        code += f"  var r_bola = {p['rot_r']};\n"
        code += f"  var bola = CSG.sphere({{center:[0,0,0], radius:r_bola, resolution:32}}); var eje_bola = CSG.cylinder({{start:[0,0,0], end:[0,0,-r_bola*2], radius:r_bola*0.6, slices:32}});\n"
        code += f"  var componente_bola = UTILS.rotY(UTILS.rotX(bola.union(eje_bola), KINE_T/4), KINE_T/4);\n"
        code += f"  var copa_ext = CSG.cylinder({{start:[0,0,-r_bola*0.2], end:[0,0,r_bola*1.5], radius:r_bola+4, slices:32}});\n"
        code += f"  var hueco_bola = CSG.sphere({{center:[0,0,0], radius:r_bola+G_TOL, resolution:32}}); var apertura = CSG.cylinder({{start:[0,0,r_bola*0.5], end:[0,0,r_bola*2], radius:r_bola*0.8, slices:32}});\n"
        code += f"  var componente_copa = copa_ext.subtract(hueco_bola).subtract(apertura);\n  return UTILS.mat(componente_bola.union(componente_copa));\n}}"
    elif h == "carcasa":
        code += f"  var w = {p['car_x']}; var l = {p['car_y']}; var h = {p['car_z']}; var t = {p['car_t']};\n"
        code += f"  var ext = CSG.cube({{center:[0,0,h/2], radius:[w/2, l/2, h/2]}}); var int_box = CSG.cube({{center:[0,0,(h/2)+t], radius:[(w/2)-t, (l/2)-t, h/2]}}); var base = ext.subtract(int_box);\n"
        code += f"  var r_post = 3.5; var r_hole = 1.5; var h_post = 6; var m = [[1,1], [1,-1], [-1,1], [-1,-1]];\n"
        code += f"  for(var i=0; i<4; i++) {{\n      var px = m[i][0] * ((w/2) - t - r_post - 1); var py = m[i][1] * ((l/2) - t - r_post - 1);\n"
        code += f"      var post = CSG.cylinder({{start:[px,py,t], end:[px,py,t+h_post], radius:r_post, slices:16}});\n"
        code += f"      var hole = CSG.cylinder({{start:[px,py,t], end:[px,py,t+h_post+1], radius:r_hole + (G_TOL/2), slices:16}});\n"
        code += f"      base = base.union(post).subtract(hole);\n  }}\n"
        code += f"  var vents = null;\n  for(var vx=-(w/2)+15; vx < (w/2)-15; vx += 7) {{\n      for(var vy=-(l/2)+15; vy < (l/2)-15; vy += 7) {{\n"
        code += f"          var agujero = CSG.cylinder({{start:[vx,vy,-1], end:[vx,vy,t+1], radius:2, slices:8}});\n"
        code += f"          if(!vents) vents = agujero; else vents = vents.union(agujero);\n      }}\n  }}\n"
        code += f"  if(vents) base = base.subtract(vents);\n  return UTILS.mat(base);\n}}"
    elif h == "muelle":
        code += f"  var r_res = {p['mue_r']}; var r_hilo = {p['mue_h']}; var h = {p['mue_alt']}; var vueltas = {p['mue_v']};\n"
        code += f"  var resorte = null; var pasos = Math.floor(vueltas * 24); var paso_z = h / pasos; var a_step = (Math.PI * 2 * vueltas) / pasos;\n"
        code += f"  for(var i=0; i<pasos; i++) {{\n      var a1 = i * a_step; var a2 = (i+1) * a_step;\n"
        code += f"      var x1 = Math.cos(a1)*r_res; var y1 = Math.sin(a1)*r_res; var z1 = i*paso_z;\n"
        code += f"      var x2 = Math.cos(a2)*r_res; var y2 = Math.sin(a2)*r_res; var z2 = (i+1)*paso_z;\n"
        code += f"      var seg = CSG.cylinder({{start:[x1,y1,z1], end:[x2,y2,z2], radius:r_hilo, slices:8}});\n"
        code += f"      var esp = CSG.sphere({{center:[x2,y2,z2], radius:r_hilo, resolution:8}});\n"
        code += f"      if(!resorte) resorte = seg.union(esp); else resorte = resorte.union(seg).union(esp);\n  }}\n  return UTILS.mat(resorte);\n}}"
    elif h == "acme":
        code += f"  var r = {p['acme_d']/2}; var pitch = {p['acme_p']}; var len = {p['acme_l']};\n"
        code += f"  var r_core = r - (pitch * 0.4); var eje = CSG.cylinder({{start:[0,0,0], end:[0,0,len], radius:r_core, slices:32}});\n"
        code += f"  var thread = null; var steps = Math.floor((len / pitch) * 24); var z_step = len / steps; var a_step = (Math.PI * 2 * (len/pitch)) / steps; var w = pitch * 0.35;\n"
        code += f"  for(var i=0; i<steps; i++) {{\n      var a1 = i * a_step; var a2 = (i+1) * a_step; var z1 = i * z_step; var z2 = (i+1) * z_step;\n"
        code += f"      var seg = CSG.cylinder({{start:[Math.cos(a1)*r, Math.sin(a1)*r, z1], end:[Math.cos(a2)*r, Math.sin(a2)*r, z2], radius:w, slices:8}});\n"
        code += f"      if(!thread) thread = seg; else thread = thread.union(seg);\n  }}\n"
        code += f"  if(thread) eje = eje.union(thread);\n  return UTILS.mat(UTILS.rotZ(eje, KINE_T));\n}}"
    elif h == "codo":
        code += f"  var r_tubo = {p['codo_r']}; var r_curva = {p['codo_c']}; var angulo = {p['codo_a']}; var grosor = {p['codo_g']};\n"
        code += f"  var codo = null; var pasos = Math.max(8, Math.floor(angulo / 5));\n"
        code += f"  for(var i=0; i<pasos; i++) {{\n      var a1 = (i * (angulo/pasos)) * Math.PI / 180; var a2 = ((i+1) * (angulo/pasos)) * Math.PI / 180;\n"
        code += f"      var x1 = Math.cos(a1)*r_curva; var y1 = Math.sin(a1)*r_curva; var x2 = Math.cos(a2)*r_curva; var y2 = Math.sin(a2)*r_curva;\n"
        code += f"      var ext = CSG.cylinder({{start:[x1,y1,0], end:[x2,y2,0], radius:r_tubo, slices:16}});\n"
        code += f"      var esf = CSG.sphere({{center:[x2,y2,0], radius:r_tubo, resolution:16}});\n"
        code += f"      var sol = ext.union(esf);\n      if(!codo) codo = sol; else codo = codo.union(sol);\n  }}\n"
        code += f"  if(grosor > 0) {{\n     var hueco = null;\n     for(var i=0; i<pasos; i++) {{\n"
        code += f"         var a1 = (i * (angulo/pasos)) * Math.PI / 180; var a2 = ((i+1) * (angulo/pasos)) * Math.PI / 180;\n"
        code += f"         var x1 = Math.cos(a1)*r_curva; var y1 = Math.sin(a1)*r_curva; var x2 = Math.cos(a2)*r_curva; var y2 = Math.sin(a2)*r_curva;\n"
        code += f"         var int_c = CSG.cylinder({{start:[x1,y1,0], end:[x2,y2,0], radius:r_tubo-grosor, slices:12}});\n"
        code += f"         var isf = CSG.sphere({{center:[x2,y2,0], radius:r_tubo-grosor, resolution:12}});\n"
        code += f"         var hol = int_c.union(isf); if(!hueco) hueco = hol; else hueco = hueco.union(hol);\n"
        code += f"     }}\n     if(hueco) codo = codo.subtract(hueco);\n  }}\n  return UTILS.mat(codo);\n}}"
    elif h == "naca":
        code += f"  var cuerda = {p['naca_c']}; var grosor = {p['naca_g']}; var envergadura = {p['naca_e']};\n"
        code += f"  var ala = null; var num_pasos = 40;\n"
        code += f"  for(var i=0; i<=num_pasos; i++) {{\n      var x = i/num_pasos;\n"
        code += f"      var yt = 5 * (grosor/100) * (0.2969*Math.sqrt(x) - 0.1260*x - 0.3516*(x*x) + 0.2843*Math.pow(x,3) - 0.1015*Math.pow(x,4));\n"
        code += f"      var x_real = x * cuerda; var yt_real = Math.max(yt * cuerda, 0.1);\n"
        code += f"      var cyl = CSG.cylinder({{start:[x_real, 0, 0], end:[x_real, 0, envergadura], radius: yt_real, slices: 16}});\n"
        code += f"      if(!ala) ala = cyl; else ala = ala.union(cyl);\n  }}\n  return UTILS.mat(ala);\n}}"
    elif h == "stand_movil":
        code += f"  var ang = {p['st_ang']} * Math.PI / 180; var w = {p['st_w']}; var t = {p['st_t']};\n"
        code += f"  var base = CSG.cube({{center:[0, -20, t/2], radius:[w/2, 40, t/2]}});\n"
        code += f"  var h_back = 80; var dx = Math.sin(ang)*h_back; var dy = Math.cos(ang)*h_back;\n"
        code += f"  var back = CSG.cube({{center:[0, dy/2, dx/2], radius:[w/2, dy/2, dx/2]}});\n"
        code += f"  var lip = CSG.cube({{center:[0, -50, t + 5], radius:[w/2, t/2, 5]}});\n"
        code += f"  return UTILS.mat(base.union(back).union(lip));\n}}"
    elif h == "clip_cable":
        code += f"  var d = {p['clip_d']}; var w = {p['clip_w']}; var t = 3;\n"
        code += f"  var base = CSG.cube({{center:[0, 0, t/2], radius:[w/2, w/2, t/2]}});\n"
        code += f"  var anillo = CSG.cylinder({{start:[0,0,t], end:[0,0,t+w], radius:(d/2)+t, slices:32}});\n"
        code += f"  var hueco = CSG.cylinder({{start:[0,0,t-1], end:[0,0,t+w+1], radius:(d/2), slices:32}});\n"
        code += f"  var slot = CSG.cube({{center:[0, d, t+(w/2)], radius:[(d/2)-0.5, d, w/2+1]}});\n"
        code += f"  return UTILS.mat(base.union(anillo).subtract(hueco).subtract(slot));\n}}"
    elif h == "vr_pedestal":
        code += f"  var s = {p['vr_s']};\n"
        code += f"  var base1 = CSG.cube({{center:[0, 0, 10], radius:[s/2, s/2, 10]}});\n"
        code += f"  var base2 = CSG.cube({{center:[0, 0, 30], radius:[(s/2)-20, (s/2)-20, 10]}});\n"
        code += f"  var pillar = CSG.cylinder({{start:[0,0,40], end:[0,0,150], radius: s/4, slices:32}});\n"
        code += f"  var top = CSG.cylinder({{start:[0,0,150], end:[0,0,160], radius: (s/4)+10, slices:32}});\n"
        code += f"  return UTILS.mat(UTILS.rotZ(base1.union(base2).union(pillar).union(top), KINE_T));\n}}"
        
    # -----------------------------------------
    # 4. KIT AEROESPACIAL: DRON PARAMÉTRICO
    # -----------------------------------------
    elif h == "dron_frame":
        code += f"  var size = {p.get('drn_size', 150)}; var thick = {p.get('drn_thk', 5)}; var center_r = {p.get('drn_cr', 30)}; var arm_w = {p.get('drn_aw', 15)};\n"
        code += f"  var core = CSG.cylinder({{start: [0,0,0], end: [0,0,thick], radius: center_r}});\n"
        code += f"  var arm1 = CSG.cube({{center: [0,0,thick/2], radius: [size/2, arm_w/2, thick/2]}}).rotateZ(45);\n"
        code += f"  var arm2 = CSG.cube({{center: [0,0,thick/2], radius: [size/2, arm_w/2, thick/2]}}).rotateZ(-45);\n"
        code += f"  var frame = core.union(arm1).union(arm2);\n"
        code += f"  var hole = CSG.cylinder({{start: [0,0,-1], end: [0,0,thick+1], radius: center_r * 0.6}});\n"
        code += f"  frame = frame.subtract(hole);\n"
        code += f"  var m_pad_r = arm_w * 0.8; var dist = size/2; var angles = [45, 135, -45, -135];\n"
        code += f"  for(var i=0; i<4; i++) {{\n      var rad = angles[i] * Math.PI / 180; var px = dist * Math.cos(rad); var py = dist * Math.sin(rad);\n"
        code += f"      var pad = CSG.cylinder({{start: [px, py, 0], end: [px, py, thick], radius: m_pad_r}});\n"
        code += f"      var m_hole = CSG.cylinder({{start: [px, py, -1], end: [px, py, thick+1], radius: m_pad_r * 0.3}});\n"
        code += f"      frame = frame.union(pad).subtract(m_hole);\n  }}\n  return UTILS.mat(frame);\n}}"
    
    elif h == "dron_propeller":
        code += f"  var r = {p.get('drn_pr', 65)}; var blades = {p.get('drn_pb', 3)}; var pitch = {p.get('drn_pp', 30)}; var h = 6;\n"
        code += f"  var hub = CSG.cylinder({{start: [0,0,0], end: [0,0,h], radius: 6}}).subtract(CSG.cylinder({{start: [0,0,-1], end: [0,0,h+1], radius: 2.5}}));\n"
        code += f"  var prop = hub;\n"
        code += f"  for(var i=0; i<blades; i++) {{\n      var angle = (360 / blades) * i;\n"
        code += f"      var blade = CSG.cube({{center: [r/2, 0, h/2], radius: [r/2, 5, 0.8]}}).rotateX(pitch).translate([4, 0, 0]).rotateZ(angle);\n"
        code += f"      prop = prop.union(blade);\n  }}\n  return UTILS.mat(prop);\n}}"

    else:
        code += f"  return CSG.cube({{radius:[10,10,10]}});\n}}"

    return code
