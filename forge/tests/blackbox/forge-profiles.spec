FILE service.yaml
name: forge-profiles-TEST_ID
END

FILE key.json
{
  "type": "service_account",
  "project_id": "forgetest-project",
  "private_key_id": "c49f1dd1c0c55418796c510af2cc7f46c4327058",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDymqNXy8GUKSDx\n8/QBPTziiOyZExO1LNa31I5mc+ut4/KPEHzVtCHETpE610utxleUoyt64b9SgYEv\nySEjBJz1Nt36NNM8Pb2/+ju0L6Ha+Cui5iqfKmkHxSbCFIk25s7bh6zWWoQLw3hH\nkK7dSAJ4yeX8/xaExuYOJx9q4mkn7uNuBkIhx/YE17p2NRmuDQR8YxUadz9QgcEL\ntDXb5zBudh1MsLgBK98gZTedDNtlJMHE2zLhIJTPJ7VNwcaPP34OD5W06wcllAjZ\nxmA3eKnl/M8jdLtfrYBituNtQi2UMsNKbAffYWq1XLAvaBMLs+l9Bz4NWCxJJtTB\n0UpGt/BzAgMBAAECggEARNJgdxYKzrySJ4E0nathG8SLFeunAhT7vn+Se/bzi0to\ncnRTbY5hq9477czIn73t93EIcx4aV838N3GfsF7tJdUQSJv2tpavPwg+KqH+kO8o\n9dfEjI2L6RPhKFqKCGSWlwlYmyBnaCzl8KtXJ9f3N4vS7h/xI+6GscogbAJZoWVi\nfODsXZQqO854NwbtsjZj0xBE9ZCEc2MpcXOPn3zYcj5oRP5bNYHd8zsQ6iWGmNnp\n1IloaAFmQDIwijqraGaYHFEATB/2QwXwTjvdr0NVo7tmMkUwJ/wMxxTLgALeddu4\nfuwh1ithkzS8KRK77S/D4PSfpvtUSEu5gkZmslbZ3QKBgQD96FAysHywri/QvElg\nuqhzOmBs2pNmkt9tS5wKSc+oVZ0FlL0qMPomZOZqn2g7Os3p60LMbsriEqn/rvQO\nd3oYjWht2drdqIRPy1R7nVv7/34AYr0SIKJ/W/l3o0FllLN7hJLiJvgxCERyj1Id\na6PWbXYEW8hkbfZi+X5flMSWrwKBgQD0mnom2By5j/SzGg1doMCqb7tCxptF5tFc\nKYBtPORihm34iA77AJK5HBb7Wb4k/WwWXYGOliqRXvQ+MlDcM/iyCvfoHuqz/BWe\nYc+21GKhgbbRJz3XX1uS8UBSaEDmgHLAfXkGLvqtst+ra8MicJ+Ycfc8qNa5wRhy\nTkbwAAKzfQKBgQD0AECxtbDeCUaiDY9miXo/4aWwdgyY0iQsYDDAIlaQqlWPe3Se\nCxsZsnVLmY0M/mHLne4/j2khAFamA3c+P8rxtVLZ3jXaNYuRMxEpCfvPm6N2s2yG\n8x21zqlaM2UxPUmONcUB1/lDBXLhtKFw7HQyKFb1sU5OVO4mByVOrSSOuQKBgQDq\nWNoxPxp+OkrCEXK+wlX0tOmfd3KqTRNGjkiJ4C4bqxnPZGOd3ZW1HhFyrS98dwRI\nhTusJXkRH/03XbOU1YIu6k1LqdtJp3n67VE5pE/+1q0Vw9f+8VBl/xeWHGYZsPTA\nMTZzUy0+n8KllLA23do6Du5Fwqk+/J50XUSfihMMbQKBgH5lRaF14hj1oGckYt3P\nM45hTlW+/wUC1kJGd1gxtdpIMm3RHVGdGl9BGOwJVvAAIigbO8w01279xImcXcCb\nD+XBlvw1pDT3QfFs1t7T+x8blVqoflxsfnQW6eQB5W9arZ9CZBpSzzECppOdus46\n6J1fVJxDL9Nq5ykxjYhDYXY1\n-----END PRIVATE KEY-----\n",
  "client_email": "forge-test@forgetest-project.iam.gserviceaccount.com",
  "client_id": "106271144892298981142",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/forge-test%40forgetest-project.iam.gserviceaccount.com"
}
END

FILE k8s/DUMMY
END

FILE Dockerfile
FROM alpine:3.6
END

FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg

profiles:
  foo:
    registry:
      type: gcr
      url: gcr.io
      project: forgetest-project
END

RUN docker login registry.hub.docker.com/forgeorg -u forgetest -p forgetest
RUN gcloud auth activate-service-account --key-file key.json
RUN forge build
OUT docker push registry.hub.docker.com/forgeorg/forge-profiles
RUN forge --profile foo build
OUT docker push gcr.io/forgetest-project/forge-profiles
