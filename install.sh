#!/usr/bin/env sh

{ # this ensures the entire script is downloaded #

set -e

# Check if stdout is a terminal...
if [ -t 1 ]; then

    # See if it supports colors...
    ncolors=$(tput colors)

    if [ -n "$ncolors" ] && [ $ncolors -ge 8 ]; then
        bold="$(tput bold)"
        underline="$(tput smul)"
        standout="$(tput smso)"
        normal="$(tput sgr0)"
        black="$(tput setaf 0)"
        red="$(tput setaf 1)"
        green="$(tput setaf 2)"
        yellow="$(tput setaf 3)"
        blue="$(tput setaf 4)"
        magenta="$(tput setaf 5)"
        cyan="$(tput setaf 6)"
        white="$(tput setaf 7)"
    fi
fi

# Define a bunch of pretty output helpers
output () {
    fmt="$1"
    text="$2"

    printf -- "$fmt" "$text"
}

msg () {
    output "%s\n" "$1"
}

step () {
    output "--> %s\n" "$1"
}

substep () {
    output "-->  %s" "$1"
}

substep_ok() {
    output "${green}OK${normal}\n" ""
}

substep_skip() {
    output "${yellow}OK${normal}\n" "$1"
}

die() {
    printf "${red}FAIL${normal}"
    printf "\n\n        "
    printf "$1"
    printf "\n\n"
    exit 1
}

PROJECT="Forge"
PYTHON_VERSION="python2.7"
INSTALL_URL="git+https://github.com/datawire/forge.git"

if [ -z "$INSTALL_DIR" ]; then
    echo "Please specify an install directory."
    exit 1
fi

required_commands () {
    for cmd in $*; do
        substep "Checking for ${cmd}: "
        loc=$(command -v ${cmd} || true)
        if [ -n "${loc}" ]; then
            substep_ok
        else
            die "Cannot find ${cmd}, please install and try again."
        fi
    done
}

is_project_installed () {
    substep "Checking install target: "
    if [ -e ${INSTALL_DIR} ]; then
        die "Install directory exists at '${INSTALL_DIR}', please (re)move to proceed, or choose another install target."
    else
        substep_ok
    fi
}

step "Performing installation environment sanity checks..."
required_commands python virtualenv
is_project_installed

step "Creating ${INSTALL_DIR} installation directory..."
virtualenv -q --python ${PYTHON_VERSION} ${INSTALL_DIR}

step "Installing ${PROJECT}..."

. ${INSTALL_DIR}/bin/activate
pip --quiet install ${INSTALL_URL}
deactivate

step "${bold}Installed!${normal}"

msg
msg "  ${PROJECT} has been installed into '${INSTALL_DIR}'. You may want to"
msg "  add '${INSTALL_DIR}/bin' to your PATH."
msg

} # this ensures the entire script is downloaded #
