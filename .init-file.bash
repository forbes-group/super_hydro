export PS1="\h:\W \u\$ "
source $(conda info --base)/etc/profile.d/conda.sh

# Assume that this is set by running anaconda-project run shell
CONDA_ENV="${CONDA_PREFIX}"
conda deactivate
conda activate                 # Activate the base environment
conda activate "${CONDA_ENV}"  # Now activate the previously set environment
alias ap="anaconda-project"
alias apr="anaconda-project run"

_exclude_array=(
    -name ".hg" -or
    -name ".git" -or
    -name '.eggs' -or
    -name '.ipynb_checkpoints' -or
    -name 'envs' -or 
    -name "*.sage-*" -or
    -name "_build" -or
    -name "build" -or
    -name "__pycache__"
)
# Finding stuff
function finda {
    find . \( "${_exclude_array[@]}" \) -prune -or -type f \
         -print0 | xargs -0 grep -H "${*:1}"
}

function findf {
    include_array=( -name "*.$1" )
    find . \( "${_exclude_array[@]}" \) -prune -or \( "${include_array[@]}" \) \
         -print0 | xargs -0 grep -H "${*:2}"
}

function findpy { findf py "${*}"; }
function findipy { findf ipynb "${*}"; }
function findjs { findf js "${*}"; }
function findcss { findf css "${*}"; }

# Personal customizations... unlikely to work unless you configure your machine like mine.
if [ "$(whoami)" == "mforbes" ]; then
    # Write this as a function so that we can run it in the background
    # Should make these use existing variables
    EMACSNAME=${EMACSNAME:-"Emacs"}
    EMACSAPP=${EMACSAPP:-"/Applications/${EMACSNAME}.app"}
    export EMACS=${EMACS:-"/Applications/${EMACSNAME}.app/Contents/MacOS/${EMACSNAME}"}
    export EMACSCLIENT=${EMACSCLIENT:-"${EMACSAPP}/Contents/MacOS/bin/emacsclient"}

    alias emacs_="${EMACS}"
    
    function emacs {
        "${EMACSCLIENT}" -a ${EMACS} --quiet --no-wait "$@" & disown
    }
    export emacs
fi

