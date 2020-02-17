"""Entry point to TGVmax destinations map UI."""

import sys

from user_interface import LoadingUi, MainUi

if __name__ == "__main__":
    try:
        loading_ui = LoadingUi()
        loading_ui.launch()
        main_ui = MainUi()
        main_ui.configure()
        main_ui.pack()
        main_ui.run()
    except KeyboardInterrupt:
        print("Keyboard interrupt, exiting...")
        sys.exit(1)
