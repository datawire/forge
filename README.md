# Forge

Forge is a build/deployment system for microservices running on Kubernetes. Forge is designed to produce deployable services (i.e., Docker images + Kubernetes YAML) instead of just binary artifacts.

For more information on how to use Forge, visit http://forge.sh.

# Developing Forge

```bash
mkdir forgedev
cd forgedev
virtualenv py2 --python python2
git clone https://github.com/datawire/forge.git
cd forge
pip install -e .
```
