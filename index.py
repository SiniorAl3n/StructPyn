# ============================ IMPORTAR LIBRERIAS ============================
from flask import Flask, render_template,request,session,redirect, jsonify, session, url_for
from django.conf import settings
from django.conf.urls.static import static
from openseespy.opensees import *
import opseestools.utilidades as ut
import opseestools.analisis as an

import os
import numpy as np
import Utilities_DN as ut_DN

import io
import base64

#import matplotlib
#matplotlib.use('Agg')  # Establece el backend a 'Agg' (renderizado sin GUI)

# A continuación, importa las bibliotecas necesarias y genera la figura
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import opsvis as opsv

from PIL import Image

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para usar sesiones

app.config['UPLOAD_FOLDER'] = 'static' 

@app.route('/') # Lo que va a aparecer como página principal. el objeto app es el importante
def home():
    return render_template('home.html') # Para retornar en el archivo home.html

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    # Aquí puedes agregar el código para almacenar los mensajes en una base de datos o enviarlos por correo electrónico
    # Por ahora, simplemente imprimiremos los datos en la consola
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Message: {message}")
    
    return render_template('contact_us.html', message="Thank you for your feedback!")
  

@app.route('/generate_nodes', methods=['POST'])
def generate_nodes():
    data = request.get_json()
    x_coords = request.json.get('x', [])
    y_coords = request.json.get('y', [])

    # Guardar coordenadas en la sesión
    session['x_coords'] = x_coords
    session['y_coords'] = y_coords
    
    # Generar el gráfico de nodos
    plt.figure(figsize=(6, 6))
    ax = plt.gca()
    
    for i in range(len(x_coords)):
        for j in range(len(y_coords)):
            plt.plot(x_coords[i], y_coords[j], '.k', markersize=9)
        
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    
    # Personalizar la gráfica
    ax.grid(True, alpha = 0.4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Mejorar la calidad del texto
    plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
    
    # Guardar el gráfico en memoria
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    
    return jsonify(image=image_base64)

@app.route('/modulo1', methods=['GET'])
def modulo1():
    return render_template('modulo1.html')


@app.route('/modulo2', methods=['GET'])
def modulo2():
    return render_template('modulo2.html')


@app.route('/step2', methods=['GET', 'POST'])
def step2():
    if request.method == 'POST':
        # Recoger los datos del formulario enviados por AJAX
        data = request.get_json()
        sa = float(data.get('sa'))
        cortes_columnas = [float(i) for i in data.get('cortes_columnas')]
        cargas_vigas = [float(i) for i in data.get('cargas_vigas')]
        cargas_techo = [float(i) for i in data.get('cargas_techo')]
        fc_concreto = float(data.get('fc_concreto'))
        fy_acero = float(data.get('fy_acero'))
        
        # Guardar los datos en la sesión
        session['sa'] = sa
        session['cortes_columnas'] = cortes_columnas
        session['cargas_vigas'] = cargas_vigas
        session['fc_concreto'] = fc_concreto
        session['fy_acero'] = fy_acero
        
        return jsonify({"message": "success"})
    
    x_coords = session.get('x_coords', [])
    y_coords = session.get('y_coords', [])
    return render_template('step2.html', x_coords=x_coords, y_coords=y_coords)


@app.route('/step3', methods=['GET', 'POST'])
def step3():
    if request.method == 'POST':
        data = request.get_json()
        BCol = float(data.get('valBsec'))
        HCol = float(data.get('valHsec'))
        c = float(data.get('valRsec'))
        cM = [int(i) for i in data.get('cbarMdd')]
        nM = data.get('nbarMdd')
        cT = [int(i) for i in data.get('cbarTop')]
        nT = data.get('nbarTop')
        cB = [int(i) for i in data.get('cbarBtt')]
        nB = data.get('nbarBtt')

        # Convertir nM, nT, nB a listas si no lo son
        if isinstance(nM, str):
            nM = [nM]
        if isinstance(nT, str):
            nT = [nT]
        if isinstance(nB, str):
            nB = [nB]

        if isinstance(cM, float):
            cM = [cM]
        if isinstance(cT, float):
            cT = [cT]
        if isinstance(cB, float):
            cB = [cB]

        # Guardar los datos en la sesión
        session['BCol'] = BCol
        session['HCol'] = HCol
        session['c'] = c
        session['cM'] = cM
        session['nM'] = nM
        session['cT'] = cT
        session['nT'] = nT
        session['cB'] = cB
        session['nB'] = nB

        fiber_layers, rect_patches = ut_DN.Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB)

        # Generate the section graph
        fig, ax = plt.subplots(figsize=(6, 6))
        colors = {1: '#9F9F9F', 3: '#D9D9D9'}

        for rect in rect_patches:
            _, _, _, y1, x1, y2, x2 = rect
            width = x2 - x1
            height = y2 - y1
            color = colors[rect[0]]
            rect = patches.Rectangle((x1, y1), width, height, linewidth=1, edgecolor='black', facecolor=color)
            ax.add_patch(rect)

        for layer in fiber_layers:
            _, _, mark_size, y1, x1, y2, x2 = layer
            
            
            if mark_size == 0.000071: # #3
                mark_size_val = 7
                mark_color = '#B2796E'
            elif mark_size == 0.000127: # #4
                mark_size_val = 8
                mark_color = '#B0AD70'
            elif mark_size == 0.000198: # #5
                mark_size_val = 9
                mark_color = '#7EB070'
            elif mark_size == 0.000286: # #6
                mark_size_val = 10
                mark_color = '#6EB4B2'
            elif mark_size == 0.000387: # #7
                mark_size_val = 11
                mark_color = '#707CB0'
            elif mark_size == 0.000508: # #8
                mark_size_val = 12
                mark_color = '#B26EB0'
            
            border_color = 'lightgray'
            
            x_positions = [x1, x2]
            y_positions = [y1, y2]
            ax.plot(x_positions, y_positions, 'o', markersize=mark_size_val, color=mark_color, markeredgecolor=border_color, markeredgewidth=1.0)

        # Ajustar los ejes y mostrar la gráfica
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_aspect('equal', 'box')

        plt.xlabel('Section base')
        plt.ylabel('Section height')

        # Mejorar la calidad del texto
        plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
            
        # Guardar el gráfico en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return jsonify({"image": image_base64})
    
    return render_template('step3.html')


