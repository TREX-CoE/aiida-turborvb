# AiiDA TurboRVB plugin

This is AiiDA plugin for [TurboRVB] Quantum Monte Carlo code developed at SISSA Trieste.

The plugin consists of three families of CalcJobs, distinguishable by suffixes:

 - **WRP** Turbo-Genius wrapper
 - **INT** Using Turbo-Genius API
 - **SA** Standalone version

Different parts of the calculation can be done by CalcJobs from an arbitrary family. In other words, they are interchangeable.

## Wrapper CalcJobs (WRP)

TurboRVB is not a single executable, it consists of several dozens of binaries providing preparation calculation and post-processing of different parts of QMC calculation. Therefore there is a native manipulation framework called Turbo-Genius[paper in preparation] easing this process. This family of CalcJobs are executing native command-line instructions in a shell in principle one submit script can execute several TurboRVB executables. The normal workflow with turbogenius follows as this:

 - Prepare input files with `turbo-genius -j <job_name> -g <other_options>`
   where job name is type of job
 - Edit input files if necessary
 - Run QMC code
 - Postprocess with `turbo-genius -j <job_name> -post <other_options>`
   where job name has to be the same as previous.

One can setup the `other options` by passing parameters `Dict` with key value pairs, also if input namelist has to be updated (step 2), one can pass a dictonary with updated values under key `namelist_update`. Parameters for VMC optimization can look like this:

```python
parameters = { "optmethod"       : "lin",
               "eq"              : 100,
               "update_namelist" : { "nw"      : 100,
                                     "ngen"    : 50000,
                                     "nweight" : 250 }
```



### How to setup WRP code

In order to run this family of CalcJobs, one has to prepare AiiDA code that puts install binary directory into path variable such as:

```yaml
---
label: "prepwrp"
description: "prep wrapper"
input_plugin: "turborvb.prepwrp"
on_computer: true
remote_abs_path: "/usr/bin/bash"
computer: "Z15G3"
prepend_text: |
  # Activate python environment with Turbo-Genius
  source /home/user/Robota/ENVs/turboblank/bin/activate
  # Source modules
  source /home/user/Software/TurboRVB-production/gcc/sourceme
  # Append to PATH variable
  export PATH=/home/user/Software/TurboRVB-production/gcc/bin/:$PATH
append_text: " "

```


## Stand alone CalcJobs (SA)

Turbo-Genius, however, so far does not provide full flexibility of inputs and output therefore another family of CalcJobs was made that does not rely on Turbo-Genius at all. Only a few of CalcJobs are present in this family.

### How to setup WRP code

```yaml
---
label: "makefort10sa"
description: "makefort10 wrapper"
input_plugin: "turborvb.makefort10sa"
on_computer: true
remote_abs_path: "/absolute/path/to/turborvb/binary/directory/makefort10.x"
computer: "Z15G3"
prepend_text: |
  source /home/user/Robota/ENVs/turboblank/bin/activate
  source /home/user/Software/TurboRVB-production/gcc/sourceme
  export PATH=/home/user/Software/TurboRVB-production/gcc/bin/:$PATH
append_text: " "
```

## Integrated, Calcjobs using Turbo-Genius API (INT)

The ultimate goal is to change to use CalcJobs which uses Turbo-Genius API. However, Turbo-Genius is an older framework than this plugin and API is currently being prepared. For the time being one can use CalcJobs from other families.

### How to setup WRP code

## List of CalcJobs in families

Name | WRP | INT | SA |
--- | --- | --- | ---  
Makefort10 | ✅ |  | ✅ |
Convertfort10mol | ✅ |  |  |
Assembling pseudo | ✅ |  | ✅ |
TurboDFT(prep) | ✅ |  |  |
VMC (opt) | ✅ |  |  |
VMC | ✅ |  |  |
DMC | ✅ |  |  |

[TurboRVB]: https://people.sissa.it/~sorella/TurboRVB_Manual/build/html/index.html
