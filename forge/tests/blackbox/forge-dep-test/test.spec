RUN git init
RUN git add .
RUN git commit -m "inital commit"
RUN git remote add origin git@github.com:datawire/forge.git
RUN forge deploy
RUN forge pull
OUT git pull
OUT git pull
