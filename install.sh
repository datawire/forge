#!/usr/bin/env sh

{ # this ensures the entire script is downloaded #

set -e

# Get the script directory
SCRIPT_SOURCE="${0}"
while [ -h "$SCRIPT_SOURCE" ]; do # resolve $SCRIPT_SOURCE until the file is no longer a symlink
  SCRIPT_DIR="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" && pwd )"
  SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
  [[ $SCRIPT_SOURCE != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE" # if $SCRIPT_SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SCRIPT_DIR="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" && pwd )"

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

# Assume pretty verbose output
VERBOSITY=3

# Define a bunch of pretty output helpers
output () {
    lvl="$1"
    fmt="$2"
    text="$3"

    if [ $VERBOSITY -ge $lvl ]; then
        printf -- "$fmt" "$text"
    fi
}

msg () {
    output 1 "%s\n" "$1"
}

step () {
    output 2 "--> %s\n" "$1"
}

substep () {
    output 3 "-->  %s" "$1"
}

substep_ok() {
    output 3 "${green}OK${normal}\n" ""
}

substep_skip() {
    output 3 "${yellow}OK${normal}\n" "$1"
}

die() {
    printf "${red}FAIL${normal}"
    printf "\n\n        "
    printf "$1"
    printf "\n\n"
    exit 1
}

project="Skunkworks"
python_version="python2.7"
install_url="git+https://github.com/datawire/skunkworks.git"

while getopts ':qv' opt; do
    case $opt in
        :)  echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;

        q)  VERBOSITY=$(( $VERBOSITY - 1 ))
            if [ $VERBOSITY -lt 0 ]; then VERBOSITY=0; fi
            ;;

        v)  VERBOSITY=$(( $VERBOSITY + 1 ))
            ;;

        \?) echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

shift $((OPTIND-1))

install_dir="$1"

if [ -z "$install_dir" ]; then
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
    if [ -e ${install_dir} ]; then
        die "Install directory exists at '${install_dir}', please (re)move to proceed, or choose another install target."
    else
        substep_ok
    fi
}

step "Performing installation environment sanity checks..."
required_commands python virtualenv
is_project_installed

step "Creating ${install_dir} installation directory..."
virtualenv -q --python ${python_version} ${install_dir}

step "Installing ${project}..."

. ${install_dir}/bin/activate
pip --quiet install ${install_url}
deactivate

step "Installed!"

msg
msg "  ${project} has been installed into '${install_dir}'. You may want to"
msg "  add '${install_dir}/bin' to your PATH."
msg

} # this ensures the entire script is downloaded #
