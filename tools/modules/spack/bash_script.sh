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

# Capture the environment before sourcing the setup-env script
# and parse variables and functions into bash associative arrays
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

# Set up SPACK_PYTHON
export SPACK_PYTHON="$spack_python"
# Set up SPACK_ROOT
export SPACK_ROOT="$spack_root"
# Source the setup-env script
source "$setup_env_script" > /dev/null

# Capture the environment after sourcing the setup-env script
# and parse it to find changes
while IFS= read -r -d '' entry; do
    if [[ "$entry" =~ $function_regex ]]; then
        # Function
        name="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        if [[ ! -v before_functions["$name"] ]]; then 
            # If the function got added, print out the bash command for it to be exported
            # and add to the old_env_var_name the bash command for it to be unset
            printf '%s ; ' "${name}() $value ; export -f $name"
            old_env_var_reference+=$(printf '%s ;' "unset -f $name")
        elif [[ "${before_functions[$name]}" != "$value" ]]; then
            # If the function got changed, print out the bash command for it to be exported
            # and add to the old_env_var_name the bash command for it to be set to its old value
            printf '%s ; ' "${name}() $value ; export -f $name"
            old_value="${before_functions["$name"]}"
            old_env_var_reference+=$(printf '%s ; ' "${name}() $old_value ; export -f $name")
        fi
    else
        # Variable
        name="${entry%%=*}"
        value="${entry#*=}"
        if [[ ! -v before_variables["$name"] ]]; then
            # If the variable got added, print out the bash command for it to be exported
            # and add to the old_env_var_name the bash command for it to be unset
            printf '%s ; ' "export $name=$value"
            old_env_var_reference+=$(printf '%s ; ' "unset $name")
        elif [[ "${before_variables[$name]}" != "$value" ]]; then
            # If the variable got changed, print out the bash command for it to be exported
            # and add to the old_env_var_name the bash command for it to be set to its old value
            printf '%s ; ' "export $name=$value"
            old_value="${before_variables["$name"]}"
            old_env_var_reference+=$(printf '%s ; ' "export $name=$old_value")
        fi
    fi
done < <(env -0)
# Print a null character as a separator, to help splitting the commands to set the new environment
# from those to reinstate the old environment
printf '\x00'
# Print the commands to reinstate the old environment
echo "${!old_env_var_name}"