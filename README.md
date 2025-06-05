# pico2wcaptiveportal
Pico 2W access point with a captive portal. Uses WPA3 by default. Written in MicroPython.

# Usage
1. Flash the Pico 2W with the correct MicroPython uf2 file downloaded from [here](https://micropython.org/download/RPI_PICO2_W).
2. Clone this repository locally, copy the public folder (including its content) to the Pico 2W, and run the `main.py` file or copy that as well onto the Pico 2W to run it automatically on boot (it must be named `main.py` in order to run by default).

# Config
Default SSID: `Pico2W`<br>
Default key: `captiveportal`

# Files
* `main.py` is the program which spins up an access point and runs the networking loop
* in the `public` folder, you put static HTML, CSS and JS which get sent to the client accessing the captive portal

# MicroPython stubs (typings)
Get the typings folder from [here](https://flatgithub.com/Josverl/micropython-stubs/?filename=all_modules.json&filters=port%3Drp2%26board%3Drpi_pico2_w) with:<br>
`python -m venv .venv` to create a venv (optional, but recommended)<br>
`pip install -U micropython-rp2-rpi_pico2_w-stubs --target typings --no-user` (if you want them installed globally, remove target and no-user flags)
> But wait, what's the typings folder for?

It adds MicroPython stubs for the Pico 2W, aka you will have autocompletion to help you modify the code. The .vscode/settings.json is relevant if you're using VS Code:
```json
"python.analysis.typeshedPaths": [
    "typings"
],
"python.analysis.extraPaths": [
    "typings"
]
```
If you're using another IDE, you should add the path to your linter/language server's (e.g. Pylance) config in order to benefit from these (if you don't have MicroPython stubs already setup).<br>
More about this: [Introduction to MicroPython Stubs](https://micropython-stubs.readthedocs.io/en/main/10_introduction.html) and [MicroPython Stubs repo](https://github.com/Josverl/micropython-stubs)
