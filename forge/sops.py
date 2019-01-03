import base64
import eventlet
import os
import subprocess
import sys
import yaml

from forge.tasks import sh, TaskError


SOPS_ENV_VARS = (
    'SOPS_KMS_ARN',
    'SOPS_PGP_FP',
    'SOPS_GCP_KMS_IDS',
    'SOPS_AZURE_KEYVAULT_URL',
)

def key_check():
    if not any(os.getenv(name) for name in SOPS_ENV_VARS):
        names = ", ".join(SOPS_ENV_VARS)
        raise TaskError(
            "you must configure Sops using one or more environment variables: %s" % names
        )

def decrypt(filename):
    return sh("sops", "--output-type", "binary", "-d", filename).output

def edit_secret(secret_file_path, create):
    if not os.path.exists(secret_file_path):
        if not create:
            raise TaskError("no such file: %s" % secret_file_path)
        key_check()
        content = sh("sops", "--input-type", "binary", "-e", "/dev/null").output
        try:
            with open(secret_file_path, "w") as fd:
                fd.write(content)
        except IOError, e:
            raise TaskError(e)
    try:
        subprocess.check_call(["sops", "--input-type", "binary", "--output-type", "binary", secret_file_path])
    except eventlet.green.subprocess.CalledProcessError, e:
        raise TaskError(e)

def view_secret(secret_file_path):
    try:
        subprocess.check_call(["sops", "--output-type", "binary", "-d", secret_file_path])
    except eventlet.green.subprocess.CalledProcessError, e:
        raise TaskError(e)
