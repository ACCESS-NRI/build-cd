The modulerc file was created to address this issue:

https://github.com/ACCESS-NRI/ACCESS-OM2/issues/48

It is not automatically deployed, but placed in `/g/data/vk83/modules/access-models/.modulerc`. Because it affects the access to all deployed models the code was placed here for visibility.

This allows `module use` a single directory, and automatically load all spack generated module files which are in spack version and build architecture specific sub-directories:

```
$ module use /g/data/vk83/modules/access-models/
$ module avail access
----------------- /g/data/vk83/modules/access-models ---------------------
access-om2-bgc/2024.03.0  access-om2/2023.11.23  access-om2/2024.03.0  
``
