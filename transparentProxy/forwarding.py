#from nova import utils
import logging
from multiprocessing.managers import BaseManager, RemoteError


class ForwardingManager(BaseManager):
    pass


class FMWrapper(object):
    '''
    '''

    def __init__(self, _fm_instance):
        # Expose all attributes from the Forward Manager instance
        self.base_client = _fm_instance

    def __getattr__(self, name):
        obj = getattr(self.base_client, name)
        if callable(obj):
            obj = self.proxy(obj)
        return obj

    def proxy(self, obj):
        def wrapper(*args, **kwargs):
            ret = obj(*args, **kwargs)
            return ret
        return wrapper


class Forwarding(object):

    _log = logging.getLogger("ForwardingClient")
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._manager = None
        self._forwarding = None
        self._connect()

    def open(self, *args, **kwargs):
        return self._manager.open(*args, **kwargs)

    def _connect(self):
        self._manager = ForwardingManager(address="/tmp/fmanager.sock",
                                          authkey='')
        self._manager.register('instance')
        self._manager.register('open')
        self._log.debug("Trying to connect forwarding manager")
        try:
            self._manager.connect()
        except Exception as ex:
            msg = "Connect to forwarding manager failed: %s" % ex
            self._log.error(msg)
            sys.exit(-1)

        self._forwarding = self._manager.instance()
        self.fmProxy = FMWrapper(self._forwarding)

    def __getattr__(self, name):
        try:
            ret = getattr(self.fmProxy, name)
            return ret
        except RemoteError:
            self._connect()
            raise RuntimeError(
                "Connection to the Forwarding Manager is broken."
                " Failed call to %s" % self.name)
