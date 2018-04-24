import os
import subprocess
import sys


def key_check():
    if not os.getenv('SOPS_KMS_ARN'):
        sys.exit("You must obtain the master key and export it in the 'SOPS_KMS_ARN' environment variable")

def decrypt(secret_file_dir, secret_file_name):
    key_check()
    secret_file_path = os.path.join(secret_file_dir, secret_file_name)
    temp_secret_file_path = os.path.join(secret_file_dir, "tmp-" + secret_file_name)
    os.rename(secret_file_path, temp_secret_file_path)
    with open(secret_file_path, "w") as decrypted_file:
        subprocess.call(["sops", "-d", temp_secret_file_path], stdout=decrypted_file)

def decrypt_cleanup(secret_file_dir, secret_file_name):
    secret_file_path = os.path.join(secret_file_dir, secret_file_name)
    temp_secret_file_path = os.path.join(secret_file_dir, "tmp-" + secret_file_name) 
    os.remove(secret_file_path)
    os.rename(temp_secret_file_path, secret_file_path)

def edit_secret(secret_file_path):
    key_check()
    subprocess.call(["sops", secret_file_path])

def view_secret(secret_file_path):
    key_check()
    subprocess.call(["sops", "-d", secret_file_path])
