# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AutoUpdateTAXREF
                                 A QGIS plugin
 Automatic update of the new version of TAXREF and species status
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-09-14
        copyright            : (C) 2024 by E. FAGE & C. ALLÉNÉ
        email                : elisa_fage@hotmail.fr
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AutoUpdateTAXREF class from file AutoUpdateTAXREF.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from .AutoUpdateTAXREF import AutoUpdateTAXREF
    return AutoUpdateTAXREF(iface)
