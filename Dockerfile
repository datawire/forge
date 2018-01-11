FROM datawire/forge-base:1

WORKDIR /work

COPY requirements.txt dev-requirements.txt ./
RUN pip install -r dev-requirements.txt
RUN pip install -r requirements.txt

# Bleh, this is really only necessary to make versioneer work
COPY .git .git
COPY scripts scripts
COPY forge forge
COPY examples examples
COPY docs docs
COPY Makefile setup.cfg setup.py versioneer.py MANIFEST.in LICENSE ./
COPY entrypoint.sh /

RUN pip install -e .

ENTRYPOINT ["/entrypoint.sh"]
