#!/bin/bash

# AWS Ops Installation Script
# Simple setup for aws-ops development environment

set -e

# Simple colored output
info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
    exit 1
}

# Basic checks
[[ ! -f "pyproject.toml" ]] && error "Run this script from the project root directory"
command -v python3 >/dev/null || error "python3 not found"
command -v pip3 >/dev/null || error "pip3 not found"

info "Installing aws-ops package..."

# Create and activate virtual environment if not in one
if [[ -z "$VIRTUAL_ENV" ]]; then
    info "Creating virtual environment..."
    python3 -m venv venv
    info "Activating virtual environment..."
    source venv/bin/activate
    # Verify activation worked
    if [[ -z "$VIRTUAL_ENV" ]]; then
        error "Failed to activate virtual environment"
    fi
    info "Virtual environment activated: $VIRTUAL_ENV"
else
    info "Using existing virtual environment: $VIRTUAL_ENV"
fi

# Install package using python3 -m pip to avoid interpreter issues
info "Upgrading pip..."
python3 -m pip install --upgrade pip -q
info "Installing aws-ops package..."
python3 -m pip install -e .

# Optional dev dependencies
read -p "Install dev dependencies? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "Installing development dependencies..."
    python3 -m pip install -e ".[dev]"
fi

# Simple verification
info "Verifying installation..."
python3 -m pip show aws-ops >/dev/null || error "Installation failed"

success "Installation completed!"
echo
info "Usage: aws-ops --help"
if [[ -n "$VIRTUAL_ENV" ]]; then
    info "Virtual environment: $VIRTUAL_ENV"
fi