@app.route('/step4', methods=['GET', 'POST'])
def step4():
    if request.method == 'POST':
        data = request.get_json()
        BVig = float(data.get('valBsec_Vig'))
        HVig = float(data.get('valHsec_Vig'))
        c_Vig = float(data.get('valRsec_Vig'))
        cT_Vig = [int(i) for i in data.get('cbarTop_Vig')]
        nT_Vig = data.get('nbarTop_Vig')
        cB_Vig = [int(i) for i in data.get('cbarBtt_Vig')]
        nB_Vig = data.get('nbarBtt_Vig')

        # Convertir nT, nB a listas si no lo son
        if isinstance(nT_Vig, str):
            nT_Vig = [nT_Vig]
        if isinstance(nB_Vig, str):
            nB_Vig = [nB_Vig]

        if isinstance(cT_Vig, float):
            cT_Vig = [cT_Vig]
        if isinstance(cB_Vig, float):
            cB_Vig = [cB_Vig]

        # Guardar los datos en la sesión
        session['BVig'] = BVig
        session['HVig'] = HVig
        session['c_Vig'] = c_Vig
        session['cT_Vig'] = cT_Vig
        session['nT_Vig'] = nT_Vig
        session['cB_Vig'] = cB_Vig
        session['nB_Vig'] = nB_Vig

        fiber_layers, rect_patches = ut_DN.Graph_FiberSection_Beams(BVig,HVig,c_Vig, cT_Vig, cB_Vig, nT_Vig, nB_Vig)

        # Generate the section graph
        fig, ax = plt.subplots(figsize=(6, 6))
        colors = {1: '#9F9F9F', 3: '#D9D9D9'}

        for rect in rect_patches:
            _, _, _, y1, x1, y2, x2 = rect
            width = x2 - x1
            height = y2 - y1
            color = colors[rect[0]]
            rect = patches.Rectangle((x1, y1), width, height, linewidth=1, edgecolor='black', facecolor=color)
            ax.add_patch(rect)

        for layer in fiber_layers:
            _, _, mark_size, y1, x1, y2, x2 = layer
            
            
            if mark_size == 0.000071: # #3
                mark_size_val = 7
                mark_color = '#B2796E'
            elif mark_size == 0.000127: # #4
                mark_size_val = 8
                mark_color = '#B0AD70'
            elif mark_size == 0.000198: # #5
                mark_size_val = 9
                mark_color = '#7EB070'
            elif mark_size == 0.000286: # #6
                mark_size_val = 10
                mark_color = '#6EB4B2'
            elif mark_size == 0.000387: # #7
                mark_size_val = 11
                mark_color = '#707CB0'
            elif mark_size == 0.000508: # #8
                mark_size_val = 12
                mark_color = '#B26EB0'
            
            border_color = 'lightgray'
            
            x_positions = [x1, x2]
            y_positions = [y1, y2]
            ax.plot(x_positions, y_positions, 'o', markersize=mark_size_val, color=mark_color, markeredgecolor=border_color, markeredgewidth=1.0)

        # Ajustar los ejes y mostrar la gráfica
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_aspect('equal', 'box')

        plt.xlabel('Section base')
        plt.ylabel('Section height')

        # Mejorar la calidad del texto
        plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
            
        # Guardar el gráfico en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return jsonify({"image": image_base64})
    
    return render_template('step4.html')

