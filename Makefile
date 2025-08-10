# Define phony targets to prevent issues if a file named 'clean' or 'install-deps' exists
.PHONY: find-native all clean quick install-deps

find-native:
	@find node_modules -type f -name "*.node" 2>/dev/null | grep -v "obj\.target"

built/npm.built: packages.json
	@echo "Installing npm dependencies..."
	npm install

built/electron.built: packages.json built/npm.built
	@npm run electron-rebuild
	touch built/electron.built



circuitpython/setup.py-stubs:
	@./scripts/build-stubs.py cloneRepo

circuitpython/.venv: circuitpython/setup.py-stubs:
	@echo "Building stubs..."
	@./scripts/build-stubs.py setupVenv

circuitpython/circuitpython-stubs/setup.py: circuitpython/.venv
	@echo "Building stubs..."
	@./scripts/build-stubs.py makeStubs

stubs/setup.py: circuitpython/circuitpython-stubs/setup.py
	@echo "Copying stubs..."
	@./scripts/build-stubs.py copyStubs


boards/metadata.json: stubs/setup.py
	@echo "Building stubs..."
	@./scripts/build-stubs.py makeBoards

	


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
	rm -rf node_modules
	rm -f package-lock.json
	@echo "Clean complete."

# Optional: A target to clean and then reinstall dependencies
# This is often useful after a 'clean' to get a fresh start
install-deps: clean
	@echo "Installing npm dependencies..."
	npm install
	@echo "Dependency installation complete."