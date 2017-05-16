import collections, logging, os, socket, yaml

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

def setup_yaml():
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    yaml.add_representer(collections.OrderedDict, dict_representer)
    yaml.add_constructor(_mapping_tag, dict_constructor)

HOSTNAME = socket.gethostname()
try:
    IP = socket.gethostbyname(socket.gethostname())
except socket.gaierror:
    IP = "unknown"

def setup_logging():
    logging.basicConfig(
        # filename=logPath,
        level=logging.INFO, # if appDebug else logging.INFO,
        format="%(asctime)s forge 0.0.1 %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.info("forge initializing on %s (resolved %s, pid %s)" % (HOSTNAME, IP, os.getpid()))

    NOISY = ('socketio', 'engineio')
    for n in NOISY:
        logging.getLogger(n).setLevel(logging.WARNING)

def setup():
    setup_yaml()
    setup_logging()
