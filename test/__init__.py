# import qgis libs so that ve set the correct sip api version
import qgis   # pylint: disable=W0611  # NOQA

def classFactory(iface):  # pylint: disable=invalid-name
    """Load AutoUpdateTAXREF class from file AutoUpdateTAXREF.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from ..AutoUpdateTAXREF import AutoUpdateTAXREF
    return AutoUpdateTAXREF(iface)