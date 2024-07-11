
# ====================================================================================================================
# ================================================ IMPORTAR LIBRERIAS ================================================ 
# ====================================================================================================================
from flask import Flask, render_template,request,session,redirect
from django.conf import settings
from django.conf.urls.static import static
from openseespy.opensees import *
import opseestools.utilidades as ut

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Establece el backend a 'Agg' (renderizado sin GUI)
# A continuación, importa las bibliotecas necesarias y genera la figura
import matplotlib.pyplot as plt
import opsvis as opsv
from PIL import Image


# ====================================================================================================================
# ======================================== GENERADOR DE SECCIONES (COLUMNAS) ========================================= 
# ====================================================================================================================

def fiber_elemens_Columns(BCol, HCol, c, cT, cM, cB, nT, nM, nB, fc, Fy, yloc):
    '''
    Parameters
    ---------------------------------------------------------------------------
      * BCol : float
            Column base in meters
      * HCol : float
            Column height in meters
      * c : float
            Column coating in meters
      * cT : list
            Number of Top bars
      * cM : list
            Number of Middle bars
      * cB : list
            Number of Bottom bars
      * nT : list
            Bar number (diameter in eighths of inch) - Top
      * nM : list
            Bar number (diameter in eighths of inch) - Middle
      * nB : list
            Bar number (diameter in eighths of inch) - Bottom           
      * fc : float
            Concrete f'c in KPa
      * fy : float
            Steel fy in KPa            
      * yloc : list
            y coordinates of each node    
            
    Returns
    ---------------------------------------------------------------------------
    section, tag_section
        Fiber element section, section tag
    '''

    ylist = [np.around(yloc[i+1]-yloc[i], 2) for i in range(len(yloc)-1)]
    pint = 5
    Lcol = np.median(ylist) * 1000
    # --------------------------------- Tag de los materiales --------------------------------
    Col_Conf = 1
    Col_Unconf = 3
    Steel = 5
    # --------------------------------- Concreto sin confinar --------------------------------
    E = 4700 * (fc/1000)**0.5 * 1000
    ec = 2 * fc / E
    fcu = 0.2 * fc
    Gfc = fc / 1000
    e20 = ut.e20Lobatto(Gfc, Lcol, pint, fc/1000, E/1000, ec)
    uniaxialMaterial('Concrete01', Col_Unconf, -fc, -ec, -fcu, -e20)
    # --------------------------------- Concreto confinado -----------------------------------
    k = 1.3
    fcc = fc * k
    ecc = 2 * fcc / E
    fucc = 0.2 * fcc
    Gfcc = 2 * (fcc / 1000)
    e20cc = ut.e20Lobatto(Gfcc, Lcol, pint, fcc/1000, E/1000, ecc)
    uniaxialMaterial('Concrete01', Col_Conf, -fcc, -ecc, -fucc, -e20cc)
    # ---------------------------------------- Acero -----------------------------------------
    Es = 210000000.0
    uniaxialMaterial('Steel01', 6, Fy, Es, 0.01)
    uniaxialMaterial('MinMax', Steel, 6, '-min', -0.008, '-max', 0.05)

    y1col = HCol / 2.0
    z1col = BCol / 2.0
    nFibZ = 1
    nFib = 20
    nFibCover = 3
    nFibZcore = 10
    nFibCore = 16

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    

    tag1 = 10
    sec1 = [0] * (6 + sum(NpTop) + sum(NpBtt) + NpMdd)
    sec1[0] = ['section', 'Fiber', tag1, '-GJ', 1.0e6]
    sec1[1] = ['patch', 'rect', Col_Conf, nFibCore, nFibZcore, c - y1col, c - z1col, y1col - c, z1col - c]
    sec1[2] = ['patch', 'rect', Col_Unconf, nFib, nFibZ, -y1col, -z1col, y1col, c - z1col]
    sec1[3] = ['patch', 'rect', Col_Unconf, nFib, nFibZ, -y1col, z1col - c, y1col, z1col]
    sec1[4] = ['patch', 'rect', Col_Unconf, nFibCover, nFibZ, -y1col, c - z1col, c - y1col, z1col - c]
    sec1[5] = ['patch', 'rect', Col_Unconf, nFibCover, nFibZ, y1col - c, c - z1col, y1col, z1col - c]

    
    def ordenar_lista_par_impar(lista):
        pares = [x for x in lista if x % 2 == 0]
        impares = [x for x in lista if x % 2 != 0]
        if pares and impares:
            return [pares[0], impares[0]]
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        idx = start_idx
        # 1 o 2 configuraciones de acero
        if len(bar_count) == 1:
            npunto = pos_count[0]
            for j in range(npunto):
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                else:
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                idx += 1
        else:
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                jini = j+1
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2]
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2]
                idx += 1
            
            else:
                # Se va a organizar la lista, colocando de primero el numero par y 
                # despues el impar, si hay 2 configuraciones de acero
                bar_count = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                        idx += 1
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    
    Steel = 55
    
    y1col = HCol / 2.0
    z1col = BCol / 2.0

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)
    ]
    
    
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        pares = [x for x in lista if x % 2 == 0]
        impares = [x for x in lista if x % 2 != 0]
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        idx = start_idx
        # 1 o 2 configuraciones de acero
        if len(bar_count) == 1:
            npunto = pos_count[0]
            for j in range(npunto):
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                jini = j+1
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            else:
                # Se va a organizar la lista, colocando de primero el numero par y 
                # despues el impar, si hay 2 configuraciones de acero
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 0
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = (Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col)
        else:
            sec1[suma] = (Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col)
        suma += 1

    return sec1, rect_patches


