# AWS Web UI Automation Tests

This repository contains a test automation framework designed to test AWS infrastructure via the AWS Management Console using **Python**, **Playwright**, and **Pytest**. 

It uses the Page Object Model (POM) design pattern to navigate through various AWS services such as CloudFormation, EC2, S3, Lambda, SNS, and SQS.

## Project Structure

Here is a quick overview of what is inside the repository:

- **`pages/`**: Contains the Page Object classes. Each file corresponds to an AWS service or page in the console (e.g., `login_page.py`, `cfn_page.py`, `ec2_page.py`, etc.).
- **`tests/`**: Contains the actual Pytest test scripts (e.g., `test_cfn_stack.py`, `test_sns_sqs_flow.py`).
- **`conftest.py`**: Shared Pytest fixtures that manage the Playwright browser lifecycle (setup, teardown) and instantiate the Page Objects.
- **`config.py`**: Global configuration variables (like `REGION`, `STACK_NAME`, and file paths) used across the project.
- **`pytest.ini`**: Pytest configuration file.
- **`requirements.txt`**: List of Python dependencies required to run the project.
- **`*.yaml` templates** (`template.yaml`, `sns_sqs_template.yaml`): AWS CloudFormation templates used during the tests to spin up infrastructure.
- **`.env`**: Environment file containing the AWS login credentials and sign-in URL used by the automation script.

## Prerequisites

Ensure you have Python (3.7+) installed on your machine.

## Setup Instructions

1. **Install Dependencies**
   Navigate to the root directory of the project in your terminal and install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright Browsers**
   Playwright needs to download its own browser binaries to run the web automation:
   ```bash
   playwright install
   ```

3. **Configure AWS Credentials**
   Create a `.env` file in the root directory and add the following variables:
   ```env
   AWS_SIGN_IN_URL=https://<your-account-alias-or-id>.signin.aws.amazon.com/console
   AWS_USERNAME=your-iam-username
   AWS_PASSWORD=your-iam-password
   ```
   *(Note: Ensure this `.env` file is added to your `.gitignore` so you do not accidentally push sensitive credentials to GitHub!)*

## Running the Tests

To run the entire test suite, simply use the `pytest` command from the root directory:

```bash
pytest
```

To run a specific test file:
```bash
pytest tests/test_cfn_stack.py
```

### Generating Allure Reports

The project is configured to use `allure-pytest` for test reporting. 

To generate and view the report:
1. Run the tests and save the results to a directory:
   ```bash
   pytest --alluredir=allure-results
   ```
2. Serve the report using the Allure command-line tool:
   ```bash
   allure serve allure-results
   ```
   *(Note: You must have the [Allure CLI](https://allurereport.org/docs/install/) installed on your system to serve the report).*
