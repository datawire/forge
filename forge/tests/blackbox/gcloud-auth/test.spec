RUN rm forge.yaml
RUN gcloud auth activate-service-account --key-file key.json
RUN forge setup
OUT Registry type ; TYPE gcr
OUT url ; TYPE gcr.io
OUT project ; TYPE forgetest-project
OUT key ; TYPE -
OUT gcloud auth print-access-token
OUT <OUTPUT_ELIDED>
OUT <ELIDED>
OUT Login Succeeded