# ====================================================================================================================
# ========================================== GENERADOR DE SECCIONES (VIGAS) ========================================== 
# ====================================================================================================================


def fiber_elemens_Beams(BCol, HCol, c, cT, cB, nT, nB, fc, Fy, xloc):
    '''
    Parameters
    ---------------------------------------------------------------------------
      * BCol : float
            Column base in meters
      * HCol : float
            Column height in meters
      * c : float
            Column coating in meters
      * cT : list
            Number of Top bars
      * cB : list
            Number of Bottom bars
      * nT : list
            Bar number (diameter in eighths of inch) - Top
      * nB : list
            Bar number (diameter in eighths of inch) - Bottom           
      * fc : float
            Concrete f'c in KPa
      * fy : float
            Steel fy in KPa            
      * xloc : list
            x coordinates of each node  
            
    Returns
    ---------------------------------------------------------------------------
    section, tag_section
        Fiber element section, section tag
    '''
    # longitud de la viga
    xlist = [np.around(xloc[i+1]-xloc[i], 2) for i in range(len(xloc)-1)]
    pint = 5
    Lvig = np.median(xlist) * 1000
    # Tag de los materiales
    Vig_Conf = 2
    Vig_Unconf = 4
    Steel = 7
    # Concreto sin confinar 
    E = 4700 * (fc/1000)**0.5 * 1000
    ec = 2 * fc / E
    fcu = 0.2 * fc
    Gfc = fc / 1000
    e20 = ut.e20Lobatto(Gfc, Lvig, pint, fc/1000, E/1000, ec)
    uniaxialMaterial('Concrete01', Vig_Unconf, -fc, -ec, -fcu, -e20)
    # Concreto confinado 
    k = 1.3
    fcc = fc * k
    ecc = 2 * fcc / E
    fucc = 0.2 * fcc
    Gfcc = 2 * (fcc / 1000)
    e20cc = ut.e20Lobatto(Gfcc, Lvig, pint, fcc/1000, E/1000, ecc)
    uniaxialMaterial('Concrete01', Vig_Conf, -fcc, -ecc, -fucc, -e20cc)
    # Acero
    Es = 210000000.0
    uniaxialMaterial('Steel01', 8, Fy, Es, 0.01)
    uniaxialMaterial('MinMax', Steel, 8, '-min', -0.008, '-max', 0.05)
    #--------------------------------------------------------------------------

    y1col = HCol / 2.0
    z1col = BCol / 2.0
    nFibZ = 1
    nFib = 20
    nFibCover = 3
    nFibZcore = 10
    nFibCore = 16

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    
    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    

    tag1 = 12
    sec1 = [0] * (6 + sum(NpTop) + sum(NpBtt))
    sec1[0] = ['section', 'Fiber', tag1, '-GJ', 1.0e6]
    sec1[1] = ['patch', 'rect', Vig_Conf, nFibCore, nFibZcore, c - y1col, c - z1col, y1col - c, z1col - c]
    sec1[2] = ['patch', 'rect', Vig_Unconf, nFib, nFibZ, -y1col, -z1col, y1col, c - z1col]
    sec1[3] = ['patch', 'rect', Vig_Unconf, nFib, nFibZ, -y1col, z1col - c, y1col, z1col]
    sec1[4] = ['patch', 'rect', Vig_Unconf, nFibCover, nFibZ, -y1col, c - z1col, c - y1col, z1col - c]
    sec1[5] = ['patch', 'rect', Vig_Unconf, nFibCover, nFibZ, y1col - c, c - z1col, y1col, z1col - c]

    def ordenar_lista_par_impar(lista):
        pares = [x for x in lista if x % 2 == 0]
        impares = [x for x in lista if x % 2 != 0]
        if pares and impares:
            return [pares[0], impares[0]]
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        idx = start_idx
        # 1 o 2 configuraciones de acero
        if len(bar_count) == 1:
            npunto = pos_count[0]
            for j in range(npunto):
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                else:
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                idx += 1
        else:
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                jini = j+1
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2]
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2]
                idx += 1
            
            else:
                # Se va a organizar la lista, colocando de primero el numero par y 
                # despues el impar, si hay 2 configuraciones de acero
                bar_count = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                        idx += 1
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    return sec1, tag1

def Graph_FiberSection_Beams(BCol,HCol,c, cT, cB, nT, nB):
    
    Steel = 555
    
    y1col = HCol / 2.0
    z1col = BCol / 2.0

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)
    ]
    
    
    sec1 = [0]*(sum(NpTop) + sum(NpBtt))
    
    def ordenar_lista_par_impar(lista):
        pares = [x for x in lista if x % 2 == 0]
        impares = [x for x in lista if x % 2 != 0]
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        idx = start_idx
        # 1 o 2 configuraciones de acero
        if len(bar_count) == 1:
            npunto = pos_count[0]
            for j in range(npunto):
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                jini = j+1
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            else:
                # Se va a organizar la lista, colocando de primero el numero par y 
                # despues el impar, si hay 2 configuraciones de acero
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 0
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    return sec1, rect_patches
