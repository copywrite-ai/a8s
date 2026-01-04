#!/bin/bash

# =================================================================
# Quick Deploy Wrapper for Ansible
# Usage: ./deploy.sh [app_name1] [app_name2] [--force]
# =================================================================

PLAYBOOK="deploy.yml"
FORCE_RECREATE="false"
APPS=()

# Parse Arguments
for arg in "$@"; do
    case $arg in
        --force-recreate|--force|-f)
            FORCE_RECREATE="true"
            shift
            ;;
        *)
            APPS+=("$arg")
            shift
            ;;
    esac
done

# Construct Extra Vars
EXTRA_VARS=""

# 1. Handle force-recreate
if [ "$FORCE_RECREATE" == "true" ]; then
    EXTRA_VARS="$EXTRA_VARS -e force_recreate=true"
fi

# 2. Handle specific apps
if [ ${#APPS[@]} -gt 0 ]; then
    # Join array with comma
    APP_LIST=$(IFS=,; echo "${APPS[*]}")
    EXTRA_VARS="$EXTRA_VARS -e only_apps=$APP_LIST"
fi

# RUN
echo -e "\033[1;34m[Deployer]\033[0m Executing Ansible Playbook..."
echo -e "\033[1;30mCommand: ansible-playbook $PLAYBOOK $EXTRA_VARS\033[0m\n"

ansible-playbook "$PLAYBOOK" $EXTRA_VARS