@app.route('/step5', methods=['GET', 'POST'])
def step5():
    if request.method == 'POST':

        # 1).  Cargar informacion de las otras secciones >>>
        # Coordenadas 'x' y 'y' :
        xloc = session.get('x_coords', [])  # List
        yloc = session.get('y_coords', [])  # List

        # Sa de diseno y corte en la base de las columnas :
        Sad = session.get('sa', [])  # Float
        CrtBase = session.get('cortes_columnas', [])  # List

        # Cargas en las vigas :
        val_Mload = session.get('cargas_vigas', []) # List
        val_Rload = session.get('cargas_techo', []) # List

        # fc y fy :
        fc = session.get('fc_concreto', [])*1000  #int
        fy = session.get('fy_acero', [])*1000  #int

        # Propiedades seccion columna :
        BCol = session.get('BCol')  # Float
        HCol = session.get('HCol')  # Float
        c = session.get('c')  # Float
        cM = session.get('cM')  # List
        nM = session.get('nM')  # List
        cT = session.get('cT')  # List
        nT = session.get('nT')  # List
        cB = session.get('cB')  # List
        nB = session.get('nB')  # List

        # Propiedades seccion viga :
        BVig = session.get('BVig')  # Float
        HVig = session.get('HVig')  # Float
        c_Vig = session.get('c_Vig')  # Float
        cT_Vig = session.get('cT_Vig')  # List
        nT_Vig = session.get('nT_Vig')  # List
        cB_Vig = session.get('cB_Vig')  # List
        nB_Vig = session.get('nB_Vig')  # List

        # 2).  Generar el modelo >>>
        wipe()            # ------------------------------------------ Resetear el modelo 
        diafragma = 1     # ------------------------------------------ Colocar 1 si se desea diafragma en cada piso
        pushlimit = 0.05     # --------------------------------------- limite del pushover
        model('basic','-ndm',2,'-ndf',3)     # ----------------------- Definir modelo 2D

        # 3).  Generar nodos >>>
        Npisos = len(yloc)-1     # ----------------------------------- Número de pisos   
        nx = len(xloc)           # ----------------------------------- Número de coordenadas x
        ny = len(yloc)           # ----------------------------------- Número de coordenadas y
        for i in range(ny):
            for j in range(nx):
                nnode = 1000*(j+1)+i     # --------------------------- Tag del nodo
                node(nnode, xloc[j], yloc[i])  # --------------------- Generar el nodo

        # 4).  Restricciones y asignacion de masas >>>
        empotrado = [1,1,1]     # ------------------------------------ Restriccion x, y, z             
        fixY(0.0,*empotrado)     # ----------------------------------- Empotrar los nodos que se encuentran en el nodo 0.0
        Masa_list = np.zeros((Npisos,len(CrtBase)))     # ------------ Matriz que almacena la masa de cada nodo por piso
        for piso in range(Npisos):
            for indx, crt in enumerate(CrtBase):
                Masa_list[piso,indx] = ((crt/Sad)/9.81)/Npisos     # - Calular las masas en los nodos por piso
        Wedificio = np.sum(CrtBase)/Sad     # ------------------------ Peso del edificio                       
        for i in range(1,ny):
            for j in range(nx):
                nodemass = 1000*(j+1)+i     # ------------------------ Tag del nodo
                mass(nodemass,Masa_list[i-1][j],Masa_list[i-1][j],0.0) # - Asignar las masas en el nodo

        # 5).  Diafragma rigido >>>
        if diafragma == 1:
            for j in range(1,ny):
                for i in range(1,nx):
                    masternode = 1000 + j     # ---------------------- Nodo maestro
                    slavenode = 1000*(i+1) + j     # ----------------- Demas nodos del piso
                    equalDOF(masternode,slavenode,1)     # ----------- EqualDOF por piso -- asigan el diafragma rigido

        # 6).  Generar secciones >>>
        sec1, tag1 = ut_DN.fiber_elemens_Columns(BCol, HCol, c, cT, cM, cB, nT, nM, nB, fc, fy, yloc)

        opsv.fib_sec_list_to_cmds(sec1)
        beamIntegration('Lobatto', tag1, tag1, 5)

        sec2, tag2 = ut_DN.fiber_elemens_Beams(BVig, HVig, c_Vig, cT_Vig, cB_Vig, nT_Vig, nB_Vig, fc, fy, xloc)

        opsv.fib_sec_list_to_cmds(sec2)
        beamIntegration('Lobatto', tag2, tag2, 5)

        # 7).  Transformaciones >>>
        lineal = 1
        geomTransf('Linear',lineal)
        pdelta = 2
        geomTransf('PDelta',pdelta)

        # 8).  Generar columnas >>>
        TagColumns = []
        for i in range(ny-1):
            for j in range(nx):
                nodeI = 1000*(j+1)+i
                nodeJ = 1000*(j+1)+(i+1)
                eltag = 10000*(j+1) + i
                TagColumns.append(eltag)
                element('forceBeamColumn',eltag,nodeI,nodeJ,pdelta,tag1)

        # 9).  Generar vigas >>>
        TagVigas = []
        for i in range(1, ny):
            for j in range(nx - 1):
                nodeI = 1000 * (j + 1) + i
                nodeJ = 1000 * (j + 2) + i
                eltag = 100000 * (j + 1) + i
                TagVigas.append(eltag)
                element('forceBeamColumn', eltag, nodeI, nodeJ, lineal, tag2)

        # 10).  Cargas de gravedad >>>
        timeSeries('Linear', 1)
        pattern('Plain', 1, 1)
        # 10.1).  Para columnas :
        for i in range(nx):
            for j in range(1, ny):
                nodeCol = 1000 * (i + 1) + j
                wcol_list = BCol * HCol * 24 * (yloc[j] - yloc[j - 1])
                load(nodeCol, 0.0, -wcol_list, 0.0)
        # 10.1).  Para vigas :
        for i in range(1,ny):
            for j in range(nx-1):
                if i == Npisos+1:
                    eltag = 100000*(j+1) + i
                    eleLoad('-ele',eltag,'-type','beamUniform',-val_Rload[j])
                else:
                    eltag = 100000*(j+1) + i
                    eleLoad('-ele',eltag,'-type','beamUniform',-val_Mload[j])

        # Guardar el gráfico en memoria
        fig_defo1 = plt.figure()
        opsv.plot_defo()

        buf_defo1 = io.BytesIO()
        plt.savefig(buf_defo1, format='png')
        buf_defo1.seek(0)
        image_base64_defo1 = base64.b64encode(buf_defo1.read()).decode('utf-8')
        buf_defo1.close()
        plt.close()

        # 11).  Analisis de gravedad >>>
        w1 = eigen(1)
        T = 2 * 3.1416 / np.sqrt(w1)
        an.gravedad()
        loadConst('-time', 0.0)

        # 12).  Analisis pushover >>>
        w2 = eigen(1)
        T2 = 2 * 3.1416 / np.sqrt(w2)

        timeSeries('Linear', 2)
        pattern('Plain', 2, 2)

        tagsnodos = getNodeTags()
        ntecho = tagsnodos[-1]
        hedif = nodeCoord(ntecho)[1]

        POnodes = tagsnodos[int(1):int(len(tagsnodos) / nx)]
        posnodes = []
        for i in range(len(POnodes)):
            posnodes.append(i + 1)
        valor = sum(posnodes)

        for indx, val in enumerate(tagsnodos[int(1):int(len(tagsnodos) / nx)]):
            load(val, (indx + 1) / valor, 0.0, 0.0)

        [dtecho, Vcorte] = an.pushover2(0.05*hedif, 0.001, ntecho, 1, [hedif, Wedificio])

        # Guardar el gráfico en memoria
        fig_defo2 = plt.figure()
        opsv.plot_defo()
        plt.title('Pushover deformation')
        plt.xlabel('X Coordinate', fontsize=11)
        plt.ylabel('Y Coordinate', fontsize=11)

        buf_defo2 = io.BytesIO()
        plt.savefig(buf_defo2, format='png')
        buf_defo2.seek(0)
        image_base64_defo2 = base64.b64encode(buf_defo2.read()).decode('utf-8')
        buf_defo2.close()
        plt.close()

        roof_drift = [(dtecho[i]/hedif)*100 for i in range(len(dtecho))]
        base_shear = [Vcorte[i]/Wedificio for i in range(len(Vcorte))]

        # Encontrar el punto de capacidad máxima
        max_index = np.argmax(base_shear)
        max_roof_drift = roof_drift[max_index]
        max_base_shear = base_shear[max_index]

        # Encontrar el 80% de la capacidad máxima
        base_shear_80 = 0.8 * max_base_shear

        # Encontrar el índice del 80% de la capacidad máxima
        index_80 = np.where(base_shear >= base_shear_80)[0][0]
        roof_drift_80 = roof_drift[index_80]
        base_shear_80_actual = base_shear[index_80]

        # Crear la gráfica y resaltar los puntos importantes
        fig = plt.figure()
        plt.plot(roof_drift, base_shear,  label='Capacity curve', color='#13272C')
        plt.plot(max_roof_drift, max_base_shear,'D', label='Max capacity', color='#E97132')
        plt.text(max_roof_drift, max_base_shear, f'({np.around(max_roof_drift,2)},{np.around(max_base_shear,2)})', fontsize=9, verticalalignment='bottom')
        plt.plot(roof_drift_80, base_shear_80_actual,'X', label='Capacity (80%)', color='#65A753')
        plt.text(roof_drift_80, base_shear_80_actual, f'({np.around(roof_drift_80,2)},{np.around(base_shear_80_actual,2)})', fontsize=9, verticalalignment='bottom')

        plt.xlabel('Roof drift (%)', fontsize=11)
        plt.ylabel('Normalized seismic base shear (V/W)', fontsize=11)
        plt.title('RCFs Capacity curve')
        plt.legend()

        # Personalizar la gráfica
        plt.grid(True, alpha = 0.4)
        # Mejorar la calidad del texto
        plt.rcParams.update({'font.family': 'Calibri'})

        # Guardar el gráfico en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()

        return jsonify({"image": image_base64, "defo1": image_base64_defo1, "defo2": image_base64_defo2})

    return render_template('step5.html')
    

if __name__ == '__main__':
    app.run(debug=True)


