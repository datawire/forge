RUN git init
RUN git add .
RUN git commit -m "inital commit"
RUN git remote add origin https://github.com/datawire/forge.git
RUN forge deploy
RUN forge pull
OUT git pull
OUT git pull
