#!/bin/bash
# Script to run Gmail integration tests
# This script assumes you have activated your virtual environment

set -e  # Exit on error

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config file location (default if not specified)
CONFIG_FILE="config.yaml"
VERBOSE="-v"
MARKERS="integration and gmail"
TEST_FILES="tests/test_gmail_integration.py"

# Parse command line arguments
while getopts "c:m:f:vq" opt; do
  case ${opt} in
    c )
      CONFIG_FILE=$OPTARG
      ;;
    m )
      MARKERS=$OPTARG
      ;;
    f )
      TEST_FILES=$OPTARG
      ;;
    v )
      VERBOSE="-vv"
      ;;
    q )
      VERBOSE=""
      ;;
    \? )
      echo "Usage: $0 [-c config_file] [-m markers] [-f test_files] [-v verbose] [-q quiet]"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}      Gmail Integration Tests Runner                 ${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo ""

# Check if the config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo -e "${RED}Config file not found: $CONFIG_FILE${NC}"
  echo -e "${YELLOW}Please create a config file or specify with -c option${NC}"
  exit 1
fi

# Extract OAuth2 info from config.yaml
# Note: This is a simple approach and doesn't handle all YAML formats
echo -e "${BLUE}Checking configuration in $CONFIG_FILE...${NC}"
if ! grep -q "oauth2:" "$CONFIG_FILE"; then
  echo -e "${RED}OAuth2 configuration not found in $CONFIG_FILE${NC}"
  echo -e "${YELLOW}Please ensure your config file contains OAuth2 credentials${NC}"
  exit 1
fi

# Create a temporary .env file if it doesn't exist
if [ ! -f ".env.test" ]; then
  echo -e "${YELLOW}Creating temporary .env.test file for testing${NC}"
  
  # Extract values from config.yaml
  CLIENT_ID=$(grep -A 10 "oauth2:" "$CONFIG_FILE" | grep "client_id:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
  CLIENT_SECRET=$(grep -A 10 "oauth2:" "$CONFIG_FILE" | grep "client_secret:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
  REFRESH_TOKEN=$(grep -A 10 "oauth2:" "$CONFIG_FILE" | grep "refresh_token:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
  TEST_EMAIL=$(grep -A 20 "oauth2:" "$CONFIG_FILE" | grep "username:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'" || echo "eye.map.em.see.p@gmail.com")
  
  if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$REFRESH_TOKEN" ]; then
    echo -e "${RED}Failed to extract OAuth2 credentials from config file${NC}"
    exit 1
  fi
  
  # Create .env.test with credentials
  cat > .env.test << EOF
# Gmail OAuth2 credentials for integration tests
GMAIL_CLIENT_ID=$CLIENT_ID
GMAIL_CLIENT_SECRET=$CLIENT_SECRET
GMAIL_REFRESH_TOKEN=$REFRESH_TOKEN
GMAIL_TEST_EMAIL=$TEST_EMAIL
EOF
  
  echo -e "${GREEN}Created .env.test with OAuth2 credentials${NC}"
fi

# Load environment variables from .env.test
echo -e "${BLUE}Loading environment variables for testing...${NC}"
if [ -f ".env.test" ]; then
  export $(grep -v '^#' .env.test | xargs)
  echo -e "${GREEN}Environment variables loaded successfully${NC}"
else
  echo -e "${RED}Error: .env.test file not found${NC}"
  exit 1
fi

# Run the tests
echo -e "${BLUE}Running integration tests...${NC}"
echo -e "${YELLOW}Using markers: ${MARKERS}${NC}"
echo -e "${YELLOW}Test files: ${TEST_FILES}${NC}"
echo ""

uv run python -m pytest -m "$MARKERS" $TEST_FILES $VERBOSE --no-header

TEST_EXIT_CODE=$?

# Cleanup
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}====================================================${NC}"
  echo -e "${GREEN}  Integration tests completed successfully!         ${NC}"
  echo -e "${GREEN}====================================================${NC}"
else
  echo -e "${RED}====================================================${NC}"
  echo -e "${RED}  Integration tests failed with exit code $TEST_EXIT_CODE ${NC}"
  echo -e "${RED}====================================================${NC}"
fi

echo ""
echo -e "${BLUE}Test run complete.${NC}"
echo ""

exit $TEST_EXIT_CODE
