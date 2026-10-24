    # SigmaOS-file-manager-system

    File manager (nemo-style, tabs, extensions)

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/nemo
- https://github.com/omacom/omafind

    ## Design principles applied
    - **Least Astonishment**
- **Defensive Programming**
- **Fail-Fast**
- **KISS**
- **Separation of Concerns**
- **Deterministic Testing**

    ## Usage
    Verbs: `list, search, tabs-plan, actions, trash-plan`

    ```
    $ sigma-files list ~/Documents
$ sigma-files search ~/Documents --pattern "*.md" --max-depth 3
$ sigma-files tabs-plan ~/Documents ~/Downloads
$ sigma-files actions report.pdf
$ sigma-files trash-plan ~/Documents --name old.txt --name draft.md

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
