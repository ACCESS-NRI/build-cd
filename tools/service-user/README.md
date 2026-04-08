# Service User Setup Scripts

## Overview

This folder contains scripts that can be used to set up a service user on a HPC platform, ready to administer Pre/Release instances of spack via [a custom site scope defined here](https://github.com/ACCESS-NRI/spack-config/blob/main/v1.1/include/defaults.yaml).

## Scripts

### Setup

Exports the `ACCESS_SPACK_ADMIN` environment variable to the service users `~/.bashrc`, which is used to enable admin-specific install trees and configuration.
