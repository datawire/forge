import collections, errno, hashlib, logging, os, socket, yaml

def find(root, exclude=(".git",)):
    files = []

    for path, dirnames, filenames in os.walk(root):
        for ex in exclude:
            if ex in dirnames:
                dirnames.remove(ex)
        for name in filenames:
            full = os.path.join(path, name)
            relative = os.path.relpath(full, start=root)
            files.append(relative)

    files.sort()
    return files

def shadir(root):
    result = hashlib.sha1()
    files = find(root)
    result.update("files %s\0" % len(files))
    for name in files:
        result.update("file %s\0" % name)
        try:
            with open(os.path.join(root, name)) as fd:
                result.update(fd.read())
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
    return result.hexdigest()

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
