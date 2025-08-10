# Define phony targets to prevent issues if a file named 'clean' or 'install-deps' exists
.PHONY: find-native all clean quick install-deps

find-native:
	@find node_modules -type f -name "*.node" 2>/dev/null | grep -v "obj\.target"

built.npm: package.json
	@echo "Installing npm dependencies..."
	npm install
	touch built.npm

built.electron: package.json built.npm
	@npm run electron-rebuild
	touch built.electron

BUILD_STUBS=python ./scripts/build-stubs.py

built.cpRepo: 
	$(BUILD_STUBS) cloneRepo
	touch built.cpRepo

#circuitpython/setup.py-stubs: circuitpython/setup.py-stubs#
#	@./scripts/build-stubs.py cloneRepo

built.venv: built.cpRepo circuitpython/setup.py-stubs
	$(BUILD_STUBS) setupVenv
	touch built.venv



built.cpStubs: built.venv
	$(BUILD_STUBS) makeStubs
	touch built.cpStubs

built.stubs: built.cpStubs circuitpython/circuitpython-stubs/setup.py
	@echo "Copying stubs..."
	@$(BUILD_STUBS) copyStubs
	touch built.stubs


built.boards: built.stubs stubs/setup.py
	@echo "Building stubs..."
	@$(BUILD_STUBS) makeBoards
	touch built.boards
# boards/metadata.json

vsix: built.boards
	@echo "Packaging VS Code extension..."
	@npx @vscode/vsce package



all: vsix # built.npm built.electron built.cpRepo built.venv built.cpStubs built.stubs built.boards
	@echo "All build steps complete."

# Main target to build everything for release
oldall: install-deps
	@echo "Running electron-rebuild..."
	@npm run electron-rebuild
	@echo "Building stubs..."
	@./scripts/build-stubs.py
	@echo "Packaging VS Code extension..."
	@npx @vscode/vsce package
	@echo "All build steps complete."

# Quick package target for faster iteration
quick: install-deps
	@echo "Packaging VS Code extension quickly..."
	@npx @vscode/vsce package
	@echo "Quick package complete."

# Target to clean up node_modules and package-lock.json
clean:
	@echo "Cleaning node_modules and package-lock.json..."
	rm built.*
	rm -rf node_modules
	rm -f package-lock.json
	@echo "Clean complete."


full-clean: clean
	rm -rf circuitpython
	rm -rf boards
	rm -rf stubs

# Optional: A target to clean and then reinstall dependencies
# This is often useful after a 'clean' to get a fresh start
install-deps: clean
	@echo "Installing npm dependencies..."
	npm install
	@echo "Dependency installation complete."


	default: all