export PS1="\h:\W \u\$ "
source $(conda info --base)/etc/profile.d/conda.sh
conda deactivate
conda activate envs/super_hydro
alias ap="anaconda-project"
alias apr="anaconda-project run"