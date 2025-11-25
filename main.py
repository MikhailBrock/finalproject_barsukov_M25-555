#!/usr/bin/env python3
"""Main entry point for ValutaTrade Hub"""

from valutatrade_hub.cli.interface import CLIInterface

def main():
    cli = CLIInterface()
    cli.run()

if __name__ == "__main__":
    main()
