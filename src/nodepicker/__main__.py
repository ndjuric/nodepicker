#!/usr/bin/env python3

import subprocess
import sys
import os
import signal
try:
    import libtmux
except ImportError:
    libtmux = None

class NvmManager:
    def __init__(self):
        # Try to locate NVM_DIR; fall back to standard location
        self.nvm_dir = os.environ.get('NVM_DIR') or os.path.expanduser('~/.nvm')
        if not os.path.isdir(self.nvm_dir):
            print("Warning: Could not locate NVM directory. Ensure nvm is installed and NVM_DIR is set.", file=sys.stderr)

    def _run_nvm(self, nvm_subcommand):
        """Run an nvm subcommand (string) and return (stdout, stderr, returncode)."""
        command = f'source "{self.nvm_dir}/nvm.sh" >/dev/null 2>&1 && {nvm_subcommand}'
        result = subprocess.run(['bash', '-lc', command], capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode

    def get_installed_versions(self, *_):
        """Return a sorted list of installed Node.js versions (only truly installed ones).

        Strategy:
        1. Prefer directory scan of $NVM_DIR/versions/node/* (most reliable)
        2. Fallback to parsing `nvm ls --no-colors` if directory scan empty
        """
        versions_dir = os.path.join(self.nvm_dir, 'versions', 'node')
        candidates = []
        if os.path.isdir(versions_dir):
            try:
                for name in os.listdir(versions_dir):
                    full = os.path.join(versions_dir, name)
                    if not os.path.isdir(full):
                        continue
                    # names typically like v18.20.8 or v16.20.2
                    if name.startswith('v'):
                        ver_str = name[1:]
                    else:
                        ver_str = name
                    if all(part.isdigit() for part in ver_str.split('.')):
                        # ensure node binary exists
                        if os.path.isfile(os.path.join(full, 'bin', 'node')):
                            candidates.append(ver_str)
            except Exception as e:
                print(f"Warning: could not scan versions directory: {e}", file=sys.stderr)

        if not candidates:
            # Fallback to parsing nvm ls (may include non-installed but we try to filter)
            out, err, code = self._run_nvm('nvm ls --no-colors')
            if code == 0:
                for line in out.splitlines():
                    line = line.strip()
                    if not line or '->' in line and not line.startswith('v'):
                        # skip alias lines like 'default -> v18.20.0'
                        pass
                    # lines for installed versions usually start with optional arrow/asterisk then version
                    # Accept tokens that are standalone like vX.Y.Z at line start
                    if line.startswith('v') and all(c.isdigit() or c == '.' for c in line[1:].split()[0]):
                        token = line.split()[0]
                        ver = token[1:]
                        if all(part.isdigit() for part in ver.split('.')):
                            candidates.append(ver)
            else:
                if err:
                    print(err.strip(), file=sys.stderr)

        # Deduplicate & version sort
        def vers_key(v):
            try:
                return tuple(int(x) for x in v.split('.'))
            except ValueError:
                return (0,)
        return sorted(set(candidates), key=vers_key)

    def set_node_version(self, version, default=False):
        if default:
            # Set default alias and immediately switch current shell via 'nvm use default'
            return [f"nvm alias default {version}", "nvm use default"]
        # Session only
        return [f"nvm use {version}"]

class TmuxManager:
    def __init__(self):
        self.is_tmux = 'TMUX' in os.environ
        if not self.is_tmux:
            print("This script must be run inside a tmux session.", file=sys.stderr)
            sys.exit(1)
        if libtmux is None:
            print("Missing 'libtmux' module. Please install it with 'pip install libtmux'.", file=sys.stderr)
            sys.exit(1)
        self.server = libtmux.Server()
        self.session = self._get_current_session()
        self.pane = self._get_current_pane()

    def _get_current_session(self):
        sessions = self.server.list_sessions()
        if not sessions:
            print("No tmux sessions found.", file=sys.stderr)
            sys.exit(1)
        tmux_env = os.environ.get('TMUX')
        for session in sessions:
            for window in session.windows:
                for pane in window.panes:
                    if pane.get('pane_id') in tmux_env:
                        return session
        return sessions[0]

    def _get_current_pane(self):
        pane_id = os.environ.get('TMUX_PANE')
        if pane_id:
            for window in self.session.windows:
                for pane in window.panes:
                    if pane.get('pane_id') == pane_id:
                        return pane
        return self.session.attached_window.attached_pane

    def send_command(self, command, enter=True):
        """Send a command to the active pane.

        enter=False will leave the command typed but not executed so the user can review/modify and press Enter manually.
        """
        try:
            self.pane.send_keys(command, enter=enter)
        except TypeError:
            # Older libtmux versions may not support enter kwarg
            if enter:
                self.pane.send_keys(command)
                try:
                    self.pane.enter()
                except Exception:
                    pass
            else:
                # Just type without executing
                self.pane.send_keys(command)

class SignalHandler:
    def __init__(self):
        signal.signal(signal.SIGINT, self.handle_sigint)

    def handle_sigint(self, signum, frame):
        print("\nGraceful shutdown. Bye!")
        sys.exit(0)

class Cli:
    def __init__(self, nvm_manager, tmux_manager):
        self.nvm_manager = nvm_manager
        self.tmux_manager = tmux_manager

    def main_menu(self):
        while True:
            print("\nSelect an action:")
            print("1. Change Node version for current session")
            print("2. Change default Node version")
            print("q. Quit")
            choice = input("Enter your choice: ")
            
            if choice == '1':
                self.handle_version_selection(default=False)
                break
            
            if choice == '2':
                self.handle_version_selection(default=True)
                break
            
            if choice.lower() == 'q':
                print("Exiting.")
                sys.exit(0)
            
            print("Invalid choice. Please enter '1', '2', or 'q'.")

    def handle_version_selection(self, default):
        versions = self.nvm_manager.get_installed_versions()
        if not versions:
            print("No Node.js versions detected. Install one with 'nvm install <version>'.", file=sys.stderr)
            return
        print("\nInstalled Node.js versions:")
        for idx, v in enumerate(versions, 1):
            print(f"{idx}. {v}")
        chosen = self.prompt_for_version(versions)
        if chosen not in versions:
            print(f"Selected version '{chosen}' not among installed versions.", file=sys.stderr)
            return
        commands = self.nvm_manager.set_node_version(chosen, default=default)
        if default:
            print(f"Setting default Node.js version to {chosen} and applying now...")
        else:
            print(f"Switching Node.js version for this session to {chosen}...")
        for cmd in commands:
            self.tmux_manager.send_command(cmd)
        if default:
            print("Default updated.")
        else:
            print("Session updated.")

    def prompt_for_version(self, versions):
        while True:
            try:
                choice = input("Enter the number of the version you want to use (or 'q' to quit): ")
                if choice.lower() == 'q':
                    print("Exiting.")
                    sys.exit(0)
                
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(versions):
                    return versions[choice_index]
                
                print("Invalid choice. Please enter a number from the list.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

class App:
    def __init__(self):
        self.signal_handler = SignalHandler()
        print("--- NVM Node Version Picker ---")
        self.nvm_manager = NvmManager()
        self.tmux_manager = TmuxManager()
        self.cli = Cli(self.nvm_manager, self.tmux_manager)

    def run(self):
        self.cli.main_menu()

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
