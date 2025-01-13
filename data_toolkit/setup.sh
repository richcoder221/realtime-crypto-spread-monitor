#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Python virtual environment...${NC}"

# Check if python3-venv is installed
if ! dpkg -l | grep -q python3-venv; then
    echo -e "${RED}python3-venv not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3-venv
fi

# Create virtual environment if it doesn't exist
VENV_PATH="./venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv $VENV_PATH
fi

# Install pip if not present
if ! command -v pip &> /dev/null; then
    echo -e "${RED}pip not found. Installing pip...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# Activate virtual environment and install dependencies
echo -e "${GREEN}Activating virtual environment and installing dependencies...${NC}"
source $VENV_PATH/bin/activate
pip install -r requirements.txt

echo -e "${GREEN}All dependencies installed successfully!${NC}"

# Create activation script
echo -e "${GREEN}Creating activation shortcut...${NC}"
ACTIVATE_SCRIPT="activate_venv.sh"
echo "#!/bin/bash" > $ACTIVATE_SCRIPT
echo "source $VENV_PATH/bin/activate" >> $ACTIVATE_SCRIPT
chmod +x $ACTIVATE_SCRIPT

echo -e "${GREEN}Setup complete! Virtual environment is now active.${NC}"
echo -e "${GREEN}To activate the virtual environment in new terminals, run:${NC}"
echo -e "${GREEN}source ./activate_venv.sh${NC}"

# Activate the virtual environment in the current shell
source ./activate_venv.sh