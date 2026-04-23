# Set TCL variables passed as arguments
# old environment env var
old_env_var_name="$1"
# setup-env script
setup_env_script="$2"
# python path used by spack
spack_python="$3"
# spack root
spack_root="$4"

# Create a name reference variable, so we can use the reference to dynamically set/update the variable
declare -n old_env_var_reference="$old_env_var_name"

# Set regex for bash functions in the environment printout
function_regex='^BASH_FUNC_(.+)%%=\(\) (.*)'

# ==============================================================================
# Capture the environment and aliases before sourcing the setup-env script
# ==============================================================================
# Functions and variables
declare -A before_functions
declare -A before_variables
while IFS= read -r -d '' entry; do
    if [[ "$entry" =~ $function_regex ]]; then
        # Set function
        name="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        before_functions["$name"]="$value"
    else
        # Set variable
        name="${entry%%=*}"
        value="${entry#*=}"
        before_variables["$name"]="$value"
    fi
done < <(env -0)
#Aliases
declare -A before_aliases
while IFS= read -r entry; do
    entry="${entry#alias }"
    name="${entry%%=*}"
    value="${entry#*=}"
    before_aliases["$name"]="$value"
done < <(alias -p)

# ==============================================================================
# Source the setup-env script
# ==============================================================================
# Set up SPACK_PYTHON
export SPACK_PYTHON="$spack_python"
# Set up SPACK_ROOT
export SPACK_ROOT="$spack_root"
source "$setup_env_script" > /dev/null

# ==============================================================================
# Capture the environment and aliases after sourcing the setup-env script
# ==============================================================================
# Functions and variables
declare -A after_functions
declare -A after_variables
while IFS= read -r -d '' entry; do
    if [[ "$entry" =~ $function_regex ]]; then
        # Set function
        name="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        after_functions["$name"]="$value"
    else
        # Set variable
        name="${entry%%=*}"
        value="${entry#*=}"
        after_variables["$name"]="$value"
    fi
done < <(env -0)
# Aliases
declare -A after_aliases
while IFS= read -r entry; do
    entry="${entry#alias }"
    name="${entry%%=*}"
    value="${entry#*=}"
    after_aliases["$name"]="$value"
done < <(alias -p)

# ==============================================================================
# Parse before and after variables, functions and aliases to find addition, changes and removals
# ==============================================================================
# FUNCTIONS
# Added and changed
for name in "${!after_functions[@]}"; do
    value="${after_functions[$name]}"
    if [[ ! -v before_functions["$name"] ]]; then 
        # Added function: print command for it to be exported and record the command for it to be unset
        printf '%s ; ' "${name}() $value ; export -f $name"
        old_env_var_reference+=$(printf '%s ;' "unset -f $name")
    elif [[ "${before_functions[$name]}" != "$value" ]]; then
        # Changed function: print command for it to be exported and record command for it to be reinstated
        printf '%s ; ' "${name}() $value ; export -f $name"
        old_value="${before_functions["$name"]}"
        old_env_var_reference+=$(printf '%s ; ' "${name}() $old_value ; export -f $name")
    fi
done
# Removed
for name in "${!before_functions[@]}"; do
    if [[ ! -v after_functions["$name"] ]]; then
        # Removed function: record command for it to be reinstated
        old_value="${before_functions[$name]}"
        old_env_var_reference+=$(printf '%s ; ' "${name}() $old_value ; export -f $name")
    fi
done
# VARIABLES
# Added and changed
for name in "${!after_variables[@]}"; do
    value="${after_variables[$name]}"
    if [[ ! -v before_variables["$name"] ]]; then 
        # Added variable: print command for it to be exported and record the command for it to be unset
        printf '%s ; ' "export $name=$value"
        old_env_var_reference+=$(printf '%s ; ' "unset $name")
    elif [[ "${before_variables[$name]}" != "$value" ]]; then
        # Changed variable: print command for it to be exported and record command for it to be reinstated
        printf '%s ; ' "export $name=$value"
        old_value="${before_variables["$name"]}"
        old_env_var_reference+=$(printf '%s ; ' "export $name=$old_value")
    fi
done
# Removed
for name in "${!before_variables[@]}"; do
    if [[ ! -v after_variables["$name"] ]]; then
        # Removed variable: record command for it to be reinstated
        old_value="${before_variables["$name"]}"
        old_env_var_reference+=$(printf '%s ; ' "export $name=$old_value")
    fi
done
# ALIASES
# Added and changed
for name in "${!after_aliases[@]}"; do
    value="${after_aliases[$name]}"
    if [[ ! -v before_aliases["$name"] ]]; then 
        # Added aliase: print command for it to be set and record the command for it to be unset
        printf '%s ; ' "alias $name=$value"
        old_env_var_reference+=$(printf '%s ; ' "unalias $name")
    elif [[ "${before_aliases[$name]}" != "$value" ]]; then
        # Changed aliase: print command for it to be set and record command for it to be reinstated
        printf '%s ; ' "alias $name=$value"
        old_value="${before_aliases["$name"]}"
        old_env_var_reference+=$(printf '%s ; ' "alias $name=$old_value")
    fi
done
# Removed
for name in "${!before_aliases[@]}"; do
    if [[ ! -v after_aliases["$name"] ]]; then
        # Removed aliase: record command for it to be unset
        old_value="${before_aliases["$name"]}"
        old_env_var_reference+=$(printf '%s ; ' "unalias $name")
    fi
done

# Print a null character as a separator, to help splitting the commands to set the new environment
# from those to reinstate the old environment
printf '\x00'
# Print the commands to reinstate the old environment
echo "${!old_env_var_name}"