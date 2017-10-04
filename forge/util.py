import collections, errno, logging, os, socket, yaml

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

def setup_yaml():
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    yaml.add_representer(collections.OrderedDict, dict_representer)
    yaml.add_representer(os._Environ, dict_representer)
    yaml.add_constructor(_mapping_tag, dict_constructor)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s forge 0.0.1 %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    NOISY = ('socketio', 'engineio')
    for n in NOISY:
        logging.getLogger(n).setLevel(logging.WARNING)

def setup():
    setup_yaml()
    setup_logging()

def search_parents(name, start=None):
    prev = None
    path = start or os.getcwd()
    while path != prev:
        prev = path
        candidate = os.path.join(path, name)
        if os.path.exists(candidate):
            return candidate
        path = os.path.dirname(path)
    return None
